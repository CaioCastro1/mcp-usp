"""Carrega o `.env` para `os.environ` — o equivalente Python do
`set -a && . ./.env && set +a` da linha 15 do `scripts/ws.sh`.

Isto existe porque nada no lado Python fazia: só os scripts bash sourceavam o
arquivo. O efeito era um erro legível apontando a cura errada — a suíte dizia
"MOODLE_TOKEN está vazio, copie .env.example para .env" para quem já tinha o
`.env` preenchido, porque o valor nunca chegava a `os.environ` (§9, 31/08/2026).

Mora em `usp_mcp/` e não em `tests/` porque os dois lados precisam: a suíte e o
entrypoint stdio do Moodle. Decisão de 31/08/2026 — o `.env` (§8, gitignorado)
continua sendo a única casa do token, e o `.mcp.json` vai para o git sem segredo
nenhum. A alternativa descartada era o token vir do bloco `env` da configuração
do cliente MCP, que duplicaria o segredo num arquivo fácil de commitar por
acidente (Invariante 3).

Parser de stdlib de propósito: `python-dotenv` seria a primeira dependência de
runtime do projeto, e o formato aqui é `CHAVE=valor` com comentário.
"""
from __future__ import annotations

import os
from pathlib import Path

# usp_mcp/env.py → sobe dois níveis até a raiz do checkout (ou do worktree).
_RAIZ = Path(__file__).resolve().parents[1]


def achar_env(raiz: Path | None = None) -> Path | None:
    """Onde está o `.env`, ou None se não estiver em lugar nenhum.

    O `.env` é gitignorado, então `git worktree add` não o copia e um worktree
    novo não tem o dele — mesma situação do cru do §3.3. Procura na raiz e, se
    não achar, sobe até o checkout que tem o `.git` de verdade (num worktree o
    `.git` é arquivo, não diretório).

    Devolve None em vez de levantar: "não tem `.env`" e "tem `.env` sem a
    chave" pedem mensagens diferentes, e quem chama é que sabe qual dar
    (Invariante 6).
    """
    raiz = raiz if raiz is not None else _RAIZ
    candidatos = [raiz / ".env"]
    for pai in raiz.parents:
        if (pai / ".git").is_dir():
            candidatos.append(pai / ".env")
            break
    for c in candidatos:
        if c.is_file():
            return c
    return None


def carregar_env(raiz: Path | None = None) -> Path | None:
    """Põe o `.env` em `os.environ` e devolve o arquivo usado (ou None).

    `setdefault`, e não atribuição: **quem já está no ambiente ganha**. É o que
    mantém `USP_MCP_LIVE=1 pytest` valendo mesmo se o `.env` disser o
    contrário, o que deixa o bloco `env` de um cliente MCP sobrescrever o
    arquivo, e o que impede este carregador de ligar a camada live por baixo de
    quem não pediu.

    Nenhum valor é impresso, nem em erro (Invariante 3): linha malformada é
    ignorada em silêncio em vez de ecoada.
    """
    arquivo = achar_env(raiz)
    if arquivo is None:
        return None
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        # `export CHAVE=valor` é válido num arquivo feito para ser sourceado.
        chave = chave.removeprefix("export ").strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        if chave:
            os.environ.setdefault(chave, valor)
    return arquivo
