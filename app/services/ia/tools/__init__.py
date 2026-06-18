"""Tools do agente de chat, segregadas por tipo de recurso."""

from app.services.ia.tools.alertas_tools import alertas_tools
from app.services.ia.tools.context import ToolContext
from app.services.ia.tools.obras_tools import obras_tools
from app.services.ia.tools.rdos_tools import rdos_tools
from app.services.ia.tools.saude_tools import saude_tools


def construir_tools(ctx: ToolContext) -> list:
    """Monta a lista completa de tools disponíveis ao agente para o contexto dado."""
    return [
        *obras_tools(ctx),
        *rdos_tools(ctx),
        *saude_tools(ctx),
        *alertas_tools(ctx),
    ]


__all__ = ["ToolContext", "construir_tools"]
