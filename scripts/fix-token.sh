#!/usr/bin/env bash
# Conserta um MOODLE_TOKEN colado a mao torto no .env: se o valor for a URL ou o
# base64 do fluxo de launch (§8 do SPEC1.md), decodifica e grava so o wstoken de
# 32 hex. Idempotente. Nunca imprime o valor do token — so diagnostico de forma.
#
# Este e o caso "eu ja tinha editado o .env". Para o setup do zero, use
# `./scripts/token.sh`, que guia o fluxo inteiro e confirma o token contra a USP.
#
# A regra do formato NAO mora aqui: mora em scripts/_decodificar_token.py, que os
# dois scripts importam. Duas copias da mesma regra divergem na primeira vez que
# o Moodle mudar de versao.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

[ -f .env ] || { echo "sem .env — copie o .env.example ou rode ./scripts/token.sh" >&2; exit 1; }

"$PY" - <<'PY'
import re, sys
sys.path.insert(0, "scripts")
from _decodificar_token import RE_32HEX, decodificar

linhas = open(".env", encoding="utf-8").read().splitlines(keepends=True)
saida, mudou, diag = [], False, []

for l in linhas:
    if not re.match(r"^\s*MOODLE_TOKEN\s*=", l):
        saida.append(l); continue
    v = l.split("=", 1)[1].strip().strip("\"'")
    if RE_32HEX.fullmatch(v):
        diag.append("MOODLE_TOKEN ja estava em 32 hex — nada a fazer.")
        saida.append(l); continue
    # decodificar() reprova com mensagem legivel no stderr e SystemExit(1);
    # deixar subir e o comportamento certo — o .env fica como estava.
    _siteid, wstoken, partes = decodificar(v)
    saida.append(f"MOODLE_TOKEN={wstoken}\n")
    mudou = True
    diag.append(f"MOODLE_TOKEN: {len(v)} chars -> 32 hex. OK.")
    diag.append(f"(o base64 trazia {partes} partes; siteid e privatetoken descartados)")

if mudou:
    open(".env", "w", encoding="utf-8").writelines(saida)
print("\n".join(diag) or "MOODLE_TOKEN nao encontrado no .env")
PY
