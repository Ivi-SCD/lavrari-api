"""Repositório de Empresas."""

from typing import Optional

from app.repositories.base_repository import BaseRepository


class EmpresaRepository(BaseRepository):
    collection_name = "empresas"
    id_field = "id_empresa"

    async def buscar_por_cnpj(self, cnpj: str) -> Optional[dict]:
        return await self.buscar_um({"cnpj": cnpj})
