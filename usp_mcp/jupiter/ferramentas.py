"""A ferramenta `disciplina` — a fatia vertical do Jupiter.

Responde a pergunta candidata do §5 do SPEC1, com o vocabulário do dono:

    "Essa disciplina tem quantos créditos e qual o pré-requisito?"

Duas coisas que a implementação tem de errado por padrão e que aqui estão
certas de propósito:

**Carga horária não é campo.** O DWR devolve `cgahoreto` valendo `"0"` — nas
duas amostras da Fase 1. A carga real sai de `creaul*15 + cretrb*30`, que é o
que o JavaScript oficial do JupiterWeb calcula. Quem lê o campo devolve **zero
hora com cara de resposta certa**: o silêncio do Invariante 6 sem erro nenhum
no caminho.

**O pré-requisito não é desta ferramenta.** Ele depende do currículo, e o único
`codcur` que a API deixa descobrir devolve zero linha para as disciplinas do dono
(§9, 14/09). `requisitos(sigla)` responde sem código de curso; esta ficha só aponta
para lá — e não oferece `codcur` no schema para o modelo não trilhar o caminho errado.

**A ficha vem por seção.** "Quantos créditos" é o cabeçalho (139 B); a ficha inteira
de PTC3314 são 3.880 B, 38% deles a lista de competências dos objetivos. Por padrão
sai só a ementa, o resto sob pedido — e o que ficou de fora é declarado no fim.
"""
from __future__ import annotations

import re

from . import requisitos as _recorte
from .erros import ErroJupiter

# O nome da consulta NUNCA aparece nesta camada: quem o conhece é a política.
# Uma ferramenta que aceite o nome da consulta como argumento deixa de ter
# superfície, e a allowlist inteira vira decoração.

CAMPOS_PT = (
    "sigla", "nome", "creditos_aula", "creditos_trabalho", "carga_horaria_total",
    "tipo", "ativacao", "ementa", "objetivos", "programa", "bibliografia",
    "metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao",
    "secoes", "secoes_omitidas", "avisos",
)
CAMPOS_EN = ("nome_en", "ementa_en", "objetivos_en", "programa_en")
CAMPOS_SAIDA = frozenset(CAMPOS_PT + CAMPOS_EN)

_TIPOS = {"S": "semestral", "A": "anual"}

# Texto livre em português, na ordem em que a pessoa lê a ficha.
_TEXTO_PT = (
    ("ementa", "pgmrsudis"),
    ("objetivos", "objdis"),
    ("programa", "pgmdis"),
    ("bibliografia", "dscbbgdis"),
    ("metodo_avaliacao", "dscmtdavl"),
    ("criterio_avaliacao", "crtavl"),
    ("norma_recuperacao", "dscnorrcp"),
)
_TEXTO_EN = (
    ("nome_en", "nomdisigl"),
    ("ementa_en", "pgmrsudisigl"),
    ("objetivos_en", "objdisigl"),
    ("programa_en", "pgmdisigl"),
)

# As seções da ficha que o modelo pode pedir, na ordem em que a pessoa lê. O
# cabeçalho (sigla, nome, créditos, carga, tipo, ativação) vem sempre e não é
# seção: é a resposta de "quantos créditos". `avaliacao` junta três campos
# porque ninguém pergunta "qual a norma de recuperação" separado do resto.
SECOES: tuple[str, ...] = ("ementa", "objetivos", "programa", "bibliografia", "avaliacao")
SECOES_PADRAO: tuple[str, ...] = ("ementa",)
_CAMPOS_DA_SECAO: dict[str, tuple[str, ...]] = {
    "ementa": ("ementa", "ementa_en"),
    "objetivos": ("objetivos", "objetivos_en"),
    "programa": ("programa", "programa_en"),
    "bibliografia": ("bibliografia",),
    "avaliacao": ("metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao"),
}

# Curto e fixo: a descrição da ferramenta já diz o mesmo, e o aviso existe para
# a resposta não parecer completa quando a pergunta era sobre pré-requisito.
AVISO_PRE_REQUISITO = (
    "Pré-requisito não vem por aqui: use a ferramenta requisitos com a mesma sigla."
)

_PARAGRAFO = re.compile(r"\n\s*\n")


def normalizar_sigla(bruta: str) -> str:
    """`psi 3323` e `  PSI3323 ` são a mesma disciplina para quem pergunta."""
    return "".join(bruta.split()).upper()


def resolver_secoes(pedidas) -> tuple[str, ...]:
    """Lista pedida pelo modelo → seções válidas, na ordem fixa da ficha.

    Vazio é o padrão (só a ementa); 'todas' expande; nome desconhecido é erro
    legível citando as válidas, não silêncio (Invariante 6).
    """
    if not pedidas:
        return SECOES_PADRAO
    escolhidas: set[str] = set()
    for pedida in pedidas:
        chave = str(pedida).strip().lower()
        if chave == "todas":
            return SECOES
        if chave not in SECOES:
            raise ErroJupiter(
                f"seção {pedida!r} não existe na ficha. Use "
                f"{', '.join(SECOES)} ou 'todas'."
            )
        escolhidas.add(chave)
    return tuple(s for s in SECOES if s in escolhidas)


def _sem_paragrafos_repetidos(texto: str) -> str:
    """A fonte às vezes repete um parágrafo inteiro — a bibliografia de PTC3314
    vem duplicada. Parágrafo idêntico (comparado sem diferença de espaçamento)
    sai uma vez, na primeira posição. Não é perda: é a fonte que se repetiu."""
    vistos: set[str] = set()
    saida: list[str] = []
    for paragrafo in _PARAGRAFO.split(texto.strip()):
        chave = re.sub(r"\s+", " ", paragrafo).strip()
        if chave and chave not in vistos:
            vistos.add(chave)
            saida.append(paragrafo.strip())
    return "\n\n".join(saida)


def _preencher(destino: dict, cru: dict, pares, campos: set[str]) -> None:
    for saida, campo in pares:
        if saida not in campos:
            continue
        valor = cru.get(campo)
        if valor in ("", None):
            continue
        destino[saida] = _sem_paragrafos_repetidos(valor) if isinstance(valor, str) else valor


def disciplina(sigla: str, *, cliente, secoes: tuple[str, ...] = SECOES_PADRAO,
               idiomas: tuple[str, ...] = ("pt",)) -> dict:
    """Ficha da disciplina: cabeçalho sempre, e as seções pedidas.

    Pré-requisito não é desta ferramenta desde 14/09 (§9): o único `codcur` que
    a API deixa descobrir devolve zero linha, e `requisitos(sigla)` responde sem
    código de curso. O aviso fixo aponta para lá, e o schema não oferece `codcur`.
    """
    sigla = normalizar_sigla(sigla)
    cru = cliente.obter_disciplina(sigla)

    aula, trabalho = int(cru["creaul"]), int(cru["cretrb"])
    ficha: dict = {
        "sigla": cru["coddis"],
        "nome": cru["nomdis"],
        "creditos_aula": aula,
        "creditos_trabalho": trabalho,
        # Calculada. O campo cgahoreto do DWR vem "0" e não é usado.
        "carga_horaria_total": aula * 15 + trabalho * 30,
        "tipo": _TIPOS.get(cru["tipdis"], cru["tipdis"]),
        "ativacao": cru["dtaatvdis"],
    }

    campos = {campo for secao in secoes for campo in _CAMPOS_DA_SECAO[secao]}
    _preencher(ficha, cru, _TEXTO_PT, campos)
    if "en" in idiomas:
        # O nome em inglês é cabeçalho, não seção: vem sempre que inglês é pedido.
        _preencher(ficha, cru, _TEXTO_EN, campos | {"nome_en"})
    # Espanhol nunca sai: os quatro campos vêm vazios nas duas amostras da
    # Fase 1, e campo vazio é token gasto para dizer nada.

    ficha["secoes"] = list(secoes)
    # Invariante 7: o que ficou de fora é dito, não omitido.
    ficha["secoes_omitidas"] = [s for s in SECOES if s not in secoes]
    ficha["avisos"] = [AVISO_PRE_REQUISITO]
    return ficha


# --- a fatia de 14/09: o requisito pela sigla, não pelo curso ---------------

# Zero currículo tem DUAS causas, e a página devolve a mesma coisa para as duas.
# Ranquear uma delas foi o que a pergunta de aceite P8 pegou: MAT2453 é Cálculo
# I, primeira do currículo, e recebia a explicação sobre ênfase e 7º semestre.
_SEM_CURRICULO = (
    "O JupiterWeb não lista nenhum currículo com exigência para {sigla}. Isso "
    "tem duas causas possíveis, e desta página não dá para saber qual é: (a) a "
    "disciplina realmente não exige nada — é o caso das primeiras do currículo, "
    "como Cálculo I; ou (b) existe exigência e ela não está registrada aqui — "
    "acontece da ênfase (7º semestre) e do módulo (9º) em diante, estruturas "
    "que viram curso novo. NÃO conclua 'não precisa de nada' a partir deste "
    "silêncio: se a disciplina for de meio ou fim de curso, confirme na "
    "coordenação ou na grade do seu currículo."
)

_FORA_DO_INGRESSO = (
    "{quantos} não {consta} na lista de cursos de ingresso. Isso pode ser "
    "currículo de geração anterior, ênfase ou módulo — o JupiterWeb não "
    "distingue os três, e eu não invento qual é."
)

_CURRICULO_VAZIO = (
    "O currículo {codcur} aparece na página mas sem nenhuma linha de "
    "exigência. Não li isso como 'não precisa de nada' — a página apenas não "
    "traz registro para ele."
)


def requisitos(sigla: str, *, cliente) -> dict:
    """O que é preciso ter feito antes desta disciplina, **por currículo**.

    O parâmetro é a sigla, e só. A medição de 14/09 (§9) mostrou que pedir o
    curso não funciona: o único `codcur` que a API deixa descobrir devolve zero
    linha justamente para as disciplinas de 6º semestre em diante.

    A resposta sai por currículo porque o tipo de exigência é propriedade do
    currículo: MAT2454 é requisito duro em Minas e fraco em Elétrica.
    """
    sigla = normalizar_sigla(sigla)
    blocos = _recorte.recortar(cliente.obter_requisitos(sigla))

    avisos: list[str] = []
    if not blocos:
        return {
            "sigla": sigla,
            "curriculos": [],
            "avisos": [_SEM_CURRICULO.format(sigla=sigla)],
        }

    # Uma consulta de pertencimento por família de código, não uma por bloco.
    de_ingresso: set[str] = set()
    for codcur in {b.codcur for b in blocos}:
        de_ingresso |= cliente.cursos_de_ingresso(codcur)

    curriculos = []
    for b in blocos:
        curriculos.append(
            {
                "codcur": b.codcur,
                "curso": b.nome_curso,
                "habilitacao": b.habilitacao,
                "periodo": b.periodo,
                "periodo_ideal": b.periodo_ideal,
                "ingresso": b.codcur in de_ingresso,
                "exigencias": [
                    {
                        "sigla": e.sigla,
                        "nome": e.nome,
                        "tipo": e.tipo,
                        "rotulo": e.rotulo,
                    }
                    for e in b.exigencias
                ],
            }
        )
        if not b.exigencias:
            avisos.append(_CURRICULO_VAZIO.format(codcur=b.codcur))

    fora = sum(1 for c in curriculos if not c["ingresso"])
    if fora:
        avisos.append(
            _FORA_DO_INGRESSO.format(
                quantos=(
                    "O único currículo listado"
                    if len(curriculos) == 1
                    else f"{fora} dos {len(curriculos)} currículos listados"
                ),
                consta="consta" if fora == 1 else "constam",
            )
        )

    return {"sigla": sigla, "curriculos": curriculos, "avisos": avisos}
