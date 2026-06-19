"""Insights baseados em LLM: padrões de NC, sugestão de texto e resumo executivo."""

import logging
import uuid
from datetime import datetime, timezone
from typing import cast

from app.core.exceptions import NotFoundError
from app.globals.enums.alerta.tipo_alerta import SeveridadeAlerta, TipoAlerta
from app.globals.enums.rdo.fonte_dado_rdo import FonteDado
from app.globals.models.alerta.alerta import Alerta
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_repository import RDORepository
from app.services.ia.analytics import _RESTRICAO_FLAGS
from app.services.ia.llm import (
    MODELO_TEXTO,
    EstruturaRDOLLM,
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


_RESTRICAO_FLAGS_RDO = (
    "pessoal",
    "equipamento",
    "instalacoes",
    "cronograma_fisico",
    "qualidade",
    "atendimento_fiscalizacao",
    "administracao_obra",
    "meio_ambiente",
)


class EstruturarRDOService:
    """Extrai um RDO completo (estruturado) a partir de fala/texto livre do dia.

    Sem efeito colateral: apenas devolve a sugestão para o frontend fazer merge no
    formulário; nada é persistido — a gravação segue pelo PATCH /rdos/{id} existente.
    """

    async def estruturar(self, texto: str, data_relatorio: datetime) -> dict:
        prompt = (
            "Você é um engenheiro fiscal que preenche o Registro Diário de Obra (RDO) a "
            "partir do relato falado do responsável em campo. Extraia APENAS o que estiver "
            "explícito no relato — nunca invente números, serviços ou restrições. Quando uma "
            "informação não for mencionada, deixe o campo vazio/nulo.\n\n"
            "Regras:\n"
            "- pessoal_direto: mão de obra de produção (pedreiro, servente, carpinteiro...).\n"
            "- pessoal_indireto: apoio/gestão (encarregado, engenheiro, técnico de segurança...).\n"
            "- equipamentos: máquinas e equipamentos citados, com quantidade.\n"
            "- servicos: atividades executadas, com situação (em andamento/concluído/paralisado).\n"
            "- clima_manha/clima_tarde: só preencha o período citado; praticavel=false se choveu/parou.\n"
            "- eventos_restricao: marque a(s) categoria(s) só se houver impedimento real e descreva.\n"
            "- ocorrencias e resumo_dia: redija em português, objetivo.\n"
            "- confianca: sua autoavaliação de 0.0 a 1.0 da fidelidade da extração.\n\n"
            f"Data do relatório: {data_relatorio.date().isoformat()}\n"
            f"RELATO DO DIA:\n{texto}"
        )
        llm = get_chat(MODELO_TEXTO, 0.1).with_structured_output(EstruturaRDOLLM)
        r = cast(EstruturaRDOLLM, await llm.ainvoke(prompt))
        return self._montar(r)

    @staticmethod
    def _clima(bloco) -> dict | None:
        if not bloco or not (bloco.tempo or "").strip():
            return None
        return {
            "tempo": bloco.tempo.strip(),
            "praticavel": bool(bloco.praticavel),
            "fonte": FonteDado.TRANSCRICAO.value,
        }

    def _montar(self, r: EstruturaRDOLLM) -> dict:
        resultado: dict = {}

        clima_m = self._clima(r.clima_manha)
        if clima_m:
            resultado["clima_manha"] = clima_m
        clima_t = self._clima(r.clima_tarde)
        if clima_t:
            resultado["clima_tarde"] = clima_t

        if r.pessoal_direto:
            resultado["pessoal_direto"] = [i.model_dump() for i in r.pessoal_direto]
        if r.pessoal_indireto:
            resultado["pessoal_indireto"] = [i.model_dump() for i in r.pessoal_indireto]
        if r.equipamentos:
            resultado["equipamentos"] = [i.model_dump() for i in r.equipamentos]
        if r.servicos:
            resultado["servicos"] = [i.model_dump() for i in r.servicos]

        if r.eventos_restricao:
            ev = r.eventos_restricao
            tem_flag = any(getattr(ev, f) for f in _RESTRICAO_FLAGS_RDO)
            if tem_flag or (ev.descricao or "").strip():
                resultado["eventos_restricao"] = ev.model_dump()

        if (r.ocorrencias or "").strip():
            resultado["ocorrencias"] = r.ocorrencias.strip()
        if (r.resumo_dia or "").strip():
            resultado["resumo_dia"] = r.resumo_dia.strip()

        resultado["campos_preenchidos"] = list(resultado.keys())
        resultado["confianca"] = round(max(0.0, min(float(r.confianca or 0.0), 1.0)), 2)
        return resultado


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
