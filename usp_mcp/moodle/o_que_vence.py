"""A ferramenta: "o que eu tenho que entregar?" (§5).

O nome vem da pergunta do dono, não da função do Moodle: ninguém pergunta
"me dá `core_calendar_get_action_events_by_timesort`", pergunta "o que vence
essa semana". Esta função é a fronteira de uma chamada só (critério 2 do §5) —
uma função escolhida à mão, um parâmetro real (a janela de tempo), texto curto
na saída (critério 3 do §5).

O motivo do `vazio_por` está no §9 de 28/08: `MOODLE_USERID` estava com o
número USP em vez do userid interno, e `get_users_courses` devolvia `[]`. Do
lado de quem lê, "não tem nada para entregar" e "você perguntou errado" são
indistinguíveis se a saída não rotula por quê está vazia. Por isso zero
vencimento aqui não vira silêncio: vira `vazio_por="sem_eventos_no_periodo"`
mais a janela por extenso no texto — e um erro do cliente (token recusado,
Moodle fora do ar) nunca é engolido para virar essa mesma lista vazia; ele
sobe (T38), porque as duas falhas têm curas diferentes.

A janela (`dias`) é parâmetro da CHAMADA (`timesortfrom`/`timesortto`), não
filtro aplicado depois de baixar a resposta inteira: filtrar em memória já
pagou o custo de transporte que este módulo existe para evitar (ver docstring
de `projecao.py` — ~528 kB crus por chamada). A redução de payload para texto
fica por conta de `projecao.projetar_eventos`; esta função só decide a janela,
faz a única chamada, e formata o `Resultado` dela em texto compacto.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .projecao import FUSO_SAO_PAULO, Vencimento, projetar_eventos

# Abreviação de dia da semana em português. datetime.weekday() é 0=segunda,
# ..., 6=domingo — não usamos strftime("%a") porque isso depende do locale do
# processo (em inglês por padrão) e não deve variar entre máquinas.
_DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

# Nome da atividade do Moodle (`modulename`) traduzido pro que o dono lê. Só
# tarefa e questionário aparecem no calendário do Moodle (ver COBERTURA em
# projecao.py); um `modulename` fora daí cai no fallback (o nome cru), porque
# um rótulo desconhecido é melhor que um rótulo inventado.
_TIPOS_PT = {"assign": "tarefa", "quiz": "questionário"}

# Teto de `limitnum` aceito pelo web service, medido em 31/08/2026 contra o
# e-Disciplinas: `limitnum=-5` responde "Limit must be between 1 and 50
# (inclusive)". E o DEFAULT, quando não se manda nada, é 20 — silenciosamente.
# Medido: a mesma janela de 365 dias devolve 20 eventos sem `limitnum` e 30 com
# `limitnum=50`. Não mandar o parâmetro é perder entrega sem aviso, que é
# exatamente o que o Invariante 7 proíbe.
_LIMITE_DA_API = 50


@dataclass(frozen=True)
class RespostaOQueVence:
    """Saída da ferramenta: texto curto pronto pro modelo, mais o que ele
    precisa saber sem reabrir o texto (`truncado`, `vazio_por`)."""

    texto: str
    truncado: bool
    vazio_por: str | None


def _formatar_data(quando: datetime) -> str:
    """"dom 06/09 23:59" — curto de propósito (T39: poucos milhares de
    caracteres para dezenas de eventos)."""
    dia = _DIAS_SEMANA[quando.weekday()]
    return f"{dia} {quando.day:02d}/{quando.month:02d} {quando.hour:02d}:{quando.minute:02d}"


def _formatar_linha(v: Vencimento) -> str:
    # Sem URL de propósito: ~55 caracteres por evento estourariam o
    # orçamento de T39 (528 kB crus -> < 4.000 caracteres) sem responder à
    # pergunta "o que vence, quando, em que disciplina".
    tipo = _TIPOS_PT.get(v.tipo, v.tipo)
    quando = _formatar_data(v.quando) if v.quando is not None else "sem data"
    return f"{quando} {v.disciplina} ({tipo}): {v.nome}"


def o_que_vence(
    cliente, dias: int = 14, agora=None, limite: int | None = None
) -> RespostaOQueVence:
    """Uma chamada ao Moodle, projeta, e devolve texto curto que diz o que não sabe."""
    # `agora` no fuso de São Paulo (ver projecao.FUSO_SAO_PAULO: literal -3,
    # não fuso nomeado) — reaproveitado em vez de duplicado.
    agora = agora if agora is not None else datetime.now(FUSO_SAO_PAULO)
    inicio = agora
    fim = agora + timedelta(days=dias)

    # A janela vira parâmetro da ÚNICA chamada (T32, T33) — nunca filtro
    # aplicado depois de baixar a resposta inteira.
    bruto = cliente.chamar(
        "core_calendar_get_action_events_by_timesort",
        timesortfrom=int(inicio.timestamp()),
        timesortto=int(fim.timestamp()),
        limitnum=_LIMITE_DA_API,
    )
    # Um erro do cliente (ErroMoodle e subclasses) sobe daqui sem ser
    # capturado: T38 é o outro lado do bug do §9 de 28/08 — falha de
    # credencial não pode virar lista vazia.

    resultado = projetar_eventos(bruto)

    # Se o Moodle devolveu exatamente o teto que pedimos, NÃO dá para saber se
    # existe mais depois disso — a API não diz. Declarar a dúvida é o Invariante
    # 7; presumir que acabou é o bug que essa detecção existe para não repetir.
    no_teto_da_api = len(bruto.get("events", [])) >= _LIMITE_DA_API

    vencimentos = resultado.vencimentos
    total = len(vencimentos)
    truncado = (limite is not None and total > limite) or no_teto_da_api
    if truncado:
        vencimentos = vencimentos[:limite]

    linhas = [_formatar_linha(v) for v in vencimentos]

    if resultado.vazio_por is not None:
        # Zero evento é resposta legítima (T37) — mas rotulada, para não ser
        # confundida com o bug do §9 de 28/08 (credencial errada disfarçada
        # de "não tem nada").
        cabecalho = f"Nenhum vencimento nos próximos {dias} dias."
    elif truncado:
        # Invariante 7: truncamento declarado, não silencioso (T35).
        cabecalho = (
            f"Mostrando os primeiros {limite} de {total} vencimentos "
            f"nos próximos {dias} dias:"
        )
    else:
        cabecalho = f"Vencimentos nos próximos {dias} dias ({total} encontrados):"

    partes = [cabecalho, *linhas]

    if no_teto_da_api:
        # Sem isto, "não tem mais nada" e "o Moodle parou de contar em 50" são
        # indistinguíveis para quem lê.
        partes.append(
            f"O e-Disciplinas devolve no máximo {_LIMITE_DA_API} eventos por "
            "consulta e atingiu esse teto: pode haver mais depois do último "
            "item. Reduza a janela de dias para ver o resto."
        )

    if resultado.sem_data:
        # Invariante 7 de novo: eventos descartados por falta de data usável
        # não desaparecem silenciosamente da contagem.
        partes.append(
            f"{resultado.sem_data} evento(s) sem data utilizável não entraram "
            "nesta lista."
        )

    # Invariante 6 na resposta ao usuário (T40): o que este calendário NÃO
    # cobre (prova presencial etc.) é dito, não presumido.
    partes.append(resultado.cobertura)

    texto = "\n".join(partes)

    return RespostaOQueVence(
        texto=texto, truncado=truncado, vazio_por=resultado.vazio_por
    )
