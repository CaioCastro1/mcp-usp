"""Peças compartilhadas da suíte do Jupiter.

Nenhum caminho absoluto de máquina: tudo sai da posição deste arquivo.
Nenhuma fixture crua é impressa — só lida (§0 do CONVENTIONS.md).
"""
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "fixtures" / "jupiter"

# As quatro fixtures da fatia vertical (§4.1 do spec). Uma quinta aqui é
# alargar o escopo, e o teste da allowlist vai reclamar.
FATIA = {
    "psi3323": "dwr-pubObterDisciplina-PSI3323.txt",
    "ptc3314": "dwr-pubObterDisciplina-PTC3314.txt",
    "requisito": "dwr-pubListarRequisitoDisciplina-MAT2454.txt",
    "erro": "dwr-pubObterDisciplina-ERRO-sigla-inexistente.txt",
}

SENTINELA_ESQUELETO = "ESQUELETO-FASE2"


def caminho(chave):
    return FIXTURES / FATIA[chave]


def texto(chave):
    return caminho(chave).read_text(encoding="utf-8")


def fonte_de(modulo):
    """Fonte de um módulo, recusando-se a ler esqueleto.

    Três testes provam uma AUSÊNCIA no fonte (nada de eval, nada de token,
    nada de choke point). Contra o esqueleto praticamente vazio os três
    ficariam verdes verificando nada — medido. Este guarda transforma esse
    falso-verde em vermelho honesto.
    """
    fonte = pathlib.Path(modulo.__file__).read_text(encoding="utf-8")
    assert SENTINELA_ESQUELETO not in fonte, (
        f"{modulo.__name__} ainda é esqueleto. Uma varredura de fonte aqui "
        "passaria espuriamente: só significa algo depois da Fase 2."
    )
    return fonte


class Gravador:
    """Transporte falso: devolve fixture e guarda a requisição que teria saído.

    É o que torna os testes de corpo de requisição possíveis. Sem ele, corpo
    DWR malformado passa despercebido — o Jupiter responde 200 de qualquer
    jeito, e o erro aparece como campo vazio em vez de falha.
    """

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.chamadas = []

    def __call__(self, url, corpo, cabecalhos):
        self.chamadas.append({"url": url, "corpo": corpo, "cabecalhos": dict(cabecalhos)})
        if len(self._respostas) > 1:
            return 200, self._respostas.pop(0)
        return 200, self._respostas[0]


@pytest.fixture
def psi3323():
    return texto("psi3323")


@pytest.fixture
def ptc3314():
    return texto("ptc3314")


@pytest.fixture
def requisito():
    return texto("requisito")


@pytest.fixture
def erro():
    return texto("erro")


@pytest.fixture
def gravador():
    return Gravador


# --- A fatia de requisitos (14/09). HTML, não DWR: outra superfície, outro
# transporte, e por isso fixtures próprias. Todas de dado público — o §5 do
# design mediu 0 ocorrência de nome de docente nas três.
REQUISITOS = {
    "psi3323_html": "html-listarCursosRequisitos-PSI3323.html",
    "mat2455_html": "html-listarCursosRequisitos-MAT2455.html",
    "ptc3313_html": "html-listarCursosRequisitos-PTC3313.html",
    "ingresso_poli": "dwr-pubListarCursoEntrada-codclg3.txt",
}


def html(chave):
    """O JupiterWeb serve ISO-8859-1, e ler como UTF-8 estoura no primeiro
    acento. A decodificação é responsabilidade de quem lê o fio, então o teste
    passa BYTES adiante — é o que o transporte real entrega."""
    return (FIXTURES / REQUISITOS[chave]).read_bytes()


@pytest.fixture
def psi3323_html():
    return html("psi3323_html")


@pytest.fixture
def mat2455_html():
    return html("mat2455_html")


@pytest.fixture
def ptc3313_html():
    return html("ptc3313_html")


@pytest.fixture
def ingresso_poli():
    return (FIXTURES / REQUISITOS["ingresso_poli"]).read_text(encoding="utf-8")
