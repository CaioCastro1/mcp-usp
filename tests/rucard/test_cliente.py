"""R11-R20: o cliente — transporte, erro legível, cache com duas regras.

O que este arquivo protege e nenhuma outra camada protege:

**O método é POST.** Não por gosto: `GET /menu/6` devolve HTTP 500 com HTML do
Tomcat, medido em 27/08 e de novo em 31/08. Um refactor que "simplifique" para
GET quebra tudo, e o erro chega como HTML, não como falha de rede.

**O HTML do Tomcat morre aqui.** São 3.240 B de página de erro que não
respondem nada. Mesmo raciocínio do stack trace do Jupiter (§9 de 31/08): o
cru é a resposta ERRADA.

**O cache tem DUAS regras, não uma.** TTL protege a USP (Invariante 5); a
validação de semana protege a resposta. Só a primeira deixaria o cliente
devolver o cardápio da semana passada na segunda-feira, com cara de resposta
certa — o §1.2 registra que não há parâmetro de data e a captura de 31/08
mostrou a semana já virada às 19:22 de segunda.
"""
import datetime
import json

import pytest

from tests.rucard.conftest import HASH_DE_TESTE, texto
from usp_mcp.rucard import cliente as mod_cliente
from usp_mcp.rucard.cliente import ClienteRucard
from usp_mcp.rucard.erros import (
    HashAusente,
    RespostaInvalida,
    RucardIndisponivel,
)

pytestmark = pytest.mark.contrato

SEG_FASE1 = datetime.date(2026, 8, 24)
SEG_SEGUINTE = datetime.date(2026, 8, 31)


class Relogio:
    """Relógio injetável: o teste verifica a REGRA do TTL, não o valor da
    constante. Uma constante mudada de propósito não deve quebrar teste."""

    def __init__(self):
        self.agora = 1_000.0

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += segundos


def test_r11_a_requisicao_e_post_form_urlencoded_com_a_hash_no_corpo(cliente_de_fixture):
    c, transporte = cliente_de_fixture()
    c.menu("6", SEG_FASE1)

    (chamada,) = transporte.chamadas
    assert chamada["url"] == f"{mod_cliente.URL_BASE}/menu/6"
    assert chamada["corpo"] == f"hash={HASH_DE_TESTE}", (
        "o corpo tem que ser form-urlencoded com a hash: é o único parâmetro "
        "que a rota aceita (§1.2)."
    )
    assert chamada["cabecalhos"]["Content-Type"] == "application/x-www-form-urlencoded"
    # Identificável e com contato, como o Jupiter: quem administra o RUCard tem
    # que conseguir saber quem está batendo.
    assert "usp-mcp" in chamada["cabecalhos"]["User-Agent"]


def test_r11b_nenhum_caminho_do_cliente_usa_get():
    fonte = mod_cliente.__file__ and open(mod_cliente.__file__, encoding="utf-8").read()
    assert 'method="GET"' not in fonte and "'GET'" not in fonte
    assert 'method="POST"' in fonte, (
        "o método tem que estar explícito: urllib manda GET quando não há data, "
        "e um GET aqui volta 500 com HTML."
    )


def test_r12_hash_ausente_falha_cedo_e_diz_onde_configurar(gravador, monkeypatch):
    monkeypatch.delenv("RUCARD_HASH", raising=False)
    transporte = gravador({})
    with pytest.raises(HashAusente) as exc:
        ClienteRucard(transporte, hash_rucard="")
    assert ".env" in str(exc.value)
    assert transporte.chamadas == [], "saiu requisição sem hash"


def test_r12b_a_hash_sai_do_ambiente_quando_nao_e_passada(gravador, monkeypatch):
    monkeypatch.setenv("RUCARD_HASH", HASH_DE_TESTE)
    c = ClienteRucard(gravador({"restaurants": texto("restaurantes")}))
    c.restaurantes()
    assert f"hash={HASH_DE_TESTE}" == c._transporte.chamadas[0]["corpo"]


def test_r13_html_do_tomcat_vira_erro_legivel_sem_arrastar_o_html(gravador):
    html = texto("erro_500")
    c = ClienteRucard(gravador({"menu/6": (500, html)}), hash_rucard=HASH_DE_TESTE)

    with pytest.raises(RespostaInvalida) as exc:
        c.menu("6", SEG_FASE1)

    mensagem = str(exc.value)
    assert "500" in mensagem
    for vazamento in ("<html", "Tomcat", "doctype", "font-family"):
        assert vazamento.lower() not in mensagem.lower(), (
            f"{vazamento!r} na mensagem: são 3.240 B de página de erro que não "
            "respondem nada, e o Invariante 6 pede a mensagem, não o cru."
        )
    assert len(mensagem) < len(html) / 4


def test_r14_duas_perguntas_na_mesma_semana_custam_uma_requisicao(cliente_de_fixture):
    relogio = Relogio()
    c, transporte = cliente_de_fixture(relogio=relogio)

    c.menu("6", SEG_FASE1)
    c.menu("6", SEG_FASE1 + datetime.timedelta(days=2))  # outro dia, mesma semana

    assert transporte.rotas() == ["menu/6"], (
        "o cardápio da semana já estava em memória: perguntar por outro dia da "
        "MESMA semana não pode custar chamada nova (Invariante 5)."
    )


def test_r15_cache_com_a_semana_errada_refaz_a_chamada_dentro_do_ttl(gravador):
    # O caso que TTL sozinho não pega: às 19:22 de segunda 31/08 a semana
    # corrente já era 31/08→06/09, e um cache de horas atrás ainda tem a
    # semana anterior. Devolvê-lo é responder o cardápio errado com cara de
    # resposta certa.
    relogio = Relogio()
    transporte = gravador(
        {"menu/6": [texto("menu_6"), texto("menu_6_semana_seguinte")]}
    )
    c = ClienteRucard(
        transporte, hash_rucard=HASH_DE_TESTE, relogio=relogio, ttl_menu=10**6
    )

    primeiro = c.menu("6", SEG_FASE1)
    assert primeiro["meals"][0]["date"] == "24/08/2026"

    segundo = c.menu("6", SEG_SEGUINTE)  # mesmo TTL, semana diferente

    assert transporte.rotas() == ["menu/6", "menu/6"], (
        "o cliente devolveu o cache de outra semana. TTL não é suficiente: a "
        "API não aceita parâmetro de data, e a única forma de saber se o "
        "payload responde é olhar as datas que ele traz."
    )
    assert segundo["meals"][0]["date"] == "31/08/2026"


def test_r15b_data_fora_das_duas_semanas_nao_e_maquiada_pelo_cliente(gravador):
    # O cliente refaz a chamada e devolve o que a USP mandar; quem decide o que
    # dizer sobre "essa data não está na semana" é a ferramenta (R27). O que o
    # cliente NÃO pode fazer é fingir que o payload serve.
    transporte = gravador({"menu/6": texto("menu_6")})
    c = ClienteRucard(transporte, hash_rucard=HASH_DE_TESTE)

    bruto = c.menu("6", datetime.date(2026, 12, 25))
    datas = [d["date"] for d in bruto["meals"]]
    assert "25/12/2026" not in datas
    assert len(transporte.chamadas) == 1


def test_r16_ttl_expirado_refaz(cliente_de_fixture):
    relogio = Relogio()
    c, transporte = cliente_de_fixture(relogio=relogio, ttl_menu=100)

    c.menu("6", SEG_FASE1)
    relogio.avancar(99)
    c.menu("6", SEG_FASE1)
    assert transporte.rotas() == ["menu/6"], "expirou antes do TTL"

    relogio.avancar(2)
    c.menu("6", SEG_FASE1)
    assert transporte.rotas() == ["menu/6", "menu/6"], "não expirou depois do TTL"


def test_r16b_a_revalidacao_por_data_continua_viva_depois_do_ttl_expirar(gravador):
    """A proteção do R15, mas na SEGUNDA janela de TTL — e nas seguintes.

    O R15 sozinho só exercita a primeira janela de vida do processo, e é por
    isso que ele ficava verde com a proteção desligada. O flag "já revalidei
    nesta janela" era ligado sempre que existia entrada anterior, inclusive
    quando a refeita fora por TTL vencido: depois da primeira expiração, toda
    entrada nova nascia marcada como já revalidada e a virada de semana deixava
    de ser percebida para sempre.

    A ironia é o ponto: às 3 h de processo vivo, que é quando a virada da
    segunda-feira de fato acontece, a proteção já estava desligada.
    """
    relogio = Relogio()
    transporte = gravador(
        {"menu/6": [texto("menu_6"), texto("menu_6"), texto("menu_6_semana_seguinte")]}
    )
    c = ClienteRucard(
        transporte, hash_rucard=HASH_DE_TESTE, relogio=relogio, ttl_menu=100
    )

    c.menu("6", SEG_FASE1)          # 1ª requisição: nasce a primeira janela
    relogio.avancar(101)            # o TTL vence
    c.menu("6", SEG_FASE1)          # 2ª requisição: janela NOVA, não revalidação
    assert transporte.rotas() == ["menu/6", "menu/6"]

    # Agora a virada de semana, dentro da segunda janela.
    segundo = c.menu("6", SEG_SEGUINTE)

    assert transporte.rotas() == ["menu/6", "menu/6", "menu/6"], (
        "o cliente devolveu o cache da semana anterior. O flag de revalidação "
        "foi ligado por uma refeita de TTL, que não é revalidação por data: a "
        "partir da primeira expiração a virada de semana passa despercebida."
    )
    assert segundo["meals"][0]["date"] == "31/08/2026"


def test_r16c_revalidar_por_data_continua_valendo_uma_vez_por_janela(gravador):
    """O outro lado, para a cura do R16b não virar uma requisição por pergunta.

    Uma pergunta sobre uma data que a API nunca vai cobrir (Natal) não pode
    custar uma chamada cada vez. Depois de revalidar uma vez, a janela está
    gasta — e é isso que o flag deve significar.
    """
    relogio = Relogio()
    transporte = gravador({"menu/6": [texto("menu_6"), texto("menu_6")]})
    c = ClienteRucard(
        transporte, hash_rucard=HASH_DE_TESTE, relogio=relogio, ttl_menu=10**6
    )

    c.menu("6", SEG_FASE1)
    c.menu("6", datetime.date(2026, 12, 25))  # revalida: 1 chamada a mais
    assert transporte.rotas() == ["menu/6", "menu/6"]

    c.menu("6", datetime.date(2026, 12, 25))
    c.menu("6", datetime.date(2026, 12, 26))
    assert transporte.rotas() == ["menu/6", "menu/6"], (
        "a janela já tinha sido revalidada: perguntar de novo por uma data que "
        "a API não serve não pode virar uma requisição por pergunta"
    )


def test_r17_o_catalogo_tem_ttl_maior_que_o_menu():
    # Medido: `/restaurants` veio byte-idêntico em 27/08 e 31/08 — é o dado
    # mais estático do projeto. O cardápio muda toda semana. Um TTL só para os
    # dois seria colado na frequência da pergunta, não na taxa de mudança do
    # dado, que é o que o Invariante 5 pede.
    assert mod_cliente.TTL_CATALOGO > mod_cliente.TTL_MENU
    assert mod_cliente.TTL_MENU <= 60 * 60 * 24, (
        "TTL de menu maior que um dia atravessa a virada da semana. A validação "
        "de data salva a resposta, mas o TTL não deve depender dela."
    )


def test_r17b_o_catalogo_e_buscado_uma_vez_so(cliente_de_fixture):
    c, transporte = cliente_de_fixture()
    c.restaurantes()
    c.restaurantes()
    assert transporte.rotas() == ["restaurants"]


def test_r18_json_invalido_com_200_vira_erro_legivel(gravador):
    c = ClienteRucard(
        gravador({"menu/6": (200, "<html>manutenção</html>")}), hash_rucard=HASH_DE_TESTE
    )
    with pytest.raises(RespostaInvalida) as exc:
        c.menu("6", SEG_FASE1)
    assert "JSON" in str(exc.value)


def test_r18b_message_error_true_no_corpo_e_erro_de_verdade(gravador):
    # Em `/menu`, `message.error` é booleano DE VERDADE (ao contrário de
    # `/restaurants`, onde tudo é string) — §1.2. Não é decoração: se ele vier
    # ligado, o payload não é resposta.
    corpo = json.dumps(
        {"message": {"error": True, "message": "Restaurante não encontrado"},
         "meals": [], "observation": {}}
    )
    c = ClienteRucard(gravador({"menu/6": corpo}), hash_rucard=HASH_DE_TESTE)
    with pytest.raises(RespostaInvalida) as exc:
        c.menu("6", SEG_FASE1)
    assert "Restaurante não encontrado" in str(exc.value)


def test_r19_timeout_vira_indisponivel_em_portugues(gravador):
    def transporte_que_cai(url, corpo, cabecalhos):
        raise TimeoutError("timed out")

    c = ClienteRucard(transporte_que_cai, hash_rucard=HASH_DE_TESTE)
    with pytest.raises(RucardIndisponivel) as exc:
        c.menu("6", SEG_FASE1)
    assert "não respondeu" in str(exc.value)


def test_r20_uma_requisicao_por_vez():
    # Invariante 5: não é thread-safety por acaso, é gentileza com a USP. Mesma
    # trava do cliente do Jupiter.
    fonte = open(mod_cliente.__file__, encoding="utf-8").read()
    assert "Lock()" in fonte, (
        "sem trava, quatro RUs em paralelo viram quatro requisições simultâneas "
        "no mesmo endpoint."
    )
