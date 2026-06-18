"""Insights baseados em LLM: padrões de NC, sugestão de texto e resumo executivo."""

import logging
import uuid
from datetime import datetime, timezone
from typing import cast

from app.core.exceptions import NotFoundError
from app.globals.enums.alerta.tipo_alerta import SeveridadeAlerta, TipoAlerta
from app.globals.models.alerta.alerta import Alerta
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_repository import RDORepository
from app.services.ia.analytics import _RESTRICAO_FLAGS
from app.services.ia.llm import (
    MODELO_TEXTO,
    PadroesNCLLM,
    SugestaoLLM,
    get_chat,
)

logger = logging.getLogger(__name__)

_SEVERIDADE_VALIDAS = {s.value for s in SeveridadeAlerta}


class PadroesService:
    """Diferencial 3 — Detecção de Padrões de NC (LLM) com persistência de alertas."""

    def __init__(self):
        self.rdo_repo = RDORepository()
        self.obra_repo = ObraRepository()
        self.alerta_repo = AlertaRepository()

    async def detectar(self, id_obra: str) -> dict:
        obra = await self.obra_repo.buscar_por_id(id_obra)
        if not obra:
            raise NotFoundError("Obra não encontrada.")

        rdos = await self.rdo_repo.listar(
            {"id_obra": id_obra}, limit=45, ordenar=[("data_relatorio", -1)]
        )
        linhas = []
        for r in rdos:
            eventos = r.get("eventos_restricao") or {}
            flags = [f for f in _RESTRICAO_FLAGS if eventos.get(f)]
            linhas.append(
                f"- {r.get('data_relatorio')} | status={r.get('status')} | "
                f"restricoes={flags or 'nenhuma'} | obs={(eventos.get('descricao') or '')} | "
                f"ocorrencias={(r.get('ocorrencias') or '')}"
            )
        historico = "\n".join(linhas) if linhas else "Sem RDOs registrados."

        prompt = (
            "Você é um analista de obras de engenharia. Analise o histórico de RDOs abaixo "
            "e identifique padrões recorrentes de não conformidade, restrições ou problemas. "
            "Para cada padrão informe: descrição clara, severidade (baixa/media/alta/critica), "
            "número de ocorrências e uma recomendação prática. Não invente — baseie-se apenas "
            f"nos dados.\n\nHISTÓRICO DE RDOs:\n{historico}"
        )
        llm = get_chat(MODELO_TEXTO, 0.2).with_structured_output(PadroesNCLLM)
        resultado = cast(PadroesNCLLM, await llm.ainvoke(prompt))

        padroes = []
        for p in resultado.padroes:
            sev = p.severidade.lower().strip()
            if sev not in _SEVERIDADE_VALIDAS:
                sev = SeveridadeAlerta.MEDIA.value
            padroes.append(
                {
                    "descricao": p.descricao,
                    "severidade": sev,
                    "ocorrencias": p.ocorrencias,
                    "recomendacao": p.recomendacao,
                }
            )

        await self._persistir(id_obra, padroes)

        return {
            "id_obra": id_obra,
            "padroes_detectados": padroes,
            "rdos_analisados": len(rdos),
            "gerado_em": datetime.now(timezone.utc),
        }

    async def _persistir(self, id_obra: str, padroes: list[dict]) -> None:
        for p in padroes:
            descricao = f"{p['descricao']} — Recomendação: {p['recomendacao']}".strip(" —")
            ja_existe = await self.alerta_repo.contar(
                {
                    "id_obra": id_obra,
                    "tipo": TipoAlerta.PADRAO_NC.value,
                    "descricao": descricao,
                    "lido": False,
                }
            )
            if ja_existe:
                continue
            alerta = Alerta(
                id_alerta=str(uuid.uuid4()),
                id_obra=id_obra,
                tipo=TipoAlerta.PADRAO_NC,
                severidade=SeveridadeAlerta(p["severidade"]),
                descricao=descricao,
                lido=False,
            )
            await self.alerta_repo.criar(alerta.model_dump())


class SugestaoService:
    """Sugestão de preenchimento do RDO via LLM."""

    async def sugerir(self, id_obra: str, data: datetime, historico_rdos: list[dict]) -> dict:
        resumos = [
            {
                "data": str(r.get("data_relatorio")),
                "resumo_dia": r.get("resumo_dia"),
                "ocorrencias": r.get("ocorrencias"),
            }
            for r in historico_rdos[:10]
        ]
        prompt = (
            "Com base no histórico recente de RDOs desta obra, gere uma sugestão de "
            "preenchimento para o dia informado, em português.\n"
            f"Data do relatório: {data.isoformat()}\n"
            f"Histórico (mais recentes primeiro): {resumos}"
        )
        llm = get_chat(MODELO_TEXTO, 0.5).with_structured_output(SugestaoLLM)
        resultado = cast(SugestaoLLM, await llm.ainvoke(prompt))
        return {"ocorrencias": resultado.ocorrencias, "resumo_dia": resultado.resumo_dia}


class ResumoExecutivoService:
    """Resumo executivo narrativo da obra (usado no Dossiê Executivo)."""

    async def gerar(self, contexto: dict) -> str:
        prompt = (
            "Você é um consultor sênior de obras de infraestrutura. Com base nos dados "
            "consolidados abaixo, escreva um resumo executivo de até 3 parágrafos, em "
            "português, descrevendo o projeto, o progresso geral, os principais desafios e "
            "recomendações objetivas para a diretoria. Não invente números — use apenas os "
            f"dados fornecidos.\n\nDADOS DA OBRA:\n{contexto}"
        )
        resp = await get_chat(MODELO_TEXTO, 0.4).ainvoke(prompt)
        return (resp.content or "").strip() if isinstance(resp.content, str) else str(resp.content)
