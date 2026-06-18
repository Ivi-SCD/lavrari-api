"""Serviço de assinatura eletrônica auditável de RDOs."""

import logging
import uuid
from typing import Optional

from app.core.exceptions import AppError, AuthError, NotFoundError, PermissionDeniedError
from app.core.security import verificar_senha
from app.globals.enums.rdo.status_rdo import StatusRDO
from app.globals.models.assinatura.assinatura import Assinatura
from app.repositories.assinatura_repository import AssinaturaRepository
from app.repositories.rdo_repository import RDORepository
from app.repositories.rdo_versao_repository import RdoVersaoRepository
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

_STATUS_ASSINAVEIS = {StatusRDO.BLOQUEADO.value, StatusRDO.FINALIZADO.value}


class AssinaturaService:
    def __init__(self):
        self.repo = AssinaturaRepository()
        self.rdo_repo = RDORepository()
        self.versao_repo = RdoVersaoRepository()
        self.pdf_service = PDFService()

    async def assinar(
        self,
        id_rdo: str,
        usuario: dict,
        senha: str,
        papel: str,
        cargo: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> dict:
        rdo = await self.rdo_repo.buscar_por_id(id_rdo)
        if not rdo:
            raise NotFoundError("RDO não encontrado.")

        if not verificar_senha(senha, usuario["senha_hash"]):
            raise AuthError("Senha incorreta.")

        if rdo["status"] not in _STATUS_ASSINAVEIS:
            raise PermissionDeniedError(
                "O RDO precisa estar BLOQUEADO ou FINALIZADO para ser assinado."
            )

        if await self.repo.buscar_por_rdo_e_usuario(id_rdo, usuario["id_usuario"]):
            raise AppError("Usuário já assinou este RDO.")

        versao_atual = max(await self.versao_repo.proximo_numero_versao(id_rdo) - 1, 1)

        pdf_url, hash_doc = await self.pdf_service.gerar_e_armazenar(id_rdo)

        assinatura = Assinatura(
            id_assinatura=str(uuid.uuid4()),
            id_rdo=id_rdo,
            versao_rdo=versao_atual,
            id_usuario=usuario["id_usuario"],
            nome_completo=usuario["nome"],
            email=usuario["email"],
            cargo=cargo,
            papel=papel,
            hash_documento=hash_doc,
            ip_address=ip,
            pdf_url=pdf_url,
        )
        return await self.repo.criar(assinatura.model_dump())

    async def listar_por_rdo(self, id_rdo: str) -> list[dict]:
        return await self.repo.listar_por_rdo(id_rdo)
