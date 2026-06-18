"""Tools de saúde da obra."""

from langchain_core.tools import tool

from app.services.ia.tools.context import ToolContext


def saude_tools(ctx: ToolContext) -> list:
    @tool
    async def calcular_saude_obra(id_obra: str) -> dict:
        """Retorna o score de saúde (0-100), a classificação e o breakdown de uma obra."""
        if not await ctx.checar_acesso(id_obra):
            return {"erro": "sem acesso a esta obra"}
        saude = await ctx.saude_service.calcular(id_obra)
        return {
            "score": saude["score"],
            "classificacao": saude["classificacao"],
            "breakdown": saude["breakdown"],
        }

    return [calcular_saude_obra]
