"""E7-E12: o plano, o código que o guarda, as recusas e a pergunta.

Camada 2, offline, contra os construtores do `conftest`. Nenhum destes testes
toca a rede, e é aqui que isso deixa de ser só uma propriedade da suíte e passa
a ser o objeto dela: **E7 existe para provar que a primeira chamada de
`entregar` não escreve.** O dublê não conhece a função de escrita, então
qualquer chamada a ela vira vermelho com o nome na mensagem.

O que estes seis travam, e por que cada um é o teste que o desenho precisa:

- **E7** a camada 2 inteira: plano primeiro, escrita nunca na primeira chamada.
- **E8** o código é sensível ao que muda o significado de entregar.
- **E9** código velho não escreve, e a resposta não deixa quem lê sem saída —
  ela traz o plano de agora.
- **E10** as cinco recusas da camada 5, com cinco mensagens distintas. Cinco
  mensagens iguais seriam a mesma coisa que uma recusa muda.
- **E11** a distinção entre "não pude perguntar" e "perguntei e disseram não".
- **E12** dois verbos, e nenhum parâmetro que escolha entre eles.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from tests.moodle.conftest import ClienteFalso, entregas_falsas, status_de_entrega
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle import entrega as ent
from usp_mcp.moodle import politica, server
from usp_mcp.moodle.projecao import FUSO_SAO_PAULO

pytestmark = pytest.mark.contrato

CURSO_PTC3314 = 142036
ASSIGNID = 577509
NOME_DA_ENTREGA = "EC-1"
PRAZO = 1789354740  # o `duedate` real do EC-1, da captura de 12/09
AGORA = datetime(2026, 9, 15, 20, 0, tzinfo=FUSO_SAO_PAULO)

# A função de escrita NÃO entra nas respostas do dublê de propósito: o
# `ClienteFalso` levanta com o nome de qualquer função que o código chame e ele
# não preveja, então "não escreveu" vira vermelho com o nome na mensagem em vez
# de um silêncio que passa.
ESCRITA = "mod_assign_submit_for_grading"


def _respostas(disciplinas_brutas, status, **do_assign):
    return {
        "core_webservice_get_site_info": {"userid": 8214},
        "core_enrol_get_users_courses": disciplinas_brutas,
        "mod_assign_get_assignments": entregas_falsas(
            [(CURSO_PTC3314, [(ASSIGNID, NOME_DA_ENTREGA, PRAZO, 0)])], **do_assign
        ),
        "mod_assign_get_submission_status": status,
    }


@pytest.fixture(autouse=True)
def _cache_limpo():
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _entregar(cliente, **kwargs):
    return asyncio.run(
        ent.entregar(
            cliente, "PTC3314", NOME_DA_ENTREGA, agora=AGORA, **kwargs
        )
    )


def _rascunho_editavel(**extras):
    """O estado do caminho feliz: rascunho salvo, editável, com um arquivo."""
    return status_de_entrega(status="draft", com_texto_online=False, **extras)


# ---------------------------------------------------------------------- E7


def test_e7_a_primeira_chamada_nao_toca_o_transporte_de_escrita(disciplinas_brutas):
    cliente = ClienteFalso(_respostas(disciplinas_brutas, _rascunho_editavel()))

    resposta = _entregar(cliente)

    assert not resposta.escreveu
    assert cliente.escritas == [], (
        f"a primeira chamada escreveu: {cliente.escritas}. O plano é leitura, e "
        "a camada que separa ler de escrever é a razão de o desenho existir."
    )
    assert ESCRITA not in [f for f, _ in cliente.chamadas]
    # E as duas leituras que ela FAZ são as duas que a allowlist já tinha.
    assert [f for f, _ in cliente.chamadas] == [
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "mod_assign_get_assignments",
        "mod_assign_get_submission_status",
    ]

    # O plano precisa dizer o que muda e trazer o código — sem as duas coisas
    # ele é um texto bonito que não leva a lugar nenhum.
    assert resposta.codigo and resposta.codigo in resposta.texto
    assert NOME_DA_ENTREGA in resposta.texto
    assert "EC1-relatorio.pdf" in resposta.texto


def test_e7b_a_segunda_chamada_com_o_codigo_certo_escreve_uma_vez(
    disciplinas_brutas,
):
    """A outra metade de E7, e ela não é opcional.

    Sem este teste, um `entregar` que nunca escrevesse passaria por E7, E9 e E10
    inteiros. É o mesmo raciocínio do T8 da política: a negativa só significa
    alguma coisa se existir o caminho que ela nega.
    """
    respostas = _respostas(disciplinas_brutas, _rascunho_editavel())
    respostas[ESCRITA] = {"status": True}
    cliente = ClienteFalso(respostas)

    plano = _entregar(cliente)
    feito = _entregar(cliente, confirmacao=plano.codigo)

    assert feito.escreveu
    assert len(cliente.escritas) == 1, (
        f"escreveu {len(cliente.escritas)} vez(es): {cliente.escritas}"
    )
    # A saída de sucesso NÃO pode repetir as duas frases do plano que só valiam
    # antes da escrita. O plano é reaproveitado como recibo, e "nada foi
    # escrito" logo abaixo de "Feito" seria a pior frase que este módulo teria
    # como produzir — e sairia de graça, porque o texto é o mesmo objeto.
    assert "nada foi escrito" not in feito.texto.lower(), (
        f"a resposta de sucesso diz que não escreveu:\n{feito.texto}"
    )
    assert "chame de novo" not in feito.texto.lower(), (
        f"a resposta de sucesso ainda pede confirmação:\n{feito.texto}"
    )
    # E o contrário: a do plano diz as duas coisas, senão o corte acima teria
    # sido feito no lugar errado.
    assert "nada foi escrito" in plano.texto.lower()

    funcao, params = cliente.escritas[0]
    assert funcao == ESCRITA
    # Asserção sobre o parâmetro ENVIADO: o dublê devolveria sucesso de
    # qualquer jeito, e só isto pega um `assignid` trocado — que aqui seria
    # entregar a atividade errada, sem desfazer.
    assert params["assignid"] == ASSIGNID


# ---------------------------------------------------------------------- E8


def _codigo(disciplinas_brutas, status):
    cliente = ClienteFalso(_respostas(disciplinas_brutas, status))
    return _entregar(cliente).codigo


def test_e8_o_codigo_muda_quando_o_plano_muda(disciplinas_brutas):
    """E8 — as três coisas que mudam o significado de entregar.

    Um código que não mudasse com o conjunto de arquivos seria o pior dos
    mundos: ele passaria a autorizar a entrega de um arquivo que quem leu o
    plano nunca viu, com a cara de ter sido confirmado.
    """
    base = _codigo(disciplinas_brutas, _rascunho_editavel())

    outro_arquivo = _codigo(
        disciplinas_brutas, _rascunho_editavel(arquivos=("EC1-v2.pdf",))
    )
    mesmo_nome_outro_tamanho = _codigo(
        disciplinas_brutas, _rascunho_editavel(tamanho=999)
    )
    mais_um_arquivo = _codigo(
        disciplinas_brutas,
        _rascunho_editavel(arquivos=("EC1-relatorio.pdf", "anexo.pdf")),
    )
    outro_status = _codigo(
        disciplinas_brutas, status_de_entrega(status="new", com_texto_online=False)
    )
    outro_carimbo = _codigo(
        disciplinas_brutas, _rascunho_editavel(timemodified=1789300001)
    )

    distintos = {
        "arquivo trocado": outro_arquivo,
        "mesmo nome, outro tamanho": mesmo_nome_outro_tamanho,
        "arquivo a mais": mais_um_arquivo,
        "outro estado": outro_status,
        "outro carimbo de alteração": outro_carimbo,
    }
    iguais = sorted(rotulo for rotulo, c in distintos.items() if c == base)
    assert not iguais, (
        f"o código não mudou quando mudou: {iguais}. Um código cego a isso "
        "autoriza uma escrita diferente da que foi mostrada."
    )

    # E o contrário, que é a metade que faltaria: o MESMO plano dá o mesmo
    # código. Um código aleatório passaria em tudo acima e tornaria a segunda
    # chamada impossível.
    assert _codigo(disciplinas_brutas, _rascunho_editavel()) == base


# ---------------------------------------------------------------------- E9


def test_e9_codigo_velho_e_recusado_e_a_mensagem_traz_o_plano_novo(
    disciplinas_brutas,
):
    velho = _codigo(disciplinas_brutas, _rascunho_editavel())

    # Alguém anexou outro arquivo entre a leitura e a escrita — o caso real que
    # esta camada existe para pegar.
    agora_com_outro = _rascunho_editavel(
        arquivos=("EC1-relatorio.pdf", "anexo-novo.pdf")
    )
    cliente = ClienteFalso(_respostas(disciplinas_brutas, agora_com_outro))

    resposta = _entregar(cliente, confirmacao=velho)

    assert not resposta.escreveu
    assert cliente.escritas == []
    # A recusa sem o plano novo mandaria quem lê adivinhar o que mudou, e o
    # caminho mais curto dali seria tentar de novo com o mesmo código.
    assert "anexo-novo.pdf" in resposta.texto, (
        "a recusa não trouxe o plano de agora — quem lê fica sem saber o que "
        f"mudou:\n{resposta.texto}"
    )
    assert resposta.codigo in resposta.texto
    assert velho in resposta.texto, "a recusa não diz qual código foi mandado"


# --------------------------------------------------------------------- E10


def test_e10_as_cinco_recusas_dizem_cinco_coisas_diferentes(disciplinas_brutas):
    """E10 — cinco recusas, cinco mensagens.

    A ordem das checagens é parte da asserção: uma entrega já enviada tem
    `cansubmit` falso por consequência, e responder ali "o site não aceita envio
    seu" mandaria procurar um problema que não existe. Cada caso abaixo é
    montado para disparar exatamente uma delas.
    """
    casos = {
        "grupo": (
            _rascunho_editavel(em_grupo=True),
            {},
            ("grupo", "outras pessoas"),
        ),
        "travada": (
            _rascunho_editavel(travada=True),
            {},
            ("travada",),
        ),
        "ja entregue": (
            status_de_entrega(status="submitted", com_texto_online=False),
            {},
            ("já está entregue",),
        ),
        "nao pode enviar": (
            _rascunho_editavel(pode_enviar=False),
            {},
            ("não pode enviar",),
        ),
        "sem arquivo": (
            _rascunho_editavel(arquivos=()),
            {},
            ("nenhum arquivo",),
        ),
    }

    mensagens = {}
    for rotulo, (status, do_assign, esperados) in casos.items():
        cliente = ClienteFalso(_respostas(disciplinas_brutas, status, **do_assign))
        resposta = _entregar(cliente)

        assert not resposta.escreveu, rotulo
        assert cliente.escritas == [], rotulo
        assert resposta.recusa, f"{rotulo}: não recusou:\n{resposta.texto}"
        for esperado in esperados:
            assert esperado.lower() in resposta.texto.lower(), (
                f"{rotulo}: a recusa não fala de {esperado!r}:\n{resposta.texto}"
            )
        mensagens[rotulo] = resposta.recusa

    assert len(set(mensagens.values())) == 5, (
        "duas recusas com a mesma mensagem: "
        f"{ {r: m[:40] for r, m in mensagens.items()} }. Cinco causas com um "
        "texto só é o mesmo que uma recusa muda — quem lê não sabe o que fazer."
    )

    # E o caminho feliz não pode ser recusado por nenhuma delas, senão os cinco
    # verdes acima seriam um `entregar` que recusa tudo.
    respostas = _respostas(disciplinas_brutas, _rascunho_editavel())
    respostas[ESCRITA] = {"status": True}
    assert _entregar(ClienteFalso(respostas), confirmacao=None).recusa is None


def test_e10b_a_recusa_do_cronometro_e_o_que_o_spec_nao_previu(disciplinas_brutas):
    """A sexta recusa, achada ao implementar e não no spec.

    `mod_assign_start_submission` continua no bloqueio permanente: ela liga o
    cronômetro de uma entrega cronometrada, e o catálogo deste repositório a
    registra como análogo exato de `mod_quiz_start_attempt`. A consequência é
    que gravar rascunho numa entrega cronometrada e não iniciada é um caminho
    que este servidor não tem — e sem esta recusa ele chegaria como erro cru do
    site, que é o oposto do que o projeto promete.

    O contrário também é asserção: entrega cronometrada JÁ iniciada segue
    normal. Recusar as duas seria matar o caso legítimo junto com o impossível.
    """
    parada = status_de_entrega(
        status="draft",
        com_texto_online=True,
        tempo_limite=3600,
        comecou=False,
    )
    cliente = ClienteFalso(_respostas(disciplinas_brutas, parada, tempo_limite=3600))

    resposta = asyncio.run(
        ent.salvar_rascunho(
            cliente, "PTC3314", NOME_DA_ENTREGA, "texto novo", agora=AGORA
        )
    )

    assert not resposta.escreveu
    assert cliente.escritas == []
    assert "cronometrada" in resposta.texto.lower()
    assert "60 minuto" in resposta.texto, (
        f"a recusa não diz de quanto é o relógio:\n{resposta.texto}"
    )

    ja_iniciada = status_de_entrega(
        status="draft", com_texto_online=True, tempo_limite=3600, comecou=True
    )
    cliente2 = ClienteFalso(
        _respostas(disciplinas_brutas, ja_iniciada, tempo_limite=3600)
    )
    segunda = asyncio.run(
        ent.salvar_rascunho(
            cliente2, "PTC3314", NOME_DA_ENTREGA, "texto novo", agora=AGORA
        )
    )
    assert segunda.recusa is None, (
        f"entrega cronometrada já iniciada foi recusada:\n{segunda.texto}"
    )


# --------------------------------------------------------------------- E11


def test_e11_sem_suporte_a_elicitacao_nao_bloqueia_e_a_saida_diz_qual_foi(
    disciplinas_brutas,
):
    """E11 — os três desfechos da pergunta, e as três saídas diferentes.

    "Não pude perguntar" tratado como "disseram não" cancelaria toda entrega
    feita de um cliente sem elicitação; tratado como "disseram sim" seria pior,
    porque a saída afirmaria uma confirmação que ninguém deu. O certo é o
    terceiro: escreve, porque quem autorizou foi o código do plano, e DIZ que
    não houve pergunta.
    """
    def _com(perguntar):
        respostas = _respostas(disciplinas_brutas, _rascunho_editavel())
        respostas[ESCRITA] = {"status": True}
        cliente = ClienteFalso(respostas)
        codigo = _entregar(cliente).codigo
        return cliente, _entregar(cliente, confirmacao=codigo, perguntar=perguntar)

    def _nao_sabe_perguntar(_mensagem):
        raise ent.ElicitacaoIndisponivel

    sem_suporte_cliente, sem_suporte = _com(_nao_sabe_perguntar)
    assert sem_suporte.escreveu, (
        "cliente sem elicitação ficou bloqueado — a camada do plano continua "
        f"valendo sozinha:\n{sem_suporte.texto}"
    )
    assert "não foi possível perguntar" in sem_suporte.texto.lower()
    assert len(sem_suporte_cliente.escritas) == 1

    recusou_cliente, recusou = _com(lambda _mensagem: False)
    assert not recusou.escreveu
    assert recusou_cliente.escritas == [], (
        "disseram NÃO e escreveu assim mesmo — é a única resposta da pergunta "
        "que muda o desfecho, e ela precisa mudar"
    )
    assert "resposta foi não" in recusou.texto.lower()

    aceitou_cliente, aceitou = _com(lambda _mensagem: True)
    assert aceitou.escreveu
    assert len(aceitou_cliente.escritas) == 1
    assert "não foi possível perguntar" not in aceitou.texto.lower(), (
        "perguntou, ouviu sim, e a saída ainda avisa que não perguntou"
    )

    # As três saídas são distintas: um texto igual para os três desfechos
    # deixaria quem lê sem saber o que aconteceu do outro lado.
    assert len({sem_suporte.texto, recusou.texto, aceitou.texto}) == 3

    # E a pergunta feita é o PLANO, não um "confirma?" pelado — quem responde
    # tem de ver o que está confirmando.
    vistas = []
    _com(lambda mensagem: vistas.append(mensagem) or True)
    assert vistas and NOME_DA_ENTREGA in vistas[0], (
        f"a pergunta não mostra o plano: {vistas!r}"
    )


def test_e11b_a_pergunta_so_acontece_depois_do_codigo_conferido(
    disciplinas_brutas,
):
    """A ordem das camadas 2 e 3, que nenhum outro teste alcança.

    Perguntar antes de conferir o código faria o cliente abrir uma pergunta
    sobre um plano velho — e a pessoa confirmaria uma coisa que já não é
    verdade. A pergunta é a ÚLTIMA parada antes da escrita, nunca a primeira.
    """
    perguntas = []
    cliente = ClienteFalso(_respostas(disciplinas_brutas, _rascunho_editavel()))

    _entregar(cliente, perguntar=lambda m: perguntas.append(m) or True)
    assert perguntas == [], "perguntou na chamada do plano, que não escreve nada"

    _entregar(
        cliente,
        confirmacao="000000",
        perguntar=lambda m: perguntas.append(m) or True,
    )
    assert perguntas == [], "perguntou com código que não confere"
    assert cliente.escritas == []


# --------------------------------------------------------------------- E12


def test_e12_sao_duas_ferramentas_e_nenhuma_escolhe_entre_salvar_e_entregar(
    monkeypatch,
):
    """E12 — camada 1, do lado do que o modelo vê.

    Um `acao: "salvar" | "entregar"` põe as duas a uma letra de distância na
    cabeça de quem gera a chamada, e a segunda não tem volta. Este teste é a
    única coisa que impede alguém de "simplificar" as duas em uma.
    """
    monkeypatch.setenv(politica.NOME_DA_FLAG, "1")
    ferramentas = {f["name"]: f for f in server.listar_ferramentas()}

    assert "salvar_rascunho" in ferramentas and "entregar" in ferramentas

    assert set(ferramentas["entregar"]["inputSchema"]["properties"]) == {
        "disciplina",
        "entrega",
        "confirmacao",
    }
    assert set(ferramentas["salvar_rascunho"]["inputSchema"]["properties"]) == {
        "disciplina",
        "entrega",
        "texto",
        "confirmacao",
    }

    for nome in ("salvar_rascunho", "entregar"):
        schema = ferramentas[nome]["inputSchema"]
        for parametro, forma in schema["properties"].items():
            assert "enum" not in forma, (
                f"{nome}.{parametro} tem um enum — é por aí que um parâmetro "
                "que escolhe o verbo entraria"
            )
            assert forma.get("description"), f"{nome}.{parametro} sem descrição"
        # `confirmacao` NÃO é obrigatória: se fosse, não haveria primeira
        # chamada, e a camada do plano deixaria de existir.
        assert "confirmacao" not in schema["required"], nome

    # O nome de cada ferramenta é o verbo, e as descrições não se confundem:
    # a de entregar avisa que não desfaz, a de rascunho avisa que não entrega.
    assert "NÃO tem como ser desfeito" in ferramentas["entregar"]["description"]
    assert "NÃO é entrega feita" in ferramentas["salvar_rascunho"]["description"]


# ----------------------------------------------------------- 16/09/2026
# Dois defeitos medidos depois do spec. O primeiro é do PRÓPRIO spec: a lista
# das "quatro coisas" que entram no código não tem o verbo, e a Camada 2 reabria
# o que a Camada 1 tinha separado. O segundo é do cliente, mas só aqui ele tem
# a cara que importa: "Feito" impresso sobre uma recusa do site.


def _rascunho_com_texto_e_arquivo():
    """O estado em que os DOIS verbos passam pela camada 5: rascunho editável,
    com texto online (para `salvar_rascunho`) e um arquivo (para `entregar`)."""
    return status_de_entrega(status="draft", com_texto_online=True)


def test_e15_o_codigo_do_rascunho_nao_confirma_a_entrega(disciplinas_brutas):
    """E15 — o código amarra o VERBO, não só o estado.

    Caminho real: a pessoa pede "salva aí", recebe o plano do rascunho com o
    código, diz "agora entrega" — e o mesmo código, para o mesmo estado, faria
    `mod_assign_submit_for_grading` sair sem o plano de entrega ter sido
    mostrado. É o caso "uma palavra de distância" que a Camada 1 separa,
    reaberto pela Camada 2. O spec lista quatro coisas no hash; são cinco.
    """
    respostas = _respostas(disciplinas_brutas, _rascunho_com_texto_e_arquivo())
    respostas[ESCRITA] = []
    respostas["mod_assign_save_submission"] = []
    cliente = ClienteFalso(respostas)

    plano_rascunho = asyncio.run(
        ent.salvar_rascunho(
            cliente, "PTC3314", NOME_DA_ENTREGA, "texto do rascunho", agora=AGORA
        )
    )
    plano_entrega = _entregar(cliente)
    assert not plano_rascunho.escreveu and not plano_entrega.escreveu
    assert plano_rascunho.codigo != plano_entrega.codigo, (
        "o MESMO código confirma salvar e entregar — o plano do rascunho "
        "autoriza a escrita que não tem volta"
    )

    # O código do rascunho, apresentado a `entregar`, é código velho: não
    # escreve, e a resposta traz o plano de ENTREGA para a pessoa ler.
    resposta = _entregar(cliente, confirmacao=plano_rascunho.codigo)
    assert not resposta.escreveu
    assert cliente.escritas == [], f"entregou com o código do rascunho: {cliente.escritas}"
    assert resposta.recusa == "codigo_velho"
    assert "Plano de entrega" in resposta.texto

    # E o contrário: o de rascunho não grava a partir do código de entrega.
    segunda = asyncio.run(
        ent.salvar_rascunho(
            cliente, "PTC3314", NOME_DA_ENTREGA, "texto do rascunho",
            confirmacao=plano_entrega.codigo, agora=AGORA,
        )
    )
    assert not segunda.escreveu
    assert cliente.escritas == []

    # Cada verbo com o próprio código continua funcionando, senão a cura seria
    # dois verbos que não escrevem nunca.
    feito = _entregar(cliente, confirmacao=plano_entrega.codigo)
    assert feito.escreveu
    assert [f for f, _ in cliente.escritas] == [ESCRITA]


def test_e15b_o_codigo_de_verbos_diferentes_difere_para_o_mesmo_plano(
    disciplinas_brutas,
):
    """A metade de unidade de E15: `codigo_do_plano` é função do verbo."""
    atividade = ent.projetar_atividades(
        entregas_falsas([(CURSO_PTC3314, [(ASSIGNID, NOME_DA_ENTREGA, PRAZO, 0)])])
    )[0]
    plano = ent.montar_plano(_rascunho_com_texto_e_arquivo(), atividade, "PTC3314")

    assert ent.codigo_do_plano(plano, verbo="entrega") != ent.codigo_do_plano(
        plano, verbo="rascunho"
    )
    assert ent.codigo_do_plano(plano, verbo="entrega") == ent.codigo_do_plano(
        plano, verbo="entrega"
    )


def test_e16_recusa_do_site_na_escrita_nao_vira_feito(disciplinas_brutas, monkeypatch):
    """E16 — HTTP 200 com `[{"warningcode": ...}]` é recusa, e "Feito" é mentira.

    Aqui o cliente é o `ClienteMoodle` DE VERDADE com transporte injetado, e não
    o dublê: o defeito mora na tradução de erro do cliente, e um dublê que
    devolve o que o teste mandou não passaria por ela. Nada sai para a rede.
    """
    from usp_mcp.moodle.cliente import ClienteMoodle
    from usp_mcp.moodle.erros import ErroMoodle

    monkeypatch.setenv(politica.NOME_DA_FLAG, "1")
    respostas = _respostas(disciplinas_brutas, _rascunho_editavel())
    respostas[ESCRITA] = [
        {
            "item": "assignment",
            "itemid": ASSIGNID,
            "warningcode": "submissionsclosed",
            "message": "Submissions are closed",
        }
    ]
    saiu = []

    def transporte(*, url, dados):
        saiu.append(dados["wsfunction"])
        return respostas[dados["wsfunction"]]

    cliente = ClienteMoodle(
        token="TOKEN-SINTETICO-NAO-E-CREDENCIAL",
        url="https://exemplo.invalid",
        transporte=transporte,
    )

    plano = _entregar(cliente)
    assert not plano.escreveu and plano.codigo

    with pytest.raises(ErroMoodle) as e:
        _entregar(cliente, confirmacao=plano.codigo)
    texto = str(e.value)
    assert "submissionsclosed" in texto
    assert "feito" not in texto.lower()
    # A escrita FOI tentada — o que este teste nega é o "Feito", não a chamada.
    assert saiu.count(ESCRITA) == 1
