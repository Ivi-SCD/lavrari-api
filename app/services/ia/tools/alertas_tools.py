"""Tools de alertas e padrões de não conformidade."""

from typing import Optional

from langchain_core.tools import tool

from app.globals.enums.alerta.tipo_alerta import TipoAlerta
from app.services.ia.tools.context import ToolContext


def alertas_tools(ctx: ToolContext) -> list:
    @tool
    async def listar_alertas(id_obra: Optional[str] = None) -> list[dict]:
        """Lista alertas. Informe id_obra para uma obra específica ou omita para todas as acessíveis."""
        if id_obra:
            if not await ctx.checar_acesso(id_obra):
                return [{"erro": "sem acesso a esta obra"}]
            alertas = await ctx.alerta_repo.listar_por_obra(id_obra)
        else:
            obras = await ctx.obras_acessiveis()
            alertas = await ctx.alerta_repo.listar_por_obras([o["id_obra"] for o in obras])
        return [
            {
                "id_obra": a["id_obra"],
                "tipo": a["tipo"],
                "severidade": a["severidade"],
                "descricao": a["descricao"],
                "lido": a["lido"],
            }
            for a in alertas
        ]

    @tool
    async def buscar_padroes_nc(id_obra: str) -> list[dict]:
        """Retorna padrões de não conformidade já detectados (alertas PADRAO_NC) de uma obra."""
        if not await ctx.checar_acesso(id_obra):
            return [{"erro": "sem acesso a esta obra"}]
        alertas = await ctx.alerta_repo.listar_por_obra(id_obra)
        return [
            {"descricao": a["descricao"], "severidade": a["severidade"]}
            for a in alertas
            if a["tipo"] == TipoAlerta.PADRAO_NC.value
        ]

    return [listar_alertas, buscar_padroes_nc]
