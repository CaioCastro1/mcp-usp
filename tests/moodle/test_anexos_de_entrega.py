"""T111-T120: os PDFs que moram dentro de uma entrega, e não no acervo.

O achado que originou estes testes veio do uso, não da suíte: `material` listava
53 itens de PTC3314 e **nenhum** era o enunciado do EC-1 — que existe, é um PDF
de 218 kB e estava a uma chamada de distância. Medido em 12/09/2026:

| chamada | o que traz sobre o EC-1 |
|---|---|
| `core_course_get_contents` | o módulo `assign`, com `contents` **vazio** |
| `description` do módulo | 529 B de datas, **zero `href`**, zero `pluginfile` |
| `mod_assign_get_assignments` | `EP1-2026.pdf` (218.344 B) e `EP1-2026.odt` |

As fixtures deste arquivo são um **par real**: as duas respostas são da mesma
disciplina, da mesma sessão, e o `cmid` que liga o anexo à seção é o do Moodle.
Um par escrito à mão provaria só que o teste sabe casar dois dicionários que ele
mesmo inventou.
"""
from __future__ import annotations

import pytest

from tests.moodle.conftest import ClienteFalso
from usp_mcp.moodle import arquivo as arq
from usp_mcp.moodle import disciplinas as disc
from usp_mcp.moodle import material as mat
from usp_mcp.moodle import politica

COURSEID_PTC3314 = 142036
CMID_EC1 = 6372328
NOME_EC1 = "EC-1 - Transitórios em LT"
SECAO_EC1 = "17 agosto - 23 agosto"


@pytest.fixture(autouse=True)
def _cache_limpo():
    disc.limpar_cache()
    yield
    disc.limpar_cache()


@pytest.fixture
def cliente_ptc3314(disciplinas_brutas, conteudo_ptc3314, entregas_ptc3314):
    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 999},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_ptc3314,
            "mod_assign_get_assignments": entregas_ptc3314,
        }
    )


# ------------------------------------------------------------------ projeção

@pytest.mark.contrato
def test_a_projecao_registra_as_entregas_com_cmid_e_secao(conteudo_ptc3314):
    """T111 — `assign` deixa de ser só um nome na lista de "sem conteúdo".

    É esse registro que decide se a segunda chamada vale: sem `cmid` não há como
    ligar o anexo à seção onde ele aparece, e sem a lista não há como saber que a
    disciplina tem entrega nenhuma.
    """
    conteudo = mat.projetar_material(conteudo_ptc3314)

    assert len(conteudo.entregas) == 4, (
        "PTC3314 tem 4 módulos assign na captura de 12/09 — 2 ECs e 2 provas"
    )
    ec1 = [e for e in conteudo.entregas if e.cmid == CMID_EC1]
    assert len(ec1) == 1, f"o cmid {CMID_EC1} sumiu da projeção"
    assert ec1[0].nome == NOME_EC1
    assert ec1[0].secao == SECAO_EC1


@pytest.mark.contrato
def test_o_anexo_da_entrega_vira_item_com_o_assign_como_modulo(
    conteudo_ptc3314, entregas_ptc3314
):
    """T112 — o anexo entra no acervo com o nome da entrega como rótulo.

    O nome do arquivo (`EP1-2026.pdf`) não diz o assunto; `EC-1 - Transitórios em
    LT` diz. `rotulo_do_modulo` já imprime esse campo — é por ele que quem lê a
    listagem consegue escolher.
    """
    conteudo = mat.projetar_material(conteudo_ptc3314)
    itens = mat.projetar_anexos_de_entrega(entregas_ptc3314, conteudo.entregas).itens

    pdfs = [i for i in itens if i.nome == "EP1-2026.pdf"]
    assert len(pdfs) == 1, f"EP1-2026.pdf não virou item. Itens: {[i.nome for i in itens]}"
    item = pdfs[0]
    assert item.tipo == "PDF"
    assert item.tamanho == 218344
    assert item.modulo == NOME_EC1
    assert item.secao == SECAO_EC1
    assert item.fileurl_bruta and "pluginfile.php" in item.fileurl_bruta, (
        "sem a fileurl bruta o item é visível e não baixável"
    )
    assert item.url_externa is None, (
        "é arquivo do webservice: o endereço não sai daqui (Invariante 3)"
    )
    odt = [i for i in itens if i.nome == "EP1-2026.odt"][0]
    assert odt.tipo == "documento", (
        "o professor publica o mesmo enunciado em PDF e ODT; sair como "
        "'arquivo' esconde que é a mesma coisa em outro formato"
    )


@pytest.mark.contrato
def test_o_warning_de_sem_acesso_nao_e_engolido(conteudo_ptc3314, entregas_ptc3314):
    """T113 — Invariante 7: dois módulos que o token não lê têm de ser ditos.

    A resposta real traz `warningcode: 1` para dois módulos. Sem isto a lista
    sai com cara de completa quando não é — o falso "não tem nada".
    """
    conteudo = mat.projetar_material(conteudo_ptc3314)
    anexos = mat.projetar_anexos_de_entrega(entregas_ptc3314, conteudo.entregas)

    assert len(anexos.avisos) == 1, f"avisos: {anexos.avisos}"
    assert "2" in anexos.avisos[0], (
        "o aviso precisa dizer QUANTAS atividades ficaram fora de alcance"
    )


# -------------------------------------------------------------------- acervo

@pytest.mark.contrato
def test_o_acervo_pede_as_entregas_com_escopo_de_uma_disciplina(cliente_ptc3314):
    """T114 — asserção sobre o parâmetro ENVIADO (item 11 do CLAUDE.md).

    `mod_assign_get_assignments` **sem** `courseids` devolve as 74 matrículas: 1
    MB, ~251k tokens (§9, 28/08). O escopo não é otimização, é requisito — e o
    dublê devolveria a fixture de qualquer jeito, então olhar a saída não prova
    que o escopo foi mandado.
    """
    mat.acervo(cliente_ptc3314, COURSEID_PTC3314)

    params = cliente_ptc3314.params_de("mod_assign_get_assignments")
    assert params == {"courseids[0]": COURSEID_PTC3314}


@pytest.mark.contrato
def test_disciplina_sem_entrega_nao_gasta_a_segunda_chamada(disciplinas_brutas):
    """T115 — Invariante 5: não martelar a USP por uma resposta previsível.

    A lista de módulos já diz se existe `assign`. Sem nenhum, a chamada só pode
    devolver vazio — e o dublê REPROVA função não prevista, que é o que torna
    esta asserção uma prova e não uma esperança.
    """
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 999},
            "core_enrol_get_users_courses": disciplinas_brutas,
            # `mod_assign_get_assignments` ausente de propósito: se o código a
            # chamar, o ClienteFalso levanta AssertionError e o teste reprova.
            "core_course_get_contents": [
                {"name": "Geral", "modules": [{"modname": "forum", "name": "Avisos"}]}
            ],
        }
    )

    mat.acervo(cliente, 1)

    assert [c[0] for c in cliente.chamadas] == ["core_course_get_contents"]


# --------------------------------------------------------- as duas ferramentas

@pytest.mark.contrato
def test_material_lista_o_enunciado_que_estava_fora_de_alcance(cliente_ptc3314):
    """T116 — o caso que o dono relatou, ponta a ponta e offline."""
    r = mat.material(cliente_ptc3314, "PTC3314", agora=lambda: 0.0)

    assert "EP1-2026.pdf" in r.texto
    assert NOME_EC1 in r.texto, "sem o nome da entrega, ninguém liga o PDF ao EC-1"


@pytest.mark.contrato
def test_o_aviso_nao_diz_mais_que_assign_esta_fora_da_lista(cliente_ptc3314):
    """T117 — o rodapé era verdade e deixou de ser.

    Ele dizia "não estão nesta lista: assign, forum, quiz". Com os anexos dentro,
    repetir isso mandaria quem lê procurar em outro lugar o que está ali.
    """
    r = mat.material(cliente_ptc3314, "PTC3314", agora=lambda: 0.0)

    rodape = r.texto.split("⚠", 1)[1] if "⚠" in r.texto else ""
    assert "assign" not in rodape, (
        "o rodapé ainda declara `assign` como ausente da lista:\n" + rodape
    )
    assert "forum" in rodape, "forum continua fora da lista, e continua declarado"


@pytest.mark.contrato
def test_baixar_arquivo_acha_o_anexo_da_entrega(cliente_ptc3314, tmp_path):
    """T118 — a segunda ferramenta ganha o anexo sem caso especial.

    `baixar_arquivo` opera sobre a mesma projeção; o anexo chega como `Item` com
    `fileurl_bruta` e `fileid`, então o download é o mesmo caminho de sempre. A
    asserção é sobre a URL PEDIDA ao transporte, não sobre bytes que o dublê
    devolveria de qualquer forma.
    """
    # `raiz=tmp_path` e não o depósito real: com o cache de verdade, o segundo
    # `pytest` do dia acharia o arquivo em disco, pularia o download e passaria
    # sem provar nada — o falso-verde que esta suíte existe para não produzir.
    r = arq.baixar_arquivo(
        cliente_ptc3314, "PTC3314", "EP1-2026.pdf", agora=lambda: 0.0, raiz=tmp_path
    )

    assert len(cliente_ptc3314.downloads) == 1, (
        f"downloads: {cliente_ptc3314.downloads}"
    )
    assert "mod_assign/introattachment" in cliente_ptc3314.downloads[0]
    assert len(r.baixados) == 1
    assert r.baixados[0].nome == "EP1-2026.pdf"


# ------------------------------------------------------------------- política

@pytest.mark.politica
def test_a_allowlist_cresceu_por_uma_funcao_de_leitura_so():
    """T119 — a quinta função entra, e as irmãs de escrita seguem negadas.

    `mod_assign_get_assignments` é leitura. `mod_assign_submit_for_grading` mora
    no bloqueio permanente do §2.2 e não é liberada por prefixo nenhum — é essa
    vizinhança de nome que faz esta asserção valer a pena.
    """
    assert politica.decidir("mod_assign_get_assignments").permitida
    assert not politica.decidir("mod_assign_submit_for_grading").permitida
    assert not politica.decidir("mod_assign_save_submission").permitida
    assert not politica.decidir("mod_assign_get_submissions").permitida, (
        "entrega de colega não é material do dono — só a função medida entrou"
    )


@pytest.mark.contrato
def test_a_descricao_da_ferramenta_conta_que_o_enunciado_esta_la():
    """T121 — o anexo entrou no acervo; se a descrição não disser, ninguém pede.

    Quem escolhe a ferramenta é um modelo lendo a descrição diante de uma
    pergunta em português. "Que arquivos tem em PTC3314" já achava `material`;
    "cadê o enunciado do EC-1" não achava, e continuaria não achando com o
    código certo por trás.
    """
    from usp_mcp.moodle.server import listar_ferramentas

    descricao = [f for f in listar_ferramentas() if f["name"] == "material"][0][
        "description"
    ]

    assert "enunciado" in descricao.lower()
    assert "mod_assign" not in descricao, (
        "a descrição fala a língua de quem pergunta, não a da API (T43)"
    )


@pytest.mark.contrato
def test_o_rodape_nomeia_algumas_entregas_mudas_e_conta_o_resto(disciplinas_brutas):
    """T122 — declarar o que ficou de fora não é despejar a lista inteira.

    Medido em PSI3472 (12/09): 10 das 11 entregas não têm anexo, e nomear as 10
    produziu um rodapé de 4 linhas que enterra os outros avisos. O Invariante 7
    pede que o corte seja DITO, não que não exista — a contagem é o que faz o
    corte honesto, e é ela que tem de sobreviver ao teto.
    """
    modulos = [
        {"modname": "assign", "id": i, "name": f"Lição aulas {i}"} for i in range(11)
    ]
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 999},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": [
                {
                    "name": "Geral",
                    "modules": modulos
                    + [
                        {
                            "modname": "resource",
                            "id": 99,
                            "name": "Regras",
                            "contents": [
                                {"filename": "regras.pdf", "mimetype": "application/pdf"}
                            ],
                        }
                    ],
                }
            ],
            "mod_assign_get_assignments": {"courses": [], "warnings": []},
        }
    )

    texto = mat.material(cliente, "PSI3323", agora=lambda: 0.0).texto

    assert "11 de 11 entregas" in texto, "a contagem é o que não pode ser cortada"
    assert texto.count("Lição aulas") <= 3, (
        "o rodapé despeja a lista inteira de entregas mudas:\n" + texto
    )
    assert "e mais 8" in texto, "cortou sem dizer quantos ficaram de fora"


@pytest.mark.contrato
@pytest.mark.parametrize("quantas", [1, 2, 3, 4, 5])
def test_o_rodape_nao_promete_entregas_que_nao_existem(disciplinas_brutas, quantas):
    """T123 — abaixo do teto não há resto, e o rodapé não pode inventar um.

    O T122 mediu o caso ACIMA do teto (11 de 11 em PSI3472) e travou o corte.
    Abaixo dele ninguém olhou, e é lá que estava o defeito: com 2 entregas mudas
    o rodapé de PTC3314 saiu, ao vivo em 12/09/2026, com

        "... : Prova Presencial - 1, Prova Presencial - 2, e mais -1."

    "e mais -1" não é nada que exista. E o dano não é cosmético: quem lê o
    rodapé é um modelo decidindo se já viu tudo, e um resto anunciado o faz
    procurar uma entrega que a ferramenta não tem — o Invariante 7 ao contrário,
    afirmando ausência em vez de declará-la.

    Parametrizado em torno do teto (3) porque o erro é de sinal: só aparece
    quando a subtração dá negativo, e some exatamente no limite.
    """
    modulos = [
        {"modname": "assign", "id": i, "name": f"Prova Presencial - {i}"}
        for i in range(quantas)
    ]
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 999},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": [
                {
                    "name": "Geral",
                    "modules": modulos
                    + [
                        {
                            "modname": "resource",
                            "id": 99,
                            "name": "Regras",
                            "contents": [
                                {"filename": "regras.pdf", "mimetype": "application/pdf"}
                            ],
                        }
                    ],
                }
            ],
            "mod_assign_get_assignments": {"courses": [], "warnings": []},
        }
    )

    texto = mat.material(cliente, "PSI3323", agora=lambda: 0.0).texto

    assert "e mais -" not in texto, (
        "o rodapé anunciou um resto negativo — não existe 'e mais -1':\n" + texto
    )
    assert f"{quantas} de {quantas} entregas" in texto, (
        "a contagem some quando o teto muda de lado:\n" + texto
    )

    sobra = quantas - mat._TETO_NOMES_NO_RODAPE
    if sobra > 0:
        assert f"e mais {sobra}" in texto, (
            f"cortou {sobra} sem dizer quantos ficaram de fora:\n" + texto
        )
    else:
        assert "e mais" not in texto, (
            "nomeou todas as entregas e ainda assim falou em resto:\n" + texto
        )
        assert texto.count("Prova Presencial") == quantas, (
            "abaixo do teto o rodapé nomeia todas — não é amostra:\n" + texto
        )
