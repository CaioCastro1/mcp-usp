"""R5-R10: allowlist e ausência de segredo.

Camada 1: nada aqui depende de resposta da USP. O que estes testes protegem é
uma propriedade do §6 do SPEC1 que é fácil de perder num refactor: **este é o
servidor que pode ser hospedado justamente porque não carrega credencial de
ninguém**. No dia em que alguém acrescentar uma variável de ambiente com
segredo aqui, essa decisão de empacotamento morre em silêncio.
"""
import pytest

from tests.rucard.conftest import HASH_DE_TESTE, carregar, fonte_de
from usp_mcp.rucard import cliente as mod_cliente
from usp_mcp.rucard import politica
from usp_mcp.rucard.erros import ConsultaNegada

pytestmark = pytest.mark.politica


def test_r5_rota_fora_da_allowlist_e_negada_com_motivo():
    for rota in ("saldo", "extrato", "recarga", "menu/6/../../admin", ""):
        d = politica.decidir(rota)
        assert not d.permitida, f"rota {rota!r} passou pela allowlist"
        assert d.motivo, "negativa sem motivo é o silêncio que o Invariante 6 proíbe"

    assert politica.decidir("restaurants").permitida
    assert politica.decidir("menu", ru="6").permitida


def test_r6_ru_fora_do_escopo_e_negado_e_o_motivo_distingue_de_inexistente():
    # "existe mas não foi liberado" e "não existe no RUCard" têm curas
    # diferentes para quem lê o erro: a primeira é decisão de §9, a segunda é
    # id errado. Uma negativa genérica confunde as duas.
    fora = politica.decidir("menu", ru="13")  # EACH, capturado em 27/08
    assert not fora.permitida
    assert "13" in fora.motivo
    assert "escopo" in fora.motivo.lower()

    inexistente = politica.decidir("menu", ru="4242")
    assert not inexistente.permitida
    assert "4242" in inexistente.motivo

    assert fora.motivo != inexistente.motivo, (
        "o mesmo motivo para RU fora de escopo e para RU inexistente apaga a "
        "diferença que quem lê o erro precisa ver."
    )


def test_r6b_os_quatro_ids_permitidos_sao_exatamente_os_do_recorte_do_dono():
    # §1.2: 6 CENTRAL, 7 PUSP-CB, 8 FÍSICA, 9 QUÍMICAS. Conjunto inteiro
    # comparado de propósito — crescer é decisão registrada, não conveniência.
    assert set(politica.RUS_PERMITIDOS) == {"6", "7", "8", "9"}

    # E os ids têm que ser os que a API de verdade usa: um alias trocado aqui
    # apontaria para outro RU sem ninguém notar (§1.2: resolver por id).
    do_catalogo = {
        r["id"]: r["alias"]
        for campus in carregar("restaurantes")
        for r in campus["restaurants"]
    }
    for id_, nome in politica.RUS_PERMITIDOS.items():
        assert do_catalogo[id_] == nome, (
            f"id {id_} é {do_catalogo[id_]!r} na API e {nome!r} na allowlist"
        )


def test_r7_permitir_escrita_nao_libera_nada():
    # Invariante 1. Nenhuma rota de escrita do RUCard foi mapeada na Fase 1 —
    # e uma flag não inventa fonte. Se algum dia houver, a decisão passa pelo
    # §9 e por este teste.
    for rota in ("recarga", "saldo", "menu/6/pedido"):
        assert not politica.decidir(rota, permitir_escrita=True).permitida
    assert set(politica.ROTAS_PERMITIDAS) == {"menu", "restaurants"}


def test_r8_o_valor_da_hash_nao_aparece_em_fonte_nenhum():
    """A hash não pode estar hardcodada no pacote — e nem AQUI.

    Primeira versão deste teste trazia o valor real como agulha, e o gate
    reprovou o commit: a isenção do §9 é por PAR (variável, arquivo), e vale só
    para `.env.example` e `SPEC1.md`. O gate estava certo, e o conserto deixou o
    teste melhor: em vez de procurar uma constante escrita à mão, ele procura a
    hash que estiver REALMENTE configurada. Nenhuma mensagem daqui ecoa o valor
    (Invariante 3) — por isso `pytest.fail`, e não `assert x not in y`, que
    imprimiria os dois lados da comparação.
    """
    import os
    from pathlib import Path

    from usp_mcp.env import carregar_env

    carregar_env()
    valor = os.environ.get("RUCARD_HASH", "")
    if not valor:
        pytest.fail(
            "RUCARD_HASH não está no ambiente nem no .env: esta checagem não "
            "verificou nada. Checagem que não pôde rodar reprova, em vez de "
            "reportar OK (mesma regra do scripts/gate.sh)."
        )

    fonte_de(mod_cliente)  # recusa esqueleto: varredura de fonte vazia é falso-verde
    diretorio = Path(mod_cliente.__file__).parent
    for arquivo in sorted(diretorio.glob("*.py")):
        if valor in arquivo.read_text(encoding="utf-8"):
            pytest.fail(
                f"a hash do RUCard está hardcodada em {arquivo.name}. Ela vem do "
                "ambiente (RUCARD_HASH); o gate reprova a colocação em qualquer "
                "arquivo fora do par isento."
            )


def test_r9_o_cliente_nao_le_credencial_pessoal():
    fonte = fonte_de(mod_cliente)
    for agulha in ("MOODLE_TOKEN", "MOODLE_URL", "wstoken", "authtoken", "privatetoken"):
        assert agulha not in fonte, (
            f"{agulha!r} no cliente do RUCard. Este é o servidor que o §6 do "
            "SPEC1 quer hospedar — ele não pode virar portador de credencial."
        )
    # Nenhum cookie, nenhuma sessão: a rota é pública e stateless.
    for agulha in ("Cookie", "set-cookie", "JSESSIONID"):
        assert agulha not in fonte


def test_r10_o_default_e_negar():
    # Uma rota que ninguém pensou ainda tem que ser negada sem ninguém
    # acrescentá-la a lista nenhuma (Invariante 2: allowlist, não denylist).
    assert not politica.decidir("rota-que-ainda-nao-existe").permitida
    assert not politica.decidir("MENU").permitida, "allowlist não é case-insensitive"


def test_r10b_o_cliente_aplica_a_politica_antes_de_qualquer_io(gravador):
    # A política mora no cliente, não na ferramenta: qualquer código novo que
    # instancie o cliente direto passa por ela. Um RU negado não toca o
    # transporte — nem uma requisição sai.
    transporte = gravador({})
    c = mod_cliente.ClienteRucard(transporte, hash_rucard=HASH_DE_TESTE)

    with pytest.raises(ConsultaNegada):
        c.menu("13")

    assert transporte.chamadas == [], (
        "saiu requisição para um RU negado: a política rodou depois do I/O, ou "
        "não rodou."
    )
