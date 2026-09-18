"""Questionário como objeto: "já fiz?", "ainda dá?", "perdi algum?".

No Moodle, **atividade** (`mod_assign`) e **questionário** (`mod_quiz`) são
objetos diferentes, e até 17/09/2026 este servidor tratava só o primeiro.
`ja_entreguei` recusa questionário por escrito (com razão: não há rascunho, há
orçamento de tentativa, e o vocabulário de estados dela não descreve isso), e
`o_que_vence` diz a data e nada mais. Metade dos vencimentos reais do dono é
questionário — 3 de 4 numa janela de 14 dias; 13 dos 20 itens de nota de
PTC3314 —, e ele perguntou por um e não teve resposta. O desenho inteiro está
em `docs/superpowers/specs/2026-09-17-questionario-como-objeto-design.md`.

**Uma pergunta em três tempos verbais, e uma ferramenta.** "Já fiz?", "quantas
tentativas sobram?" e "fechou e eu não fiz?" são a mesma consulta aos mesmos
dados: a lista de tentativas **finalizadas** do aluno em cada questionário.
O objeto tem quatro estados, e a linha que ninguém dava é a de baixo à
direita:

|  | aberto | fechado |
|---|---|---|
| **com tentativa finalizada** | FEITO, dá para refazer se sobrar | FEITO |
| **sem tentativa finalizada** | ainda no prazo | perdido |

`notas` não dá essa linha: item sem nota é `"-"` tanto para "não fiz" quanto
para "está oculta", e 9 dos 13 itens de quiz da captura estão ocultos.

**Duas funções, e não três.** `mod_quiz_get_quizzes_by_courses` diz que o
questionário existe, o nome, quando abre e fecha, e quantas tentativas permite
(`0` é ilimitadas). `mod_quiz_get_user_attempts` diz quantas o aluno finalizou
e quando. A de melhor nota ficou de fora de propósito: a nota do questionário
já sai em `notas`, e um segundo número por outro caminho é o problema, não a
solução — um número, um lugar.

**Este módulo nasceu ANTES da captura, e diz isso.** O worktree em que ele foi
escrito não tem token, e o projeto tem caso registrado do custo de escrever
projeção contra dicionário imaginado (`tests/moodle/test_forma_real.py`). Por
isso tudo que a projeção lê está declarado em `CAMPOS_LIDOS_*`, com teste que
lê o fonte por AST e exige igualdade, e cada campo cuja presença é hipótese
tem comportamento declarado para a ausência — que **fala**, em vez de degradar
calada como `grademax` degradou em `notas`:

- `attempts` ausente: a linha não fala de orçamento, e um aviso diz que o
  e-Disciplinas não informou quantas tentativas cada questionário permite.
  "Já fiz" continua respondido.
- `timeclose` ausente: "prazo não informado", com aviso. `0` é outra coisa —
  "sem fechamento", que o Moodle aceita — e nenhum dos dois vira 1970.
- lista de tentativas vazia: "sem tentativa finalizada" **deste** questionário.
  A existência veio da outra chamada, então o vazio aqui nunca é "você não tem
  questionário".

**A fronteira, herdada do spec de 15/09 e verificável.** Nenhum identificador
de tentativa entra por parâmetro nem sai na resposta: o `quizid` nasce na
primeira chamada, viaja para a segunda e morre ali; o id da tentativa chega na
segunda resposta e não é lido. `status` vai literal como `finished`, e a
projeção conta só o que está `finished` mesmo assim — tentativa em andamento
não conta, e o aviso diz. E este fonte não contém, nem em docstring, o nome de
nenhuma função de escrita da família: é o módulo que abre a família para
leitura, e um nome desses escrito aqui estaria a uma linha de ser chamado.

**Custo.** Uma chamada para a lista, uma por questionário consultado, com o
teto de `ja_entreguei` importado e não recopiado. Sob o teto, abertos primeiro
(do que fecha antes para o que fecha depois: onde ainda dá para agir), depois
fechados do mais recente para o mais antigo. Quem fica fora **aparece** na
lista com nome e prazo, sem estado — não consultar não é sumir. Questionário
que ainda não abriu não gasta chamada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .disciplinas import carregar, resolver, userid_do_token
from .erros import ErroMoodle
from .ja_entreguei import TETO_CONSULTAS
from .projecao import FUSO_SAO_PAULO, data_de
from .texto import casa, formatar_data

# Tudo que a projeção lê de cada item das duas respostas — e nada além. QO24
# lê o fonte por AST e exige igualdade com estes dois conjuntos; no dia da
# captura, QO25 os confronta com a resposta real. `intro`, `grade`,
# `sumgrades` e o id da tentativa não estão aqui de propósito.
CAMPOS_LIDOS_DO_QUESTIONARIO = ("id", "course", "name", "timeopen", "timeclose", "attempts")
CAMPOS_LIDOS_DA_TENTATIVA = ("state", "timefinish")

# O valor de `state` que conta como feita. Literal aqui e no parâmetro enviado.
_FINALIZADA = "finished"

# Os rótulos que quem pergunta lê. `SEM TENTATIVA FINALIZADA` e não `NÃO FEITO`:
# a frase é sobre o que o sistema registra, e a tentativa em curso (que não é
# contada) é o caso em que "não fez" seria falso.
_FEITO = "FEITO"
_SEM_TENTATIVA = "SEM TENTATIVA FINALIZADA"
_NAO_CONSULTADO = "não consultado"
_AINDA_NAO_ABRIU = "AINDA NÃO ABRIU"

# Os cinco estados de prazo de um questionário.
_FUTURO = "futuro"
_ABERTO = "aberto"
_FECHADO = "fechado"
_SEM_FECHAMENTO = "sem fechamento"
_PRAZO_NAO_INFORMADO = "prazo não informado"


@dataclass(frozen=True)
class Questionario:
    """Um quiz como `mod_quiz_get_quizzes_by_courses` o descreve.

    `fecha_informado` separa "o site mandou `timeclose: 0`" (sem fechamento,
    que existe) de "o site não mandou `timeclose`" (não sei). Os dois dão
    `fecha=None`, e só o segundo é hipótese derrubada.

    `tentativas_permitidas=None` é "o campo não veio", e `0` é "ilimitadas".
    Confundir os dois faria a ferramenta prometer tentativas que não sabe se
    existem.
    """

    quizid: int
    nome: str
    abre: datetime | None
    fecha: datetime | None
    fecha_informado: bool
    tentativas_permitidas: int | None
    courseid: int | None = None


@dataclass(frozen=True)
class Situacao:
    """Um questionário consultado e o que se sabe dele."""

    questionario: Questionario
    finalizadas: int = 0
    ultima: datetime | None = None


@dataclass(frozen=True)
class RespostaQuestionarios:
    texto: str
    total: int
    consultados: int
    truncado: bool
    vazio_por: str | None = None


def _inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def projetar_questionarios(bruto) -> tuple[Questionario, ...]:
    """`mod_quiz_get_quizzes_by_courses` → os questionários, na ordem do site.

    Das dezenas de chaves por quiz sobram seis. `intro` é a gorda (HTML do
    enunciado da atividade) e não responde nada daqui; `grade` e `sumgrades`
    são nota, e nota é assunto de `notas`.
    """
    lista = []
    for q in (bruto or {}).get("quizzes") or ():
        fecha_cru = q.get("timeclose")
        permitidas_cru = q.get("attempts")
        lista.append(
            Questionario(
                quizid=q.get("id"),
                nome=q.get("name") or "",
                abre=data_de(q.get("timeopen")),
                fecha=data_de(fecha_cru),
                fecha_informado=_inteiro(fecha_cru),
                tentativas_permitidas=(
                    permitidas_cru
                    if _inteiro(permitidas_cru) and permitidas_cru >= 0
                    else None
                ),
                courseid=q.get("course"),
            )
        )
    return tuple(lista)


def projetar_tentativas(bruto) -> tuple[int, datetime | None]:
    """`mod_quiz_get_user_attempts` → (quantas finalizadas, quando foi a última).

    Conta só `state == "finished"` mesmo tendo pedido `status=finished`: um
    site que ignore o parâmetro não pode fazer esta ferramenta contar uma
    tentativa em curso como feita. O id da tentativa e `sumgrades` não são
    lidos — é a fronteira do módulo, no fonte.
    """
    finalizadas = 0
    ultima: datetime | None = None
    for a in (bruto or {}).get("attempts") or ():
        if a.get("state") != _FINALIZADA:
            continue
        finalizadas += 1
        quando = data_de(a.get("timefinish"))
        if quando is not None and (ultima is None or quando > ultima):
            ultima = quando
    return finalizadas, ultima


def _situacao_de_prazo(q: Questionario, agora: datetime) -> str:
    if q.abre is not None and q.abre > agora:
        return _FUTURO
    if not q.fecha_informado:
        return _PRAZO_NAO_INFORMADO
    if q.fecha is None:
        return _SEM_FECHAMENTO
    return _FECHADO if q.fecha < agora else _ABERTO


# O sentinela leva fuso, pelo mesmo motivo anotado em `ja_entreguei`: comparar
# `datetime.max` ingênuo com data ciente do fuso levanta TypeError.
_FIM_DA_FILA = datetime.max.replace(tzinfo=FUSO_SAO_PAULO)


def _ordem_de_consulta(qs, agora: datetime) -> list[Questionario]:
    """Quem é consultado primeiro sob o teto — e é a ordem em que a lista sai.

    Abertos primeiro, do que fecha antes para o que fecha depois: é onde ainda
    dá para agir. Depois os fechados, do mais recente para o mais antigo:
    "perdi o de semana passada" é pergunta, "perdi o de março" não é. Os que
    ainda não abriram ficam de fora daqui — não podem ter tentativa.
    """
    por_estado = {q.quizid: _situacao_de_prazo(q, agora) for q in qs}
    abertos = sorted(
        (q for q in qs if por_estado[q.quizid] in (_ABERTO, _SEM_FECHAMENTO, _PRAZO_NAO_INFORMADO)),
        key=lambda q: q.fecha or _FIM_DA_FILA,
    )
    fechados = sorted(
        (q for q in qs if por_estado[q.quizid] == _FECHADO),
        key=lambda q: q.fecha,
        reverse=True,
    )
    return abertos + fechados


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _orcamento(q: Questionario, s: Situacao, estado: str) -> str:
    """"1 de 3 tentativas usadas" — ou nada, se o site não disse quantas são."""
    n = q.tentativas_permitidas
    if n is None:
        # Chave ausente: o aviso da resposta diz que não veio. Aqui, silêncio —
        # "1 usada" sem o "de 3" leria como ilimitadas, que é afirmar a mais.
        return ""
    if n == 0:
        return "; tentativas ilimitadas"
    if s.finalizadas == 0:
        if estado == _FECHADO:
            # "3 disponíveis" sobre um questionário fechado é promessa falsa.
            return ""
        return f"; {n} {_plural(n, 'tentativa disponível', 'tentativas disponíveis')}"
    texto = f"; {s.finalizadas} de {n} tentativas usadas"
    sobram = n - s.finalizadas
    if estado != _FECHADO and sobram > 0:
        texto += f" — ainda dá para refazer {sobram} {_plural(sobram, 'vez', 'vezes')}"
    return texto


def _formatar_linha(q: Questionario, s: Situacao | None, agora: datetime) -> str:
    estado = _situacao_de_prazo(q, agora)
    if estado == _FUTURO:
        return f"abre {formatar_data(q.abre)}  {q.nome}: {_AINDA_NAO_ABRIU}"

    if estado in (_ABERTO, _FECHADO):
        prazo = formatar_data(q.fecha)
    else:
        prazo = estado  # "sem fechamento" ou "prazo não informado"
    linha = f"{prazo}  {q.nome}: "

    if s is None:
        return linha + f"{_NAO_CONSULTADO} (teto de {TETO_CONSULTAS} por chamada)"

    if s.finalizadas:
        linha += (
            f"{_FEITO} — {s.finalizadas} "
            f"{_plural(s.finalizadas, 'tentativa finalizada', 'tentativas finalizadas')}"
        )
        if s.ultima is not None:
            linha += f", a última em {formatar_data(s.ultima)}"
    else:
        linha += _SEM_TENTATIVA

    if estado == _FECHADO:
        linha += " (fechado)" if s.finalizadas else " — PRAZO VENCIDO"
    elif estado == _ABERTO:
        linha += " — ainda no prazo"

    return linha + _orcamento(q, s, estado)


# Os avisos fixos. Saem em toda resposta que tem questionário consultado.
_SO_LEITURA = (
    "Esta ferramenta só lê. Ela não abre, não responde e não finaliza "
    "questionário, e não há configuração que a faça fazer isso — para "
    "responder, use a página do e-Disciplinas."
)

# Sem a palavra "usadas" de propósito: ela é o vocabulário do orçamento, e
# QO12 exige que o orçamento fique em silêncio quando o site não informou o
# permitido. Este aviso vale independentemente disso.
_EM_ANDAMENTO = (
    "Tentativa EM ANDAMENTO não conta: só a finalizada conta como feita. Se "
    "você tem uma aberta agora, ela não aparece aqui, e a contagem de "
    "tentativas finalizadas está uma abaixo do que você vê na tela."
)

COBERTURA = (
    "Esta resposta cobre só QUESTIONÁRIO. Tarefa de entrega é `ja_entreguei`; "
    "a nota de cada questionário, quando lançada, sai em `notas`."
)

_ORCAMENTO_NAO_INFORMADO = (
    "O e-Disciplinas não informou, para esta conta, quantas tentativas cada "
    "questionário permite: dá para dizer se você já fez, mas não quantas vezes "
    "ainda pode fazer."
)


def _quantos_warnings(bruto) -> int:
    return len((bruto or {}).get("warnings") or ())


def _aviso_da_lista(quantos: int) -> str:
    return (
        f"O e-Disciplinas avisou que {quantos} atividade(s) desta disciplina "
        "não puderam ser lidas com esta credencial: pode haver questionário "
        "fora desta lista."
    )


def _aviso_do_estado(quantos: int) -> str:
    return (
        f"O e-Disciplinas avisou ao responder sobre {quantos} questionário(s) "
        f"desta lista: o estado deles pode estar incompleto, e um "
        f"{_SEM_TENTATIVA} aqui pode ser que não deu para ler — que não é a "
        "mesma coisa."
    )


def _aviso_de_prazo_nao_informado(quantos: int) -> str:
    return (
        f"O e-Disciplinas não informou a data de fechamento de {quantos} "
        "questionário(s): eles aparecem acima sem estado de prazo."
    )


def questionarios(
    cliente, disciplina: str, questionario: str | None = None, agora=None
) -> RespostaQuestionarios:
    """Uma disciplina, uma ida para listar, uma ida por questionário consultado.

    Sigla que não resolve levanta erro legível **sem** gastar chamada de quiz.
    `agora` é um DATETIME (o instante da pergunta) e o `agora` de `carregar` é
    um RELÓGIO — mesma armadilha anotada em `ja_entreguei`, e nada é encaminhado.
    """
    agora = agora if agora is not None else datetime.now(FUSO_SAO_PAULO)
    lista = carregar(cliente)
    resolucao = resolver(lista, disciplina)
    if resolucao.disciplina is None:
        raise ErroMoodle(resolucao.motivo)
    alvo = resolucao.disciplina
    # Derivado do token, cache quente: zero chamada nova.
    userid = userid_do_token(cliente)

    # Escopo explícito, sempre: sem `courseids[0]` a função devolve todos os
    # cursos, e ninguém mediu o que isso custa em 74 matrículas.
    bruto = cliente.chamar(
        "mod_quiz_get_quizzes_by_courses", **{"courseids[0]": alvo.courseid}
    )
    todos = projetar_questionarios(bruto)
    nao_listados = _quantos_warnings(bruto)
    cabecalho = f"{alvo.sigla} ({alvo.rotulo}) — questionários"

    if not todos:
        avisos = [_aviso_da_lista(nao_listados)] if nao_listados else []
        avisos.extend([_SO_LEITURA, COBERTURA])
        return RespostaQuestionarios(
            texto=f"{cabecalho}\n\nEsta disciplina não tem nenhum questionário "
            "no e-Disciplinas." + "".join(f"\n\n⚠ {a}" for a in avisos),
            total=0,
            consultados=0,
            truncado=False,
            vazio_por="sem_questionarios",
        )

    filtro = (questionario or "").strip()
    escolhidos = [q for q in todos if casa(filtro, q.nome)]

    if filtro and not escolhidos:
        # "Nada com esse nome" ≠ "nada para fazer": o total e os nomes são o que
        # separa as duas. E a cobertura sai AQUI também — é o ramo de quem
        # pergunta por uma tarefa pelo nome, e o simétrico dele em
        # `ja_entreguei` ficou mudo sobre questionário até 17/09.
        avisos = [_aviso_da_lista(nao_listados)] if nao_listados else []
        avisos.extend([_SO_LEITURA, COBERTURA])
        return RespostaQuestionarios(
            texto=(
                f"{cabecalho}\n\nNenhum questionário com {questionario!r} no "
                f"nome. A disciplina tem {len(todos)}: "
                + ", ".join(q.nome for q in todos)
                + "."
                + "".join(f"\n\n⚠ {a}" for a in avisos)
            ),
            total=len(todos),
            consultados=0,
            truncado=False,
            vazio_por="busca_sem_resultado",
        )

    ordem = _ordem_de_consulta(escolhidos, agora)
    futuros = [q for q in escolhidos if _situacao_de_prazo(q, agora) == _FUTURO]
    truncado = len(ordem) > TETO_CONSULTAS
    consultaveis = ordem[:TETO_CONSULTAS]
    cortados = ordem[TETO_CONSULTAS:]

    situacoes: dict[int, Situacao] = {}
    estados_incompletos = 0
    for q in consultaveis:
        # Um erro do cliente sobe daqui sem ser capturado: falha de credencial
        # não pode virar "você não fez nenhum".
        bruto_tentativas = cliente.chamar(
            "mod_quiz_get_user_attempts",
            quizid=q.quizid,
            userid=userid,
            status=_FINALIZADA,
            includepreviews=0,
        )
        if _quantos_warnings(bruto_tentativas):
            estados_incompletos += 1
        finalizadas, ultima = projetar_tentativas(bruto_tentativas)
        situacoes[q.quizid] = Situacao(q, finalizadas, ultima)

    linhas = [f"{cabecalho} ({len(todos)})", ""]
    linhas.extend(_formatar_linha(q, situacoes.get(q.quizid), agora) for q in ordem)
    linhas.extend(_formatar_linha(q, None, agora) for q in futuros)

    avisos = []
    if truncado:
        avisos.append(
            f"Esta consulta custa uma ida ao e-Disciplinas por questionário, e "
            f"para em {TETO_CONSULTAS}: {len(cortados)} questionário(s) de prazo "
            "mais antigo aparecem acima sem estado. Use o parâmetro "
            "`questionario` para perguntar por um deles pelo nome."
        )
    if nao_listados:
        avisos.append(_aviso_da_lista(nao_listados))
    if estados_incompletos:
        avisos.append(_aviso_do_estado(estados_incompletos))
    if any(q.tentativas_permitidas is None for q in consultaveis):
        avisos.append(_ORCAMENTO_NAO_INFORMADO)
    sem_prazo = sum(
        1 for q in escolhidos if _situacao_de_prazo(q, agora) == _PRAZO_NAO_INFORMADO
    )
    if sem_prazo:
        avisos.append(_aviso_de_prazo_nao_informado(sem_prazo))
    if consultaveis:
        avisos.append(_EM_ANDAMENTO)
    avisos.extend([_SO_LEITURA, COBERTURA])

    linhas.extend(f"\n⚠ {a}" for a in avisos)

    return RespostaQuestionarios(
        texto="\n".join(linhas),
        total=len(todos),
        consultados=len(consultaveis),
        truncado=truncado,
    )
