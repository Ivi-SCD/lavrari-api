"""Serviço de versionamento imutável de RDOs."""

import logging
import uuid
from typing import Optional

from app.globals.enums.rdo.acao_versao import AcaoVersao
from app.globals.models.rdo.rdo_versao import RdoVersao
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_versao_repository import RdoVersaoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Ações que congelam um documento oficial: cada uma gera um PDF imutável,
# armazenado no COS e referenciado na própria versão (rascunhos não congelam,
# pois ainda são mutáveis).
_ACOES_DOCUMENTO = {
    AcaoVersao.ENVIO_REVISAO,
    AcaoVersao.APROVACAO_EXTERNA,
    AcaoVersao.REPROVACAO_EXTERNA,
    AcaoVersao.APROVACAO_SUAPE,
    AcaoVersao.REPROVACAO_SUAPE,
    AcaoVersao.REABERTURA,
    AcaoVersao.FINALIZACAO,
}


class VersioningService:
    def __init__(self):
        self.repo = RdoVersaoRepository()
        self.obra_repo = ObraRepository()
        self.empresa_repo = EmpresaRepository()
        self.usuario_repo = UsuarioRepository()
        self.storage = StorageService()
        self._pdf_service = None

    def _pdf(self):
        # Lazy: evita instanciar PDFService (e IAService) quando não há geração de PDF.
        if self._pdf_service is None:
            from app.services.pdf_service import PDFService

            self._pdf_service = PDFService()
        return self._pdf_service

    async def _montar_dados_obra(self, id_obra: str) -> dict:
        obra = await self.obra_repo.buscar_por_id(id_obra)
        if not obra:
            return {}
        contratada = await self.empresa_repo.buscar_por_id(
            obra["id_empresa_contratada"]
        )
        fiscal_suape = await self.usuario_repo.buscar_por_id(obra["id_fiscal_suape"])
        fiscal_externo = None
        if obra.get("id_fiscal_externo"):
            fiscal_externo = await self.usuario_repo.buscar_por_id(
                obra["id_fiscal_externo"]
            )
        # Cabeçalho completo da obra congelado no momento da versão. Permite reproduzir
        # o documento exatamente como era — mesmo que a obra (responsáveis, ART, logos)
        # seja alterada depois.
        return {
            "id_obra": obra.get("id_obra"),
            "numero_contrato": obra.get("numero_contrato"),
            "objeto_contratual": obra.get("objeto_contratual"),
            "tipologia": obra.get("tipologia"),
            "local_descricao": obra.get("local_descricao"),
            "endereco": obra.get("endereco"),
            "prazo_contratual_dias": obra.get("prazo_contratual_dias"),
            "data_inicio_execucao": obra.get("data_inicio_execucao"),
            "empresa_contratada": (
                contratada.get("razao_social") if contratada else None
            ),
            "fiscal_suape": fiscal_suape.get("nome") if fiscal_suape else None,
            "art_fiscal_suape": obra.get("art_fiscal_suape"),
            "fiscal_externo": fiscal_externo.get("nome") if fiscal_externo else None,
            "art_fiscal_externo": obra.get("art_fiscal_externo"),
            "responsaveis": obra.get("responsaveis") or [],
            "logo_suape_url": obra.get("logo_suape_url"),
            "logo_contratada_url": obra.get("logo_contratada_url"),
            "logo_fiscalizacao_externa_url": obra.get("logo_fiscalizacao_externa_url"),
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

        numero_versao = await self.repo.proximo_numero_versao(rdo["id_rdo"])

        pdf_url, pdf_hash = None, None
        if acao in _ACOES_DOCUMENTO:
            # Congela o documento desta versão (PDF imutável a partir do snapshot).
            # Alterações posteriores na obra criam novas versões, sem sobrescrever esta.
            try:
                pdf_bytes, pdf_hash = await self._pdf().gerar_pdf_de_snapshot(snapshot)
                pdf_url, _ = await self.storage.upload_pdf_versao(
                    pdf_bytes, rdo["id_rdo"], numero_versao
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Falha ao congelar PDF da versão %s do RDO %s: %s",
                    numero_versao, rdo["id_rdo"], exc,
                )
                pdf_url, pdf_hash = None, None

        versao = RdoVersao(
            id_versao=str(uuid.uuid4()),
            id_rdo=rdo["id_rdo"],
            versao=numero_versao,
            snapshot=snapshot,
            acao=acao,
            justificativa=justificativa,
            pdf_url=pdf_url,
            pdf_hash=pdf_hash,
            criado_por=usuario["id_usuario"],
            criado_por_nome=usuario["nome"],
        )
        return await self.repo.criar(versao.model_dump())

    async def listar_versoes(self, id_rdo: str) -> list[dict]:
        return await self.repo.listar_por_rdo(id_rdo)

    async def buscar_versao(self, id_rdo: str, versao: int):
        return await self.repo.buscar_versao(id_rdo, versao)
