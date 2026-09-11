"""Camada 1 — a decodificação do payload de `launch.php`.

Nenhum token real entra aqui, nem higienizado: o payload é montado no próprio
teste, com um `wstoken` sintético que tem a FORMA de 32 hex e não é credencial
de ninguém. Testar decodificação com token real seria gravar a credencial num
arquivo rastreado (Invariante 3) para verificar um regex.

O que estes testes alcançam é o §6 do desenho de 10/09: a unidade que os dois
scripts compartilham. O que eles NÃO alcançam — abrir navegador, ler clipboard,
escrever no `.env`, falar com a USP — está dito em voz alta no §7 do desenho, e
a regra 11 do `CLAUDE.md` é o motivo de dizer.
"""
from __future__ import annotations

import base64
import subprocess
import sys

import pytest

from tests.moodle.conftest import RAIZ

pytestmark = pytest.mark.politica

HELPER = RAIZ / "scripts" / "_decodificar_token.py"

# Sintéticos. A forma é a do §1.3 do SPEC1.md; o conteúdo não abre nada.
SITEID = "0" * 32
WSTOKEN = "ab12cd34" * 4  # 32 hex
PRIVATE = "ffffffffffffffffffffffffffffffff"


def payload(*partes: str) -> str:
    """base64 de `a:::b:::c`, como o Moodle emite."""
    return base64.b64encode(":::".join(partes).encode()).decode()


def decodificar(entrada: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER)],
        input=entrada,
        capture_output=True,
        text=True,
        cwd=RAIZ,
    )


def campos(saida: str) -> dict[str, str]:
    return dict(
        linha.split("=", 1) for linha in saida.strip().splitlines() if "=" in linha
    )


# --------------------------------------------------------------- o caminho bom


def test_extrai_o_wstoken_de_url_completa():
    """T-tok-1 — o que a pessoa copia do DevTools é a URL inteira."""
    r = decodificar(f"moodlemobile://token={payload(SITEID, WSTOKEN, PRIVATE)}")
    assert r.returncode == 0, r.stderr
    assert campos(r.stdout)["wstoken"] == WSTOKEN


def test_extrai_o_wstoken_de_base64_nu():
    """T-tok-2 — quem já sabe o fluxo cola só o base64."""
    r = decodificar(payload(SITEID, WSTOKEN, PRIVATE))
    assert r.returncode == 0, r.stderr
    assert campos(r.stdout)["wstoken"] == WSTOKEN


def test_devolve_o_siteid_para_a_conferencia_do_passaporte():
    """T-tok-3 — o §3.1 do desenho confere md5(wwwroot+passport) contra ele."""
    r = decodificar(payload(SITEID, WSTOKEN, PRIVATE))
    assert campos(r.stdout)["siteid"] == SITEID


def test_tolera_espaco_e_quebra_de_linha_ao_redor():
    """T-tok-4 — clipboard traz sujeira; ela não é erro de forma."""
    r = decodificar(f"  moodlemobile://token={payload(SITEID, WSTOKEN, PRIVATE)}/ \n")
    assert r.returncode == 0, r.stderr
    assert campos(r.stdout)["wstoken"] == WSTOKEN


# ------------------------------------------------------- o privatetoken não sai


def test_o_privatetoken_nao_aparece_na_saida():
    """T-tok-5 — §4 do desenho, e a asserção é sobre a saída, não a intenção.

    `tool_mobile_get_autologin_key` está no bloqueio permanente do §2.2. O
    terceiro campo do payload é o que a habilita: ele é decodificado por força
    do formato e tem de morrer aqui dentro.
    """
    r = decodificar(payload(SITEID, WSTOKEN, PRIVATE))
    assert PRIVATE not in r.stdout
    assert PRIVATE not in r.stderr


def test_a_saida_tem_so_os_campos_declarados():
    """T-tok-6 — um campo novo na saída é um vazamento em potencial."""
    r = decodificar(payload(SITEID, WSTOKEN, PRIVATE))
    assert set(campos(r.stdout)) == {"siteid", "wstoken", "partes"}


# ------------------------------------------------------------ a forma reprovada


@pytest.mark.parametrize(
    "entrada, porque",
    [
        ("não é base64 de jeito nenhum ###", "lixo colado"),
        ("", "nada colado"),
        (base64.b64encode(b"sozinho").decode(), "payload de uma parte"),
        (payload(SITEID, "curto", PRIVATE), "wstoken fora de 32 hex"),
        (payload(SITEID, WSTOKEN.upper(), PRIVATE), "wstoken em maiúscula"),
    ],
)
def test_forma_errada_reprova_com_mensagem(entrada, porque):
    """T-tok-7 — Invariante 6: erro legível, código ≠ 0, nada de stack trace."""
    r = decodificar(entrada)
    assert r.returncode != 0, f"passou com {porque}"
    assert r.stderr.strip(), f"reprovou calado com {porque}"
    assert "Traceback" not in r.stderr, f"cru na cara do usuário com {porque}"
    assert not campos(r.stdout), f"emitiu campo com {porque}"


def test_base64_minusculizado_reprova():
    """T-tok-8 — a armadilha do Chrome do §1.3.

    Com `urlscheme=http` o base64 cai na posição de host e o Chrome normaliza
    host para minúsculas. base64 é sensível a caixa: o resultado é um token
    corrompido com a forma certa. Reprovar é o comportamento correto; gravar
    um token de 32 hex que não autentica é o pior desfecho possível, porque
    parece sucesso.
    """
    bom = payload(SITEID, WSTOKEN, PRIVATE)
    r = decodificar(bom.lower())
    if r.returncode == 0:
        assert campos(r.stdout)["wstoken"] != WSTOKEN, (
            "minusculizar o base64 não deveria devolver o token intacto"
        )
    else:
        assert r.stderr.strip()


def test_nunca_ecoa_a_entrada_inteira_no_erro():
    """T-tok-9 — a entrada É a credencial; diagnóstico é forma, não conteúdo."""
    entrada = payload(SITEID, WSTOKEN, "x")[:-4] + "!!!!"
    r = decodificar(entrada)
    assert entrada not in r.stderr
    assert entrada not in r.stdout


# ---------------------------------------------- o fix-token.sh usa o mesmo helper

# O risco real da extracao do §6 do desenho nao e a decodificacao — e a fiacao:
# o fix-token.sh importa o helper com `sys.path.insert(0, "scripts")`, e um
# import quebrado passaria calado pela suite se ninguem rodasse o script. Estes
# testes rodam o script de verdade, num .env de mentira, num diretorio de
# mentira. Nunca no .env do repo: um teste que escreve no .env do dono e um
# teste que pode gravar credencial de teste na credencial de verdade.


@pytest.fixture
def raiz_falsa(tmp_path):
    """Uma raiz com scripts/, usp_mcp/ e .env proprios — os scripts fazem cd para ca.

    O `usp_mcp/env.py` vem junto de proposito: desde 11/09 o `fix-token.sh`
    localiza o `.env` por `achar_env`, e nao por `./.env`. Um fake sem ele
    testaria um script diferente do que esta no repo.

    `tmp_path` nao tem `.git` em pai nenhum, entao `achar_env` fica na raiz
    falsa e nunca alcanca o `.env` de verdade de quem roda a suite.
    """
    (tmp_path / "scripts").mkdir()
    for nome in ("fix-token.sh", "_decodificar_token.py"):
        destino = tmp_path / "scripts" / nome
        destino.write_bytes((RAIZ / "scripts" / nome).read_bytes())
        destino.chmod(0o755)
    (tmp_path / "usp_mcp").mkdir()
    for nome in ("__init__.py", "env.py"):
        (tmp_path / "usp_mcp" / nome).write_bytes((RAIZ / "usp_mcp" / nome).read_bytes())
    return tmp_path


def fix_token(raiz):
    return subprocess.run(
        ["bash", str(raiz / "scripts" / "fix-token.sh")],
        capture_output=True,
        text=True,
        cwd=raiz,
    )


def test_fix_token_normaliza_base64_colado_a_mao(raiz_falsa):
    """T-tok-10 — o caso que o fix-token.sh existe para consertar."""
    env = raiz_falsa / ".env"
    env.write_text(
        f"MOODLE_URL=https://exemplo.invalid\n"
        f"MOODLE_TOKEN=moodlemobile://token={payload(SITEID, WSTOKEN, PRIVATE)}\n"
        f"USP_MCP_ALLOW_WRITES=0\n",
        encoding="utf-8",
    )
    r = fix_token(raiz_falsa)
    assert r.returncode == 0, r.stderr
    depois = env.read_text(encoding="utf-8")
    assert f"MOODLE_TOKEN={WSTOKEN}\n" in depois
    assert PRIVATE not in depois, "o privatetoken chegou ao disco"
    assert "USP_MCP_ALLOW_WRITES=0" in depois, "comeu outra linha do .env"
    assert WSTOKEN not in r.stdout + r.stderr, "ecoou o token"


def test_fix_token_e_idempotente(raiz_falsa):
    """T-tok-11 — rodar duas vezes não estraga o que já estava certo."""
    env = raiz_falsa / ".env"
    env.write_text(f"MOODLE_TOKEN={WSTOKEN}\n", encoding="utf-8")
    r = fix_token(raiz_falsa)
    assert r.returncode == 0, r.stderr
    assert env.read_text(encoding="utf-8") == f"MOODLE_TOKEN={WSTOKEN}\n"
    assert "nada a fazer" in r.stdout


def test_fix_token_com_forma_errada_nao_toca_o_env(raiz_falsa):
    """T-tok-12 — reprovar deixando o .env intacto, não meio escrito."""
    env = raiz_falsa / ".env"
    antes = "MOODLE_TOKEN=isso-nao-e-base64-###\nOUTRA=1\n"
    env.write_text(antes, encoding="utf-8")
    r = fix_token(raiz_falsa)
    assert r.returncode != 0
    assert r.stderr.strip()
    assert env.read_text(encoding="utf-8") == antes


def test_fix_token_sem_env_diz_o_que_fazer(raiz_falsa):
    """T-tok-13 — Invariante 6: a mensagem aponta a cura, não só a falta."""
    r = fix_token(raiz_falsa)
    assert r.returncode != 0
    assert "token.sh" in r.stderr or ".env.example" in r.stderr


def test_fix_token_acha_o_env_do_checkout_e_nao_o_do_worktree(tmp_path):
    """T-tok-14 — o `.env` do checkout principal, visto de dentro de um worktree.

    O `.env` e gitignorado, entao `git worktree add` nao o copia: um worktree
    novo nao tem o dele, e o de verdade esta no checkout que tem o `.git`
    diretorio. Um script que so olhasse `./.env` consertaria o arquivo errado —
    ou, pior, CRIARIA um `./.env` no worktree, que `achar_env` passaria a
    preferir, sombreando o verdadeiro em silencio. Mesmo defeito que a primeira
    versao do gate teve (§4 do CONVENTIONS.md).

    A montagem imita a real: `.git` DIRETORIO no principal (num worktree o
    `.git` e arquivo, e e assim que `achar_env` distingue os dois).
    """
    principal = tmp_path / "principal"
    (principal / ".git").mkdir(parents=True)
    env_verdadeiro = principal / ".env"
    env_verdadeiro.write_text(
        f"MOODLE_TOKEN=moodlemobile://token={payload(SITEID, WSTOKEN, PRIVATE)}\nOUTRA=1\n",
        encoding="utf-8",
    )

    wt = principal / ".claude" / "worktrees" / "algum"
    (wt / "scripts").mkdir(parents=True)
    (wt / "usp_mcp").mkdir()
    for nome in ("fix-token.sh", "_decodificar_token.py"):
        d = wt / "scripts" / nome
        d.write_bytes((RAIZ / "scripts" / nome).read_bytes())
        d.chmod(0o755)
    for nome in ("__init__.py", "env.py"):
        (wt / "usp_mcp" / nome).write_bytes((RAIZ / "usp_mcp" / nome).read_bytes())
    assert not (wt / ".env").exists(), "montagem errada: o worktree nao pode ter .env"

    r = subprocess.run(
        ["bash", str(wt / "scripts" / "fix-token.sh")],
        capture_output=True, text=True, cwd=wt,
    )
    assert r.returncode == 0, r.stderr
    assert env_verdadeiro.read_text(encoding="utf-8") == f"MOODLE_TOKEN={WSTOKEN}\nOUTRA=1\n"
    assert not (wt / ".env").exists(), "criou um .env no worktree, sombreando o verdadeiro"
    assert WSTOKEN not in r.stdout + r.stderr, "ecoou o token"
