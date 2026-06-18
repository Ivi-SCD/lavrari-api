"""Aplicação FastAPI do Lavrari."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import (
    alertas,
    auth,
    comentarios,
    empresas,
    ia,
    midias,
    obras,
    rdos,
    usuarios,
)
from app.core.config.settings import get_settings
from app.core.exceptions import AppError
from app.core.infrastructure.mongodb.manager import get_mongo_manager, init_database

logging.basicConfig(level=logging.INFO)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_database()
    yield
    get_mongo_manager().close_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensagem})


@app.get("/health", tags=["health"], summary="Healthcheck")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


PREFIX = "/lavrari/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(usuarios.router, prefix=PREFIX)
app.include_router(empresas.router, prefix=PREFIX)
app.include_router(obras.router, prefix=PREFIX)
app.include_router(rdos.router, prefix=PREFIX)
app.include_router(midias.router, prefix=PREFIX)
app.include_router(comentarios.router, prefix=PREFIX)
app.include_router(ia.router, prefix=PREFIX)
app.include_router(alertas.router, prefix=PREFIX)
