from app.globals.core.config.settings import get_settings
from logger import get_logger

from typing import Optional

settings = get_settings()

logger = get_logger(__name__)


class MongoManager:
    COLLECTIONS = {
        "obras": [
            {"keys": [{"id_obra"}, "unique", True]},
            {"keys": [{"numero_contrato"}, "unique", True]},
        ],
        "rdos": [
            {"keys": [{"id_rdo"}, "unique", True]},
            {"keys": [{"id_obra"}, "unique", False]},
            {"keys": [{"numero_registro"}, "unique", False]},
            {"keys": [{"status"}, "unique", False]},
        ],
        "rdo_versoes": [
            {"keys": [{"id_versao"}, "unique", True]},
            {"keys": [{"id_rdo"}, "unique", False]},
        ],
        "usuarios": [
            {"keys": [{"id_usuario"}, "unique", True]},
            {"keys": [{"email"}, "unique", True]},
        ],
        "empresas": [
            {"keys": [{"id_empresa"}, "unique", True]},
            {"keys": [{"cnpj"}, "unique", True]},
        ],
        "midias": [
            {"keys": [{"id_midia"}, "unique", True]},
            {"keys": [{"id_rdo"}, "unique", False]},
        ],
        "comentarios": [
            {"keys": [{"id_comentario"}, "unique", True]},
            {"keys": [{"id_rdo"}, "unique", False]},
        ],
        "obra_usuarios": [
            {"keys": [{"id_obra_usuario"}, "unique", True]},
            {"keys": [{"id_obra"}, "unique", False]},
            {"keys": [{"id_usuario"}, "unique", False]},
        ],
        "alertas": [
            {"keys": [{"id_alerta"}, "unique", True]},
            {"keys": [{"id_obra"}, "unique", False]},
        ],
    }

    def __init__(self):
        self._client = None
        self._db = None
        self._initialized = None

    def get_database(self):
        if self._client is None:
            import certifi
            from motor.motor_asyncio import AsyncIOMotorClient

            self._client = AsyncIOMotorClient(
                get_settings().MONGODB_CONNECTION_STRING,
                tlsCAFile=certifi.where(),
            )
            self._db = self._client[get_settings().MONGODB_DATABASE_NAME]
        return self._db

    def get_collection(self, collection_name: str):
        return self.get_database()[collection_name]

    async def ensure_collections_exist(self) -> None:
        """
        Ensure all required collections exist and have proper indexes.
        Safe to call multiple times - will skip existing collections/indexes.
        """
        if self._initialized:
            return

        db = self.get_database()
        existing_collections = await db.list_collection_names()

        for collection_name, indexes in self.COLLECTIONS.items():
            try:
                if collection_name not in existing_collections:
                    await db.create_collection(collection_name)
                    logger.info(f"Created collection: {collection_name}")
                else:
                    logger.debug(f"Collection already exists: {collection_name}")

                collection = db[collection_name]
                for index_def in indexes:
                    try:
                        await collection.create_index(
                            index_def["keys"],
                            unique=index_def.get("unique", False),
                            background=True,
                        )
                        logger.debug(
                            f"Created index on {collection_name}: {index_def['keys']}"
                        )
                    except Exception as idx_error:
                        logger.debug(
                            f"Index creation skipped (may already exist) on {collection_name}: {idx_error}"
                        )

            except Exception as e:
                logger.error(f"Error setting up collection {collection_name}: {e}")
                raise

        self._initialized = True
        logger.info("MongoDB collections and indexes initialized successfully")

    def close_connection(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._initialized = False


_mongo_manager: Optional[MongoManager] = None


def get_mongo_manager() -> MongoManager:
    """Get or create the MongoDB manager singleton."""
    global _mongo_manager
    if _mongo_manager is None:
        _mongo_manager = MongoManager()
    return _mongo_manager


async def init_database() -> None:
    """Initialize database collections and indexes. Call on application startup."""
    manager = get_mongo_manager()
    await manager.ensure_collections_exist()
