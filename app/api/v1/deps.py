"""Dependencies de autenticação, autorização e injeção de serviços."""

from typing import Iterable, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import AuthError, PermissionDeniedError
from app.globals.enums.usuario.perfil_usuario import PerfilUsuario
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.alerta_service import AlertaService
from app.services.assinatura_service import AssinaturaService
from app.services.auth_service import AuthService
from app.services.comentario_service import ComentarioService
from app.services.empresa_service import EmpresaService
from app.services.ia import IAService
from app.services.midia_service import MidiaService
from app.services.obra_service import ObraService
from app.services.pdf_service import PDFService
from app.services.rdo_service import RDOService
from app.services.usuario_service import UsuarioService
from app.services.workflow_service import WorkflowService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/lavrari/api/v1/auth/login")


# ---- Service factories ----

def get_auth_service() -> AuthService:
    return AuthService()


def get_usuario_service() -> UsuarioService:
    return UsuarioService()


def get_empresa_service() -> EmpresaService:
    return EmpresaService()


def get_obra_service() -> ObraService:
    return ObraService()


def get_rdo_service() -> RDOService:
    return RDOService()


def get_workflow_service() -> WorkflowService:
    return WorkflowService()


def get_comentario_service() -> ComentarioService:
    return ComentarioService()


def get_midia_service() -> MidiaService:
    return MidiaService()


def get_alerta_service() -> AlertaService:
    return AlertaService()


def get_ia_service() -> IAService:
    return IAService()


def get_pdf_service() -> PDFService:
    return PDFService()


def get_assinatura_service() -> AssinaturaService:
    return AssinaturaService()


# ---- Autenticação ----

async def get_usuario_atual(token: str = Depends(oauth2_scheme)) -> dict:
    payload = AuthService().verificar_token(token)
    if payload.get("type") != "access":
        raise AuthError("Token de acesso inválido.")
    usuario = await UsuarioRepository().buscar_por_id(payload["sub"])
    if not usuario:
        raise AuthError("Usuário não encontrado.")
    return usuario


async def requer_admin(usuario_atual: dict = Depends(get_usuario_atual)) -> dict:
    if not usuario_atual.get("is_admin"):
        raise PermissionDeniedError("Ação restrita a administradores.")
    return usuario_atual


# ---- Autorização por obra (helpers chamados dentro dos endpoints) ----

async def requer_acesso_obra(id_obra: str, usuario_atual: dict) -> Optional[dict]:
    """Garante que o usuário é admin ou possui vínculo com a obra."""
    if usuario_atual.get("is_admin"):
        return None
    vinculo = await ObraUsuarioRepository().buscar_por_obra_e_usuario(
        id_obra, usuario_atual["id_usuario"]
    )
    if not vinculo:
        raise PermissionDeniedError("Sem acesso a esta obra.")
    return vinculo


async def requer_perfil_obra(
    id_obra: str, usuario_atual: dict, perfis: Iterable[PerfilUsuario]
) -> Optional[dict]:
    """Garante que o usuário é admin ou possui um dos perfis exigidos na obra."""
    if usuario_atual.get("is_admin"):
        return None
    vinculo = await ObraUsuarioRepository().buscar_por_obra_e_usuario(
        id_obra, usuario_atual["id_usuario"]
    )
    permitidos = {p.value for p in perfis}
    if not vinculo or vinculo["perfil"] not in permitidos:
        raise PermissionDeniedError("Perfil insuficiente para esta ação na obra.")
    return vinculo


async def requer_permissao_extra(id_obra: str, usuario_atual: dict, permissao: str) -> bool:
    """Verifica permissão temporária granular (respeitando expira_em)."""
    if usuario_atual.get("is_admin"):
        return True
    return await ObraUsuarioRepository().verificar_permissao_temporaria(
        id_obra, usuario_atual["id_usuario"], permissao
    )
