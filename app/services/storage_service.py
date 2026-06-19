"""Serviço de armazenamento de objetos no IBM Cloud Object Storage (S3/boto3)."""

import asyncio
import logging
import uuid

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=settings.IBM_COS_ENDPOINT,
                aws_access_key_id=settings.IBM_COS_ACCESS_KEY,
                aws_secret_access_key=settings.IBM_COS_SECRET_KEY,
            )
        return self._client

    @staticmethod
    def _extensao(content_type: str) -> str:
        mapa = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }
        return mapa.get((content_type or "").lower(), "jpg")

    def url_publica(self, key: str) -> str:
        return f"{settings.IBM_COS_ENDPOINT}/{settings.IBM_COS_BUCKET_NAME}/{key}"

    async def upload_foto(
        self, arquivo_bytes: bytes, id_rdo: str, content_type: str = "image/jpeg"
    ) -> tuple[str, str]:
        key = f"rdos/{id_rdo}/fotos/{uuid.uuid4()}.{self._extensao(content_type)}"

        def _put():
            self._get_client().put_object(
                Bucket=settings.IBM_COS_BUCKET_NAME,
                Key=key,
                Body=arquivo_bytes,
                ContentType=content_type,
            )

        await asyncio.to_thread(_put)
        return self.url_publica(key), key

    async def _upload_bytes(self, conteudo: bytes, key: str, content_type: str) -> tuple[str, str]:
        def _put():
            self._get_client().put_object(
                Bucket=settings.IBM_COS_BUCKET_NAME,
                Key=key,
                Body=conteudo,
                ContentType=content_type,
            )

        await asyncio.to_thread(_put)
        return self.url_publica(key), key

    async def upload_logo(
        self, conteudo: bytes, id_empresa: str, content_type: str = "image/png"
    ) -> tuple[str, str]:
        key = f"empresas/{id_empresa}/logo/{uuid.uuid4()}.{self._extensao(content_type)}"
        return await self._upload_bytes(conteudo, key, content_type)

    async def upload_pdf(self, conteudo: bytes, id_rdo: str) -> tuple[str, str]:
        key = f"rdos/{id_rdo}/pdf/{uuid.uuid4()}.pdf"
        return await self._upload_bytes(conteudo, key, "application/pdf")

    async def upload_dossie(self, conteudo: bytes, id_obra: str) -> tuple[str, str]:
        key = f"obras/{id_obra}/dossie/{uuid.uuid4()}.pdf"
        return await self._upload_bytes(conteudo, key, "application/pdf")

    async def deletar_arquivo(self, storage_key: str) -> None:
        def _delete():
            self._get_client().delete_object(
                Bucket=settings.IBM_COS_BUCKET_NAME, Key=storage_key
            )

        await asyncio.to_thread(_delete)
