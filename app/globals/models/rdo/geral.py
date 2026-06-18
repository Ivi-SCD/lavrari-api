from pydantic import BaseModel, Field
from typing import Optional

from app.globals.enums.rdo.fonte_dado_rdo import FonteDado


class CondicaoClimatica(BaseModel):
    tempo: str
    praticavel: bool
    fonte: FonteDado = FonteDado.MANUAL


class ItemPessoal(BaseModel):
    funcao: str
    quantidade: int


class Equipamento(BaseModel):
    nome: str
    quantidade: int


class Servico(BaseModel):
    descricao: str
    situacao: str
    grupo: Optional[str] = None


class EventosRestricao(BaseModel):
    pessoal: bool = False
    equipamento: bool = False
    instalacoes: bool = False
    cronograma_fisico: bool = False
    qualidade: bool = False
    atendimento_fiscalizacao: bool = False
    administracao_obra: bool = False
    meio_ambiente: bool = False
    descricao: Optional[str] = None
