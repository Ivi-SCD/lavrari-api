"""Tools de consulta de obras."""

from langchain_core.tools import tool

from app.services.ia.tools.context import ToolContext


def obras_tools(ctx: ToolContext) -> list:
    @tool
    async def listar_obras_ativas() -> list[dict]:
        """Lista as obras acessíveis ao usuário com objeto, prazo e data de fim prevista."""
        obras = await ctx.obras_acessiveis()
        return [
            {
                "id_obra": o["id_obra"],
                "objeto_contratual": o.get("objeto_contratual"),
                "prazo_contratual_dias": o.get("prazo_contratual_dias"),
                "data_fim_execucao": str(o.get("data_fim_execucao")),
            }
            for o in obras
        ]

    return [listar_obras_ativas]
