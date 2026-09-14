"""Peças compartilhadas da suíte do RUCard.

Nenhum caminho absoluto de máquina: tudo sai da posição deste arquivo.
Nenhuma fixture crua é impressa — só lida (§0 do CONVENTIONS.md).

O `Gravador` daqui é primo do da suíte do Jupiter, com uma diferença que importa:
o do Jupiter devolve uma resposta por chamada em sequência, e aqui a resposta
depende da ROTA pedida — um `bandejao` faz 1 chamada de catálogo e 4 de menu,
e um dublê sequencial obrigaria o teste a conhecer a ordem interna da
ferramenta. Este mapeia rota→resposta, e guarda o que teria saído.
"""
import json
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "fixtures" / "rucard"

# A fatia: os 4 RUs da Cidade Universitária, o catálogo, o par de semanas do
# mesmo RU (é ele que torna o teste de virada de semana possível) e o erro real.
FATIA = {
    "menu_6": "menu_6.json",
    "menu_7": "menu_7.json",
    "menu_8": "menu_8.json",
    "menu_9": "menu_9.json",
    "menu_6_semana_seguinte": "menu_6_semana_31-08.json",
    # O 9 na semana seguinte: é o par que permite montar uma resposta em que um
    # RU publicou o dia pedido e outro ficou na semana anterior (R27b).
    "menu_9_semana_seguinte": "menu_9_semana_31-08.json",
    # O 7 na semana de 14/09: a primeira captura em que o campo de cardápio traz
    # um COMUNICADO em negrito markdown no fim de cada almoço. É a fixture do
    # caso "comunicado não é prato".
    "menu_7_avisos": "menu_7_semana_14-09.json",
    "restaurantes": "restaurants.json",
    "erro_500": "erro-500-get-menu6.html",
}

# As duas semanas capturadas, por extenso — os testes referenciam datas dentro
# delas, e um número solto no meio de uma asserção não se explica sozinho.
SEMANA_FASE1 = ("24/08/2026", "30/08/2026")  # captura de 27/08/2026
SEMANA_SEGUINTE = ("31/08/2026", "06/09/2026")  # captura de 31/08/2026

SENTINELA_ESQUELETO = "ESQUELETO-FASE2"


def caminho(chave):
    return FIXTURES / FATIA[chave]


def texto(chave):
    return caminho(chave).read_text(encoding="utf-8")


def carregar(chave):
    return json.loads(texto(chave))


def fonte_de(modulo):
    """Fonte de um módulo, recusando-se a ler esqueleto.

    Os testes que provam uma AUSÊNCIA no fonte (nada de hash, nada de token,
    nada de GET) ficariam verdes contra o esqueleto vazio verificando nada.
    Este guarda transforma esse falso-verde em vermelho honesto — é o mesmo
    truque da suíte do Jupiter, e ele já pagou por si lá.
    """
    fonte = pathlib.Path(modulo.__file__).read_text(encoding="utf-8")
    assert SENTINELA_ESQUELETO not in fonte, (
        f"{modulo.__name__} ainda é esqueleto. Uma varredura de fonte aqui "
        "passaria espuriamente: só significa algo depois da Fase 2."
    )
    return fonte


class Gravador:
    """Transporte falso: responde por rota e guarda a requisição que sairia.

    `respostas` é `{rota: texto}` — `"menu/6"`, `"restaurants"`. Valor pode ser
    `(status, texto)` para exercitar erro, ou uma lista de respostas quando o
    teste precisa que a MESMA rota devolva coisas diferentes em chamadas
    sucessivas (é assim que o teste de virada de semana funciona).
    """

    def __init__(self, respostas):
        self._respostas = dict(respostas)
        self.chamadas = []

    def __call__(self, url, corpo, cabecalhos):
        rota = url.split("/rucard/servicos/", 1)[-1]
        self.chamadas.append(
            {"url": url, "rota": rota, "corpo": corpo, "cabecalhos": dict(cabecalhos)}
        )
        resposta = self._respostas.get(rota)
        if resposta is None:
            raise AssertionError(
                f"o dublê não tem resposta para a rota {rota!r}. Rotas "
                f"disponíveis: {sorted(self._respostas)}. Se a ferramenta pediu "
                "uma rota inesperada, é isso que o teste deve reportar."
            )
        if isinstance(resposta, list):
            resposta = resposta.pop(0) if len(resposta) > 1 else resposta[0]
        if isinstance(resposta, tuple):
            return resposta
        return 200, resposta

    def rotas(self):
        return [c["rota"] for c in self.chamadas]


HASH_DE_TESTE = "0" * 32  # forma, não o valor real (Invariante 3)


@pytest.fixture
def gravador():
    return Gravador


@pytest.fixture
def respostas_da_fatia():
    """As 5 rotas que um `bandejao` completo pede, na semana da Fase 1."""
    return {
        "restaurants": texto("restaurantes"),
        "menu/6": texto("menu_6"),
        "menu/7": texto("menu_7"),
        "menu/8": texto("menu_8"),
        "menu/9": texto("menu_9"),
    }


@pytest.fixture
def cliente_de_fixture(gravador, respostas_da_fatia):
    """Cliente pronto contra fixture, com relógio parado.

    Fábrica, e não o objeto: construir o objeto sob teste dentro de uma fixture
    do pytest transforma `FAILED` em `ERROR` quando ele levanta — é um dos dois
    casos que o §4 do CONVENTIONS.md registra como já tendo mordido.
    """

    def fabricar(**kwargs):
        from usp_mcp.rucard.cliente import ClienteRucard

        transporte = kwargs.pop("transporte", None) or gravador(respostas_da_fatia)
        cliente = ClienteRucard(
            transporte,
            hash_rucard=kwargs.pop("hash_rucard", HASH_DE_TESTE),
            **kwargs,
        )
        return cliente, transporte

    return fabricar
