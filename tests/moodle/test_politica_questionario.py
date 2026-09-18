"""QO1-QO7: a família `mod_quiz_` abre para leitura, e a fronteira fica onde estava.

Camada 1, offline, sem rede e sem SDK — tabela de nomes contra uma decisão, no
mesmo espírito de `test_politica_entrega.py`, e num arquivo separado porque o
assunto é outro: lá, o que o projeto ESCREVE e sob que condição; aqui, o que
ele passa a LER numa família que tem as três escritas mais perigosas do §2.2 a
um prefixo de distância.

O desenho está em `docs/superpowers/specs/2026-09-17-questionario-como-objeto-
design.md`, e as duas coisas que estes sete testes travam:

1. **A fronteira é verificável, não cuidadosa.** Nenhum identificador de
   tentativa entra por parâmetro (QO6), e o módulo que toca a família não tem
   nome de escrita ao alcance da mão (QO7). Uma fronteira que dependesse de o
   modelo não querer seria frágil; estas dependem de o vocabulário não existir.
2. **Teto não é autorização.** O prefixo `mod_quiz_get_` entra em P5 e cobre
   cinco funções que o projeto recusa por escrito. QO4 e QO5 são o que impede a
   próxima sessão de ler o prefixo como permissão.
"""
from __future__ import annotations

import pathlib

import pytest

from usp_mcp.moodle import politica, server

pytestmark = pytest.mark.politica

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FONTE_QUESTIONARIOS = RAIZ / "usp_mcp" / "moodle" / "questionarios.py"

# Escritas à mão, e não derivadas do módulo: derivar faria os testes concordarem
# com o conjunto que encontrassem — inclusive um que tivesse perdido uma delas.
AS_TRES_DE_ESCRITA = (
    "mod_quiz_start_attempt",
    "mod_quiz_save_attempt",
    "mod_quiz_process_attempt",
)

# Escrita também, e o §2.2 não as nomeia: disparam evento no relatório do
# professor (catálogo §3.8). Estão aqui só para QO4 provar que o prefixo novo
# não as alcança — o item A2 do roadmap é quem decide se entram no bloqueio.
AS_QUATRO_VIEW = (
    "mod_quiz_view_quiz",
    "mod_quiz_view_attempt",
    "mod_quiz_view_attempt_summary",
    "mod_quiz_view_attempt_review",
)

# As duas leituras que ENTRAM (Decisão 2 do spec).
AS_DUAS_QUE_ENTRAM = (
    "mod_quiz_get_quizzes_by_courses",
    "mod_quiz_get_user_attempts",
)

# As duas leituras que entram no BLOQUEIO (R4): enunciado de prova em curso.
AS_DUAS_LEITURAS_BLOQUEADAS = (
    "mod_quiz_get_attempt_data",
    "mod_quiz_get_attempt_summary",
)

# Leituras que casam com o prefixo e ficam de fora por omissão — cada uma com a
# razão no spec: a gêmea, a de nota (um número, um lugar) e a de revisão (R3).
AS_TRES_FORA_POR_OMISSAO = (
    "mod_quiz_get_user_quiz_attempts",
    "mod_quiz_get_user_best_grade",
    "mod_quiz_get_attempt_review",
)

# R1: nenhum destes nomes pode ser propriedade de `inputSchema` de ferramenta
# nenhuma do Moodle. `id` entra porque é o nome que um `quizid` ganharia se
# alguém o abreviasse.
IDENTIFICADORES_PROIBIDOS = {"attemptid", "quizid", "cmid", "id"}


# ------------------------------------------------------------------ QO1 a QO5


@pytest.mark.parametrize("funcao", AS_TRES_DE_ESCRITA)
def test_qo1_as_tres_de_escrita_seguem_recusadas_com_qualquer_flag(funcao):
    """QO1 — regressão do §2.2 numa trilha que mexe nas vizinhas.

    Afrouxar aqui é o modo de falha desta mudança: as três estão a um prefixo
    das duas que entram, e a recusa tem de sobreviver às duas flags juntas.
    """
    assert funcao in politica.BLOQUEIO_PERMANENTE
    for kwargs in (
        {},
        {"permitir_escrita": True},
        {"confirmada": True},
        {"permitir_escrita": True, "confirmada": True},
    ):
        d = politica.decidir(funcao, **kwargs)
        assert not d.permitida, f"{funcao} passou com {kwargs}"
        assert "bloqueio permanente" in d.motivo


@pytest.mark.parametrize("funcao", AS_DUAS_LEITURAS_BLOQUEADAS)
def test_qo2_as_duas_leituras_de_prova_em_curso_estao_no_bloqueio(funcao):
    """QO2 — pertencimento, NUNCA cardinalidade.

    O spec de entrega propõe 40 → 38 e este 40 → 42 sobre nomes distintos; um
    teste que travasse a contagem quebraria conforme a ordem de merge. E são as
    primeiras funções de LEITURA da lista — o §2.2 passa a dizer também "não lê
    o que não pode estar no contexto de um modelo".
    """
    assert funcao in politica.BLOQUEIO_PERMANENTE, (
        f"{funcao} devolve o enunciado de uma tentativa em andamento e não está "
        "no bloqueio permanente. A allowlist a nega por omissão; a segunda camada "
        "é para o dia em que a allowlist errar — e R5 torna esse dia plausível."
    )
    assert not politica.decidir(funcao, permitir_escrita=True, confirmada=True).permitida


def test_qo2b_nenhum_nome_da_familia_esta_nas_duas_listas():
    familia_dos_dois_lados = {
        n for n in politica.ALLOWLIST if n.startswith("mod_quiz_")
    } & politica.BLOQUEIO_PERMANENTE
    assert not familia_dos_dois_lados, sorted(familia_dos_dois_lados)


@pytest.mark.parametrize("funcao", AS_DUAS_QUE_ENTRAM)
def test_qo3_as_duas_que_entram_sao_permitidas(funcao):
    """QO3 — a política não é um `return False` disfarçado para a família nova."""
    assert funcao in politica.ALLOWLIST
    assert politica.decidir(funcao).permitida


@pytest.mark.parametrize("funcao", AS_TRES_FORA_POR_OMISSAO)
def test_qo3b_as_vizinhas_de_leitura_ficam_fora_por_omissao(funcao):
    """QO3b — recusadas, e pelo motivo da OMISSÃO, não do bloqueio.

    A distinção importa para quem lê o motivo: "está fora da lista fechada" é
    decisão de §9 reversível com dado; "está no bloqueio permanente" não é.
    """
    assert funcao not in politica.ALLOWLIST
    assert funcao not in politica.BLOQUEIO_PERMANENTE
    d = politica.decidir(funcao)
    assert not d.permitida
    assert "lista é fechada" in d.motivo, d.motivo


def test_qo4_o_prefixo_novo_e_teto_e_nao_autorizacao():
    """QO4 — `mod_quiz_get_` casa com o que entra E com o que se recusa.

    É a primeira vez que o teto de P5 cobre função que o projeto recusa por
    escrito. Prefixo nunca foi autorização (T6): a autorização é igualdade
    exata de nome, e é o que este teste afirma para cada lado.
    """
    from tests.moodle.test_politica import PREFIXOS_DE_LEITURA

    assert "mod_quiz_get_" in PREFIXOS_DE_LEITURA, (
        "o prefixo da família não entrou em P5 — sem ele as duas novas reprovam P5"
    )
    for funcao in AS_DUAS_QUE_ENTRAM:
        assert funcao.startswith("mod_quiz_get_")
    for funcao in AS_TRES_DE_ESCRITA + AS_QUATRO_VIEW:
        assert not funcao.startswith("mod_quiz_get_"), (
            f"{funcao} é escrita e casa com o prefixo de leitura: o teto está furado"
        )
    # Casa, e é negada mesmo assim: teto ≠ autorização.
    for funcao in AS_DUAS_LEITURAS_BLOQUEADAS + AS_TRES_FORA_POR_OMISSAO:
        assert funcao.startswith("mod_quiz_get_")
        assert not politica.decidir(funcao).permitida, funcao


@pytest.mark.parametrize("funcao", AS_DUAS_LEITURAS_BLOQUEADAS)
def test_qo5_o_bloqueio_vence_a_allowlist_para_a_leitura_de_prova(funcao, monkeypatch):
    """QO5 — a segunda camada exercitada de verdade, como T3b, para a leitura.

    Põe a função bloqueada NA allowlist e exige que ela siga negada, com o
    motivo citando o bloqueio e não a omissão. É o cenário exato que R4 existe
    para cobrir: alguém lê o prefixo `mod_quiz_get_` como permissão e acrescenta
    "só mais uma" função de leitura da família.
    """
    monkeypatch.setattr(
        politica, "ALLOWLIST", politica.ALLOWLIST | frozenset({funcao})
    )
    d = politica.decidir(funcao)
    assert not d.permitida, f"{funcao} passou pela allowlist"
    assert "bloqueio permanente" in d.motivo


# ------------------------------------------------------------------ QO6 e QO7


def _propriedades_de_todas(monkeypatch, valor_da_flag: str) -> dict[str, set[str]]:
    monkeypatch.setenv(politica.NOME_DA_FLAG, valor_da_flag)
    return {
        f["name"]: set((f.get("inputSchema") or {}).get("properties") or {})
        for f in server.listar_ferramentas()
    }


@pytest.mark.parametrize("valor_da_flag", ["0", "1"])
def test_qo6_nenhuma_ferramenta_aceita_identificador_de_tentativa(monkeypatch, valor_da_flag):
    """QO6 — R1 travada por leitura do descritor, e não por convenção.

    Enquanto nenhuma ferramenta aceitar `attemptid`, `quizid` ou `cmid`, não
    existe pergunta cujo próximo passo útil seja "me arruma um attemptid" — e é
    só essa pergunta que encosta na função que fabrica um. Com a flag ligada e
    desligada, porque as duas de escrita também têm de obedecer.
    """
    por_ferramenta = _propriedades_de_todas(monkeypatch, valor_da_flag)
    assert "questionarios" in por_ferramenta, (
        "a ferramenta `questionarios` não está no descritor — este teste "
        "afirmaria a fronteira sobre um conjunto que não a inclui"
    )
    intrusos = {
        nome: sorted(props & IDENTIFICADORES_PROIBIDOS)
        for nome, props in por_ferramenta.items()
        if props & IDENTIFICADORES_PROIBIDOS
    }
    assert not intrusos, (
        f"ferramenta aceitando identificador de tentativa/quiz por parâmetro: "
        f"{intrusos}. Os parâmetros deste servidor são `disciplina` e um pedaço "
        "de nome — o id nasce dentro da invocação e morre nela."
    )


def test_qo7_o_modulo_de_questionarios_nao_tem_nome_de_escrita_ao_alcance():
    """QO7 — R6: vocabulário, e não só identificador.

    Substring sobre o fonte INTEIRO, docstring inclusive, como P2 faz para a
    camada live: um nome de função de escrita escrito no módulo que abre a
    família para leitura está a uma linha de ser chamado. O módulo explica a
    fronteira sem nomear o que fica do outro lado dela.
    """
    assert FONTE_QUESTIONARIOS.exists(), (
        f"{FONTE_QUESTIONARIOS} não existe. Se o módulo mudou de nome, mova esta "
        "guarda junto — ela é a única que lê o fonte dele."
    )
    fonte = FONTE_QUESTIONARIOS.read_text(encoding="utf-8")
    vigiados = politica.BLOQUEIO_PERMANENTE | politica.ESCRITA_CONFIRMADA
    presentes = sorted(n for n in vigiados if n in fonte)
    assert not presentes, (
        f"nomes de função bloqueada ou de escrita no fonte de "
        f"{FONTE_QUESTIONARIOS.name}: {presentes}"
    )
