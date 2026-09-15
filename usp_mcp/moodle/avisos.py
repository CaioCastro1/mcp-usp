"""O que o calendário não sabe: "o professor avisou alguma coisa?".

`o_que_vence` responde o que tem **prazo**; esta responde o que foi **dito**. A
distância entre as duas foi medida antes de a ferramenta existir: a
`notas/fase1-moodle.md` registra que o anúncio da "Prova Prática P1" de PSI3323
estava no fórum *Avisos* e a prova **não** estava no calendário da disciplina.
Prova presencial não vira evento de calendário, e é exatamente sobre ela que o
professor escreve no mural.

**A função certa, e a armadilha do comparável.** O `loyaniu/moodle-mcp` chama
`mod_forum_get_discussions`, que **não existe** no Moodle 5.0 da USP. A função é
`mod_forum_get_forum_discussions` — medido em 14/09/2026 e registrado no
ROADMAP. A19 é a asserção que impede o nome errado de entrar por cópia.

**Duas funções, e a primeira existe porque a segunda pede um id que ninguém
tem.** `mod_forum_get_forum_discussions` quer um `forumid`, que não é o
`courseid` nem o `cmid`; quem o dá é `mod_forum_get_forums_by_courses`. É a
mesma forma da tradução sigla → `courseid` que `disciplinas` já faz, um nível
abaixo.

**Três decisões de custo:**

1. **Fórum sem tópico não gasta chamada.** `numdiscussions` vem na resposta da
   primeira função e diz quantos tópicos o fórum tem; zero significa que a
   consulta voltaria vazia. É o `nosubmissions` de `ja_entreguei`, e a mesma
   regra vale: não consultar **não é sumir** — o fórum aparece com o motivo
   (A4). Ausência do campo é "não sei", nunca zero, e o erro cai para o lado de
   gastar a chamada (A4b).
2. **Teto de `TETO_FORUNS` fóruns por invocação**, pelo mesmo motivo do teto de
   `ja_entreguei`: latência e log da conta (Invariante 5).
3. **Teto de `TETO_TEXTO` caracteres por tópico.** Esta é a decisão incômoda, e
   é declarada no texto porque o corte aqui remove **resposta**, não transporte:
   o catálogo (§3.6) registra o fórum como a resposta que menos comprime do
   projeto inteiro, porque ali o payload *é* o conteúdo. Descartar o corpo
   inteiro devolveria "o professor avisou alguma coisa" sem dizer o quê, que não
   responde a pergunta; devolver inteiro faria um tópico longo comer a resposta.

**Fórum é o único lugar deste projeto onde o payload é escrito por terceiros.**
Cada discussão chega com `userfullname`, `usermodifiedfullname`, `userid` e duas
URLs de foto de perfil. **Nada disso sai** (§3.3, A6) — e a omissão é dita, não
silenciosa: quem lê precisa saber que a autoria ficou de fora, senão atribui ao
professor o que um colega escreveu. Saem também os anexos: deles não vai nem a
`fileurl` (Invariante 3, A18) nem o nome, porque `material` é a ferramenta que
responde "que arquivo tem aqui".

Descartados também, e sem aviso no texto porque não escondem resposta:
`intro` (a descrição do fórum, em HTML), `numreplies` (responde "tem conversa?",
que é outra pergunta), `pinned`, `istracked`, `unreadpostscount` e as dezenas de
chaves de configuração do fórum.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .disciplinas import carregar, resolver
from .erros import ErroMoodle
from .projecao import FUSO_SAO_PAULO
from .texto import formatar_data, sem_html

# Quantos fóruns uma invocação consulta. Uma ida por fórum, e o corte fica com
# os primeiros DEPOIS da ordenação — isto é, com o mural de avisos.
TETO_FORUNS = 4

# `perpage` explícito. O catálogo (§3.6) registra o default como `[opt=0]`, e o
# que o 0 faz não foi verificado — mesma decisão de `notas` com `userid [opt=0]`:
# depender de default não verificado é prometer o que não se sabe, e aqui o modo
# de falha é trazer o fórum inteiro de uma disciplina de cinco anos atrás.
DISCUSSOES_POR_FORUM = 5

# Caracteres do corpo de cada tópico. Ver decisão 3 da docstring: o corte é de
# RESPOSTA, não de transporte, e por isso ele é declarado no texto com a cura.
TETO_TEXTO = 600

# `type` do fórum, no vocabulário de quem pergunta. O mural (`news`) é o que
# responde "o professor avisou": nele só quem dá aula posta. Tipo desconhecido
# sai com o rótulo cru entre parênteses — a mesma regra de `o_que_vence`, porque
# um rótulo inventado é pior que um rótulo estranho.
_TIPOS_PT = {
    "news": "mural de avisos",
    "general": "fórum de discussão",
    "qanda": "fórum de pergunta e resposta",
    "eachuser": "fórum de um tópico por pessoa",
    "single": "fórum de tópico único",
    "blog": "fórum em formato de blog",
}

# O mural de avisos primeiro, sempre. A resposta do Moodle não promete ordem
# nenhuma, e deixar a ordem da API decidir faria o aviso do professor sair
# depois da dúvida de um colega assim que a disciplina tivesse muitos fóruns.
_PRIMEIRO = "news"


@dataclass(frozen=True)
class Topico:
    """Um tópico de fórum reduzido ao que responde "o que foi dito"."""

    assunto: str
    quando: datetime | None
    texto: str
    cortado: bool = False


@dataclass(frozen=True)
class Forum:
    """Um fórum como `get_forums_by_courses` o descreve, em cinco campos.

    `quantos` é `numdiscussions`, e `None` quer dizer **não sei** — o site não
    devolveu o campo. Não é zero: zero autoriza pular a consulta, "não sei" não.
    """

    forumid: int
    nome: str
    tipo: str
    quantos: int | None


@dataclass(frozen=True)
class RespostaAvisos:
    texto: str
    total_foruns: int
    consultados: int
    truncado: bool
    cortados: int = 0
    vazio_por: str | None = None


def _data(carimbo) -> datetime | None:
    """Mesma regra de `ja_entreguei._data` e `projecao._quando_de`: epoch 0 é
    "sem data", nunca 01/01/1970."""
    if isinstance(carimbo, bool) or not isinstance(carimbo, int) or carimbo <= 0:
        return None
    return datetime.fromtimestamp(carimbo, FUSO_SAO_PAULO)


def projetar_foruns(bruto) -> tuple[Forum, ...]:
    """A lista de fóruns, com o mural de avisos na frente.

    As ~35 chaves por fórum viram quatro. A gorda é `intro` — a descrição que o
    professor escreveu para o fórum, em HTML — e ela não responde "o que foi
    dito": é o texto fixo que está lá desde o começo do semestre.
    """
    foruns = [
        Forum(
            forumid=f.get("id"),
            nome=(f.get("name") or "").strip() or "(fórum sem nome)",
            tipo=f.get("type") or "",
            quantos=f.get("numdiscussions")
            if isinstance(f.get("numdiscussions"), int)
            and not isinstance(f.get("numdiscussions"), bool)
            else None,

        )
        for f in bruto or ()
        if f.get("id") is not None
    ]
    # Ordem estável e explícita: mural primeiro, depois por nome. `sorted` é
    # estável, então fóruns de mesmo tipo mantêm a ordem do nome.
    return tuple(sorted(foruns, key=lambda f: (f.tipo != _PRIMEIRO, f.nome)))


def projetar_topicos(bruto) -> tuple[tuple[Topico, ...], int]:
    """`get_forum_discussions` → (tópicos, quantos tiveram o texto cortado).

    **O que este corte existe para descartar** é, antes de tudo, gente:
    `userfullname` e `usermodifiedfullname` (nome de quem postou e de quem
    mexeu por último), `userid`, `usermodified` e duas `userpictureurl`. O §3.3
    trata nome de pessoa como dado pessoal, e aqui ele é de **terceiro** — não
    do dono do token. Depois vêm os anexos, de onde não sai nem endereço
    (Invariante 3) nem nome de arquivo (isso é resposta de `material`).

    O corpo do post, esse, fica: é a resposta. Vem em HTML e sai em texto.
    """
    topicos: list[Topico] = []
    cortados = 0

    for d in (bruto or {}).get("discussions") or ():
        corpo = sem_html(d.get("message") or "")
        cortado = len(corpo) > TETO_TEXTO
        if cortado:
            cortados += 1
            corpo = corpo[:TETO_TEXTO].rstrip() + "…"
        topicos.append(
            Topico(
                assunto=(d.get("subject") or d.get("name") or "").strip()
                or "(tópico sem assunto)",
                # `created` é quando foi dito; `timemodified` é quando foi
                # mexido. A pergunta é sobre o aviso, então a data mostrada é a
                # do aviso — e a ordenação usa a mais recente das duas, para um
                # tópico antigo reeditado hoje não ficar enterrado.
                quando=_data(d.get("created")),
                texto=corpo,
                cortado=cortado,
            )
        )

    ordenados = sorted(
        topicos,
        key=lambda t: t.quando or datetime.min.replace(tzinfo=FUSO_SAO_PAULO),
        reverse=True,
    )
    return tuple(ordenados), cortados


_SEM_AUTOR = (
    "Quem escreveu cada tópico não sai daqui: o fórum é o único lugar do "
    "e-Disciplinas em que a resposta traz nome de outras pessoas, e nome de "
    "terceiro não atravessa esta ferramenta. Quem precisa saber quem disse o "
    "quê abre o tópico na página da disciplina."
)

_COBERTURA = (
    "Isto é o que foi escrito no fórum. Aviso dado em sala e não postado não "
    "existe aqui, e o que tem PRAZO está em `o_que_vence` — o fórum não é a "
    "agenda da disciplina."
)


def _formatar_forum(forum: Forum, topicos, mostrados_de) -> list[str]:
    tipo = _TIPOS_PT.get(forum.tipo) or (
        f"fórum ({forum.tipo})" if forum.tipo else "fórum"
    )
    linhas = [f"{forum.nome} ({tipo})"]
    if not topicos:
        # Invariante 7: fórum sem nada aparece com o motivo, em vez de sumir da
        # lista e deixar quem lê achar que ele não existe.
        linhas.append("  nenhum tópico neste fórum")
        return linhas
    for t in topicos:
        quando = formatar_data(t.quando) if t.quando is not None else "sem data"
        linhas.append(f"  {quando}  {t.assunto}")
        if t.texto:
            # A indentação vale para a continuação também: um post de três
            # parágrafos com só a primeira linha recuada deixa de parecer parte
            # do tópico e passa a parecer um tópico novo sem data.
            linhas.append("      " + t.texto.replace("\n", "\n      "))
    if mostrados_de is not None:
        linhas.append(
            f"  (mostrando {len(topicos)} de {mostrados_de} tópicos deste "
            "fórum, os mais recentes)"
        )
    return linhas


def avisos(cliente, disciplina: str) -> RespostaAvisos:
    """Uma disciplina, uma ida para listar os fóruns, uma ida por fórum lido.

    Sigla que não resolve levanta erro legível **sem** pedir fórum nenhum (A2):
    mesma regra de `material` e `ja_entreguei` — consultar o Moodle para
    descobrir que a pergunta estava errada gasta chamada da conta do dono à toa.
    """
    lista = carregar(cliente)
    resolucao = resolver(lista, disciplina)
    if resolucao.disciplina is None:
        raise ErroMoodle(resolucao.motivo)

    alvo = resolucao.disciplina
    # `courseids` é `[opt=[]]` e o vazio significa TODOS os cursos: sem escopo
    # esta chamada varreria as 74 matrículas (A1).
    foruns = projetar_foruns(
        cliente.chamar(
            "mod_forum_get_forums_by_courses", **{"courseids[0]": alvo.courseid}
        )
    )
    cabecalho = f"{alvo.sigla} ({alvo.rotulo}) — avisos e tópicos de fórum"

    if not foruns:
        return RespostaAvisos(
            texto=(
                f"{cabecalho}\n\nEsta disciplina não tem nenhum fórum no "
                f"e-Disciplinas.\n\n⚠ {_COBERTURA}"
            ),
            total_foruns=0,
            consultados=0,
            truncado=False,
            vazio_por="sem_forum",
        )

    truncado = len(foruns) > TETO_FORUNS
    de_fora = len(foruns) - TETO_FORUNS if truncado else 0
    escolhidos = foruns[:TETO_FORUNS]

    blocos: list[list[str]] = []
    cortados = 0
    consultados = 0
    com_topico = 0
    avisos_da_api = 0

    for forum in escolhidos:
        if forum.quantos == 0:
            # Sem ida ao Moodle: a primeira chamada já disse que não há o que
            # ler. `quantos is None` (site que não devolveu o campo) NÃO cai
            # aqui de propósito — "não sei" manda consultar.
            blocos.append(_formatar_forum(forum, (), None))
            continue
        bruto = cliente.chamar(
            "mod_forum_get_forum_discussions",
            forumid=forum.forumid,
            page=0,
            perpage=DISCUSSOES_POR_FORUM,
        )
        # Erro do cliente sobe daqui sem ser capturado (A14): falha de
        # credencial não pode virar "o professor não avisou nada".
        consultados += 1
        topicos, cortados_aqui = projetar_topicos(bruto)
        cortados += cortados_aqui
        avisos_da_api += len((bruto or {}).get("warnings") or ())
        if topicos:
            com_topico += 1
        # A contagem só vira aviso quando ela sabe mais que a lista: os dois
        # números já estão em mãos, então declarar o resto custa zero chamada.
        faltam = (
            forum.quantos
            if forum.quantos is not None and forum.quantos > len(topicos)
            else None
        )
        truncado = truncado or faltam is not None
        blocos.append(_formatar_forum(forum, topicos, faltam))

    if not com_topico:
        # Fórum existe e está vazio ≠ não existe fórum. No primeiro caso vale
        # voltar amanhã, e é por isso que os dois têm rótulos diferentes.
        return RespostaAvisos(
            texto=(
                f"{cabecalho}\n\nOs {len(foruns)} fóruns desta disciplina não "
                f"têm nenhum tópico publicado.\n\n⚠ {_COBERTURA}"
            ),
            total_foruns=len(foruns),
            consultados=consultados,
            truncado=truncado,
            vazio_por="sem_topico",
        )

    partes = [cabecalho, ""]
    for i, bloco in enumerate(blocos):
        if i:
            partes.append("")
        partes.extend(bloco)

    lista_avisos: list[str] = []
    if de_fora:
        lista_avisos.append(
            f"Esta consulta custa uma ida ao e-Disciplinas por fórum, e para em "
            f"{TETO_FORUNS}: {de_fora} fórum(ns) desta disciplina ficaram de "
            "fora. O mural de avisos vem sempre primeiro, então o que ficou de "
            "fora é fórum de discussão."
        )
    if cortados:
        lista_avisos.append(
            f"{cortados} tópico(s) tiveram o texto cortado em {TETO_TEXTO} "
            "caracteres e terminam em reticências. O texto inteiro está no "
            "tópico, na página da disciplina no e-Disciplinas."
        )
    if avisos_da_api:
        lista_avisos.append(
            f"{avisos_da_api} tópico(s) não puderam ser lidos com esta "
            "credencial e não estão acima."
        )
    lista_avisos.append(_SEM_AUTOR)
    lista_avisos.append(_COBERTURA)

    partes.extend(f"\n⚠ {a}" for a in lista_avisos)

    return RespostaAvisos(
        texto="\n".join(partes),
        total_foruns=len(foruns),
        consultados=consultados,
        truncado=truncado,
        cortados=cortados,
    )
