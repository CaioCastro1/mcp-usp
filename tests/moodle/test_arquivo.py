"""T84–T90, T95c — a terceira ferramenta do Moodle, no singular.

Tudo offline: nenhum teste deste arquivo toca a rede. O `raiz` do depósito é
sempre `tmp_path`, para não escrever no cache real de quem roda a suíte.
"""
from __future__ import annotations

import copy

import pytest

from usp_mcp.moodle import arquivo as arq
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.cliente import ClienteMoodle
from usp_mcp.moodle.erros import ErroMoodle, MoodleIndisponivel

from .conftest import ClienteFalso


@pytest.fixture(autouse=True)
def _cache_limpo():
    """Cache de processo compartilhado entre casos produz verde que nunca chamou
    nada — o mesmo motivo pelo qual `limpar_cache` existe."""
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(conteudo_bruto, disciplinas_brutas, **extra):
    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_bruto,
        },
        **extra,
    )


@pytest.mark.contrato
def test_T84_sigla_que_nao_resolve_nao_gasta_chamada_de_conteudo(disciplinas_brutas):
    """Consultar o Moodle para descobrir que a pergunta estava errada é gastar
    chamada da conta do dono à toa."""
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
        }
    )

    with pytest.raises(ErroMoodle):
        arq.baixar_arquivo(cliente, "XYZ9999", "prova")

    chamadas = [nome for nome, _ in cliente.chamadas]
    assert "core_course_get_contents" not in chamadas
    assert cliente.downloads == []


@pytest.mark.contrato
def test_T85_nenhum_casamento_diz_o_total_da_disciplina(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """'nada com esse nome' e 'disciplina vazia' têm curas diferentes."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "zzz-nao-existe", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == []
    assert "29" in r.texto  # o total de itens de PSI3323


@pytest.mark.contrato
def test_T86_um_casamento_baixa_grava_e_devolve_o_caminho(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert len(r.baixados) == 1
    baixado = r.baixados[0]
    assert baixado.nome == "Prova-PSI3323-2026-Grupos.pdf"
    assert baixado.caminho.is_file()
    assert baixado.caminho.read_bytes().startswith(b"%PDF")
    assert str(baixado.caminho) in r.texto
    assert len(cliente.downloads) == 1


@pytest.mark.contrato
def test_T86b_a_resposta_diz_que_quem_abre_o_arquivo_e_quem_chamou(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Sem isso, um cliente que não saiba ler arquivo local recebe um caminho e
    não entende o que fazer com ele (Invariante 6)."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert "disco" in r.texto.lower()
    assert "abra" in r.texto.lower() or "abrir" in r.texto.lower()


@pytest.mark.contrato
def test_T87_ambiguidade_recusa_e_lista_secao_e_modulo(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """A colisão REAL de PSI3323: 'Dicas para a Prova.pdf' existe duas vezes,
    com ids 9599793 (seção Geral) e 9599833 (seção AULA 6). O nome sozinho não
    distingue — por isso o desempate mostra seção e módulo, não o id."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == [], "recusou e mesmo assim baixou"
    assert len(r.candidatos) == 2
    assert "Geral" in r.texto and "AULA 6" in r.texto
    assert "todos" in r.texto.lower()


@pytest.mark.contrato
def test_T89_casamento_ignora_acento(conteudo_bruto, disciplinas_brutas, tmp_path):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "formulario", raiz=tmp_path)

    assert len(r.baixados) == 1
    assert r.baixados[0].nome.startswith("Formul")


@pytest.mark.politica
def test_T90_link_externo_nao_e_baixado(conteudo_bruto, disciplinas_brutas, tmp_path):
    """Os 7 `url` de PSI3323 apontam para fora (YouTube, Google Docs). Baixá-los
    mandaria o token para outro host — e a allowlist do cliente recusaria."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Planilha de Notas", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == []
    assert len(r.links) == 1
    assert r.links[0].url.startswith("http")
    assert "link" in r.texto.lower()


@pytest.mark.contrato
def test_T95c_segunda_chamada_reusa_o_disco_sem_baixar_de_novo(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Invariante 5: TTL colado na taxa de mudança do dado. Aqui o 'TTL' é o
    `timemodified` no caminho — arquivo não modificado não é rebaixado."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    primeira = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)
    assert len(cliente.downloads) == 1

    segunda = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert len(cliente.downloads) == 1, "baixou de novo o que já estava em disco"
    assert segunda.baixados[0].caminho == primeira.baixados[0].caminho
    assert segunda.baixados[0].reusado is True
    assert primeira.baixados[0].reusado is False


@pytest.mark.politica
def test_T99c_nenhuma_url_interna_aparece_no_texto_da_resposta(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """A ferramenta que BAIXA também não emite a URL — o caminho local é a
    entrega, e a URL continua sendo o que não sai (Invariante 3)."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert "pluginfile.php" not in r.texto
    assert "/webservice/" not in r.texto


@pytest.mark.politica
def test_T99d_nenhuma_url_interna_aparece_mesmo_quando_ha_recusa(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """T99c cobria só o caminho de SUCESSO. Achado da re-revisão: uma
    resposta com `recusados` (o `Recusado` nasce de `str(exc)` de um erro do
    cliente, que pode embutir endereço — é o caso de `FuncaoBloqueada`)
    também precisa passar por esta asserção, não só o caminho feliz.

    Usa o mesmo cenário REAL de T103b (não um dublê com mensagem
    inventada): a allowlist de verdade de `cliente.baixar` é quem recusa.
    """
    bruto = _com_dicas_geral_apontando_para_host_estranho(conteudo_bruto)
    cliente = _cliente_moodle_real(bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert r.recusados, "cenário não produziu recusa — teste não alcança o caminho"
    assert "pluginfile.php" not in r.texto
    assert "/webservice/" not in r.texto


# --- T88, T97, T98: plural e tetos -----------------------------------------

@pytest.mark.contrato
def test_T88_todos_baixa_a_colisao_inteira_em_caminhos_distintos(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) == 2
    caminhos = {b.caminho for b in r.baixados}
    assert len(caminhos) == 2, "mesmo nome sobrescreveu — o fileid não entrou no caminho"
    assert {b.fileid for b in r.baixados} == {"9599793", "9599833"}
    assert all(c.is_file() for c in caminhos)


@pytest.mark.contrato
def test_T97_arquivo_acima_do_teto_e_recusado_ANTES_de_baixar(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    """O `filesize` vem na listagem: dá para recusar sem gastar banda nenhuma."""
    monkeypatch.setattr(arq, "TETO_ARQUIVO_BYTES", 1000)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert cliente.downloads == [], "recusou pelo teto e mesmo assim baixou"
    assert r.baixados == ()
    assert len(r.recusados) == 1
    assert "teto" in r.recusados[0].motivo.lower()
    assert r.recusados[0].nome in r.texto


@pytest.mark.contrato
def test_T98_plural_acima_do_teto_de_contagem_nomeia_o_que_ficou_de_fora(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    """Invariante 7: cortou, a saída diz — e diz QUAIS, não só quantos."""
    monkeypatch.setattr(arq, "TETO_PLURAL_ARQUIVOS", 1)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) == 1
    assert len(r.recusados) == 1
    assert r.recusados[0].nome in r.texto
    assert len(cliente.downloads) == 1


@pytest.mark.contrato
def test_T98b_plural_acima_do_teto_de_bytes_para_no_limite(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    monkeypatch.setattr(arq, "TETO_PLURAL_BYTES", 1)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) <= 1
    assert r.recusados


@pytest.mark.contrato
def test_T98c_a_ordem_do_corte_e_a_da_listagem(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    """Quem leu a lista em `material` e pediu todos=true recebe o PREFIXO do que
    viu — nada de 'os menores primeiro' nem de ordenação implícita.

    'roteiro' casa com três arquivos de tamanhos bem diferentes — 841.661 B
    (AULA 2, primeiro na listagem), 269.887 B (AULA 3) e 1.339.475 B (AULA 4).
    O da AULA 2 não é nem o menor nem o maior dos três: qualquer ordenação por
    tamanho (crescente ou decrescente) o tira da primeira posição. As duas
    'Dicas para a Prova.pdf' de T87/T88 têm o MESMO tamanho e não serviriam
    aqui — um sort por tamanho seria um no-op estável entre elas.
    """
    monkeypatch.setattr(arq, "TETO_PLURAL_ARQUIVOS", 1)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "roteiro", todos=True, raiz=tmp_path)

    # AULA 2 (fileid 9752459) vem antes de AULA 3 e AULA 4 na listagem.
    assert r.baixados[0].fileid == "9752459"


# --- achados da revisão final: um arquivo ruim não derruba o lote ----------

# A colisão de T87/T88: mesmo nome, dois fileids, seções "Geral" e "AULA 6".
_URL_DICAS_GERAL = (
    "https://edisciplinas.usp.br/webservice/pluginfile.php/9599793/"
    "mod_resource/content/2/Dicas%20para%20a%20Prova.pdf?forcedownload=1"
)


@pytest.mark.contrato
def test_T103_plural_uma_falha_nao_derruba_o_lote(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Invariante 6 (erro legível vence silêncio) e 7 (nada de corte calado):
    se o SEGUNDO arquivo de um lote falhar, o primeiro (já baixado) continua
    reportado, e o que falhou é NOMEADO com o motivo — o lote inteiro não pode
    virar uma exceção que apaga o que já deu certo."""

    def falha(*_a, **_k):
        raise MoodleIndisponivel("e-Disciplinas fora do ar")

    cliente = _cliente(
        conteudo_bruto, disciplinas_brutas, arquivos={_URL_DICAS_GERAL: falha}
    )

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) == 1
    assert r.baixados[0].fileid == "9599833"  # o da seção AULA 6, que não falhou
    assert len(r.recusados) == 1
    assert r.recusados[0].nome == "Dicas para a Prova.pdf"
    # O motivo é uma mensagem SANITIZADA por tipo de exceção, não `str(exc)`
    # cru — ver `arquivo._motivo_seguro` e o teste T103b logo abaixo, que
    # prova isso contra a mensagem REAL do cliente, não uma inventada aqui.
    assert "não respondeu" in r.recusados[0].motivo
    assert r.recusados[0].nome in r.texto


# --- achados da re-revisão: o motivo do Recusado não pode vazar endereço ---

_TAMANHO_DICAS = 455725  # filesize real dos dois itens da colisão (T87/T88)


def _download_falso_do_tamanho_certo(*, url, dados, teto_bytes):
    """Transporte de download OFFLINE para um `ClienteMoodle` de verdade.

    Só é chamado para o item LEGÍTIMO (AULA 6): o item malicioso (Geral) é
    barrado por `cliente.baixar` — a allowlist real de T91 — ANTES de
    qualquer I/O, então esta função nunca vê a URL estranha. O tamanho é
    fixo porque as duas 'Dicas para a Prova.pdf' têm o MESMO filesize.
    """
    prefixo = b"%PDF-1.4 "
    return "application/pdf", prefixo + b"x" * (_TAMANHO_DICAS - len(prefixo))


def _cliente_moodle_real(conteudo_bruto, disciplinas_brutas):
    """Um `ClienteMoodle` de verdade — não o `ClienteFalso` dos outros
    testes — para que a allowlist REAL de `cliente.baixar` (T91/T91b) seja o
    que dispara `FuncaoBloqueada`, e não uma mensagem escrita à mão pelo
    teste. É a diferença entre provar o comportamento do sistema e provar
    que o teste sabe escrever strings."""

    def transporte(*, url, dados):
        funcao = dados["wsfunction"]
        if funcao == "core_webservice_get_site_info":
            return {"userid": 1}
        if funcao == "core_enrol_get_users_courses":
            return disciplinas_brutas
        if funcao == "core_course_get_contents":
            return conteudo_bruto
        raise AssertionError(f"chamada não prevista neste teste: {funcao}")

    return ClienteMoodle(
        token="TOKEN-SINTETICO-NAO-E-CREDENCIAL",
        url="https://edisciplinas.usp.br",
        transporte=transporte,
        transporte_download=_download_falso_do_tamanho_certo,
    )


def _com_dicas_geral_apontando_para_host_estranho(conteudo_bruto):
    """Deep copy do conteúdo de PSI3323 com o `fileurl` do item 'Geral' da
    colisão real trocado por um host de fora — mas ainda com
    'pluginfile.php/' no caminho, para que `_fileid` (material.py) o trate
    como arquivo interno (tem fileid) em vez de link externo. É exatamente
    o cenário do achado de segurança do finding 1: a URL PARECE interna, e
    é a allowlist real de `cliente.baixar` que de fato barra."""
    bruto = copy.deepcopy(conteudo_bruto)
    for secao in bruto:
        if secao.get("name") != "Geral":
            continue
        for modulo in secao.get("modules") or ():
            for conteudo in modulo.get("contents") or ():
                if conteudo.get("filename") == "Dicas para a Prova.pdf":
                    conteudo["fileurl"] = (
                        "https://evil.example.com/webservice/pluginfile.php/"
                        "9599793/mod_resource/content/2/"
                        "Dicas%20para%20a%20Prova.pdf?forcedownload=1"
                    )
    return bruto


@pytest.mark.politica
def test_T103b_plural_recusa_de_seguranca_e_nomeada_no_lote(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """O segundo achado do finding 1: um item cujo endereço tem
    'pluginfile.php/' mas aponta para host ESTRANHO ainda parece interno (tem
    fileid) — `cliente.baixar` recusa com `FuncaoBloqueada`, e essa recusa É
    UM EVENTO DE SEGURANÇA que precisa chegar ao chamador legível, não como um
    crash que engole o resto do lote.

    Achado da RE-revisão: a mensagem real de `FuncaoBloqueada` embute a
    `fileurl` recusada — ecoá-la (`motivo=str(exc)`) vazaria endereço de
    webservice para o texto, violando T99c/T68b mesmo sem vazar credencial.
    Por isso este teste usa um `ClienteMoodle` DE VERDADE (não um dublê que
    inventa a mensagem): é a allowlist real quem levanta `FuncaoBloqueada`
    com o texto real, e é esse texto real que `arquivo.py` tem de sanitizar.
    """
    bruto = _com_dicas_geral_apontando_para_host_estranho(conteudo_bruto)
    cliente = _cliente_moodle_real(bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) == 1
    assert r.baixados[0].fileid == "9599833"  # o item legítimo (AULA 6)
    assert len(r.recusados) == 1
    assert r.recusados[0].nome == "Dicas para a Prova.pdf"
    assert "recusado" in r.recusados[0].motivo.lower()
    assert r.recusados[0].nome in r.texto
    # A prova do achado da re-revisão: nada do endereço recusado (nem o
    # host malicioso, nem o prefixo esperado do e-Disciplinas) chega ao
    # texto que vai para o modelo.
    assert "evil.example.com" not in r.texto
    assert "pluginfile.php" not in r.texto
    assert "/webservice/" not in r.texto


@pytest.mark.contrato
def test_T103c_singular_erro_de_download_sobe_como_excecao(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    """No singular há EXATAMENTE um arquivo pedido: engolir a falha dele numa
    linha de 'recusado' leria como resultado parcial que não existiu. A
    exceção sobe crua, porque aqui ela é mais legível que um texto suave
    (Invariante 6) — decisão deliberada, distinta do modo plural acima."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    def falha(*_a, **_k):
        raise MoodleIndisponivel("e-Disciplinas fora do ar")

    monkeypatch.setattr(cliente, "baixar", falha)

    with pytest.raises(MoodleIndisponivel):
        arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)


# --- achados da revisão final: cache truncado não é servido como bom -------


@pytest.mark.contrato
def test_T104_arquivo_truncado_em_disco_e_rebaixado(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """§6.3 do design: 'arquivo truncado entregue como bom é o pior resultado
    possível'. Um processo morto no meio da gravação não pode virar cache
    válido só porque o arquivo existe e não está vazio."""
    cliente1 = _cliente(conteudo_bruto, disciplinas_brutas)
    r1 = arq.baixar_arquivo(cliente1, "PSI3323", "Grupos", raiz=tmp_path)
    caminho = r1.baixados[0].caminho
    tamanho_certo = caminho.stat().st_size
    assert len(cliente1.downloads) == 1

    # Simula o corte: trunca o arquivo já gravado pela metade.
    caminho.write_bytes(caminho.read_bytes()[: tamanho_certo // 2])
    assert caminho.stat().st_size != tamanho_certo

    cliente2 = _cliente(conteudo_bruto, disciplinas_brutas)
    r2 = arq.baixar_arquivo(cliente2, "PSI3323", "Grupos", raiz=tmp_path)

    # A prova de que rebaixou é o TRANSPORTE ter sido chamado — a saída
    # devolveria bytes de qualquer jeito (dublê).
    assert len(cliente2.downloads) == 1, "arquivo truncado foi servido do cache"
    assert r2.baixados[0].reusado is False
    assert caminho.stat().st_size == tamanho_certo


# --- achados da revisão final: sucesso também precisa distinguir a colisão -


@pytest.mark.contrato
def test_T105_todos_sobre_a_colisao_produz_texto_distinguivel(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """As duas 'Dicas para a Prova.pdf' de T87/T88 só se distinguem por seção
    e módulo — e isso precisa estar no texto de SUCESSO também, não só na
    recusa por ambiguidade (T87), senão `todos=true` devolve duas linhas
    idênticas na parte que o texto mostra."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) == 2
    assert "seção 'Geral'" in r.texto
    assert "seção 'AULA 6'" in r.texto


@pytest.mark.contrato
def test_T105b_recusa_por_mesmo_nome_nao_promete_desambiguar_por_nome(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Quando os candidatos têm o MESMO nome de arquivo (a colisão real de
    T87), 'repita com um trecho mais específico' promete o que a pessoa não
    consegue fazer: o casamento é por nome de arquivo, e o nome é idêntico
    nos dois. A saída honesta é sugerir `todos=true`."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", raiz=tmp_path)

    # A promessa antiga não aparece mais: "repita com um trecho mais
    # específico" some da recusa quando isso não ajudaria em nada.
    assert "Repita com um trecho mais específico" not in r.texto
    assert "mesmo nome" in r.texto
    assert "todos=true" in r.texto


# --- T108, T109: casar pelo rótulo do professor, com prioridade ------------

@pytest.mark.contrato
def test_T108_casa_pelo_nome_do_modulo_quando_o_do_arquivo_nao_casa(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """"pedido de prova substitutiva" só existe no nome do MÓDULO; o arquivo se
    chama `Formulário Provas Substitutivas.pdf`. Sem isto, perguntar pelo tema
    não acha nada (verificado ao vivo em 03/09 com PTC3314)."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(
        cliente, "PSI3323", "pedido de prova substitutiva", raiz=tmp_path
    )

    assert len(r.baixados) == 1
    assert r.baixados[0].nome == "Formulário Provas Substitutivas.pdf"


@pytest.mark.contrato
def test_T109_o_nome_do_arquivo_tem_prioridade_e_o_modulo_nao_amplia(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """O módulo só é consultado quando o nome do arquivo não achou NADA.

    Sem essa prioridade, um termo que já resolvia viraria ambíguo: "dicas" casa
    com dois arquivos por nome, e olhar o módulo junto não pode transformar isso
    em três nem mudar quem casou.
    """
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", raiz=tmp_path)

    assert len(r.candidatos) == 2, "o módulo ampliou um casamento que já resolvia"


@pytest.mark.contrato
def test_T109b_termo_que_nao_casa_em_lugar_nenhum_segue_nao_casando(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """A ampliação não pode virar casar-com-tudo: o vazio continua vazio."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "zzz-nao-existe", raiz=tmp_path)

    assert r.baixados == () and r.candidatos == ()
    assert cliente.downloads == []


@pytest.mark.contrato
def test_T110_segunda_tentativa_casa_palavra_a_palavra_e_nao_trecho_contiguo(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Busca por TEMA não é substring: as palavras vêm separadas por outras.

    `Tutorial_Básico_Multisim_11.pdf` tem "Básico" entre as duas palavras, então
    "tutorial multisim" não é trecho contíguo de nada — nem do nome do arquivo,
    nem do módulo "Tutorial básico para aprender a usar o Multisim". Verificado
    ao vivo em 03/09 com o caso que motivou isto: "resolução do capítulo 3" não
    achava `Lista 2.pdf` de PTC3314, cujo módulo é "Resolução Exercícios do
    Capítulo 3 da apostila do curso".
    """
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "tutorial multisim", todos=True, raiz=tmp_path)

    # Os três destinos: um dos dois achados é `url` externo e vai para `links`,
    # não para `baixados` — olhar só um subconjunto esconderia metade do
    # resultado, que é o Invariante 7 aplicado ao próprio teste.
    achados = list(r.baixados) + list(r.candidatos) + list(r.links)
    nomes = {a.nome for a in achados}

    # TODAS as palavras têm de casar, não qualquer uma — e o que separa os dois
    # é a CONTAGEM, não o conteúdo: com `any`, os quatro itens extras também
    # contêm "Multisim" (medido em 03/09), então uma asserção sobre o texto de
    # cada achado passaria em ambos os casos. Foi assim que o T98c original
    # nasceu incapaz de detectar a própria sabotagem.
    assert nomes == {
        "Tutorial_Básico_Multisim_11.pdf",
        "Video Tutorial do Multisim 12",
    }, f"casou por uma palavra só, ou deixou de casar: {sorted(nomes)}"


@pytest.mark.contrato
def test_T110b_a_segunda_tentativa_nao_atropela_a_primeira(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Termo que já resolvia por nome continua resolvendo igual — a busca ampla
    só existe quando a estreita devolve vazio."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert len(r.baixados) == 1
    assert r.baixados[0].nome == "Prova-PSI3323-2026-Grupos.pdf"
