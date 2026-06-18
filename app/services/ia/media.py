"""IA aplicada a mídia: transcrição de áudio (whisper) e análise de imagem (visão)."""

from langchain_core.messages import HumanMessage

from app.services.ia.llm import MODELO_AUDIO, MODELO_VISAO, get_chat, get_groq_client


class MediaIAService:
    async def transcrever(self, audio_bytes: bytes, filename: str = "audio.m4a") -> str:
        client = get_groq_client()
        resp = await client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=MODELO_AUDIO,
            language="pt",
        )
        return resp.text.strip()

    async def analisar_imagem(self, imagem_url: str) -> str:
        prompt = (
            "Você é um engenheiro fiscal de obras. Analise a foto da obra e descreva de "
            "forma objetiva: (1) atividade/serviço em execução, (2) equipamentos visíveis, "
            "(3) condições de segurança (EPIs, sinalização, riscos) e (4) possíveis não "
            "conformidades. Responda em português, em até 6 linhas."
        )
        mensagem = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": imagem_url}},
            ]
        )
        resp = await get_chat(MODELO_VISAO, 0.3).ainvoke([mensagem])
        return (resp.content or "").strip() if isinstance(resp.content, str) else str(resp.content)
