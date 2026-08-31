"""R21-R25: o catálogo — 27,7 kB de tabela de apoio viram ficha curta.

`/restaurants` é a resposta mais cara do projeto (~6.900 tokens) e a mais
estática (byte-idêntica em 27/08 e 31/08). Ela não é resposta: é o que
transforma `FECHADO` em "não serve jantar" ou "fechado neste dia", e é onde
mora o preço.

Dois campos desta rota são armadilha documentada, e os dois têm teste aqui:
`hasCashier`, que vem `"false"` nos 18 RUs mesmo nos 14 com caixa, e o fato de
**todo** valor ser string — inclusive os preços, com vírgula decimal.
"""
import datetime
import json

import pytest

from tests.rucard.conftest import carregar, texto
from usp_mcp.rucard import catalogo, politica

pytestmark = pytest.mark.contrato

SEGUNDA = datetime.date(2026, 8, 31)
SABADO = datetime.date(2026, 9, 5)
DOMINGO = datetime.date(2026, 9, 6)


def _fichas():
    """Função, não fixture do pytest: construir o objeto sob teste numa fixture
    transforma `FAILED` em `ERROR`, e erro de setup não é vermelho honesto
    (§4 do CONVENTIONS.md)."""
    return catalogo.projetar(carregar("restaurantes"))


def test_r21_has_cashier_e_ignorado():
    fichas = _fichas()
    # O campo vem "false" nos 18 RUs, inclusive nos 14 que TÊM caixa. Quem o lê
    # responde "não tem caixa" para um RU que tem — e é a string "false", que
    # em JS é truthy, então errar nos dois sentidos é possível.
    for ficha in fichas.values():
        assert ficha.caixas >= 1, (
            f"RU {ficha.id} ficou sem caixa: provável leitura de hasCashier, "
            "que é sempre errado. Usar len(cashiers)."
        )
    fonte = open(catalogo.__file__, encoding="utf-8").read()
    assert "hasCashier" not in fonte.split('"""', 2)[-1], (
        "hasCashier aparece no CÓDIGO (fora da docstring). Ele é sempre errado."
    )


def test_r22_a_projecao_derruba_o_custo_do_catalogo():
    fichas = _fichas()
    # Bytes COMO A USP MANDA (o arquivo da captura), não o JSON re-serializado:
    # `json.dumps` compacta o espaço em branco e mede 19.574 B onde o fio
    # entregou 27.661. Medir a serialização de outra pessoa mede a outra pessoa.
    cru = len(texto("restaurantes").encode())
    projetado = len(
        json.dumps(
            {k: vars(v) for k, v in fichas.items()}, ensure_ascii=False, default=str
        ).encode()
    )
    assert cru > 25_000, "a fixture do catálogo encolheu: refaça a medida"
    assert projetado < 3_000, f"projeção do catálogo: {projetado} B"
    assert cru / projetado > 8, (
        f"razão de redução {cru / projetado:.1f}x. Devolver o catálogo cru são "
        "~6.900 tokens para responder 'onde fica e quanto custa'."
    )


def test_r23_serve_distingue_nunca_serve_de_fechado_hoje():
    fichas = _fichas()
    # Cruzamento medido em 31/08 e coerente com o cardápio das duas semanas:
    # o 7 não tem jantar publicado em dia nenhum; o 9 é o único dos quatro que
    # abre no fim de semana — sábado almoço e jantar, domingo só almoço.
    assert catalogo.serve(fichas["7"], SEGUNDA, "almoco")
    assert not catalogo.serve(fichas["7"], SEGUNDA, "jantar"), (
        "o RU 7 (PUSP-CB) não serve jantar: workinghours.weekdays.dinner é "
        "vazio, e os 7 jantares vêm FECHADO. Isolado, o /menu dele parece um "
        "RU quebrado."
    )

    assert catalogo.serve(fichas["6"], SEGUNDA, "jantar")
    assert not catalogo.serve(fichas["6"], SABADO, "almoco"), (
        "o RU 6 não tem horário de sábado publicado"
    )

    assert catalogo.serve(fichas["9"], SABADO, "almoco")
    assert catalogo.serve(fichas["9"], SABADO, "jantar")
    assert catalogo.serve(fichas["9"], DOMINGO, "almoco")
    assert not catalogo.serve(fichas["9"], DOMINGO, "jantar"), (
        "domingo do 9 tem almoço publicado e jantar vazio — e o cardápio de "
        "06/09 confirma: almoço aberto, jantar FECHADO."
    )


def test_r23b_cafe_da_manha_tem_horario_em_alguns_e_em_outros_nao():
    fichas = _fichas()
    # O café é o caso em que a API publica o SERVIÇO e não publica o cardápio.
    # A ferramenta responde isso (R30); aqui fica registrado quem tem horário.
    assert catalogo.horario(fichas["6"], SEGUNDA, "cafe") == "07:00 às 08:30"
    assert catalogo.horario(fichas["7"], SEGUNDA, "cafe") == "07:00 às 08:30"
    assert catalogo.horario(fichas["8"], SEGUNDA, "cafe") is None
    # No 9 o café só aparece no fim de semana — a nota da Fase 1 dizia "6 e 7",
    # e isso ficou incompleto (corrigido no §1.2 em 31/08).
    assert catalogo.horario(fichas["9"], SEGUNDA, "cafe") is None
    assert catalogo.horario(fichas["9"], SABADO, "cafe") == "07:30 às 09:00"


def test_r24_preco_de_aluno_vem_como_string_com_virgula():
    fichas = _fichas()
    for id_ in ("6", "7", "8", "9"):
        assert fichas[id_].precos_aluno["almoco"] == "2,00", (
            "o preço é string na API, com vírgula decimal. Converter para float "
            "é inventar precisão e perder a forma que a USP publica."
        )
    assert fichas["7"].precos_aluno.get("jantar") == "2,00", (
        "o 7 publica preço de jantar mesmo não servindo jantar: preço e "
        "horário são fontes diferentes, e quem manda sobre servir é o horário."
    )


def test_r25_ru_fora_da_allowlist_nao_entra_na_projecao():
    fichas = _fichas()
    assert set(fichas) == set(politica.RUS_PERMITIDOS), (
        f"a projeção trouxe {sorted(set(fichas) - set(politica.RUS_PERMITIDOS))}. "
        "Iterar sobre os 18 e projetar todos é como os outros 14 entram por "
        "acidente — e são 14 RUs que o dono decidiu não usar (§1.2)."
    )


def test_r25b_a_ficha_traz_o_que_a_pergunta_usa_e_nada_mais():
    fichas = _fichas()
    ficha = fichas["6"]
    assert ficha.nome == "CENTRAL"
    assert "Relógio Solar" in ficha.endereco
    assert ficha.campus == "Cidade Universitária"
    # Coordenada, telefone e foto não entram: ninguém pergunta a latitude do
    # bandejão, e cada campo é token gasto.
    despejo = json.dumps(vars(ficha), ensure_ascii=False, default=str)
    for gordura in ("latitude", "longitude", "photourl", "phones", "-23.56"):
        assert gordura not in despejo
