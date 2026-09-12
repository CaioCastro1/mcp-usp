"""W1-W2: o `scripts/ws.sh` acha o `.env` onde ele realmente está.

O `.env` é gitignorado, então `git worktree add` não o copia: num worktree o
`./.env` não existe e o de verdade fica no checkout principal. O lado Python já
resolve isso (`usp_mcp.env.achar_env` sobe até o `.git` de verdade), e o
`token.sh`, o `fix-token.sh` e a checagem 0 do gate já perguntam a ele. O
`ws.sh` era o último `[ -f .env ]` sobrevivente — e ele é o chão da descoberta,
porque `capture.sh` e `userid.sh` chamam ele.

**Por que os dois testes não se substituem:** W1 prova que o `.env` do checkout
principal é encontrado de um worktree; W2 prova que, quando não há `.env` em
lugar nenhum, a mensagem legível continua lá. Sem W2, "achar sempre" e "fingir
que achou" passariam igual.

Nenhum dos dois toca a rede: o `ws.sh` é chamado **sem argumento**, e aí ele
morre no `$# -lt 1` (código 2) DEPOIS da checagem do token e ANTES do `curl`. O
código de saída é a condição — 2 é "o token chegou", 1 é "não chegou" — e não a
mensagem (§6 do `CONVENTIONS.md`).
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# Forma válida (32 hex) e valor obviamente sintético: o Invariante 3 vale também
# para o que se escreve em teste.
TOKEN_FALSO = "0" * 32


def _worktree_falso(tmp_path: pathlib.Path, *, com_env: bool) -> pathlib.Path:
    """Um checkout principal com `.git` e `.env`, e um worktree pendurado nele.

    Cópia e não symlink: `achar_env` faz `Path(__file__).resolve()`, que segue
    symlink, e um `usp_mcp/` apontando para o repositório de verdade acharia o
    `.env` de verdade — o teste ficaria verde sem exercitar nada.

    Só `__init__.py` e `env.py` são copiados. `ws.sh` não importa mais que isso,
    e copiar o pacote inteiro faria o teste pagar por cada arquivo novo dele.
    """
    principal = tmp_path / "principal"
    (principal / ".git").mkdir(parents=True)
    if com_env:
        (principal / ".env").write_text(f"MOODLE_TOKEN={TOKEN_FALSO}\n", encoding="utf-8")

    wt = principal / ".claude" / "worktrees" / "x"
    (wt / "usp_mcp").mkdir(parents=True)
    (wt / "scripts").mkdir()
    for nome in ("__init__.py", "env.py"):
        shutil.copy2(RAIZ / "usp_mcp" / nome, wt / "usp_mcp" / nome)
    shutil.copy2(RAIZ / "scripts" / "ws.sh", wt / "scripts" / "ws.sh")
    return wt


def _rodar_ws(wt: pathlib.Path) -> subprocess.CompletedProcess:
    """Chama o `ws.sh` do worktree falso, sem argumento e sem token herdado.

    A limpeza do ambiente não é detalhe: o `conftest` da suíte já carregou o
    `.env` de verdade para `os.environ`, e sem tirá-lo o processo filho herdaria
    um `MOODLE_TOKEN` que o teste não pôs lá. Os dois testes passariam sem o
    `ws.sh` ter achado arquivo nenhum.
    """
    ambiente = {k: v for k, v in os.environ.items() if k not in ("MOODLE_TOKEN", "MOODLE_URL")}
    return subprocess.run(
        ["bash", "scripts/ws.sh"],
        cwd=wt,
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_w1_o_ws_acha_o_env_do_checkout_principal_de_dentro_de_um_worktree(tmp_path):
    r = _rodar_ws(_worktree_falso(tmp_path, com_env=True))
    assert r.returncode == 2, (
        "esperava o ws.sh passar da checagem do token e morrer no 'uso:' (2). "
        f"Código {r.returncode}. Se for 1, ele não achou o .env do checkout "
        f"principal.\nstderr:\n{r.stderr}"
    )


def test_w2_sem_env_em_lugar_nenhum_o_ws_ainda_diz_a_cura(tmp_path):
    r = _rodar_ws(_worktree_falso(tmp_path, com_env=False))
    assert r.returncode == 1, (
        f"sem .env nenhum o ws.sh tem que recusar com 1, não {r.returncode}.\n"
        f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )
    assert "MOODLE_TOKEN" in r.stderr and ".env" in r.stderr, (
        f"a recusa tem que dizer o que falta e a cura (Invariante 6).\nstderr:\n{r.stderr}"
    )
