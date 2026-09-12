"""Os arquivos do espaço da disciplina — a pergunta, nas palavras do dono.

Não é "onde está o PDF da aula de hoje", que é como o §5 registrava a candidata.
É **descobrir o acervo**: regras da disciplina, listas de exercícios, provas
anteriores. Por isso a ferramenta lista tudo por padrão e a busca é por nome de
arquivo, não por data.

**Medido em PSI3323, e só nela** (§9, 31/08 — decisão do dono de aprofundar numa
amostra): 58.049 B crus por disciplina, ~6.486 B projetados (11,2%). 16 seções,
32 módulos, 29 itens com conteúdo — 19 PDF, 7 link externo, 1 docx, 1 jpeg, 1
octet-stream. A razão de 11,2% **não é fato do sistema**: uma disciplina com
resumo de seção longo pode ter razão bem pior, e isso só se sabe capturando
outras.

**A regra de segurança desta fronteira, e ela veio de medição.** Os 22 módulos
`resource` apontam para `edisciplinas.usp.br/webservice/pluginfile.php`, e baixar
de lá exige o token no request. Emitir uma URL com o token dentro põe a credencial
a um passo do contexto do modelo e de todo log por onde a resposta passar
(Invariante 3); emitir a URL sem o token entrega um endereço que não abre. Nos dois
casos a saída fica pior, então o endereço não sai. **Medido em 01/09: o token não
precisa ir na URL — o corpo do POST autentica igual** (§9), então quem baixa é o
servidor, sem que uma URL com segredo dentro chegue a existir. Os 7
módulos `url` apontam para fora (YouTube, Google Docs, sites de fabricante) e não
têm esse problema: esses saem inteiros, porque recusar tudo seria esconder o que
se sabe. O que identifica um arquivo interno — nome, tipo, tamanho, data — sai;
o endereço dele, não.

**O acervo não cabe numa chamada só, e isso é medição de 12/09/2026** (§9). Os
módulos `assign` chegam em `core_course_get_contents` com `contents` VAZIO: em
PTC3314 são 4, e dentro deles moram os enunciados dos exercícios computacionais —
`EP1-2026.pdf`, 218 kB. O `description` do módulo não ajuda (529 B de datas, zero
`href`). Quem tem o arquivo é `mod_assign_get_assignments`, e é por isso que
`acervo` faz DUAS chamadas — a segunda só quando a primeira encontra entrega, o
que mantém o Invariante 5 de pé para as disciplinas que não têm nenhuma.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .disciplinas import carregar, resolver
from .erros import ErroMoodle
from .texto import casa, normalizar

# Host + caminho que caracterizam arquivo servido pelo webservice do Moodle, e
# que por isso exigiria o token para ser baixado.
_MARCAS_INTERNAS = ("/webservice/", "pluginfile.php")

# Quantas entregas sem anexo o rodapé nomeia antes de virar contagem. Três é o
# que cabe numa linha e ainda deixa reconhecer o padrão do nome; o resto vira
# "e mais N", nunca silêncio.
_TETO_NOMES_NO_RODAPE = 3

_TIPOS = {
    "application/pdf": "PDF",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "documento",
    "application/msword": "documento",
    # O acervo de PTC3314 publica o mesmo enunciado em PDF e em ODT (12/09).
    # Sem esta linha o ODT saía como "arquivo", escondendo que é a mesma coisa
    # em outro formato — e nenhum `resource` da amostra de PSI3323 era ODT, que
    # é por que isto só apareceu quando as entregas entraram na lista.
    "application/vnd.oasis.opendocument.text": "documento",
    "application/vnd.oasis.opendocument.spreadsheet": "planilha",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "planilha",
    "image/jpeg": "imagem",
    "image/png": "imagem",
}


@dataclass(frozen=True)
class Item:
    nome: str
    tipo: str
    tamanho: int | None
    modificado: datetime | None
    url_externa: str | None
    # Campos para consumo INTERNO de `arquivo.py`, nunca impressos: T68b e T68c
    # são os guardas disso. `fileurl_bruta` é a `fileurl` como o Moodle a
    # devolveu — para um `resource` ela é a URL do webservice, para um `url` é o
    # endereço externo. O nome diz "bruta" e não "interna" porque as duas coisas
    # passam por aqui, e é `fileid` (ausente no link externo) que as separa.
    fileurl_bruta: str | None = None
    fileid: str | None = None
    mimetype: str | None = None
    secao: str = ""
    modulo: str = ""


@dataclass(frozen=True)
class Secao:
    nome: str
    itens: tuple[Item, ...]


@dataclass(frozen=True)
class Entrega:
    """Um módulo `assign` do espaço, como `get_contents` o descreve.

    Existe porque `get_contents` descreve a entrega mas **não** os arquivos dela:
    medido em 12/09/2026, os 4 `assign` de PTC3314 chegam com `contents` vazio e
    `description` sem link nenhum. O que sobra de útil é o `cmid` — é por ele que
    o anexo devolvido por `mod_assign_get_assignments` acha a seção onde aparecer.
    """

    cmid: int
    nome: str
    secao: str


@dataclass(frozen=True)
class AnexosDeEntrega:
    itens: tuple[Item, ...]
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Conteudo:
    secoes: tuple[Secao, ...]
    total_itens: int
    sem_conteudo: tuple[str, ...]
    entregas: tuple[Entrega, ...] = ()
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class RespostaMaterial:
    texto: str
    total: int
    mostrados: int
    vazio_por: str | None = None


def _tipo_de(modname: str, mimetype: str | None) -> str:
    if modname == "url":
        return "link"
    return _TIPOS.get(mimetype or "", "arquivo")


def _url_publica(bruto: str | None) -> str | None:
    """Devolve a URL só quando ela não depende de credencial para funcionar.

    Um endereço que só serve com o token colado atrás é um convite a colar o
    token. Ver a docstring do módulo.
    """
    if not bruto or not bruto.startswith("http"):
        return None
    if any(marca in bruto for marca in _MARCAS_INTERNAS):
        return None
    return bruto


def _fileid(bruto: str | None) -> str | None:
    """O primeiro segmento depois de `pluginfile.php/` — o id do arquivo.

    Não é segredo (a URL inteira é que exige credencial para servir de algo), e
    é o que distingue dois arquivos de mesmo nome: em PSI3323, `Dicas para a
    Prova.pdf` existe duas vezes, com ids 9599793 e 9599833.
    """
    if not bruto or "pluginfile.php/" not in bruto:
        return None
    return bruto.split("pluginfile.php/", 1)[1].split("/", 1)[0] or None


def projetar_material(bruto) -> Conteudo:
    """Seções → módulos → conteúdos vira uma lista curta com o que identifica.

    `author` e `userid` ficam de fora de propósito: vêm dentro de `contents`,
    são dado pessoal (§3.3) e não respondem "que arquivos tem aqui".
    """
    secoes: list[Secao] = []
    total = 0
    sem_conteudo: set[str] = set()

    entregas: list[Entrega] = []

    for secao in bruto or ():
        itens: list[Item] = []
        for modulo in secao.get("modules") or ():
            if modulo.get("modname") == "assign":
                # Registrada mesmo sem `contents`, e é o registro que decide se
                # a segunda chamada vale a pena: sem `assign` nenhum, perguntar
                # por anexo de entrega só pode devolver vazio (Invariante 5).
                entregas.append(
                    Entrega(
                        cmid=modulo.get("id"),
                        nome=modulo.get("name") or "",
                        secao=secao.get("name") or "",
                    )
                )
            conteudos = modulo.get("contents") or ()
            if not conteudos:
                # Invariante 7: fórum e entrega não têm `contents`. Sumir com
                # eles faria a lista parecer o espaço inteiro quando não é.
                sem_conteudo.add(modulo.get("modname") or "?")
                continue
            for conteudo in conteudos:
                itens.append(
                    _item_de(
                        conteudo,
                        modname=modulo.get("modname") or "",
                        secao=secao.get("name") or "",
                        modulo=modulo.get("name") or "",
                    )
                )
                total += 1
        secoes.append(Secao(nome=secao.get("name") or "", itens=tuple(itens)))

    return Conteudo(
        secoes=tuple(secoes),
        total_itens=total,
        sem_conteudo=tuple(sorted(sem_conteudo)),
        entregas=tuple(entregas),
    )


def _item_de(conteudo: dict, *, modname: str, secao: str, modulo: str) -> Item:
    """Um `contents` do Moodle vira `Item`. UMA função, e é o que permite os anexos.

    O anexo de entrega chega de outra função do web service
    (`mod_assign_get_assignments`) com **os mesmos nomes de campo** — `filename`,
    `filesize`, `mimetype`, `timemodified`, `fileurl` — medido em 12/09/2026. Com
    a construção num lugar só, o anexo entra no acervo sem caso especial, e
    `baixar_arquivo` o acha sem saber que ele veio de outro endpoint.
    """
    return Item(
        nome=conteudo.get("filename") or modulo or "",
        tipo=_tipo_de(modname, conteudo.get("mimetype")),
        tamanho=conteudo.get("filesize") or None,
        modificado=_data(conteudo.get("timemodified")),
        url_externa=_url_publica(conteudo.get("fileurl")),
        fileurl_bruta=conteudo.get("fileurl"),
        fileid=_fileid(conteudo.get("fileurl")),
        mimetype=conteudo.get("mimetype"),
        secao=secao,
        modulo=modulo,
    )


def projetar_anexos_de_entrega(bruto, entregas) -> AnexosDeEntrega:
    """Os `introattachments` de cada entrega viram itens do acervo.

    O rótulo de cada anexo é o nome da ENTREGA, não o do arquivo: `EP1-2026.pdf`
    não diz nada, `EC-1 - Transitórios em LT` diz tudo — e é esse campo que
    `rotulo_do_modulo` imprime junto do arquivo.

    `warnings` vira aviso em vez de sumir (Invariante 7). Na captura de 12/09 são
    dois módulos com `No access rights in module context`: uma lista sem eles
    pareceria completa sem ser.
    """
    por_cmid = {e.cmid: e for e in entregas}
    itens: list[Item] = []

    for curso in (bruto or {}).get("courses") or ():
        for entrega in curso.get("assignments") or ():
            local = por_cmid.get(entrega.get("cmid"))
            nome_modulo = local.nome if local else (entrega.get("name") or "")
            secao = local.secao if local else ""
            for anexo in entrega.get("introattachments") or ():
                itens.append(
                    _item_de(anexo, modname="assign", secao=secao, modulo=nome_modulo)
                )

    avisos: list[str] = []
    if quantos := len((bruto or {}).get("warnings") or ()):
        avisos.append(
            f"{quantos} atividade(s) desta disciplina não puderam ser lidas com "
            "esta credencial — se houver arquivo nelas, ele não está acima."
        )

    return AnexosDeEntrega(itens=tuple(itens), avisos=tuple(avisos))


def _com_anexos(conteudo: Conteudo, anexos: AnexosDeEntrega) -> Conteudo:
    """Devolve o conteúdo com os anexos dentro da seção de cada entrega.

    Anexo cuja seção não existe na projeção (não deve acontecer: o `cmid` vem da
    mesma captura) entra numa seção própria em vez de sumir — Invariante 7 vale
    também para o caso que "não acontece".
    """
    if not anexos.itens:
        return conteudo

    por_secao: dict[str, list[Item]] = {}
    for item in anexos.itens:
        por_secao.setdefault(item.secao, []).append(item)

    secoes = [
        Secao(nome=s.nome, itens=s.itens + tuple(por_secao.pop(s.nome, ())))
        for s in conteudo.secoes
    ]
    secoes += [Secao(nome=nome, itens=tuple(itens)) for nome, itens in por_secao.items()]

    # `assign` sai de `sem_conteudo` porque deixou de ser verdade que a entrega
    # está fora da lista: ela aparece, pelos arquivos anexados a ela. As que não
    # têm anexo ganham aviso próprio em `material`, com a contagem.
    return Conteudo(
        secoes=tuple(secoes),
        total_itens=conteudo.total_itens + len(anexos.itens),
        sem_conteudo=tuple(n for n in conteudo.sem_conteudo if n != "assign"),
        entregas=conteudo.entregas,
        avisos=conteudo.avisos + anexos.avisos,
    )


def acervo(cliente, courseid: int) -> Conteudo:
    """Tudo que é arquivo no espaço da disciplina — de UMA ou de DUAS chamadas.

    A segunda só sai se a primeira disser que existe `assign`. É a diferença
    entre custo sob demanda e martelar a USP por uma resposta que já se sabe
    vazia (Invariante 5), e ela é medível: PTC3314 paga +8.651 B sobre os
    106.121 B de `get_contents` (8%); uma disciplina sem entrega paga zero.

    O escopo `courseids[0]` não é otimização: **sem ele** a função devolve as 74
    matrículas, 1 MB, ~251k tokens (§9, 28/08).

    Ponto único das duas ferramentas de propósito: `material` e `baixar_arquivo`
    faziam o mesmo par de linhas em duplicata, e a segunda ficaria cega para os
    anexos se só a primeira aprendesse a pedi-los.
    """
    conteudo = projetar_material(
        cliente.chamar("core_course_get_contents", courseid=courseid)
    )
    if not conteudo.entregas:
        return conteudo

    anexos = projetar_anexos_de_entrega(
        cliente.chamar("mod_assign_get_assignments", **{"courseids[0]": courseid}),
        conteudo.entregas,
    )
    return _com_anexos(conteudo, anexos)


def _data(carimbo) -> datetime | None:
    from .projecao import FUSO_SAO_PAULO

    if not carimbo:
        return None
    return datetime.fromtimestamp(int(carimbo), FUSO_SAO_PAULO)


def como_dict(conteudo: Conteudo) -> list[dict]:
    """Forma serializável — usada pela medição de custo da suíte."""
    return [
        {
            "secao": s.nome,
            "itens": [
                {
                    "nome": i.nome,
                    "tipo": i.tipo,
                    "tamanho": i.tamanho,
                    "modificado": i.modificado.isoformat() if i.modificado else None,
                    "modulo": rotulo_do_modulo(i),
                    "url": i.url_externa,
                }
                for i in s.itens
            ],
        }
        for s in conteudo.secoes
    ]


def rotulo_do_modulo(item: Item) -> str | None:
    """O nome que o professor deu ao módulo, quando ele acrescenta informação.

    **É a única descrição semântica que o e-Disciplinas oferece**, e ela era
    descartada: `Formulário Provas Substitutivas.pdf` mora no módulo "Formulário
    para pedido de prova substitutiva", e quem procurasse pelo tema não tinha
    como achar. Medido em 03/09: os nomes de módulo de PSI3323 custam ~328
    tokens, 20% da projeção — contra ~3.569 dos `summary` de seção, que é o
    campo caro e o que menos promete.

    Devolve `None` quando o módulo repete o nome do arquivo, o que acontece em
    **9 dos 29 itens**: imprimir os dois seria pagar token para dizer a mesma
    coisa duas vezes. A comparação é normalizada, então "Como criar uma rede
    privada virtual…" casa com o arquivo de mesmo nome apesar da pontuação.
    """
    if not item.modulo:
        return None
    mod, arq = normalizar(item.modulo), normalizar(item.nome)
    if not mod or mod in arq or arq in mod:
        return None
    return item.modulo


def _formatar_item(item: Item) -> str:
    partes = [f"  - {item.nome} [{item.tipo}"]
    if item.tamanho:
        partes.append(f", {item.tamanho // 1024} kB")
    if item.modificado:
        partes.append(f", {item.modificado.strftime('%d/%m/%Y')}")
    partes.append("]")
    linha = "".join(partes)
    if (rotulo := rotulo_do_modulo(item)) is not None:
        linha += f"\n    ({rotulo})"
    if item.url_externa:
        linha += f"\n    {item.url_externa}"
    return linha


def _entregas_sem_anexo(conteudo: Conteudo) -> tuple[str, ...]:
    """As entregas que nenhum item do acervo cita como módulo de origem.

    Em PTC3314 são 2 de 4: as duas provas presenciais, que o professor criou
    como `assign` só para ter data. Nomeá-las é mais honesto do que o rodapé
    antigo, que declarava `assign` inteiro fora da lista mesmo quando metade
    dele estava dentro.
    """
    com_arquivo = {i.modulo for s in conteudo.secoes for i in s.itens}
    return tuple(e.nome for e in conteudo.entregas if e.nome not in com_arquivo)


def material(cliente, disciplina: str, busca: str | None = None, agora=None) -> RespostaMaterial:
    """Uma pergunta, uma disciplina. Resolve a sigla antes de gastar chamada.

    Sigla que não resolve levanta erro legível **sem** pedir conteúdo: consultar
    o Moodle para descobrir que a pergunta estava errada é gastar chamada da
    conta do dono à toa.
    """
    lista = carregar(cliente, agora=agora)
    resolucao = resolver(lista, disciplina)
    if resolucao.disciplina is None:
        raise ErroMoodle(resolucao.motivo)

    alvo = resolucao.disciplina
    conteudo = acervo(cliente, alvo.courseid)

    total = conteudo.total_itens
    filtro = (busca or "").strip()

    secoes = []
    mostrados = 0
    for secao in conteudo.secoes:
        itens = [i for i in secao.itens if casa(filtro, i.nome)]
        mostrados += len(itens)
        if itens:
            secoes.append((secao.nome, itens))

    cabecalho = f"{alvo.sigla} ({alvo.rotulo}) — material do espaço da disciplina"

    if total == 0:
        # Invariante 7: espaço vazio é resultado legítimo e rotulado, para não
        # se confundir com falha de credencial nem com sigla errada. Seis das
        # dez disciplinas do semestre não têm entrega nenhuma — vazio acontece.
        return RespostaMaterial(
            texto=(
                f"{cabecalho}\n\nA disciplina existe e está acessível, mas não há "
                "nenhum arquivo publicado no espaço dela."
            ),
            total=0,
            mostrados=0,
            vazio_por="sem_material",
        )

    if filtro and mostrados == 0:
        # "Nada com esse nome" ≠ "disciplina vazia". Dizer o total é o que
        # permite a quem lê distinguir as duas.
        return RespostaMaterial(
            texto=(
                f"{cabecalho}\n\nNenhum arquivo com {busca!r} no nome. "
                f"A disciplina tem {total} itens no total — repita sem busca "
                "para ver a lista inteira."
            ),
            total=total,
            mostrados=0,
            vazio_por="busca_sem_resultado",
        )

    linhas = [cabecalho]
    if filtro:
        # Invariante 7: filtrar é esconder, e esconder tem de ser declarado.
        linhas.append(f"Filtrado por {busca!r}: {mostrados} de {total} itens.")
    else:
        linhas.append(f"{total} itens.")

    for nome, itens in secoes:
        linhas.append(f"\n{nome}:" if nome else "\n(sem seção):")
        linhas.extend(_formatar_item(i) for i in itens)

    avisos = [
        "O link do arquivo interno do e-Disciplinas não é entregue aqui: um "
        "endereço sem a credencial não abre, e um com ela poria a credencial "
        "no seu contexto — por isso ele não sai desta máquina (Invariante 3), "
        "mesmo sabendo que a requisição de download autentica pelo corpo do "
        "pedido, sem precisar colar a credencial no endereço. Para baixar de "
        "fato um destes arquivos, use a ferramenta `baixar_arquivo`.",
    ]
    if conteudo.sem_conteudo:
        avisos.append(
            "Não estão nesta lista: "
            + ", ".join(conteudo.sem_conteudo)
            + " — são atividades, não arquivos, e têm consulta própria."
        )
    if mudas := _entregas_sem_anexo(conteudo):
        # Invariante 7 aplicado ao que a segunda chamada NÃO achou: a entrega
        # sem arquivo anexado continua fora da lista, e dizer quais são é o que
        # separa "o professor não anexou nada" de "a ferramenta não olhou".
        #
        # Com teto, porque medir doeu: PSI3472 tem 10 das 11 entregas sem anexo
        # ("Lição aulas 1 e 2", "Lição aulas 3 e 4", …), e nomear as 10 produziu
        # um rodapé que enterrava os outros três avisos. O que o Invariante 7
        # exige é que o corte seja DITO — a contagem fica, os nomes é que são
        # amostra, e "e mais N" é o que impede a amostra de passar por lista.
        nomeadas = ", ".join(mudas[:_TETO_NOMES_NO_RODAPE])
        if sobra := len(mudas) - _TETO_NOMES_NO_RODAPE:
            nomeadas += f", e mais {sobra}"
        avisos.append(
            f"{len(mudas)} de {len(conteudo.entregas)} entregas não têm arquivo "
            f"anexado ao enunciado e por isso não aparecem acima: {nomeadas}. "
            "O texto do enunciado, o prazo e a sua nota não são material — "
            "use `o_que_vence` para o prazo."
        )
    if conteudo.avisos:
        avisos.extend(conteudo.avisos)

    linhas.extend(f"\n⚠ {a}" for a in avisos)

    return RespostaMaterial(
        texto="\n".join(linhas), total=total, mostrados=mostrados
    )
