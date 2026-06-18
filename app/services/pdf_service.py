"""Geração de PDF (WeasyPrint): RDO no layout DNIT 097/2025 e Dossiê Executivo."""

import asyncio
import hashlib
import html
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import NotFoundError
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.assinatura_repository import AssinaturaRepository
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.midia_repository import MidiaRepository
from app.repositories.obra_repository import ObraRepository
from app.repositories.rdo_repository import RDORepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.ia import IAService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

_RESTRICAO_LABELS = {
    "pessoal": "Pessoal",
    "equipamento": "Equipamento",
    "instalacoes": "Instalações",
    "cronograma_fisico": "Cronograma físico",
    "qualidade": "Qualidade",
    "atendimento_fiscalizacao": "Atendimento à fiscalização",
    "administracao_obra": "Administração da obra",
    "meio_ambiente": "Meio ambiente",
}

_CSS = """
@page { size: A4; margin: 1.4cm; }
* { font-family: Helvetica, Arial, sans-serif; box-sizing: border-box; }
body { color: #1a1a1a; font-size: 11px; position: relative; }
h1 { font-size: 16px; color: #003366; margin: 0; }
h2 { font-size: 12px; color: #fff; background: #003366; padding: 4px 8px; margin: 14px 0 6px; }
.cab { display: flex; justify-content: space-between; align-items: center;
       border-bottom: 3px solid #003366; padding-bottom: 8px; }
.cab .meta { text-align: right; font-size: 10px; }
.logo { font-weight: bold; color: #003366; font-size: 13px; }
table { width: 100%; border-collapse: collapse; margin: 4px 0; }
th, td { border: 1px solid #cfcfcf; padding: 3px 6px; text-align: left; font-size: 10px; }
th { background: #eef2f7; }
.grid2 { display: flex; flex-wrap: wrap; gap: 8px; }
.foto { width: 48%; border: 1px solid #cfcfcf; padding: 4px; margin-bottom: 8px; }
.foto img { width: 100%; height: 150px; object-fit: cover; }
.foto .legenda { font-size: 9px; color: #444; margin-top: 3px; }
.sigs { display: flex; gap: 8px; margin-top: 10px; }
.sig { flex: 1; border: 1px solid #003366; padding: 6px; min-height: 70px; font-size: 9px; }
.sig .papel { font-weight: bold; color: #003366; }
.watermark { position: fixed; top: 42%; left: 8%; font-size: 60px; color: rgba(200,0,0,0.12);
             transform: rotate(-30deg); font-weight: bold; z-index: 0; }
.muted { color: #777; }
.barra { background: #eef2f7; border: 1px solid #cfcfcf; height: 14px; width: 200px; display: inline-block; }
.barra > span { display: block; height: 100%; background: #003366; }
"""


def _e(valor) -> str:
    return html.escape(str(valor)) if valor is not None else ""


def _fmt_data(valor) -> str:
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    return _e(valor)


def _fmt_dt(valor) -> str:
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return _e(valor)


class PDFService:
    def __init__(self):
        self.rdo_repo = RDORepository()
        self.obra_repo = ObraRepository()
        self.empresa_repo = EmpresaRepository()
        self.usuario_repo = UsuarioRepository()
        self.midia_repo = MidiaRepository()
        self.assinatura_repo = AssinaturaRepository()
        self.comentario_repo = ComentarioRepository()
        self.alerta_repo = AlertaRepository()
        self.storage = StorageService()
        self.ia = IAService()

    # ---- Helpers ----

    @staticmethod
    def _calcular_hash(conteudo) -> str:
        dados = conteudo.encode("utf-8") if isinstance(conteudo, str) else conteudo
        return hashlib.sha256(dados).hexdigest()

    @staticmethod
    def _bytes_from_html(html_str: str) -> bytes:
        from weasyprint import HTML

        return HTML(string=html_str, base_url=None).write_pdf()

    async def _render_pdf(self, html_str: str) -> bytes:
        return await asyncio.to_thread(self._bytes_from_html, html_str)

    @staticmethod
    def _watermark(status: str) -> str:
        if status == "finalizado":
            return ""
        texto = "VERSÃO PARA ASSINATURA" if status == "bloqueado" else "RASCUNHO — NÃO OFICIAL"
        return f'<div class="watermark">{texto}</div>'

    @staticmethod
    def _logo(url: Optional[str], alt: str) -> str:
        if url:
            return f'<img src="{_e(url)}" style="max-height:42px;">'
        return f'<span class="logo">{_e(alt)}</span>'

    # ---- Geração do PDF do RDO ----

    async def _carregar_contexto_rdo(self, id_rdo: str) -> dict:
        rdo = await self.rdo_repo.buscar_por_id(id_rdo)
        if not rdo:
            raise NotFoundError("RDO não encontrado.")
        obra = await self.obra_repo.buscar_por_id(rdo["id_obra"])
        empresa = (
            await self.empresa_repo.buscar_por_id(obra["id_empresa_contratada"])
            if obra
            else None
        )
        fiscal = (
            await self.usuario_repo.buscar_por_id(obra["id_fiscal_suape"]) if obra else None
        )
        midias = await self.midia_repo.listar_por_rdo(id_rdo)
        assinaturas = await self.assinatura_repo.listar_por_rdo(id_rdo)
        return {
            "rdo": rdo,
            "obra": obra or {},
            "empresa": empresa or {},
            "fiscal": fiscal or {},
            "midias": midias,
            "assinaturas": assinaturas,
        }

    async def gerar_pdf(self, id_rdo: str) -> tuple[bytes, str]:
        ctx = await self._carregar_contexto_rdo(id_rdo)
        html_core = self._renderizar_html_rdo(ctx, hash_documento=None)
        hash_doc = self._calcular_hash(html_core)
        html_final = self._renderizar_html_rdo(ctx, hash_documento=hash_doc)
        pdf = await self._render_pdf(html_final)
        return pdf, hash_doc

    async def gerar_e_armazenar(self, id_rdo: str) -> tuple[str, str]:
        pdf, hash_doc = await self.gerar_pdf(id_rdo)
        url, _ = await self.storage.upload_pdf(pdf, id_rdo)
        return url, hash_doc

    def _renderizar_html_rdo(self, ctx: dict, hash_documento: Optional[str]) -> str:
        rdo, obra, empresa = ctx["rdo"], ctx["obra"], ctx["empresa"]
        midias, assinaturas = ctx["midias"], ctx["assinaturas"]
        status = rdo.get("status", "")

        prazo = obra.get("prazo_contratual_dias") or 0
        inicio = obra.get("data_inicio_execucao")
        decorrido = 0
        if isinstance(inicio, datetime):
            ini = inicio if inicio.tzinfo else inicio.replace(tzinfo=timezone.utc)
            decorrido = max((datetime.now(timezone.utc) - ini).days, 0)
        restante = max(prazo - decorrido, 0)

        def tabela_pessoal(itens, titulo):
            linhas = "".join(
                f"<tr><td>{_e(i.get('funcao'))}</td><td>{_e(i.get('quantidade'))}</td></tr>"
                for i in (itens or [])
            )
            if not linhas:
                linhas = '<tr><td colspan="2" class="muted">—</td></tr>'
            return f"<b>{titulo}</b><table><tr><th>Função</th><th>Qtd.</th></tr>{linhas}</table>"

        total_pessoal = sum(
            i.get("quantidade", 0)
            for grp in (rdo.get("pessoal_direto"), rdo.get("pessoal_indireto"))
            for i in (grp or [])
        )

        equip = "".join(
            f"<tr><td>{_e(i.get('nome'))}</td><td>{_e(i.get('quantidade'))}</td></tr>"
            for i in (rdo.get("equipamentos") or [])
        ) or '<tr><td colspan="2" class="muted">—</td></tr>'

        servicos = "".join(
            f"<tr><td>{_e(s.get('descricao'))}</td><td>{_e(s.get('grupo'))}</td>"
            f"<td>{_e(s.get('situacao'))}</td></tr>"
            for s in (rdo.get("servicos") or [])
        ) or '<tr><td colspan="3" class="muted">—</td></tr>'

        eventos = rdo.get("eventos_restricao") or {}
        restricoes = "".join(
            f"<tr><td>{lbl}</td><td style='text-align:center'>"
            f"{'●' if eventos.get(k) else '○'}</td></tr>"
            for k, lbl in _RESTRICAO_LABELS.items()
        )

        clima_m = rdo.get("clima_manha") or {}
        clima_t = rdo.get("clima_tarde") or {}

        def clima_linha(rotulo, c):
            if not c:
                return f"<tr><td>{rotulo}</td><td class='muted'>—</td></tr>"
            prat = "praticável" if c.get("praticavel") else "impraticável"
            return f"<tr><td>{rotulo}</td><td>{_e(c.get('tempo'))} ({prat})</td></tr>"

        fotos_html = ""
        if midias:
            cards = ""
            for m in midias:
                analise = (
                    f"<div class='legenda'>{_e(m.get('ai_analise'))}</div>"
                    if m.get("ai_analise")
                    else ""
                )
                cards += (
                    f"<div class='foto'><img src='{_e(m.get('storage_url'))}'>"
                    f"<div class='legenda'>Contrato {_e(obra.get('numero_contrato'))} · "
                    f"GPS {_e(m.get('latitude'))}, {_e(m.get('longitude'))} · "
                    f"{_fmt_dt(m.get('data_hora_captura'))}</div>{analise}</div>"
                )
            fotos_html = f"<h2>FOTOS ({len(midias)})</h2><div class='grid2'>{cards}</div>"

        if assinaturas:
            sig_cards = "".join(
                f"<div class='sig'><div class='papel'>{_e(a.get('papel'))}</div>"
                f"{_e(a.get('nome_completo'))}<br>{_e(a.get('email'))}<br>"
                f"{_e(a.get('cargo') or '')}<br>Assinado em: {_fmt_dt(a.get('criado_em'))}<br>"
                f"Hash: sha256:{_e((a.get('hash_documento') or '')[:16])}…</div>"
                for a in assinaturas
            )
        else:
            sig_cards = "<div class='sig muted'>Pendente de assinatura eletrônica.</div>"

        hash_rodape = (
            f"sha256:{hash_documento}" if hash_documento else "(hash calculado na emissão)"
        )

        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>{self._watermark(status)}
<div class="cab">
  <div>{self._logo(obra.get('logo_suape_url'), 'SUAPE')}
       &nbsp; {self._logo(obra.get('logo_contratada_url'), _e(empresa.get('razao_social') or 'Contratada'))}</div>
  <div class="meta">Registro nº {_e(rdo.get('numero_registro'))}<br>
       Data: {_fmt_data(rdo.get('data_relatorio'))}<br>
       Contrato: {_e(obra.get('numero_contrato'))}<br>
       Status: {_e(status).upper()}</div>
</div>
<h1>Registro do Diário de Obra (RDO)</h1>
<table>
  <tr><th>Obra</th><td>{_e(obra.get('objeto_contratual'))}</td></tr>
  <tr><th>Local</th><td>{_e(obra.get('local_descricao'))}</td></tr>
  <tr><th>Contratante</th><td>SUAPE</td><th>Contratada</th><td>{_e(empresa.get('razao_social'))}</td></tr>
  <tr><th>Prazo (dias)</th><td>{prazo}</td><th>Decorrido</th><td>{decorrido}</td></tr>
  <tr><th>Restante</th><td>{restante}</td><th>Tipologia</th><td>{_e(obra.get('tipologia'))}</td></tr>
</table>

<h2>CONDIÇÕES CLIMÁTICAS</h2>
<table>{clima_linha('Manhã', clima_m)}{clima_linha('Tarde', clima_t)}</table>

<h2>PESSOAL (total: {total_pessoal})</h2>
{tabela_pessoal(rdo.get('pessoal_direto'), 'Mão de Obra Direta')}
{tabela_pessoal(rdo.get('pessoal_indireto'), 'Mão de Obra Indireta')}

<h2>EQUIPAMENTOS</h2>
<table><tr><th>Nome</th><th>Qtd.</th></tr>{equip}</table>

<h2>SERVIÇOS DESENVOLVIDOS NO PERÍODO</h2>
<table><tr><th>Descrição</th><th>Grupo</th><th>Situação</th></tr>{servicos}</table>

<h2>EVENTOS COM RESTRIÇÕES</h2>
<table><tr><th>Categoria</th><th>Ocorreu</th></tr>{restricoes}</table>
<p><b>Descrição:</b> {_e(eventos.get('descricao') or '—')}</p>

<h2>OCORRÊNCIAS</h2>
<p>{_e(rdo.get('ocorrencias') or '—')}</p>

<h2>RESUMO DO DIA</h2>
<p>{_e(rdo.get('resumo_dia') or '—')}</p>

{fotos_html}

<h2>ASSINATURAS ELETRÔNICAS</h2>
<div class="sigs">{sig_cards}</div>
<p class="muted" style="margin-top:10px;font-size:9px;">Documento gerado pelo Lavrari · {hash_rodape}</p>
</body></html>"""

    # ---- Dossiê Executivo ----

    async def gerar_dossie(
        self,
        id_obra: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> bytes:
        obra = await self.obra_repo.buscar_por_id(id_obra)
        if not obra:
            raise NotFoundError("Obra não encontrada.")
        empresa = await self.empresa_repo.buscar_por_id(obra["id_empresa_contratada"])

        filtros: dict = {"id_obra": id_obra}
        if data_inicio or data_fim:
            intervalo: dict = {}
            if data_inicio:
                intervalo["$gte"] = data_inicio
            if data_fim:
                intervalo["$lte"] = data_fim
            filtros["data_relatorio"] = intervalo
        rdos = await self.rdo_repo.listar(
            filtros, limit=1000, ordenar=[("data_relatorio", 1)]
        )

        ids = [r["id_rdo"] for r in rdos]
        midias = await self.midia_repo.listar_por_rdos(ids)
        reprovacoes = (
            await self.comentario_repo.contar(
                {"id_rdo": {"$in": ids}, "tipo": "solicitacao_correcao"}
            )
            if ids
            else 0
        )
        por_status: dict[str, int] = {}
        dias_restricao = 0
        contagem_restricao = {k: 0 for k in _RESTRICAO_LABELS}
        for r in rdos:
            por_status[r.get("status", "?")] = por_status.get(r.get("status", "?"), 0) + 1
            eventos = r.get("eventos_restricao") or {}
            tem = False
            for k in _RESTRICAO_LABELS:
                if eventos.get(k):
                    contagem_restricao[k] += 1
                    tem = True
            if tem:
                dias_restricao += 1
        alertas_nc = await self.alerta_repo.contar(
            {"id_obra": id_obra, "tipo": "padrao_nc"}
        )
        saude = await self.ia.calcular_saude_obra(id_obra)

        indicadores = {
            "total_rdos": len(rdos),
            "por_status": por_status,
            "dias_com_restricao": dias_restricao,
            "reprovacoes": reprovacoes,
            "total_fotos": len(midias),
            "nao_conformidades": alertas_nc,
            "saude": saude,
            "contagem_restricao": {
                _RESTRICAO_LABELS[k]: v for k, v in contagem_restricao.items() if v
            },
        }

        contexto_ia = {
            "objeto": obra.get("objeto_contratual"),
            "contrato": obra.get("numero_contrato"),
            "total_rdos": len(rdos),
            "score_saude": saude["score"],
            "classificacao": saude["classificacao"],
            "dias_com_restricao": dias_restricao,
            "reprovacoes": reprovacoes,
            "restricoes_por_categoria": indicadores["contagem_restricao"],
        }
        try:
            resumo = await self.ia.gerar_resumo_executivo(contexto_ia)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Resumo executivo indisponível: %s", exc)
            resumo = "Resumo executivo indisponível (serviço de IA não configurado)."

        html_str = self._renderizar_html_dossie(
            obra, empresa or {}, rdos, midias, indicadores, resumo, data_inicio, data_fim
        )
        pdf = await self._render_pdf(html_str)
        try:
            await self.storage.upload_dossie(pdf, id_obra)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao armazenar dossiê no COS: %s", exc)
        return pdf

    def _renderizar_html_dossie(
        self, obra, empresa, rdos, midias, ind, resumo, di, df
    ) -> str:
        saude = ind["saude"]
        periodo = (
            f"{_fmt_data(di)} – {_fmt_data(df)}"
            if (di or df)
            else "Todo o período"
        )
        status_rows = "".join(
            f"<tr><td>{_e(k)}</td><td>{v}</td></tr>" for k, v in ind["por_status"].items()
        ) or '<tr><td colspan="2" class="muted">—</td></tr>'

        restricao_rows = "".join(
            f"<tr><td>{_e(k)}</td><td>{'█' * min(v, 20)} {v}</td></tr>"
            for k, v in ind["contagem_restricao"].items()
        ) or '<tr><td colspan="2" class="muted">Nenhuma restrição registrada.</td></tr>'

        # Linha do tempo: eventos relevantes.
        eventos_tl = []
        for r in rdos:
            ev = r.get("eventos_restricao") or {}
            flags = [_RESTRICAO_LABELS[k] for k in _RESTRICAO_LABELS if ev.get(k)]
            marco = f"RDO nº {r.get('numero_registro')} ({r.get('status')})"
            if flags:
                marco += f" — restrições: {', '.join(flags)}"
            eventos_tl.append(
                f"<tr><td>{_fmt_data(r.get('data_relatorio'))}</td><td>{_e(marco)}</td></tr>"
            )
        timeline = "".join(eventos_tl) or '<tr><td colspan="2" class="muted">—</td></tr>'

        # Registro fotográfico (até 8 fotos).
        fotos = ""
        for m in midias[:8]:
            analise = (
                f"<div class='legenda'>{_e(m.get('ai_analise'))}</div>"
                if m.get("ai_analise")
                else ""
            )
            fotos += (
                f"<div class='foto'><img src='{_e(m.get('storage_url'))}'>"
                f"<div class='legenda'>GPS {_e(m.get('latitude'))}, {_e(m.get('longitude'))} · "
                f"{_fmt_dt(m.get('data_hora_captura'))}</div>{analise}</div>"
            )
        fotos_html = (
            f"<h2>5. REGISTRO FOTOGRÁFICO</h2><div class='grid2'>{fotos}</div>" if fotos else ""
        )

        rdos_rows = "".join(
            f"<tr><td>{_fmt_data(r.get('data_relatorio'))}</td>"
            f"<td>{_e(r.get('numero_registro'))}</td><td>{_e(r.get('status'))}</td>"
            f"<td>{_e((r.get('resumo_dia') or r.get('ocorrencias') or '—'))[:80]}</td></tr>"
            for r in rdos
        ) or '<tr><td colspan="4" class="muted">—</td></tr>'

        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
<div class="cab">
  <div>{self._logo(obra.get('logo_suape_url'), 'SUAPE')} &nbsp;
       {self._logo(obra.get('logo_contratada_url'), _e(empresa.get('razao_social') or 'Contratada'))}</div>
  <div class="meta">Contrato: {_e(obra.get('numero_contrato'))}<br>
       Período: {periodo}<br>Gerado em: {_fmt_data(datetime.now(timezone.utc))}<br>
       Gerado por: IA Lavrari</div>
</div>
<h1>Dossiê Executivo da Obra</h1>
<p><b>Objeto:</b> {_e(obra.get('objeto_contratual'))}</p>

<h2>1. RESUMO EXECUTIVO (gerado por IA)</h2>
<p>{_e(resumo).replace(chr(10), '<br>')}</p>

<h2>2. INDICADORES CONSOLIDADOS</h2>
<table>
  <tr><th>Total de RDOs</th><td>{ind['total_rdos']}</td>
      <th>Dias com restrição</th><td>{ind['dias_com_restricao']}</td></tr>
  <tr><th>Reprovações</th><td>{ind['reprovacoes']}</td>
      <th>Total de fotos</th><td>{ind['total_fotos']}</td></tr>
  <tr><th>Não conformidades</th><td>{ind['nao_conformidades']}</td>
      <th>Índice de Saúde</th>
      <td>{saude['score']}/100 <span class="barra"><span style="width:{saude['score']}%"></span></span>
          {_e(saude['classificacao'])}</td></tr>
</table>
<table><tr><th>Status</th><th>Qtd.</th></tr>{status_rows}</table>

<h2>3. LINHA DO TEMPO</h2>
<table><tr><th>Data</th><th>Evento</th></tr>{timeline}</table>

<h2>4. ANÁLISE DE RESTRIÇÕES</h2>
<table><tr><th>Categoria</th><th>Frequência</th></tr>{restricao_rows}</table>

{fotos_html}

<h2>6. RELATÓRIOS DIÁRIOS (RDOs)</h2>
<table><tr><th>Data</th><th>Nº</th><th>Status</th><th>Resumo</th></tr>{rdos_rows}</table>
</body></html>"""
