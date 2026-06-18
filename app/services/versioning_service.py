"""Serviço de versionamento imutável de RDOs."""

import uuid
from typing import Optional

from app.globals.enums.rdo.acao_versao import AcaoVersao
from app.globals.models.rdo.rdo_versao import RdoVersao
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_versao_repository import RdoVersaoRepository
from app.repositories.usuario_repository import UsuarioRepository


class VersioningService:
    def __init__(self):
        self.repo = RdoVersaoRepository()
        self.obra_repo = ObraRepository()
        self.empresa_repo = EmpresaRepository()
        self.usuario_repo = UsuarioRepository()

    async def _montar_dados_obra(self, id_obra: str) -> dict:
        obra = await self.obra_repo.buscar_por_id(id_obra)
        if not obra:
            return {}
        contratada = await self.empresa_repo.buscar_por_id(obra["id_empresa_contratada"])
        fiscal_suape = await self.usuario_repo.buscar_por_id(obra["id_fiscal_suape"])
        fiscal_externo = None
        if obra.get("id_fiscal_externo"):
            fiscal_externo = await self.usuario_repo.buscar_por_id(obra["id_fiscal_externo"])
        return {
            "numero_contrato": obra.get("numero_contrato"),
            "objeto_contratual": obra.get("objeto_contratual"),
            "empresa_contratada": contratada.get("razao_social") if contratada else None,
            "fiscal_suape": fiscal_suape.get("nome") if fiscal_suape else None,
            "fiscal_externo": fiscal_externo.get("nome") if fiscal_externo else None,
        }

    async def criar_versao(
        self,
        rdo: dict,
        acao: AcaoVersao,
        usuario: dict,
        justificativa: Optional[str] = None,
    ) -> dict:
        snapshot = {k: v for k, v in rdo.items() if k != "_id"}
        snapshot["obra"] = await self._montar_dados_obra(rdo["id_obra"])

        versao = RdoVersao(
            id_versao=str(uuid.uuid4()),
            id_rdo=rdo["id_rdo"],
            versao=await self.repo.proximo_numero_versao(rdo["id_rdo"]),
            snapshot=snapshot,
            acao=acao,
            justificativa=justificativa,
            criado_por=usuario["id_usuario"],
            criado_por_nome=usuario["nome"],
        )
        return await self.repo.criar(versao.model_dump())

    async def listar_versoes(self, id_rdo: str) -> list[dict]:
        return await self.repo.listar_por_rdo(id_rdo)

    async def buscar_versao(self, id_rdo: str, versao: int):
        return await self.repo.buscar_versao(id_rdo, versao)
