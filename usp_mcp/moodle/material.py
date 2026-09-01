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
de lá exige anexar o token na URL. Emitir essa URL põe a credencial a um passo do
contexto do modelo e de todo log por onde a resposta passar (Invariante 3). Os 7
módulos `url` apontam para fora (YouTube, Google Docs, sites de fabricante) e não
têm esse problema: esses saem inteiros, porque recusar tudo seria esconder o que
se sabe. O que identifica um arquivo interno — nome, tipo, tamanho, data — sai;
o endereço dele, não.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .disciplinas import carregar, resolver
from .erros import ErroMoodle

# Host + caminho que caracterizam arquivo servido pelo webservice do Moodle, e
# que por isso exigiria o token para ser baixado.
_MARCAS_INTERNAS = ("/webservice/", "pluginfile.php")

_TIPOS = {
    "application/pdf": "PDF",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "documento",
    "application/msword": "documento",
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


@dataclass(frozen=True)
class Secao:
    nome: str
    itens: tuple[Item, ...]


@dataclass(frozen=True)
class Conteudo:
    secoes: tuple[Secao, ...]
    total_itens: int
    sem_conteudo: tuple[str, ...]


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


def projetar_material(bruto) -> Conteudo:
    """Seções → módulos → conteúdos vira uma lista curta com o que identifica.

    `author` e `userid` ficam de fora de propósito: vêm dentro de `contents`,
    são dado pessoal (§3.3) e não respondem "que arquivos tem aqui".
    """
    secoes: list[Secao] = []
    total = 0
    sem_conteudo: set[str] = set()

    for secao in bruto or ():
        itens: list[Item] = []
        for modulo in secao.get("modules") or ():
            conteudos = modulo.get("contents") or ()
            if not conteudos:
                # Invariante 7: fórum e entrega não têm `contents`. Sumir com
                # eles faria a lista parecer o espaço inteiro quando não é.
                sem_conteudo.add(modulo.get("modname") or "?")
                continue
            for conteudo in conteudos:
                itens.append(
                    Item(
                        nome=conteudo.get("filename") or modulo.get("name") or "",
                        tipo=_tipo_de(modulo.get("modname") or "", conteudo.get("mimetype")),
                        tamanho=conteudo.get("filesize") or None,
                        modificado=_data(conteudo.get("timemodified")),
                        url_externa=_url_publica(conteudo.get("fileurl")),
                    )
                )
                total += 1
        secoes.append(Secao(nome=secao.get("name") or "", itens=tuple(itens)))

    return Conteudo(
        secoes=tuple(secoes),
        total_itens=total,
        sem_conteudo=tuple(sorted(sem_conteudo)),
    )


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
                    "url": i.url_externa,
                }
                for i in s.itens
            ],
        }
        for s in conteudo.secoes
    ]


def _formatar_item(item: Item) -> str:
    partes = [f"  - {item.nome} [{item.tipo}"]
    if item.tamanho:
        partes.append(f", {item.tamanho // 1024} kB")
    if item.modificado:
        partes.append(f", {item.modificado.strftime('%d/%m/%Y')}")
    partes.append("]")
    linha = "".join(partes)
    if item.url_externa:
        linha += f"\n    {item.url_externa}"
    return linha


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
    conteudo = projetar_material(
        cliente.chamar("core_course_get_contents", courseid=alvo.courseid)
    )

    total = conteudo.total_itens
    filtro = (busca or "").strip().lower()

    secoes = []
    mostrados = 0
    for secao in conteudo.secoes:
        itens = [i for i in secao.itens if not filtro or filtro in i.nome.lower()]
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
        "Link de arquivo interno do e-Disciplinas não é entregue aqui: baixá-lo "
        "exige a sua credencial na URL, e ela não sai desta máquina (Invariante 3). "
        "Abra pelo e-Disciplinas.",
    ]
    if conteudo.sem_conteudo:
        avisos.append(
            "Não estão nesta lista: "
            + ", ".join(conteudo.sem_conteudo)
            + " — são atividades, não arquivos, e têm consulta própria."
        )

    linhas.extend(f"\n⚠ {a}" for a in avisos)

    return RespostaMaterial(
        texto="\n".join(linhas), total=total, mostrados=mostrados
    )
