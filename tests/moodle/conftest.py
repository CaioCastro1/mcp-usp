"""Insumos das três camadas.

A fixture higienizada é obrigatória, não opcional: se ela sumir, os testes têm de
FALHAR, nunca dar skip. Um skip aqui produziria verde sem ter testado nada — o
falso "não tem nada" que o Invariante 6 proíbe, aplicado à própria suíte.

O segundo insumo é o `.env`, carregado por `usp_mcp.env` porque nada no lado
Python fazia isso: só `scripts/ws.sh` sourceia o arquivo (`set -a`). O
efeito era um erro legível apontando para a cura errada — `test_live` dizia
"MOODLE_TOKEN está vazio, copie .env.example para .env" para quem já tinha o
.env preenchido, porque o valor nunca chegava a `os.environ`. E fazia
`test_a_fixture_versionada_nao_contem_segredo_do_env` passar no vácuo: ela
varre a fixture procurando os segredos do ambiente, e o ambiente não tinha
nenhum para procurar.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from usp_mcp.env import carregar_env

RAIZ = Path(__file__).resolve().parents[2]
FIXTURE_EVENTOS = RAIZ / "fixtures" / "moodle" / "action_events.json"
FIXTURE_ERRO = RAIZ / "fixtures" / "moodle" / "erro_invalidtoken.json"
FIXTURE_ERRO_PARAM = RAIZ / "fixtures" / "moodle" / "erro_invalidparameter.json"
FIXTURE_ERRO_LIMITE = RAIZ / "fixtures" / "moodle" / "erro_limite_fora_da_faixa.json"
FIXTURE_CONTEUDO = RAIZ / "fixtures" / "moodle" / "course_contents_psi3323.json"
FIXTURE_DISCIPLINAS = RAIZ / "fixtures" / "moodle" / "users_courses.json"
FIXTURE_CONTEUDO_PTC3314 = RAIZ / "fixtures" / "moodle" / "course_contents_ptc3314.json"
FIXTURE_ENTREGAS_PTC3314 = RAIZ / "fixtures" / "moodle" / "assign_ptc3314.json"


# O carregador mora em usp_mcp/env.py, não aqui: o entrypoint stdio do Moodle
# precisa do mesmo comportamento (§9, 31/08/2026). `setdefault` lá dentro
# garante que quem já está no ambiente ganha — `USP_MCP_LIVE=1 pytest` continua
# valendo, e este import não liga a camada live por baixo de ninguém.
ARQUIVO_ENV = carregar_env(RAIZ)


def _achar_cru() -> Path:
    """O cru é local à máquina do dono (gitignorado, §3.3) e num worktree ele
    não existe. Procura no worktree, depois no checkout principal, depois onde
    USP_MCP_MOODLE_RAW apontar. Só os testes DO HIGIENIZADOR dependem dele —
    a fixture higienizada, essa, é obrigatória e faz falhar se sumir."""
    candidatos = [RAIZ / "fixtures" / "moodle" / "raw"]
    if (env := os.environ.get("USP_MCP_MOODLE_RAW")):
        candidatos.insert(0, Path(env))
    # .claude/worktrees/<nome>/ → sobe até o checkout que tem o .git de verdade
    for pai in RAIZ.parents:
        if (pai / ".git").is_dir():
            candidatos.append(pai / "fixtures" / "moodle" / "raw")
            break
    for c in candidatos:
        if (c / "action_events.json").exists():
            return c / "action_events.json"
    return candidatos[0] / "action_events.json"


CRU_EVENTOS = _achar_cru()


@pytest.fixture(scope="session")
def eventos_brutos() -> dict:
    if not FIXTURE_EVENTOS.exists():
        pytest.fail(
            f"Fixture higienizada ausente: {FIXTURE_EVENTOS}\n"
            "Gere com: python3 scripts/higienizar.py "
            "fixtures/moodle/raw/action_events.json fixtures/moodle/action_events.json\n"
            "Isto FALHA em vez de dar skip de propósito (Invariante 6)."
        )
    return json.loads(FIXTURE_EVENTOS.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def caminho_fixture() -> Path:
    return FIXTURE_EVENTOS


@pytest.fixture(scope="session")
def erro_invalidtoken() -> dict:
    """A resposta REAL do Moodle para token inválido, capturada em 31/08/2026.

    Capturada com `wstoken=""` — token propositalmente vazio, que não usa
    credencial de ninguém e não toca conta nenhuma. É o que faltava para os
    testes de erro pararem de assegurar só o contrato da camada.

    Obrigatória, não opcional, pelo mesmo motivo da fixture de eventos: um
    skip aqui produziria verde sem ter testado nada.
    """
    if not FIXTURE_ERRO.exists():
        pytest.fail(
            f"Fixture de erro ausente: {FIXTURE_ERRO}\n"
            "Recapture com wstoken vazio contra "
            "https://edisciplinas.usp.br/webservice/rest/server.php\n"
            "Isto FALHA em vez de dar skip de propósito (Invariante 6)."
        )
    return json.loads(FIXTURE_ERRO.read_text(encoding="utf-8"))


def pytest_runtest_setup(item):
    """Camada live só roda com a env var. O skip DIZ o motivo (Invariante 6)."""
    if "live" in item.keywords and os.environ.get("USP_MCP_LIVE") != "1":
        pytest.skip(
            "camada live desligada: exporte USP_MCP_LIVE=1 para falar com "
            "edisciplinas.usp.br. Do sandbox a rede da USP não é alcançável (§1.1)."
        )


def _carregar_fixture_erro(caminho: Path, como_recapturar: str) -> dict:
    if not caminho.exists():
        pytest.fail(
            f"Fixture de erro ausente: {caminho}\n{como_recapturar}\n"
            "Isto FALHA em vez de dar skip de propósito (Invariante 6)."
        )
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def erro_invalidparameter() -> dict:
    """Erro real de parâmetro inválido, capturado em 31/08/2026 na MESMA função
    da allowlist, read-only, com `timesortfrom` textual (Regra de Ouro §3.1)."""
    return _carregar_fixture_erro(
        FIXTURE_ERRO_PARAM,
        "Recapture chamando core_calendar_get_action_events_by_timesort "
        "com timesortfrom='nao-e-numero'.",
    )


@pytest.fixture(scope="session")
def erro_limite_fora_da_faixa() -> dict:
    """O erro que revelou o teto de 50 do `limitnum` — e que `errorcode` nem
    sempre é um código (§9, 31/08/2026)."""
    return _carregar_fixture_erro(
        FIXTURE_ERRO_LIMITE,
        "Recapture chamando core_calendar_get_action_events_by_timesort "
        "com limitnum=-5.",
    )


def _obrigatoria(caminho, cru):
    """Fixture higienizada ausente FALHA, nunca dá skip — mesmo motivo do §0
    deste arquivo: skip aqui é verde que não testou nada."""
    if not caminho.exists():
        pytest.fail(
            f"Fixture higienizada ausente: {caminho}\n"
            f"Gere com: python3 scripts/higienizar.py "
            f"fixtures/moodle/raw/{cru} {caminho.relative_to(RAIZ)}"
        )
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def conteudo_bruto() -> list:
    """`core_course_get_contents` de PSI3323 (courseid 142033), 31/08/2026.

    Amostra ÚNICA, e o dono decidiu assim conscientemente (§9, 31/08). Tudo que
    esta suíte afirma sobre proporção — a projeção de 11,2%, a mistura de tipos —
    vale para esta disciplina, não para as dez. Quem for generalizar precisa
    capturar as outras primeiro.
    """
    return _obrigatoria(FIXTURE_CONTEUDO, "course_contents_142033.json")


@pytest.fixture(scope="session")
def disciplinas_brutas() -> list:
    """`core_enrol_get_users_courses`: as 74 disciplinas, 104 kB de cru."""
    return _obrigatoria(FIXTURE_DISCIPLINAS, "users_courses.json")


class ClienteFalso:
    """Dublê que responde por NOME de função e grava o que foi enviado.

    Grava os parâmetros porque asserção sobre a saída não pega parâmetro errado:
    o dublê devolve o que o teste mandou. Foi assim que o limite silencioso de 20
    passou pela suíte (§9, 31/08) e assim que uma sabotagem de mapeamento passou
    pelo T47 do Jupiter no mesmo dia.
    """

    def __init__(self, respostas: dict, arquivos: dict | None = None):
        self._respostas = respostas
        self._arquivos = arquivos or {}
        self.chamadas: list[tuple[str, dict]] = []
        self.downloads: list[str] = []

    def chamar(self, funcao: str, **params):
        self.chamadas.append((funcao, params))
        if funcao not in self._respostas:
            raise AssertionError(
                f"O código chamou {funcao!r}, que este teste não previu. "
                f"Previstas: {sorted(self._respostas)}"
            )
        resposta = self._respostas[funcao]
        return resposta(params) if callable(resposta) else resposta

    def baixar(self, fileurl: str, *, tamanho_esperado=None, teto_bytes=None) -> bytes:
        """Grava a URL pedida — asserção sobre o que foi ENVIADO, não sobre a saída.

        `downloads` vazio é o que prova que um caminho NÃO baixou; a saída não
        prova isso, porque o dublê devolveria bytes de qualquer jeito.
        """
        self.downloads.append(fileurl)
        if fileurl in self._arquivos:
            valor = self._arquivos[fileurl]
            # Chamável = o teste quer simular uma FALHA deste download
            # específico (ex.: MoodleIndisponivel, FuncaoBloqueada) sem
            # derrubar os outros arquivos do mesmo lote.
            return valor() if callable(valor) else valor
        conteudo = b"%PDF-1.4 " + b"x" * max((tamanho_esperado or 9) - 9, 0)
        return conteudo

    def params_de(self, funcao: str) -> dict:
        for nome, params in self.chamadas:
            if nome == funcao:
                return params
        raise AssertionError(f"{funcao!r} nunca foi chamada. Chamadas: {[c[0] for c in self.chamadas]}")

# A fixture de PSI3323 tem UM módulo `assign` (`Entrega de Relatório -
# Sexta-Feira`, cmid 6372196), e desde 12/09 quem pede material dela também
# pergunta pelos anexos das entregas. Esta é a resposta que o Moodle dá para uma
# entrega SEM anexo — forma real, lista vazia — e é o insumo dos testes que não
# são sobre anexo nenhum. Escrita à mão, e não capturada, de propósito: a
# fixture de conteúdo é de 31/08 e a disciplina já mudou desde então (§9), então
# uma captura de hoje não formaria par com ela.
ENTREGAS_PSI3323_SEM_ANEXO = {
    "courses": [
        {
            "id": 142033,
            "assignments": [
                {
                    "id": 1,
                    "cmid": 6372196,
                    "name": "Entrega de Relatório - Sexta-Feira",
                    "introattachments": [],
                }
            ],
        }
    ],
    "warnings": [],
}


@pytest.fixture(scope="session")
def conteudo_ptc3314() -> list:
    """`core_course_get_contents` de PTC3314 (courseid 142036), 12/09/2026.

    Existe para formar PAR com `entregas_ptc3314`: as duas respostas são da
    MESMA disciplina, capturadas na mesma sessão, e o `cmid` que liga uma à
    outra é real. Um par sintético provaria só que o teste sabe somar dois
    dicionários que ele mesmo escreveu.
    """
    return _obrigatoria(FIXTURE_CONTEUDO_PTC3314, "course_contents_142036.json")


@pytest.fixture(scope="session")
def entregas_ptc3314() -> dict:
    """`mod_assign_get_assignments` de PTC3314, 12/09/2026: 8.623 B crus.

    É a resposta que contém `EP1-2026.pdf` e `EP2-2026.pdf` — os dois enunciados
    que `core_course_get_contents` não mostra, porque os 4 módulos `assign` da
    disciplina chegam lá com `contents` VAZIO. Traz também dois `warnings` de
    "sem direito de acesso", que é o que o Invariante 7 proíbe engolir.
    """
    return _obrigatoria(FIXTURE_ENTREGAS_PTC3314, "assign_ptc3314.json")


# --------------------------------------------------------------------------
# `mod_assign_get_submission_status` — ESCRITA À MÃO, e a procedência importa.
#
# **Não é captura.** A worktree onde isto foi escrito não tem token e não devia
# obter um, então esta resposta foi montada a partir da forma documentada da
# função no Moodle 5.0 (`mod/assign/externallib.php`, `get_submission_status_
# returns`) e do que `notas/moodle-catalogo.md` §3.5 registra dela. A forma é
# fiel; os VALORES são sintéticos, e o `assignid` 577509 é o do `EC-1` da
# fixture real de PTC3314, para o par fechar.
#
# O que isso implica, dito aqui e não descoberto depois: a projeção medida
# contra este payload mede o que a nossa projeção descarta de uma resposta
# DESTA FORMA — não o tamanho da resposta que o e-Disciplinas devolve de fato.
# O catálogo estima ~260 tokens por chamada e marca a estimativa como medida,
# enquanto `notas/fase1-moodle.md` lista `submission_status` como não medida
# (registrado em `docs/decisions/BACKLOG-correcoes.md`, 14/09). Quem rodar ao
# vivo primeiro: capture, higienize (§3.3) e troque isto por fixture de verdade.
#
# Os dois campos gordos são de propósito e são o ponto da projeção: o
# `editorfields[].text` carrega o TEXTO INTEIRO que o aluno entregou, e o
# `assignmentdata.activity` carrega o enunciado inteiro em HTML — nenhum dos
# dois responde "eu já entreguei isso?".
_TEXTO_ENTREGUE = (
    "<p dir=\"ltr\" style=\"text-align:left;\">Relatório do EC-1. A simulação do "
    "transitório na linha de transmissão foi feita no ATP, com a linha modelada "
    "por parâmetros distribuídos e passo de 1 us. Os gráficos de tensão no "
    "terminal aberto estão no PDF anexo, junto da dedução do coeficiente de "
    "reflexão.</p>"
) * 4

_ENUNCIADO_EM_HTML = (
    "<p>Exercício Computacional 1 — Transitórios em Linhas de Transmissão. "
    "Leia o roteiro anexo antes de começar. A entrega é individual e deve conter "
    "o relatório em PDF e os arquivos de simulação.</p><ul><li>Prazo: 13/09, "
    "23h59</li><li>Tolerância: 48 h com desconto</li></ul>"
) * 6


def status_de_entrega(
    *,
    status: str = "submitted",
    timemodified: int = 1789300000,
    gradingstatus: str = "notgraded",
    extensionduedate: int = 0,
    arquivos: tuple[str, ...] = ("EC1-relatorio.pdf",),
    com_lastattempt: bool = True,
    com_texto_online: bool = True,
) -> dict:
    """Uma resposta de `mod_assign_get_submission_status`, na forma documentada.

    `status` aceita os quatro valores do core: `new` (nada começado), `draft`
    (rascunho salvo e NÃO enviado), `submitted` e `reopened`. A distinção entre
    `draft` e `submitted` é a razão de a ferramenta existir — quem tem rascunho
    salvo acha que entregou.

    `com_texto_online=False` produz a entrega SÓ DE ARQUIVO, que é a forma dos
    quatro `assign` reais de PTC3314. As duas existem porque o tamanho do cru
    depende inteiramente de qual delas é — e o lado projetado, não (J6).
    """
    plugin_texto = {
        "type": "onlinetext",
        "name": "Texto online",
        "fileareas": [{"area": "submissions_onlinetext", "files": []}],
        "editorfields": [
            {
                "name": "onlinetext",
                "description": "",
                "text": _TEXTO_ENTREGUE,
                "format": 1,
            }
        ],
    }

    submissao = {
        "id": 4120391,
        "userid": 8214,
        "attemptnumber": 0,
        "timecreated": timemodified - 7200,
        "timemodified": timemodified,
        "timestarted": None,
        "status": status,
        "groupid": 0,
        "assignment": 577509,
        "latest": 1,
        "gradingstatus": gradingstatus,
        "plugins": [
            *([plugin_texto] if com_texto_online else []),
            {
                "type": "file",
                "name": "Envios de arquivo",
                "fileareas": [
                    {
                        "area": "submission_files",
                        "files": [
                            {
                                "filename": nome,
                                "filepath": "/",
                                "filesize": 218453,
                                "fileurl": (
                                    "https://edisciplinas.usp.br/webservice/"
                                    f"pluginfile.php/9599793/assignsubmission_file/"
                                    f"submission_files/4120391/{nome}"
                                ),
                                "timemodified": timemodified,
                                "mimetype": "application/pdf",
                                "isexternalfile": False,
                            }
                            for nome in arquivos
                        ],
                    }
                ],
            },
        ],
    }

    return {
        "lastattempt": {
            # `submission` ausente é como o Moodle responde quando o aluno nunca
            # abriu a entrega — não é `status: "new"` com objeto vazio.
            **({"submission": submissao} if com_lastattempt else {}),
            "teamsubmission": None,
            "submissiongroup": None,
            "submissiongroupmemberswhoneedtosubmit": [],
            "submissionsenabled": True,
            "locked": False,
            "graded": gradingstatus == "graded",
            "canedit": status in ("new", "draft"),
            "caneditowner": status in ("new", "draft"),
            "cansubmit": status in ("new", "draft"),
            "extensionduedate": extensionduedate,
            "blindmarking": False,
            "gradingstatus": gradingstatus,
            "usergroups": [],
        },
        "assignmentdata": {
            "attachments": {
                "intro": [
                    {
                        "filename": "EP1-2026.pdf",
                        "filepath": "/",
                        "filesize": 218453,
                        "fileurl": (
                            "https://edisciplinas.usp.br/webservice/pluginfile.php/"
                            "9599801/mod_assign/introattachment/0/EP1-2026.pdf"
                        ),
                        "timemodified": 1787314800,
                        "mimetype": "application/pdf",
                        "isexternalfile": False,
                    }
                ],
                "activity": [],
            },
            "activity": _ENUNCIADO_EM_HTML,
        },
        "warnings": [],
    }


# --------------------------------------------------------------------------
# As duas visões de nota — TAMBÉM ESCRITAS À MÃO, mesma procedência das de
# entrega acima e mesma ressalva: forma documentada (`gradereport/overview` e
# `gradereport/user` no core do Moodle 5.0), valores sintéticos. O que é real
# aqui são os `courseid`, que vêm de `users_courses.json`, e é isso que faz a
# tradução courseid → sigla ser exercitada contra dado de verdade.
#
# O catálogo estima ~870 tokens para a visão geral e ~320 para a de uma
# disciplina, e a `fase1-moodle.md` lista as duas como não medidas — a
# divergência está no `BACKLOG-correcoes.md` (14/09). Nada aqui depende de qual
# das duas está certa: a medição da suíte é sobre o que a projeção descarta.
def notas_gerais_falsas(pares, com_warning=False) -> dict:
    """`gradereport_overview_get_course_grades`: três campos por curso.

    `pares` é uma lista de (courseid, nota). Nota `None` vira o que o Moodle
    devolve para curso sem nota lançada: a string "-", que é o caso mais comum
    do semestre em andamento e o que não pode virar linha muda.
    """
    return {
        "grades": [
            {
                "courseid": courseid,
                "grade": "-" if nota is None else nota,
                "rawgrade": "-" if nota is None else nota.replace(",", "."),
                "rank": 12,
                "maxrank": 58,
            }
            for courseid, nota in pares
        ],
        "warnings": (
            [
                {
                    "item": "course",
                    "itemid": 142099,
                    "warningcode": "1",
                    "message": "Sem permissão para ver as notas deste curso",
                }
            ]
            if com_warning
            else []
        ),
    }


def _item_de_nota(**campos) -> dict:
    """Um `gradeitem` com as 24 chaves da forma documentada.

    As chaves gordas estão aqui de propósito: `feedback` é o comentário do
    professor em HTML, e é o campo que a projeção descarta declarando.
    """
    base = {
        "id": 8812345,
        "itemname": "EC-1 - Transitórios em LT",
        "itemtype": "mod",
        "itemmodule": "assign",
        "iteminstance": 577509,
        "itemnumber": 0,
        "idnumber": None,
        "categoryid": 55120,
        "outcomeid": None,
        "scaleid": None,
        "locked": False,
        "cmid": 6372328,
        "graderaw": 8.5,
        "gradedatesubmitted": 1789300000,
        "gradedategraded": 1789700000,
        "gradehiddenbydate": False,
        "gradeneedsupdate": False,
        "gradeishidden": False,
        "gradeislocked": False,
        "gradeisoverridden": False,
        "gradeformatted": "8,50",
        "grademin": 0,
        "grademax": 10,
        "rangeformatted": "0,00–10,00",
        "percentageformatted": "85,00 %",
        "feedback": (
            "<p dir=\"ltr\">Bom relatório. A dedução do coeficiente de reflexão "
            "está correta, mas o gráfico da tensão no terminal aberto ficou sem "
            "escala no eixo do tempo, e a discussão do passo de simulação não "
            "justifica o valor escolhido. Reveja o item 3 antes do EC-2.</p>"
        ),
        "feedbackformat": 1,
        "weightraw": 0.25,
        "weightformatted": "25,00 %",
        "status": "",
        "averageformatted": "7,10",
    }
    base.update(campos)
    return base


def itens_de_nota_falsos(itens=None, *, userid=8214, extras=(), com_warning=False) -> dict:
    """`gradereport_user_get_grade_items` de UMA disciplina.

    `extras` são blocos `usergrades` de OUTROS usuários — o que um token com
    capacidade de correção receberia. Existem para provar que a projeção não os
    imprime (§3.3): a fixture não pode ser o único motivo de eles não saírem.
    """
    itens = itens if itens is not None else [_item_de_nota()]
    return {
        "usergrades": [
            {
                "courseid": 142036,
                "courseidnumber": "",
                "userid": userid,
                "userfullname": "Joao Pedro Barreto do Prado Gunthen",
                "useridnumber": "12345678",
                "maxdepth": 2,
                "gradeitems": itens,
            },
            *extras,
        ],
        "warnings": (
            [
                {
                    "item": "course",
                    "itemid": 142036,
                    "warningcode": "1",
                    "message": "Um item de nota não pôde ser lido",
                }
            ]
            if com_warning
            else []
        ),
    }


# --------------------------------------------------------------------------
# `mod_forum_get_forums_by_courses` e `mod_forum_get_forum_discussions` —
# **FIXTURE ESCRITA À MÃO**, e o rótulo é o ponto desta seção.
#
# **Não é captura.** A worktree onde isto nasceu não tem token e não devia obter
# um. A FORMA vem da declaração das duas funções no core do Moodle 5.0
# (`mod/forum/externallib.php`, `get_forums_by_courses_returns` e
# `get_forum_discussions_returns`) e do que `notas/moodle-catalogo.md` §3.6
# registra delas.
#
# O que aqui é REAL, e vale dizer separado do que não é: os `id`, `cmid` e
# `name` dos dois fóruns vêm de `course_contents_ptc3314.json`, capturada em
# 12/09 — "Avisos" é o `instance` 301511 (cmid 6372301) e "Discussão de
# Exercícios" é o 301513 (cmid 6372305), na disciplina 142036. É isso que faz o
# `forumid` ENVIADO ser conferido contra um id de verdade, e não contra um
# número que o próprio teste inventou. Os `subject`, o `message` e os carimbos
# de tempo são inventados.
#
# Consequência, dita aqui para não ser descoberta depois: qualquer razão de
# projeção medida contra este payload mede o que a nossa projeção descarta de
# uma resposta DESTA FORMA — não o tamanho do que o e-Disciplinas devolve. O
# catálogo estima ~2.150 tokens para 4 discussões e marca a estimativa como
# medida, enquanto `notas/fase1-moodle.md` lista fóruns na seção *Ainda aberto*
# (a divergência está no `BACKLOG-correcoes.md`). Quem rodar ao vivo primeiro:
# capture, higienize (§3.3) — o payload de fórum é o que mais tem nome de
# terceiro do projeto inteiro — e troque isto por fixture de verdade.
FORUM_AVISOS = 301511
FORUM_DISCUSSAO = 301513
CMID_AVISOS = 6372301
CMID_DISCUSSAO = 6372305

# O corpo do post é o campo gordo, e no fórum ele é o CONTEÚDO — não gordura de
# transporte. O catálogo (§3.6) registra que é a resposta que menos comprime do
# projeto inteiro. Este texto é longo de propósito: é ele que exercita o teto de
# caracteres e o aviso de corte.
_AVISO_LONGO = (
    "<p dir=\"ltr\">Pessoal, a prova prática P1 foi <strong>adiada</strong> para "
    "24/09, mesma sala e mesmo horário.</p><p>O conteúdo continua o mesmo: linhas "
    "de transmissão, carta de Smith e casamento de impedância. A lista de "
    "exercícios 3 sai ainda esta semana e cobre exatamente o que cai.</p>"
    "<ul><li>Levem calculadora;</li><li>A carta de Smith impressa será "
    "distribuída;</li><li>Não haverá consulta.</li></ul><p>Quem tiver conflito "
    "de horário me procure at&eacute; sexta.</p>"
)


def foruns_falsos(*, com_avisos=True, com_discussao=True, extras=(), sem_contagem=False):
    """`mod_forum_get_forums_by_courses`: devolve uma LISTA de fóruns.

    `type` é o campo do core que separa o mural de avisos (`news`, onde só o
    professor posta) do fórum de discussão (`general`). `numdiscussions` é o que
    permite não gastar chamada num fórum vazio — `sem_contagem=True` produz a
    resposta de um site que não devolve o campo, que tem de ser tratada como
    "não sei", nunca como zero.
    """
    def _forum(forumid, cmid, nome, tipo, quantos):
        f = {
            "id": forumid,
            "course": 142036,
            "type": tipo,
            "name": nome,
            "intro": (
                "<p>Espaço para os avisos da disciplina. Acompanhe.</p>"
                "<p>Postagens apenas do professor.</p>"
            ),
            "introformat": 1,
            "introfiles": [],
            "duedate": 0,
            "cutoffdate": 0,
            "assessed": 0,
            "assesstimestart": 0,
            "assesstimefinish": 0,
            "scale": 0,
            "grade_forum": 0,
            "maxbytes": 0,
            "maxattachments": 9,
            "forcesubscribe": 1,
            "trackingtype": 1,
            "rsstype": 0,
            "rssarticles": 0,
            "timemodified": 1788900000,
            "warnafter": 0,
            "blockafter": 0,
            "blockperiod": 0,
            "completiondiscussions": 0,
            "completionreplies": 0,
            "completionposts": 0,
            "cmid": cmid,
            "istracked": True,
            "unreadpostscount": 2,
        }
        if not sem_contagem:
            f["numdiscussions"] = quantos
        return f

    lista = []
    if com_avisos:
        lista.append(_forum(FORUM_AVISOS, CMID_AVISOS, "Avisos", "news", 3))
    if com_discussao:
        lista.append(
            _forum(FORUM_DISCUSSAO, CMID_DISCUSSAO, "Discussão de Exercícios",
                   "general", 2)
        )
    lista.extend(extras)
    return lista


def discussao_falsa(
    *,
    discussionid=910001,
    subject="Prova P1 adiada para 24/09",
    message=None,
    created=1788910000,
    timemodified=1788910000,
    numreplies=0,
    pinned=False,
    nome_de_quem_postou="Fulano de Tal Professor",
):
    """Uma discussão na forma documentada de `get_forum_discussions`.

    `userfullname` e as três irmãs estão aqui **de propósito**: o fórum é o
    único lugar do projeto em que o payload traz nome de gente de verdade em
    quantidade, e a projeção só prova que não os imprime se eles chegarem a
    estar na entrada.
    """
    return {
        "id": discussionid,
        "name": subject,
        "groupid": -1,
        "timemodified": timemodified,
        "usermodified": 4471,
        "timestart": 0,
        "timeend": 0,
        "discussion": discussionid,
        "parent": 0,
        "userid": 4471,
        "created": created,
        "modified": timemodified,
        "mailed": 1,
        "subject": subject,
        "message": _AVISO_LONGO if message is None else message,
        "messageformat": 1,
        "messagetrust": 0,
        "attachment": "",
        "attachments": [
            {
                "filename": "lista3.pdf",
                "filepath": "/",
                "filesize": 91233,
                "fileurl": (
                    "https://edisciplinas.usp.br/webservice/pluginfile.php/"
                    "9599801/mod_forum/attachment/910001/lista3.pdf"
                ),
                "timemodified": timemodified,
                "mimetype": "application/pdf",
                "isexternalfile": False,
            }
        ],
        "totalscore": 0,
        "mailnow": 0,
        "userfullname": nome_de_quem_postou,
        "usermodifiedfullname": nome_de_quem_postou,
        "userpictureurl": (
            "https://edisciplinas.usp.br/webservice/pluginfile.php/"
            "1234/user/icon/boost/f1"
        ),
        "usermodifiedpictureurl": (
            "https://edisciplinas.usp.br/webservice/pluginfile.php/"
            "1234/user/icon/boost/f1"
        ),
        "numreplies": numreplies,
        "numunread": 0,
        "pinned": pinned,
        "locked": False,
        "starred": False,
        "canreply": False,
        "canlock": False,
        "canfavourite": True,
    }


def discussoes_falsas(discussoes=None, *, com_warning=False):
    """`mod_forum_get_forum_discussions`: `{discussions, warnings}`."""
    return {
        "discussions": [discussao_falsa()] if discussoes is None else list(discussoes),
        "warnings": (
            [
                {
                    "item": "forum",
                    "itemid": FORUM_DISCUSSAO,
                    "warningcode": "1",
                    "message": "Um tópico não pôde ser lido com esta credencial",
                }
            ]
            if com_warning
            else []
        ),
    }


# --------------------------------------------------------------------------
# `core_course_get_updates_since` — **FIXTURE ESCRITA À MÃO**, mesmo rótulo e
# mesma ressalva das duas seções acima.
#
# **Não é captura.** A forma vem da declaração de `core_course_get_updates_since`
# no core do Moodle 5.0 (`course/externallib.php`,
# `get_updates_since_returns` → `course_updates`) e do que
# `notas/moodle-catalogo.md` §3.3 registra dela: *"devolve ponteiro, não
# conteúdo: diz qual cmid mudou e em quê"*.
#
# O que aqui é REAL são os `cmid`, que vêm de `course_contents_ptc3314.json`
# (12/09): 6372306 é a "Apostila sobre Linhas e Ondas" (`resource`) e 6372301 é
# o fórum "Avisos". É isso que faz a tradução cmid → nome ser exercitada contra
# dado de verdade em vez de contra um dicionário que o próprio teste escreveu —
# a tradução é metade desta ferramenta, e é a metade que teria como errar calada.
# Os `timeupdated` e a escolha de quais tipos de mudança aparecem são inventados.
CMID_APOSTILA = 6372306
CMID_FORUM_AVISOS = 6372301
CMID_QUE_NAO_EXISTE = 9999999


def mudancas_falsas(instancias=None, *, com_warning=False, contextlevel="module"):
    """`core_course_get_updates_since`: ponteiro, não conteúdo.

    `instancias` é uma lista de `(cmid, [(nome_da_mudanca, timeupdated)])`. Os
    nomes seguem os do core — `configuration`, `contentfiles`, `introfiles`,
    `discussions`, `submissions`, `gradeitems` —, e um nome fora da lista existe
    para provar que o desconhecido sai cru em vez de virar rótulo inventado.
    """
    if instancias is None:
        instancias = [
            (CMID_APOSTILA, [("contentfiles", 1788900000)]),
            (CMID_FORUM_AVISOS, [("discussions", 1788910000)]),
        ]
    return {
        "instances": [
            {
                "contextlevel": contextlevel,
                "id": cmid,
                "updates": [
                    {"name": nome, "timeupdated": quando, "itemids": [1, 2]}
                    for nome, quando in mudancas
                ],
            }
            for cmid, mudancas in instancias
        ],
        "warnings": (
            [
                {
                    "item": "course",
                    "itemid": 142036,
                    "warningcode": "1",
                    "message": "Uma atividade não pôde ser verificada",
                }
            ]
            if com_warning
            else []
        ),
    }


# --------------------------------------------------------------------------
# `mod_assign_get_assignments` com VÁRIOS cursos — **ESCRITA À MÃO**, e o rótulo
# vale tanto quanto o payload.
#
# **Não é captura.** A única captura desta função que existe no repositório é
# `assign_ptc3314.json` (12/09, real, higienizada), e ela cobre UM curso. A
# ferramenta `atrasadas` (14/09) pergunta por várias disciplinas de uma vez, e
# esta forma — `courses` com mais de um item — nunca foi vista vir do
# e-Disciplinas por este projeto.
#
# O que aqui é REAL: os `courseid`, que vêm de `users_courses.json`, e a FORMA
# de cada `assign`, que é a da fixture capturada reduzida aos cinco campos que a
# projeção lê. Os `id`, nomes e prazos dos assign inventados são inventados.
#
# Consequência, dita aqui para não ser descoberta depois: qualquer contagem de
# bytes medida contra este payload mede o que a nossa projeção descarta de uma
# resposta DESTA FORMA. Os números do §9 de `atrasadas` que se apoiam em payload
# real dizem isso explicitamente, e os que não, também.
def entregas_falsas(por_curso, *, com_warning=False) -> dict:
    """`por_curso` é uma lista de `(courseid, [(assignid, nome, duedate, nosub)])`.

    `nosubmissions` é o campo que diz que a atividade NÃO aceita envio pelo
    e-Disciplinas (as provas presenciais que o professor cria só para ter data),
    e ele é a diferença entre uma consulta economizada e uma acusação falsa.
    """
    return {
        "courses": [
            {
                "id": courseid,
                "assignments": [
                    {
                        "id": assignid,
                        "cmid": 6000000 + assignid,
                        "name": nome,
                        "duedate": duedate,
                        "cutoffdate": 0,
                        "nosubmissions": nosub,
                        "introattachments": [],
                    }
                    for assignid, nome, duedate, nosub in assigns
                ],
            }
            for courseid, assigns in por_curso
        ],
        "warnings": (
            [
                {
                    "item": "module",
                    "itemid": 6372370,
                    "warningcode": "1",
                    "message": "Sem direito de acesso a este módulo",
                }
            ]
            if com_warning
            else []
        ),
    }
