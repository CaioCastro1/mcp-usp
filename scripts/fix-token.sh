#!/usr/bin/env bash
# Normaliza MOODLE_TOKEN no .env: se o valor for a URL/base64 do fluxo de launch
# (§8 do SPEC1.md), decodifica e grava só o wstoken de 32 hex. Idempotente.
# Nunca imprime o valor do token — só diagnóstico de forma.
set -euo pipefail
[ -f .env ] || { echo "sem .env" >&2; exit 1; }
python3 - <<'PY'
import re, base64, sys, io

linhas = open('.env', encoding='utf-8').read().splitlines(keepends=True)
saida, mudou, diag = [], False, []

for l in linhas:
    if not l.startswith('MOODLE_TOKEN='):
        saida.append(l); continue
    v = l.split('=', 1)[1].strip().strip('"\'')
    if re.fullmatch(r'[a-f0-9]{32}', v):
        diag.append('MOODLE_TOKEN já estava em 32 hex — nada a fazer.')
        saida.append(l); continue
    b = v.split('token=', 1)[1] if 'token=' in v else v
    b = re.sub(r'[^A-Za-z0-9+/=_-]', '', b.rstrip('/')).replace('-', '+').replace('_', '/')
    try:
        partes = base64.b64decode(b + '=' * (-len(b) % 4)).decode().split(':::')
    except Exception as e:
        diag.append(f'ERRO: não decodifica como base64 ({e}). Valor tem {len(v)} chars.')
        saida.append(l); continue
    if len(partes) < 2 or not re.fullmatch(r'[a-f0-9]{32}', partes[1]):
        diag.append(f'ERRO: decodificou em {len(partes)} parte(s), '
                    f'parte[1] não é 32 hex. Refaça o §8 do SPEC1.md.')
        saida.append(l); continue
    saida.append(f'MOODLE_TOKEN={partes[1]}\n')
    mudou = True
    diag.append(f'MOODLE_TOKEN: {len(v)} chars -> 32 hex. OK.')
    diag.append(f'(o base64 trazia {len(partes)} partes; siteid e privatetoken descartados)')

if mudou:
    open('.env', 'w', encoding='utf-8').writelines(saida)
print('\n'.join(diag) or 'MOODLE_TOKEN não encontrado no .env')
PY
