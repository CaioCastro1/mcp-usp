"""Resolução sigla → `courseid`, e o cache que impede martelar a USP por isso.

O modelo recebe "PSI3323" de quem pergunta; o Moodle só entende `courseid`. Esta
tradução é a razão de a fatia de material custar três funções e não uma, e vale
registrar o preço medido, porque ele é o que justifica o cache:

| | cru | projetado |
|---|---|---|
| `core_enrol_get_users_courses` | 104.712 B (~26.178 tokens) | 7.816 B para as 74 |

Buscar 104 kB toda vez que alguém pergunta "o que tem em PSI3323" é reconfirmar
a cada pergunta um dado que muda **uma vez por semestre**. O Invariante 5 pede
TTL colado na taxa de mudança do dado, não na frequência da pergunta — daí
`TTL_DISCIPLINAS`.

O `userid` é derivado do token, nunca configurado: §9 de 28/08 mediu que
`get_users_courses` com userid errado devolve `[]` com HTTP 200, que é a falha
silenciosa que o Invariante 6 proíbe. O modo perigoso é o valor errado, não o
ausente — por isso não há como passá-lo à mão por aqui.
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass

from .erros import ErroMoodle

# Um semestre. Matrícula não muda entre duas perguntas sobre material.
TTL_DISCIPLINAS = 60 * 60 * 24 * 120

# `shortname` no e-Disciplinas é "SIGLA-ano[-turma]": PSI3323-2026,
# PRO3811-202-2026, PSI3322-2026-REOF. A sigla é o primeiro segmento.
_SEPARADOR = "-"


@dataclass(frozen=True)
class Disciplina:
    courseid: int
    sigla: str
    rotulo: str
    nome: str


@dataclass(frozen=True)
class Resolucao:
    """Três desfechos, e nenhum deles é lista vazia sem explicação.

    `disciplina` preenchida quando resolveu; `candidatas` quando o termo casou
    com mais de uma e escolher seria errar calado; `motivo` sempre que não
    resolveu, dizendo o que foi pedido e o que existe (Invariante 6).
    """
    disciplina: Disciplina | None
    candidatas: tuple[Disciplina, ...] = ()
    motivo: str | None = None


def _normalizar(texto: str) -> str:
    """"psi 3323", "PSI-3323", " psi3323 " → "PSI3323"; "eletronica" → "ELETRONICA".

    Quem pergunta escreve como fala, e em português escreve sem acento.

    **O `NFD` é a linha que faz isso funcionar**, e não é decoração: ele separa
    "ô" em "o" + marca combinante, e aí o filtro abaixo descarta só a marca,
    sobrando o "o". Sem ele, o filtro descartava o "ô" INTEIRO — "Eletrônica"
    virava "ELETRNICA", "eletronica" virava "ELETRONICA", e os dois deixavam de
    casar entre si. Bug real, achado ao vivo em 31/08 porque o dono digitou sem
    acento; T83 fica vermelho se alguém remover o `NFD` por parecer supérfluo.
    """
    decomposto = unicodedata.normalize("NFD", texto or "")
    return re.sub(r"[^A-Z0-9]", "", decomposto.upper())


def projetar_disciplinas(bruto) -> list[Disciplina]:
    """29 chaves por disciplina viram 3. As outras 26 não resolvem sigla nenhuma.

    `summary`, `courseimage`, `overviewfiles` e `progress` respondem por quase
    todo o payload e por nada da pergunta.
    """
    lista = []
    for curso in bruto or ():
        rotulo = curso.get("shortname") or ""
        lista.append(
            Disciplina(
                courseid=curso.get("id"),
                sigla=_normalizar(rotulo.split(_SEPARADOR)[0]),
                rotulo=rotulo,
                nome=curso.get("fullname") or "",
            )
        )
    return lista


def resolver(disciplinas, termo: str) -> Resolucao:
    """Sigla exata primeiro; depois começo de sigla ou pedaço do nome.

    A ordem importa: com match parcial primeiro, "PTC3312" casaria consigo mesma
    e com qualquer PTC3312-XXX, virando ambiguidade onde havia resposta.
    """
    alvo = _normalizar(termo)
    if not alvo:
        return Resolucao(None, motivo="Nenhuma disciplina informada.")

    exatas = [d for d in disciplinas if d.sigla == alvo]
    if len(exatas) == 1:
        return Resolucao(exatas[0])
    parciais = exatas or [
        d for d in disciplinas
        if d.sigla.startswith(alvo) or alvo in _normalizar(d.nome)
    ]

    if len(parciais) == 1:
        return Resolucao(parciais[0])

    if parciais:
        # Invariante 6: escolher uma entre várias é errar calado. O motivo lista
        # as candidatas porque "ambíguo" sozinho não diz a quem lê o que fazer.
        rotulos = ", ".join(sorted({d.rotulo for d in parciais}))
        return Resolucao(
            None,
            candidatas=tuple(parciais),
            motivo=(
                f"{termo!r} casa com mais de uma disciplina: {rotulos}. "
                "Repita com a sigla completa."
            ),
        )

    # Invariante 7: "não achei" nunca sai como lista vazia muda. Listar o que
    # existe é o que separa "errei a sigla" de "não estou matriculado".
    siglas = ", ".join(sorted({d.sigla for d in disciplinas if d.sigla}))
    return Resolucao(
        None,
        motivo=(
            f"Não encontrei disciplina para {termo!r} entre as suas matrículas "
            f"no e-Disciplinas. Siglas disponíveis: {siglas}."
        ),
    )


class _Cache:
    """Cache de processo com relógio injetável.

    Injetável para que o teste verifique a REGRA (busca de novo depois do TTL) e
    não o valor da constante — se o teste dependesse do valor, mudar o TTL viraria
    mudar o teste, e o teste deixaria de proteger.
    """

    def __init__(self) -> None:
        self.disciplinas: list[Disciplina] | None = None
        self.carregado_em: float = 0.0

    def valido(self, agora: float) -> bool:
        return (
            self.disciplinas is not None
            and 0 <= agora - self.carregado_em < TTL_DISCIPLINAS
        )


_cache = _Cache()


def limpar_cache() -> None:
    """Descarta o cache. Existe para o teste, e é dele que o teste depende para
    não herdar o estado do vizinho — cache de processo compartilhado entre casos
    produz verde que nunca chamou nada."""
    global _cache
    _cache = _Cache()


def carregar(cliente, agora=None) -> list[Disciplina]:
    """As disciplinas do dono, do cache ou do Moodle. Duas chamadas na primeira vez.

    `core_webservice_get_site_info` só existe aqui para derivar o `userid` —
    §9 de 28/08 — e o valor derivado é o que viaja no parâmetro, nunca um
    configurado à mão.
    """
    relogio = agora if agora is not None else time.monotonic
    momento = relogio()

    if _cache.valido(momento):
        return _cache.disciplinas

    info = cliente.chamar("core_webservice_get_site_info")
    userid = info.get("userid") if isinstance(info, dict) else None
    if not userid:
        raise ErroMoodle(
            "O e-Disciplinas não devolveu o `userid` do token em "
            "`core_webservice_get_site_info`. Sem ele não dá para listar as "
            "disciplinas, e chutar um valor devolveria lista vazia com cara de "
            "'você não tem matrícula' (§9, 28/08)."
        )

    bruto = cliente.chamar("core_enrol_get_users_courses", userid=userid)
    _cache.disciplinas = projetar_disciplinas(bruto)
    _cache.carregado_em = momento
    return _cache.disciplinas
