"""R26-R33: a ferramenta `bandejao`.

A pergunta do §5, com o vocabulário do dono:

    "O que tem no bandejão hoje, e onde vale a pena almoçar?"

São duas perguntas numa: *o que tem* (um RU, um dia) e *onde vale a pena* (os
quatro lado a lado). Uma chamada de ferramenta responde as duas — critério 2 do
§5 — e por isso a comparação não é uma segunda ferramenta.

Três coisas que a implementação óbvia erra e que estes testes travam:

1. Escolher o dia por índice na lista de 7. Funciona até a semana virar.
2. Comparar com `"Fechado"` e não achar `"FECHADO"` (7, 8 e 9).
3. Tratar `FECHADO` como "fechado hoje" no RU 7, que **nunca** serve jantar.
"""
import datetime

import pytest

from tests.rucard.conftest import HASH_DE_TESTE, texto
from usp_mcp.rucard import ferramentas
from usp_mcp.rucard.cliente import ClienteRucard
from usp_mcp.rucard.erros import RucardIndisponivel

pytestmark = pytest.mark.contrato

# Dentro da semana da Fase 1 (24/08 → 30/08), que é a das fixtures dos 4 RUs.
SEGUNDA = datetime.date(2026, 8, 24)
QUARTA = datetime.date(2026, 8, 26)
SABADO = datetime.date(2026, 8, 29)
DOMINGO = datetime.date(2026, 8, 30)


@pytest.fixture
def chamar(gravador, respostas_da_fatia):
    def executar(**kwargs):
        transporte = kwargs.pop("transporte", None) or gravador(respostas_da_fatia)
        cliente = ClienteRucard(transporte, hash_rucard=HASH_DE_TESTE)
        hoje = kwargs.pop("hoje", SEGUNDA)
        return ferramentas.bandejao(cliente=cliente, hoje=hoje, **kwargs), transporte

    return executar


def refeicao_de(resposta, id_ru, qual):
    (ru,) = [r for r in resposta["restaurantes"] if r["id"] == id_ru]
    return ru["refeicoes"][qual]


def test_r26_hoje_resolve_por_data_e_nao_por_indice(chamar):
    resposta, _ = chamar(hoje=QUARTA)
    assert resposta["data"] == "26/08/2026"
    assert resposta["dia_semana"] == "qua"

    # A prova de que não é índice: a MESMA fixture, pedida por data explícita,
    # tem que dar o mesmo resultado que "hoje" naquele dia.
    por_data, _ = chamar(dia="26/08/2026", hoje=SEGUNDA)
    assert por_data["data"] == resposta["data"]
    assert refeicao_de(por_data, "6", "almoco") == refeicao_de(resposta, "6", "almoco")


def test_r26b_amanha_e_um_dia_depois_de_hoje(chamar):
    resposta, _ = chamar(dia="amanhã", hoje=SEGUNDA)
    assert resposta["data"] == "25/08/2026"
    # sem acento também: quem digita a pergunta não é obrigado a acertar o til
    sem_acento, _ = chamar(dia="amanha", hoje=SEGUNDA)
    assert sem_acento["data"] == "25/08/2026"


def test_r27_dia_fora_da_semana_devolvida_nao_vira_lista_vazia(chamar):
    # A API não tem parâmetro de data: só semana corrente (§1.2). Pedir Natal
    # tem que dizer isso, com a semana que existe por extenso — devolver
    # "nenhum cardápio" seria o falso "não tem nada" do Invariante 7.
    resposta, _ = chamar(dia="25/12/2026", hoje=SEGUNDA)

    assert resposta["restaurantes"] == []
    assert resposta["avisos"], "sem aviso, a resposta vazia mente por omissão"
    junto = " ".join(resposta["avisos"])
    assert "24/08/2026" in junto and "30/08/2026" in junto, (
        "o aviso tem que dizer QUAL semana está publicada, não só que a pedida "
        "não está."
    )
    assert "semana" in junto.lower()


def test_r28_as_duas_grafias_de_fechado_sao_reconhecidas(chamar):
    # Domingo: o 6 devolve "Fechado" e os outros "FECHADO". Se a comparação
    # fosse sensível a caixa, um dos dois grupos apareceria como cardápio —
    # com a palavra "FECHADO" listada como item de comida.
    resposta, _ = chamar(dia="30/08/2026", hoje=SEGUNDA)
    for id_ru in ("6", "7", "8"):
        situacao = refeicao_de(resposta, id_ru, "almoco")["situacao"]
        assert situacao != "aberto", f"RU {id_ru} no domingo apareceu como aberto"
        assert "fechado" in situacao or "nao_serve" in situacao

    for id_ru in ("6", "7", "8"):
        for qual in ("almoco", "jantar"):
            r = refeicao_de(resposta, id_ru, qual)
            assert "FECHADO" not in str(r.get("itens", "")).upper() or not r.get("itens")


def test_r29_nunca_serve_essa_refeicao_e_nao_serve_neste_dia_se_explicam(chamar):
    resposta, _ = chamar(hoje=SEGUNDA)  # dia útil

    jantar_7 = refeicao_de(resposta, "7", "jantar")
    assert jantar_7["situacao"] == "nao_serve", (
        "o RU 7 não serve jantar (workinghours.dinner vazio nos 7 dias). "
        "Chamar isso de 'fechado hoje' faz o aluno voltar amanhã à mesma hora."
    )
    assert "dia nenhum" in jantar_7["detalhe"], (
        "'nunca serve jantar' e 'não serve jantar hoje' são a mesma situação "
        "com detalhes diferentes — o detalhe é o que diz se vale voltar amanhã."
    )

    fim_de_semana, _ = chamar(dia="29/08/2026", hoje=SEGUNDA)  # sábado
    almoco_6 = refeicao_de(fim_de_semana, "6", "almoco")
    assert almoco_6["situacao"] == "nao_serve"
    assert "sáb" in almoco_6["detalhe"] and "dia nenhum" not in almoco_6["detalhe"], (
        "o 6 serve almoço em dia de semana e não no sábado: o detalhe tem que "
        "citar o dia, senão parece que ele nunca serve almoço."
    )

    # E o 9, que é o único dos quatro que abre no fim de semana (medido em
    # 31/08): sábado com almoço e jantar.
    assert refeicao_de(fim_de_semana, "9", "almoco")["situacao"] == "aberto"
    assert refeicao_de(fim_de_semana, "9", "jantar")["situacao"] == "aberto"


def test_r29b_domingo_do_9_tem_almoco_e_nao_tem_jantar(chamar):
    resposta, _ = chamar(dia="30/08/2026", hoje=SEGUNDA)
    assert refeicao_de(resposta, "9", "almoco")["situacao"] == "aberto"
    assert refeicao_de(resposta, "9", "jantar")["situacao"] == "nao_serve", (
        "domingo do 9: horário de jantar vazio e cardápio FECHADO. As duas "
        "fontes concordam em que ele não serve jantar no domingo."
    )


def test_r29c_fechado_com_horario_publicado_e_a_terceira_situacao(gravador, chamar):
    # Feriado: o RU publica horário para aquele dia da semana E o cardápio diz
    # FECHADO. É a única situação em que "fechado hoje" é a informação certa —
    # e as duas semanas capturadas não têm nenhuma (nenhum feriado caiu nelas),
    # então a entrada aqui é fabricada de propósito, com o mínimo alterado.
    import json

    from tests.rucard.conftest import carregar

    bruto = carregar("menu_6")
    bruto["meals"][0]["lunch"] = {"menu": "Fechado", "calories": "0"}
    respostas = {
        "restaurants": texto("restaurantes"),
        "menu/6": json.dumps(bruto, ensure_ascii=False),
    }

    resposta, _ = chamar(
        transporte=gravador(respostas), restaurantes=["6"], refeicao="almoco",
        hoje=SEGUNDA,
    )
    almoco = refeicao_de(resposta, "6", "almoco")
    assert almoco["situacao"] == "fechado", (
        "horário publicado para segunda + cardápio Fechado = fechado NESTE dia. "
        "Confundir com 'não serve' esconde que amanhã provavelmente abre."
    )
    assert almoco["horario"] == "11:15 às 14:15"


def test_r29d_cardapio_com_comida_e_horario_ausente_e_declarado(gravador, chamar):
    # O inverso: cardápio com comida num dia sem horário publicado. Não
    # aconteceu nas capturas, e as duas fontes discordarem é possível — o
    # cardápio é a evidência mais forte de que tem comida, e a ausência de
    # horário vira aviso em vez de virar "fechado".
    import json

    from tests.rucard.conftest import carregar

    bruto = carregar("menu_6")
    bruto["meals"][5]["lunch"] = {"menu": "Arroz\nFeijão", "calories": "800"}  # sábado
    respostas = {
        "restaurants": texto("restaurantes"),
        "menu/6": json.dumps(bruto, ensure_ascii=False),
    }

    resposta, _ = chamar(
        transporte=gravador(respostas), restaurantes=["6"], refeicao="almoco",
        dia="29/08/2026", hoje=SEGUNDA,
    )
    almoco = refeicao_de(resposta, "6", "almoco")
    assert almoco["situacao"] == "aberto"
    assert almoco.get("horario") is None
    junto = " ".join(resposta["avisos"]).lower()
    assert "horário" in junto, (
        "cardápio publicado sem horário publicado: dizer 'fechado' contra o "
        "próprio cardápio é escolher a fonte errada em silêncio."
    )


def test_r30_cafe_da_manha_responde_que_nao_ha_cardapio_publicado(chamar):
    # A pergunta tem serviço e não tem fonte: `workinghours` publica breakfast,
    # o `/menu` só traz lunch e dinner. A resposta honesta diz as duas coisas
    # (Invariante 6) — o que existiria e o que não é publicado.
    resposta, _ = chamar(refeicao="cafe", hoje=SEGUNDA)

    cafe_6 = refeicao_de(resposta, "6", "cafe")
    assert cafe_6["situacao"] == "sem_cardapio_publicado"
    assert cafe_6["horario"] == "07:00 às 08:30"
    assert "itens" not in cafe_6 or not cafe_6["itens"]

    cafe_8 = refeicao_de(resposta, "8", "cafe")
    assert cafe_8["situacao"] == "nao_serve", (
        "o 8 não publica horário de café: aí a resposta é 'não serve', não "
        "'existe mas não sei o cardápio'."
    )

    junto = " ".join(resposta["avisos"]).lower()
    assert "café" in junto and "não" in junto


def test_r31_uma_chamada_de_ferramenta_compara_os_quatro(chamar):
    resposta, transporte = chamar(refeicao="almoco", hoje=SEGUNDA)

    assert [r["id"] for r in resposta["restaurantes"]] == ["6", "7", "8", "9"]
    # 4 menus + 1 catálogo. Nada de laço sobre os 18.
    assert sorted(transporte.rotas()) == [
        "menu/6", "menu/7", "menu/8", "menu/9", "restaurants",
    ]

    # "Vale a pena" precisa do que decide: o que tem, quanto custa, quanto
    # engorda, e até que hora dá tempo.
    almoco = refeicao_de(resposta, "6", "almoco")
    assert almoco["itens"] and isinstance(almoco["itens"], list)
    assert almoco["calorias"] == "1065"
    assert almoco["preco_aluno"] == "2,00"
    assert almoco["horario"] == "11:15 às 14:15"


def test_r31b_pedir_um_ru_so_nao_paga_pelos_outros_tres(chamar):
    resposta, transporte = chamar(restaurantes=["9"], refeicao="almoco", hoje=SEGUNDA)
    assert [r["id"] for r in resposta["restaurantes"]] == ["9"]
    assert sorted(transporte.rotas()) == ["menu/9", "restaurants"]


def test_r32_um_ru_que_falha_nao_derruba_os_outros_e_a_falha_aparece(
    gravador, respostas_da_fatia, chamar
):
    respostas = dict(respostas_da_fatia)
    respostas["menu/8"] = (500, texto("erro_500"))
    resposta, _ = chamar(transporte=gravador(respostas), refeicao="almoco")

    abertos = [
        r["id"]
        for r in resposta["restaurantes"]
        if r["refeicoes"]["almoco"]["situacao"] == "aberto"
    ]
    assert abertos == ["6", "7", "9"], "a falha de um RU levou os outros embora"

    falho = refeicao_de(resposta, "8", "almoco")
    assert falho["situacao"] == "indisponivel"
    junto = " ".join(resposta["avisos"])
    assert "8" in junto or "FÍSICA" in junto, (
        "parcial silencioso: três RUs respondidos e o quarto sumido sem uma "
        "palavra é exatamente o que o Invariante 7 proíbe."
    )
    # O HTML do Tomcat não vaza para a saída da ferramenta.
    assert "<html" not in str(resposta).lower()


def test_r32b_falha_em_todos_sobe_como_erro_em_vez_de_resposta_vazia(gravador):
    # A distinção do §9 de 28/08: "não tem nada" e "a chamada falhou" não podem
    # ser a mesma saída. Se NENHUM RU respondeu, isso é erro, não cardápio.
    respostas = {
        "restaurants": texto("restaurantes"),
        **{f"menu/{i}": (500, texto("erro_500")) for i in (6, 7, 8, 9)},
    }
    cliente = ClienteRucard(gravador(respostas), hash_rucard=HASH_DE_TESTE)
    with pytest.raises(RucardIndisponivel):
        ferramentas.bandejao(cliente=cliente, hoje=SEGUNDA)


def test_r33_calorias_e_o_texto_que_a_api_manda(chamar):
    resposta, _ = chamar(hoje=SEGUNDA)
    almoco = refeicao_de(resposta, "6", "almoco")
    assert isinstance(almoco["calorias"], str), (
        "calorias é string na API. Converter para int perde o formato e ganha "
        "uma exceção no primeiro RU que mandar '' ou '1.065'."
    )

    fechado = refeicao_de(resposta, "7", "jantar")
    assert "calorias" not in fechado, (
        "dia fechado vem com calories='0'. Exibir '0 kcal' num RU fechado é "
        "número certo respondendo pergunta errada."
    )


def test_r33b_a_opcao_do_dia_nao_e_chamada_de_vegetariana_sem_a_marca(chamar):
    # Medido nas duas semanas: 100% das refeições abertas têm uma linha
    # "Opção: ...", e só algumas trazem "(V)". Rotular toda opção como
    # vegetariana é inventar informação que a API não dá.
    resposta, _ = chamar(hoje=SEGUNDA)
    almoco_6 = refeicao_de(resposta, "6", "almoco")

    assert almoco_6["opcao"] == "Grão-de-bico à indiana (V)"
    assert almoco_6["opcao_vegetariana_marcada"] is True

    jantar_8 = refeicao_de(resposta, "8", "jantar")
    assert jantar_8["opcao"], "o 8 também publica opção, sem a marca (V)"
    assert jantar_8["opcao_vegetariana_marcada"] is False, (
        "o RU 8 não marca (V) em nenhuma das duas semanas capturadas: dizer "
        "que a opção é vegetariana é afirmar o que a fonte não diz."
    )


def test_r33c_itens_saem_separados_por_linha_sem_html(chamar):
    resposta, _ = chamar(hoje=SEGUNDA)
    itens = refeicao_de(resposta, "6", "almoco")["itens"]
    assert itens[0] == "Arroz / feijão / arroz integral"
    assert all(i == i.strip() and i for i in itens)
    assert not any("<" in i for i in itens), (
        "o §1.2 registra que o texto às vezes vem com HTML. Não apareceu em 2 "
        "semanas de captura, mas o parser não pode repassá-lo cru se aparecer."
    )


def test_r33d_campos_do_topo_sao_exatamente_os_declarados(chamar):
    resposta, _ = chamar(hoje=SEGUNDA)
    assert set(resposta) == set(ferramentas.CAMPOS_SAIDA)


def test_r27b_ru_que_nao_publicou_o_dia_nao_desaparece_calado(gravador, chamar):
    # Achado na revisão da própria implementação: quando NENHUM RU tem o dia, o
    # aviso da semana aparece (R27). Quando só UM não tem, ele saía da lista sem
    # uma palavra — três RUs respondidos e o quarto sumido é o Invariante 7
    # quebrado, e é a versão mais difícil de notar dele.
    import json

    from tests.rucard.conftest import carregar, texto

    atrasado = carregar("menu_6")  # semana 24/08 → 30/08
    respostas = {
        "restaurants": texto("restaurantes"),
        "menu/6": json.dumps(atrasado, ensure_ascii=False),
        "menu/9": texto("menu_9_semana_seguinte"),
    }

    resposta, _ = chamar(
        transporte=gravador(respostas), restaurantes=["6", "9"], refeicao="almoco",
        dia="31/08/2026", hoje=datetime.date(2026, 8, 31),
    )

    assert [r["id"] for r in resposta["restaurantes"]] == ["9"]
    junto = " ".join(resposta["avisos"])
    assert "CENTRAL" in junto, (
        "o RU que não publicou o dia pedido tem que ser NOMEADO no aviso: quem "
        "lê a resposta não tem como saber que faltou um."
    )
    assert "24/08/2026" in junto and "30/08/2026" in junto, (
        "e o aviso tem que dizer qual semana ele publicou, senão 'faltou' não "
        "diz o que fazer."
    )


# --- R42: comunicado no cardápio não é prato (14/09/2026) -------------------


def test_r42_itens_e_opcao_separa_comunicado_em_negrito_de_prato():
    itens, opcao, marcada, avisos = ferramentas._itens_e_opcao(
        "Arroz / feijão\nOpção: Falafel (V)\nMinipão / refresco\n\n"
        "**Os Restaurantes Universitários não fornecem copos descartáveis. "
        "Tragam suas canecas.**"
    )
    assert itens == ["Arroz / feijão", "Minipão / refresco"]
    assert opcao == "Falafel (V)" and marcada is True
    assert avisos == [
        "Os Restaurantes Universitários não fornecem copos descartáveis. "
        "Tragam suas canecas."
    ], "o comunicado tem que sair SEM os asteriscos e sem sumir"


def test_r42b_frase_longa_com_ponto_final_e_comunicado_mesmo_sem_negrito():
    itens, _, _, avisos = ferramentas._itens_e_opcao(
        "Arroz / feijão\n"
        "Os restaurantes estarão fechados na sexta-feira por causa do feriado.\n"
        "Maçã"
    )
    assert itens == ["Arroz / feijão", "Maçã"]
    assert avisos == [
        "Os restaurantes estarão fechados na sexta-feira por causa do feriado."
    ]


def test_r42c_prato_curto_com_ponto_nao_vira_comunicado():
    # A regra de frase exige 6+ palavras: um prato com ponto no fim continua prato.
    itens, _, _, avisos = ferramentas._itens_e_opcao("Bife à rolê.\nSalada de alface")
    assert itens == ["Bife à rolê.", "Salada de alface"]
    assert avisos == []


def test_r42d_o_mesmo_comunicado_duas_vezes_na_refeicao_sai_uma_vez():
    _, _, _, avisos = ferramentas._itens_e_opcao(
        "Arroz\n**Tragam suas canecas para o almoço de hoje.**\n"
        "**Tragam suas canecas para o almoço de hoje.**"
    )
    assert avisos == ["Tragam suas canecas para o almoço de hoje."]


SEGUNDA_14_09 = datetime.date(2026, 9, 14)  # semana da fixture `menu_7_avisos`

COMUNICADO_CANECAS = (
    "Os Restaurantes Universitários não fornecem copos descartáveis. "
    "Tragam suas canecas."
)


def test_r42e_o_comunicado_vira_um_aviso_nomeando_o_ru(
    gravador, chamar, respostas_da_fatia
):
    respostas = dict(respostas_da_fatia)
    respostas["menu/7"] = texto("menu_7_avisos")
    resposta, _ = chamar(
        transporte=gravador(respostas), hoje=SEGUNDA_14_09,
        restaurantes=["7"], refeicao="almoco",
    )

    almoco = refeicao_de(resposta, "7", "almoco")
    assert almoco["situacao"] == "aberto"
    assert not [i for i in almoco["itens"] if "canecas" in i or "**" in i], (
        "o comunicado continua na lista de pratos"
    )
    assert almoco["itens"][-1] == "Minipão / refresco"
    assert almoco["avisos_publicados"] == [COMUNICADO_CANECAS]

    (aviso,) = [a for a in resposta["avisos"] if "canecas" in a]
    assert "PUSP-CB" in aviso and "**" not in aviso


def test_r42f_o_mesmo_comunicado_em_dois_rus_e_um_aviso_com_os_dois_nomes(
    gravador, chamar, respostas_da_fatia
):
    # O payload do /menu não carrega o id do RU, então a mesma fixture serve
    # para o 7 e para o 8: é exatamente o caso real de 14/09, em que três RUs
    # publicaram o mesmo texto.
    respostas = dict(respostas_da_fatia)
    respostas["menu/7"] = texto("menu_7_avisos")
    respostas["menu/8"] = texto("menu_7_avisos")
    resposta, _ = chamar(
        transporte=gravador(respostas), hoje=SEGUNDA_14_09,
        restaurantes=["7", "8"], refeicao="almoco",
    )

    com_canecas = [a for a in resposta["avisos"] if "canecas" in a]
    assert len(com_canecas) == 1, com_canecas
    assert "PUSP-CB" in com_canecas[0] and "FÍSICA" in com_canecas[0]


def test_r42g_refeicao_sem_comunicado_tem_a_lista_vazia_e_nenhum_aviso(chamar):
    resposta, _ = chamar(hoje=SEGUNDA)
    for ru in resposta["restaurantes"]:
        for dados in ru["refeicoes"].values():
            if dados["situacao"] == "aberto":
                assert dados["avisos_publicados"] == []
    assert not [a for a in resposta["avisos"] if "publicado no cardápio" in a]
