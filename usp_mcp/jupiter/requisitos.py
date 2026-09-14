"""Recorte da página de requisitos por curso do JupiterWeb.

**Por que HTML, se existe DWR.** Porque o DWR exige `codcur`, e o `codcur` é
justamente o que não se descobre: `pubListarCursoEntrada` devolve 3033 para a
Elétrica, e com 3033 o requisito de PSI3323 e PTC3314 vem **vazio** — quem
responde é 3032, que não aparece em lista nenhuma (§9 do SPEC1, 14/09). Esta
página é a única superfície que cita os currículos onde a exigência de fato
mora, e o parâmetro dela é a sigla que o aluno já sabe.

**Por que o tipo sai por currículo.** Porque ele é propriedade do currículo, não
da dupla de disciplinas: MAT2454 é exigência dura em 3250 (Minas) e fraca em
3032 (Elétrica). Achatar os 23 currículos de MAT2455 numa resposta só apagaria
a informação que decide a matrícula.

A página é 26-66 kB de layout dos anos 2000; o recorte devolve ~600 B. Nada do
HTML cru sobe para quem chamou (Invariante 8).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Exigencia", "Bloco", "recortar", "TIPOS"]

# O cabeçalho de cada currículo. `re.S` porque o JupiterWeb quebra a linha no
# meio da frase, entre a habilitação e o período.
_CABECALHO = re.compile(
    r"Curso:\s*<b>\s*(?P<codcur>\d+)\s+(?P<nomcur>[^<]*?)\s*</b>\s*"
    r"-\s*Habilita\w*:\s*(?P<habilitacao>.*?)\s*"
    r"\((?P<periodo>[^)]*)\)\s*-\s*Per\w*odo ideal:\s*(?P<ideal>\d+)",
    re.S,
)

_LINHA = re.compile(r"<tr\b[^>]*>(?P<corpo>.*?)</tr>", re.S | re.I)
_TAG = re.compile(r"<[^>]*>")
_SIGLA = re.compile(r"^([A-Z0-9]{3,4}\d{3,4})\s*-\s*(.*)$")

# O rótulo que o aluno lê na página, e o que ele significa para a matrícula.
# Verificado contra o `tipreq`/`stamtrrcp` do DWR em 3 pares (§9, 14/09) — é um
# mapeamento de 3 pontos, não uma lei, e por isso o rótulo cru viaja junto.
TIPOS = {
    "Requisito": "requisito",
    "Requisito fraco": "requisito_fraco",
    "Indicação de Conjunto": "correquisito",
}


@dataclass(frozen=True)
class Exigencia:
    """Uma disciplina exigida, e em que termos."""

    sigla: str
    nome: str
    tipo: str
    rotulo: str


@dataclass(frozen=True)
class Bloco:
    """Um currículo, com as exigências que ele impõe. `exigencias` vazia é
    resposta legítima e diferente de bloco ausente — ver §9, os quatro
    silêncios."""

    codcur: str
    nome_curso: str
    habilitacao: str
    periodo: str
    periodo_ideal: int
    exigencias: list[Exigencia]


def _texto(html: str) -> str:
    """Tira as tags e normaliza o espaço. `&nbsp;` vira espaço porque as
    células de preenchimento da tabela são só isso."""
    sem_tag = _TAG.sub("\x00", html).replace("&nbsp;", " ").replace("&nbsp", " ")
    return sem_tag


def _exigencias(corpo: str) -> list[Exigencia]:
    achadas = []
    for linha in _LINHA.finditer(corpo):
        partes = [p.strip() for p in _texto(linha.group("corpo")).split("\x00") if p.strip()]
        if not partes:
            continue
        junto = re.sub(r"\s+", " ", " ".join(partes))
        casou = _SIGLA.match(junto)
        if not casou:
            continue
        rotulo = next(
            (p.strip() for p in partes if p.strip() in TIPOS),
            "",
        )
        nome = casou.group(2)
        if rotulo:
            nome = nome[: nome.rfind(rotulo)] if rotulo in nome else nome
        achadas.append(
            Exigencia(
                sigla=casou.group(1),
                nome=nome.strip(),
                # Rótulo fora do mapa não vira "requisito" por otimismo: sai
                # como desconhecido, com o texto cru à vista (Invariante 6).
                tipo=TIPOS.get(rotulo, "desconhecido"),
                rotulo=rotulo,
            )
        )
    return achadas


def recortar(bruto: bytes) -> list[Bloco]:
    """Da página crua para a lista de currículos.

    Recebe BYTES: o JupiterWeb serve ISO-8859-1, e quem decide o charset é quem
    lê o fio. Decodificar como UTF-8 estoura no primeiro acento; decodificar
    errado entrega "CÃ¡lculo", que nenhum teste de contagem pega.
    """
    html = bruto.decode("iso-8859-1") if isinstance(bruto, bytes) else bruto

    cabecalhos = list(_CABECALHO.finditer(html))
    blocos = []
    for i, cab in enumerate(cabecalhos):
        fim = cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(html)
        blocos.append(
            Bloco(
                codcur=cab.group("codcur"),
                nome_curso=cab.group("nomcur").strip(),
                habilitacao=re.sub(r"\s+", " ", cab.group("habilitacao")).strip(),
                periodo=cab.group("periodo").strip(),
                periodo_ideal=int(cab.group("ideal")),
                exigencias=_exigencias(html[cab.end():fim]),
            )
        )
    return blocos
