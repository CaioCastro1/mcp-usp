"""Baixar UM arquivo do espaço da disciplina, e entregar o CAMINHO.

A ferramenta não lê o arquivo: quem lê é o agente que chamou. A decisão é do §9
de 01/09/2026 e veio com número — entregar os bytes pelo canal MCP custaria
~302.000 tokens no PDF médio da amostra (base64), contra ~50 do caminho; e
extrair o texto no servidor custaria ~2.679, mas **perderia as figuras**, que num
acervo de eletrônica (circuitos, formas de onda, esquemas) são o conteúdo. Os
slides medidos têm 280–440 B de texto por página: são quase só imagem.

Convenção de erro, seguindo `material`: sigla que não resolve **levanta**, porque
é pergunta malformada e resolver antes evita gastar chamada da conta. O resto —
nada casou, casou demais, é link, passou do teto — **devolve** resposta com texto
explicativo, porque são resultados legítimos e o Invariante 6 pede que cada um
diga a própria cura.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import deposito
from .cliente import TETO_ARQUIVO_BYTES as _TETO_CLIENTE
from .disciplinas import carregar, resolver
from .erros import ErroMoodle
from .material import projetar_material
from .texto import casa

# Rebatizado como nome DESTE módulo de propósito: o cliente guarda o teto do
# transporte, este é o teto da ferramenta. Mesmo valor, dois donos com razões
# diferentes — e é este nome que o `monkeypatch` do teste alcança.
TETO_ARQUIVO_BYTES = _TETO_CLIENTE


@dataclass(frozen=True)
class Baixado:
    nome: str
    tipo: str
    mimetype: str | None
    tamanho: int
    caminho: Path
    fileid: str
    secao: str
    modulo: str
    reusado: bool


@dataclass(frozen=True)
class Link:
    nome: str
    url: str


@dataclass(frozen=True)
class Recusado:
    nome: str
    motivo: str


@dataclass(frozen=True)
class Candidato:
    nome: str
    tamanho: int | None
    secao: str
    modulo: str


@dataclass(frozen=True)
class RespostaArquivo:
    texto: str
    baixados: tuple[Baixado, ...] = ()
    links: tuple[Link, ...] = ()
    recusados: tuple[Recusado, ...] = ()
    candidatos: tuple[Candidato, ...] = ()


_AVISO_LEITURA = (
    "O arquivo está no disco DESTA máquina. Abra-o com a sua ferramenta de "
    "leitura de arquivos para ver o conteúdo — este servidor entrega o caminho, "
    "não o texto."
)


def _kb(n) -> str:
    return f"{n // 1024} kB" if n else "tamanho desconhecido"


def _baixar_um(cliente, item, courseid: int, raiz) -> Baixado:
    """Baixa se preciso, grava, devolve o registro. Reuso é a existência do arquivo."""
    caminho = deposito.caminho_para(
        courseid=courseid,
        fileid=item.fileid,
        timemodified=int(item.modificado.timestamp()) if item.modificado else 0,
        filename=item.nome,
        raiz=raiz,
    )
    reusado = deposito.ja_baixado(caminho)
    if not reusado:
        dados = cliente.baixar(item.fileurl_bruta, tamanho_esperado=item.tamanho)
        deposito.gravar(caminho, dados)

    return Baixado(
        nome=item.nome,
        tipo=item.tipo,
        mimetype=item.mimetype,
        tamanho=item.tamanho or caminho.stat().st_size,
        caminho=caminho,
        fileid=item.fileid,
        secao=item.secao,
        modulo=item.modulo,
        reusado=reusado,
    )


def baixar_arquivo(
    cliente,
    disciplina: str,
    nome: str,
    todos: bool = False,
    agora=None,
    raiz=None,
) -> RespostaArquivo:
    """Uma disciplina, um trecho de nome, um arquivo (ou vários com `todos`)."""
    lista = carregar(cliente, agora=agora)
    resolucao = resolver(lista, disciplina)
    if resolucao.disciplina is None:
        raise ErroMoodle(resolucao.motivo)

    alvo = resolucao.disciplina
    conteudo = projetar_material(
        cliente.chamar("core_course_get_contents", courseid=alvo.courseid)
    )
    itens = [i for s in conteudo.secoes for i in s.itens]
    casados = [i for i in itens if casa(nome, i.nome)]
    cabecalho = f"{alvo.sigla} ({alvo.rotulo})"

    if not casados:
        return RespostaArquivo(
            texto=(
                f"{cabecalho} — nenhum arquivo com {nome!r} no nome. "
                f"A disciplina tem {conteudo.total_itens} itens no total; use a "
                "ferramenta `material` para ver a lista e repita com um nome de lá."
            )
        )

    if len(casados) > 1 and not todos:
        candidatos = tuple(
            Candidato(nome=i.nome, tamanho=i.tamanho, secao=i.secao, modulo=i.modulo)
            for i in casados
        )
        linhas = [
            f"{cabecalho} — {nome!r} casa com {len(casados)} arquivos. "
            "Nenhum foi baixado."
        ]
        linhas += [
            f"  - {c.nome} [{_kb(c.tamanho)}] — seção {c.secao!r}, módulo {c.modulo!r}"
            for c in candidatos
        ]
        linhas.append(
            "Repita com um trecho mais específico, ou com todos=true para baixar "
            f"os {len(casados)}."
        )
        return RespostaArquivo(texto="\n".join(linhas), candidatos=candidatos)

    return _entregar(cliente, cabecalho, casados, alvo.courseid, raiz, todos)


def _entregar(cliente, cabecalho, casados, courseid, raiz, todos) -> RespostaArquivo:
    """Separa link de arquivo, baixa o que dá, e monta o texto. `todos` entra
    aqui para a tarefa 5 acrescentar os tetos sem mexer no roteamento acima."""
    baixados: list[Baixado] = []
    links: list[Link] = []
    recusados: list[Recusado] = []

    for item in casados:
        if not item.fileurl_bruta or not item.fileid:
            # Link externo (YouTube, Google Docs): a URL já é pública e sai
            # inteira. Baixá-lo mandaria o token para outro host — e a allowlist
            # do cliente recusaria, com razão.
            links.append(Link(nome=item.nome, url=item.url_externa or ""))
            continue
        if item.tamanho and item.tamanho > TETO_ARQUIVO_BYTES:
            recusados.append(
                Recusado(
                    nome=item.nome,
                    motivo=(
                        f"{_kb(item.tamanho)} passa do teto de "
                        f"{TETO_ARQUIVO_BYTES // (1024 * 1024)} MB por arquivo"
                    ),
                )
            )
            continue
        baixados.append(_baixar_um(cliente, item, courseid, raiz))

    linhas = [f"{cabecalho} — {len(baixados)} arquivo(s) baixado(s)."]
    for b in baixados:
        marca = " (já estava em disco)" if b.reusado else ""
        linhas.append(f"\n{b.nome} [{b.tipo}, {_kb(b.tamanho)}]{marca}")
        linhas.append(f"  {b.caminho}")
    for l in links:
        linhas.append(f"\n{l.nome} — é um link externo, não um arquivo do e-Disciplinas:")
        linhas.append(f"  {l.url}")
    # Invariante 7: o que não veio é NOMEADO, nunca omitido.
    for r in recusados:
        linhas.append(f"\n{r.nome} — não baixado: {r.motivo}")
    if baixados:
        linhas.append(f"\n⚠ {_AVISO_LEITURA}")

    return RespostaArquivo(
        texto="\n".join(linhas),
        baixados=tuple(baixados),
        links=tuple(links),
        recusados=tuple(recusados),
    )
