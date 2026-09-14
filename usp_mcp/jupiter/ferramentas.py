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

**O pré-requisito é condicional ao curso.** Os créditos são incondicionais; o
pré-requisito exige `codcur`+`codhab` (§5.2 do recon). Sem curso, esta
ferramenta **não responde e diz que não respondeu** — omitir calado é o que o
Invariante 7 proíbe.
"""
from __future__ import annotations

from . import requisitos as _recorte

# O nome da consulta NUNCA aparece nesta camada: quem o conhece é a política.
# Uma ferramenta que aceite o nome da consulta como argumento deixa de ter
# superfície, e a allowlist inteira vira decoração.

CAMPOS_PT = (
    "sigla", "nome", "creditos_aula", "creditos_trabalho", "carga_horaria_total",
    "tipo", "ativacao", "ementa", "objetivos", "programa", "bibliografia",
    "metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao",
    "pre_requisito", "avisos",
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

# §5.1 do recon: a mesma habilitação aparece com códigos diferentes conforme a
# superfície. Não investigado, e não se inventa explicação — declara-se.
_DISCREPANCIA_CODCUR = {"3032": "3033", "3033": "3032"}


def normalizar_sigla(bruta: str) -> str:
    """`psi 3323` e `  PSI3323 ` são a mesma disciplina para quem pergunta."""
    return "".join(bruta.split()).upper()


def _preencher(destino: dict, cru: dict, pares) -> None:
    for saida, campo in pares:
        valor = cru.get(campo)
        if valor not in ("", None):
            destino[saida] = valor


def disciplina(sigla: str, curso: tuple[str, str] | None = None, *, cliente,
               idiomas: tuple[str, ...] = ("pt",)) -> dict:
    """Ficha da disciplina, e o pré-requisito dela **se o curso for informado**.

    `curso` é o par `(codcur, codhab)`. Resolver "Poli elétrica" para esse par é
    outra fatia; enquanto ela não existe, esta ferramenta não finge que resolve.
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
    _preencher(ficha, cru, _TEXTO_PT)
    if "en" in idiomas:
        _preencher(ficha, cru, _TEXTO_EN)
    # Espanhol nunca sai: os quatro campos vêm vazios nas duas amostras da
    # Fase 1, e campo vazio é token gasto para dizer nada.

    avisos: list[str] = []

    if curso is None:
        ficha["pre_requisito"] = None
        avisos.append(
            "Pré-requisito não consultado por aqui: ele depende do currículo, "
            "não só da disciplina. Use a ferramenta `requisitos` com a mesma "
            "sigla — ela mostra TODOS os currículos de uma vez, sem precisar "
            "de código de curso. O código que a API deixa descobrir é "
            "justamente o que devolve lista vazia aqui."
        )
    else:
        codcur, codhab = curso
        if codcur in _DISCREPANCIA_CODCUR:
            avisos.append(
                f"O código {codcur} e o {_DISCREPANCIA_CODCUR[codcur]} são o "
                "mesmo curso em gerações diferentes de currículo, não uma "
                "discrepância sem explicação. O que muda "
                "entre eles: 3033 é quem tem a **grade** curricular (67 "
                "disciplinas, 1º ao 5º semestre) e 3032 é quem tem os "
                "**requisitos**; a grade de 3032 vem vazia. Usei "
                f"{codcur} como veio, sem traduzir."
            )
        bruto = cliente.listar_requisito(coddis=sigla, codcur=codcur, codhab=codhab)
        ficha["pre_requisito"] = [
            {
                "sigla": r["coddisreq"],
                "nome": r["nomdisreq"],
                "tipo": r["tipreq"],
                "grupo": r.get("numgrpreq"),
                # `stamtrrcp="S"` é o que a página do JupiterWeb chama de
                # "Requisito fraco": dá para matricular devendo. Ficou fora da
                # fatia de 31/08 por não ter sido medido, e a ferramenta
                # anunciava exigência dura onde não havia (§9, 14/09).
                "fraco": r.get("stamtrrcp") == "S",
            }
            for r in bruto
        ]
        if not ficha["pre_requisito"]:
            avisos.append(
                f"A consulta de requisito no curso {codcur}-{codhab} não trouxe "
                "nenhuma linha, e isso tem TRÊS causas possíveis — não duas. "
                "Além de (a) não haver exigência e (b) a disciplina não "
                "pertencer a esse currículo, há (c) o código ser de outra "
                "geração do mesmo currículo: PTC3314 devolve zero linha em "
                "3033 e devolve PTC3213+PSI3213 em 3032, que são "
                "o mesmo Ciclo Básico da Elétrica em gerações diferentes. A (c) "
                "é a mais provável quando o código veio da lista de cursos de "
                "ingresso. Use a ferramenta `requisitos` com a sigla: ela "
                "mostra todos os currículos e dispensa o código."
            )

    ficha["avisos"] = avisos
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
