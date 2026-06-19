"""Serviço de gestão de empresas."""

import asyncio
import uuid

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.globals.models.empresa.empresa import Empresa
from app.repositories.empresa_repository import EmpresaRepository
from app.services.image_utils import redimensionar_para_caixa
from app.services.storage_service import StorageService

# Caixa padrão da logo no card. A imagem é redimensionada para caber dentro
# desta caixa preservando a proporção (sem esticar/distorcer).
_LOGO_MAX = (512, 512)


class EmpresaService:
    def __init__(self):
        self.repo = EmpresaRepository()
        self.storage = StorageService()

    async def listar(self, skip: int = 0, limit: int = 100) -> list[dict]:
        return await self.repo.listar({}, skip=skip, limit=limit, ordenar=[("razao_social", 1)])

    async def criar(self, razao_social: str, cnpj: str, logo_url: str | None = None) -> dict:
        if await self.repo.buscar_por_cnpj(cnpj):
            raise ConflictError("Já existe uma empresa com este CNPJ.")
        empresa = Empresa(
            id_empresa=str(uuid.uuid4()),
            razao_social=razao_social,
            cnpj=cnpj,
            logo_url=logo_url,
        )
        return await self.repo.criar(empresa.model_dump())

    async def buscar(self, id_empresa: str) -> dict:
        empresa = await self.repo.buscar_por_id(id_empresa)
        if not empresa:
            raise NotFoundError("Empresa não encontrada.")
        return empresa

    async def atualizar(self, id_empresa: str, dados: dict) -> dict:
        await self.buscar(id_empresa)
        dados = {k: v for k, v in dados.items() if v is not None}
        if "cnpj" in dados:
            existente = await self.repo.buscar_por_cnpj(dados["cnpj"])
            if existente and existente["id_empresa"] != id_empresa:
                raise ConflictError("CNPJ já utilizado por outra empresa.")
        return await self.repo.atualizar(id_empresa, dados)

    async def atualizar_logo(self, id_empresa: str, conteudo: bytes) -> dict:
        """Redimensiona a logo, envia ao storage e atualiza a empresa."""
        await self.buscar(id_empresa)
        if not conteudo:
            raise ValidationError("Arquivo de logo vazio.")
        processada = await asyncio.to_thread(redimensionar_para_caixa, conteudo, _LOGO_MAX)
        url, _ = await self.storage.upload_logo(processada, id_empresa, "image/png")
        return await self.repo.atualizar(id_empresa, {"logo_url": url})
