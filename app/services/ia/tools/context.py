"""Contexto compartilhado pelas tools do agente de chat."""

from app.repositories.alerta_repository import AlertaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.obra_usuario_repository import ObraUsuarioRepository
from app.repositories.rdo_repository import RDORepository
from app.services.ia.analytics import SaudeService


class ToolContext:
    """Reúne usuário autenticado, repositórios e helpers de autorização.

    Cada execução do agente cria um contexto novo (permissões nunca são cacheadas
    entre requisições) — apenas memoiza a lista de obras dentro da mesma chamada.
    """

    def __init__(self, usuario: dict):
        self.usuario = usuario
        self.obra_repo = ObraRepository()
        self.rdo_repo = RDORepository()
        self.alerta_repo = AlertaRepository()
        self.obra_usuario_repo = ObraUsuarioRepository()
        self.saude_service = SaudeService()
        self._ids_cache: set[str] | None = None

    async def obras_acessiveis(self) -> list[dict]:
        if self.usuario.get("is_admin"):
            return await self.obra_repo.listar({}, limit=100)
        vinculos = await self.obra_usuario_repo.listar_por_usuario(self.usuario["id_usuario"])
        ids = [v["id_obra"] for v in vinculos]
        return await self.obra_repo.listar_por_ids(ids) if ids else []

    async def checar_acesso(self, id_obra: str) -> bool:
        if self.usuario.get("is_admin"):
            return True
        if self._ids_cache is None:
            obras = await self.obras_acessiveis()
            self._ids_cache = {o["id_obra"] for o in obras}
        return id_obra in self._ids_cache
