"""Projeção de `/restaurants` — 27,7 kB de tabela de apoio viram ficha curta.

Esta rota é a resposta mais cara do projeto (~6.900 tokens) e a mais estática:
medida byte-idêntica em 27/08 e 31/08/2026. Ela **não é resposta** — é o que
transforma um `FECHADO` do cardápio em "não serve essa refeição" ou "fechado
neste dia", e é onde mora o preço.

Três armadilhas documentadas desta rota, e o que este módulo faz com elas:

**Todo valor é string** (§1.2), inclusive preço com vírgula decimal e booleano.
O preço sai daqui como veio: converter `"2,00"` para float é inventar precisão e
perder o formato que a USP publica.

**O campo de "tem caixa" vem `"false"` nos 18 RUs**, inclusive nos 14 que têm
caixa preenchido — e é a *string* `"false"`, que em JS é truthy. O número de
caixas sai do tamanho da lista, e o campo errado não é lido em lugar nenhum
deste arquivo (há teste que varre o código fora desta docstring).

**Horário é por dia da semana, não por dia.** `weekdays`, `saturday` e `sunday`
— e é essa granularidade que permite distinguir "fechado hoje" de "não serve".
Medido: o 7 não publica jantar em dia nenhum, o 8 não publica café, e o 9 é o
único dos quatro com fim de semana (sábado almoço e jantar, domingo só almoço).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import politica

# Vocabulário da pergunta → chave da API. "almoco" sem cedilha de propósito: é
# valor de enum que trafega em JSON e chega digitado por modelo.
REFEICOES: tuple[str, ...] = ("cafe", "almoco", "jantar")
_CHAVE_API = {"cafe": "breakfast", "almoco": "lunch", "jantar": "dinner"}

# datetime.weekday(): 0=segunda … 6=domingo.
_CHAVE_DIA = (
    "weekdays", "weekdays", "weekdays", "weekdays", "weekdays", "saturday", "sunday",
)


@dataclass(frozen=True)
class Ficha:
    """O que a pergunta usa, e nada mais.

    Coordenada, telefone e foto ficam de fora: ninguém pergunta a latitude do
    bandejão, e cada campo é token gasto em toda resposta.
    """

    id: str
    nome: str
    campus: str
    endereco: str
    # {chave_dia: {refeicao: "11:15 às 14:15"}} — só o que vem preenchido.
    horarios: dict[str, dict[str, str]] = field(default_factory=dict)
    precos_aluno: dict[str, str] = field(default_factory=dict)
    caixas: int = 0


def _horarios_do_ru(bruto: dict) -> dict[str, dict[str, str]]:
    horarios: dict[str, dict[str, str]] = {}
    for chave_dia, refeicoes in (bruto.get("workinghours") or {}).items():
        preenchidas = {
            nosso: (refeicoes.get(deles) or "").strip()
            for nosso, deles in _CHAVE_API.items()
            if (refeicoes.get(deles) or "").strip()
        }
        if preenchidas:
            horarios[chave_dia] = preenchidas
    return horarios


def _precos_de_aluno(bruto: dict) -> dict[str, str]:
    """Preço de aluno, do primeiro caixa que publicar cada refeição.

    Vários caixas por RU é a regra (a lista existe), e o preço é o mesmo em
    todos nas amostras. Pegar o primeiro NÃO VAZIO por refeição evita que um
    caixa com campo em branco apague um preço que outro publica.
    """
    precos: dict[str, str] = {}
    for caixa in bruto.get("cashiers") or []:
        alunos = ((caixa.get("prices") or {}).get("students")) or {}
        for nosso, deles in _CHAVE_API.items():
            valor = (alunos.get(deles) or "").strip()
            if valor and nosso not in precos:
                precos[nosso] = valor
    return precos


def projetar(bruto) -> dict[str, Ficha]:
    """`/restaurants` cru → `{id: Ficha}`, só dos RUs da allowlist.

    O filtro é aqui, e não em quem chama: projetar os 18 e filtrar depois é
    exatamente como os outros 14 entram por acidente num refactor.
    """
    fichas: dict[str, Ficha] = {}
    for campus in bruto or []:
        for ru in campus.get("restaurants") or []:
            id_ = str(ru.get("id", ""))
            if id_ not in politica.RUS_PERMITIDOS:
                continue
            fichas[id_] = Ficha(
                id=id_,
                nome=(ru.get("alias") or ru.get("name") or "").strip(),
                campus=(campus.get("name") or "").strip(),
                endereco=(ru.get("address") or "").strip(),
                horarios=_horarios_do_ru(ru),
                precos_aluno=_precos_de_aluno(ru),
                caixas=len(ru.get("cashiers") or []),
            )
    return fichas


def horario(ficha: Ficha, dia: date, refeicao: str) -> str | None:
    """Horário publicado para aquela refeição naquele dia da semana, ou None."""
    return ficha.horarios.get(_CHAVE_DIA[dia.weekday()], {}).get(refeicao)


def serve(ficha: Ficha, dia: date, refeicao: str) -> bool:
    """Se o RU publica horário para essa refeição nesse dia da semana.

    É metade do cruzamento que o §1.2 pede: `/menu` sozinho diz `FECHADO` e não
    diz por quê. A outra metade (o que o cardápio diz) é decidida na ferramenta.
    """
    return horario(ficha, dia, refeicao) is not None


def serve_em_algum_dia(ficha: Ficha, refeicao: str) -> bool:
    """Se existe QUALQUER dia da semana com horário publicado para a refeição.

    Separa "não serve jantar hoje" de "não serve jantar em dia nenhum" — a
    primeira faz voltar amanhã, a segunda faz procurar outro RU.
    """
    return any(refeicao in dia for dia in ficha.horarios.values())
