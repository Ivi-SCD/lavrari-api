"""Análises locais (sem LLM): Índice de Saúde e Evolução Visual por GPS."""

import math
from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import NotFoundError
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.midia_repository import MidiaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_repository import RDORepository

_RESTRICAO_FLAGS = (
    "pessoal",
    "equipamento",
    "instalacoes",
    "cronograma_fisico",
    "qualidade",
    "atendimento_fiscalizacao",
    "administracao_obra",
    "meio_ambiente",
)


def haversine_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em metros entre dois pontos GPS."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def percentual_prazo(obra: dict) -> int:
    inicio = obra.get("data_inicio_execucao")
    prazo = obra.get("prazo_contratual_dias") or 0
    if not isinstance(inicio, datetime) or not prazo:
        return 0
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    decorridos = max((datetime.now(timezone.utc) - inicio).days, 0)
    return min(round(decorridos / prazo * 100), 100)


class SaudeService:
    """Diferencial 1 — Índice de Saúde da Obra (cálculo local)."""

    def __init__(self):
        self.rdo_repo = RDORepository()
        self.comentario_repo = ComentarioRepository()
        self.obra_repo = ObraRepository()

    async def calcular(self, id_obra: str) -> dict:
        obra = await self.obra_repo.buscar_por_id(id_obra)
        if not obra:
            raise NotFoundError("Obra não encontrada.")

        rdos = await self.rdo_repo.listar(
            {"id_obra": id_obra}, limit=30, ordenar=[("data_relatorio", -1)]
        )
        n = len(rdos) or 1

        total_flags = 0
        for r in rdos:
            eventos = r.get("eventos_restricao") or {}
            total_flags += sum(1 for f in _RESTRICAO_FLAGS if eventos.get(f))

        dias_aprovacao: list[float] = []
        for r in rdos:
            enviado, aprovado = r.get("enviado_em"), r.get("aprovado_em")
            if isinstance(enviado, datetime) and isinstance(aprovado, datetime):
                delta = (aprovado - enviado).total_seconds() / 86400
                if delta >= 0:
                    dias_aprovacao.append(delta)
        media_dias_aprovacao = (
            round(sum(dias_aprovacao) / len(dias_aprovacao), 1) if dias_aprovacao else 0.0
        )

        ids = [r["id_rdo"] for r in rdos]
        total_reprovacoes = (
            await self.comentario_repo.contar(
                {"id_rdo": {"$in": ids}, "tipo": "solicitacao_correcao"}
            )
            if ids
            else 0
        )

        pct_prazo = percentual_prazo(obra)

        score_restricoes = max(0.0, 100 - (total_flags / n * 20))
        score_aprovacao = max(0.0, 100 - (media_dias_aprovacao * 10))
        score_reprovacoes = max(0.0, 100 - (total_reprovacoes * 15))
        score_prazo = max(0.0, 100 - max(0, pct_prazo - 70) * 3)

        score_final = round(
            score_restricoes * 0.35
            + score_aprovacao * 0.25
            + score_reprovacoes * 0.25
            + score_prazo * 0.15
        )

        if score_final < 40:
            classificacao = "Crítico"
        elif score_final < 70:
            classificacao = "Em risco"
        else:
            classificacao = "Saudável"

        return {
            "id_obra": id_obra,
            "score": int(score_final),
            "classificacao": classificacao,
            "breakdown": {
                "restricoes": {"score": round(score_restricoes), "total_ocorrencias": total_flags},
                "aprovacao": {
                    "score": round(score_aprovacao),
                    "media_dias_para_aprovar": media_dias_aprovacao,
                },
                "reprovacoes": {
                    "score": round(score_reprovacoes),
                    "total_reprovacoes": total_reprovacoes,
                },
                "prazo": {"score": round(score_prazo), "percentual_decorrido": pct_prazo},
            },
            "rdos_analisados": len(rdos),
            "periodo": "últimos 30 dias",
        }


class EvolucaoService:
    """Diferencial 2 — Evolução Visual da Obra por GPS (cálculo local)."""

    def __init__(self):
        self.obra_repo = ObraRepository()
        self.rdo_repo = RDORepository()
        self.midia_repo = MidiaRepository()

    async def calcular(
        self,
        id_obra: str,
        lat: float,
        lon: float,
        raio_metros: int = 50,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> dict:
        obra = await self.obra_repo.buscar_por_id(id_obra)
        if not obra:
            raise NotFoundError("Obra não encontrada.")

        rdos = await self.rdo_repo.listar_por_obra(id_obra)
        midias = await self.midia_repo.listar_por_rdos([r["id_rdo"] for r in rdos])

        por_data: dict[str, list[dict]] = {}
        total = 0
        for m in midias:
            mlat, mlon = m.get("latitude"), m.get("longitude")
            if mlat is None or mlon is None:
                continue
            distancia = haversine_metros(lat, lon, mlat, mlon)
            if distancia > raio_metros:
                continue
            captura = m.get("data_hora_captura")
            if isinstance(captura, datetime):
                if captura.tzinfo is None:
                    captura = captura.replace(tzinfo=timezone.utc)
                if data_inicio and captura < data_inicio:
                    continue
                if data_fim and captura > data_fim:
                    continue
                dia = captura.date().isoformat()
            else:
                dia = "sem-data"
            por_data.setdefault(dia, []).append(
                {
                    "storage_url": m.get("storage_url"),
                    "ai_analise": m.get("ai_analise"),
                    "data_hora_captura": m.get("data_hora_captura"),
                    "distancia_metros": round(distancia, 1),
                }
            )
            total += 1

        evolucao = [
            {"data": dia, "fotos": sorted(fotos, key=lambda f: str(f["data_hora_captura"]))}
            for dia, fotos in sorted(por_data.items())
        ]
        return {
            "ponto": {"lat": lat, "lon": lon},
            "raio_metros": raio_metros,
            "total_fotos": total,
            "evolucao": evolucao,
        }
