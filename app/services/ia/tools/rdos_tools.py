"""Tools de consulta de RDOs."""

from typing import Optional

from langchain_core.tools import tool

from app.services.ia.tools.context import ToolContext


def rdos_tools(ctx: ToolContext) -> list:
    @tool
    async def buscar_rdos(id_obra: str, status: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Busca RDOs de uma obra (filtro opcional por status), com número, data e status."""
        if not await ctx.checar_acesso(id_obra):
            return [{"erro": "sem acesso a esta obra"}]
        filtros = {"status": status} if status else None
        rdos = await ctx.rdo_repo.listar_por_obra(id_obra, filtros)
        return [
            {
                "numero_registro": r.get("numero_registro"),
                "data_relatorio": str(r.get("data_relatorio")),
                "status": r.get("status"),
            }
            for r in rdos[: max(1, min(limit, 50))]
        ]

    return [buscar_rdos]
