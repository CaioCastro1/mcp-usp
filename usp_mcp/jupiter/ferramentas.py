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
            "Pré-requisito não consultado: ele depende do curso, não só da "
            "disciplina (§5.2 do recon). Informe o par (codcur, codhab) para "
            "que eu busque."
        )
    else:
        codcur, codhab = curso
        if codcur in _DISCREPANCIA_CODCUR:
            avisos.append(
                f"O código de curso {codcur} e o {_DISCREPANCIA_CODCUR[codcur]} "
                "aparecem para a mesma habilitação em superfícies diferentes do "
                "JupiterWeb. Relação entre os dois: não verificada (§5.1 do "
                f"recon). Usei {codcur} como veio, sem traduzir."
            )
        bruto = cliente.listar_requisito(coddis=sigla, codcur=codcur, codhab=codhab)
        ficha["pre_requisito"] = [
            {
                "sigla": r["coddisreq"],
                "nome": r["nomdisreq"],
                "tipo": r["tipreq"],
                "grupo": r.get("numgrpreq"),
            }
            for r in bruto
        ]
        if not ficha["pre_requisito"]:
            avisos.append(
                f"A consulta de requisito no curso {codcur}-{codhab} não trouxe "
                "nenhuma linha. Isso pode significar que não há exigência, ou "
                "que a disciplina não pertence a esse currículo — o JupiterWeb "
                "não distingue os dois casos."
            )

    ficha["avisos"] = avisos
    return ficha
