"""Repositório de vínculos Obra-Usuário."""

from datetime import datetime, timezone
from typing import Optional

from app.repositories.base_repository import BaseRepository


class ObraUsuarioRepository(BaseRepository):
    collection_name = "obra_usuarios"
    id_field = "id_obra_usuario"

    async def buscar_por_obra_e_usuario(
        self, id_obra: str, id_usuario: str
    ) -> Optional[dict]:
        return await self.buscar_um({"id_obra": id_obra, "id_usuario": id_usuario})

    async def listar_por_obra(self, id_obra: str) -> list[dict]:
        return await self.listar({"id_obra": id_obra}, limit=1000)

    async def listar_por_usuario(self, id_usuario: str) -> list[dict]:
        return await self.listar({"id_usuario": id_usuario}, limit=1000)

    async def verificar_permissao_temporaria(
        self, id_obra: str, id_usuario: str, permissao: str
    ) -> bool:
        vinculo = await self.buscar_por_obra_e_usuario(id_obra, id_usuario)
        if not vinculo:
            return False
        extras = vinculo.get("permissoes_extras") or {}
        if not extras.get(permissao):
            return False
        expira_em = extras.get("expira_em")
        if expira_em:
            if isinstance(expira_em, str):
                try:
                    expira_em = datetime.fromisoformat(expira_em.replace("Z", "+00:00"))
                except ValueError:
                    return False
            if expira_em.tzinfo is None:
                expira_em = expira_em.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expira_em:
                return False
        return True
