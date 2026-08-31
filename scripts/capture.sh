#!/usr/bin/env bash
# Captura uma chamada para fixtures/moodle/raw/<nome>.json e imprime SÓ a medida:
# bytes, estimativa de tokens e forma do topo. Nunca despeja o payload.
# Existe para que ler uma resposta de 251k tokens seja impossível por acidente.
set -euo pipefail
nome="$1"; shift
dest="fixtures/moodle/raw/${nome}.json"
mkdir -p fixtures/moodle/raw
./scripts/ws.sh "$@" > "$dest"
python3 - "$dest" <<'PY'
import json,os,sys
p=sys.argv[1]; b=os.path.getsize(p)
try: d=json.load(open(p))
except Exception as e:
    print(f'{p}: {b} B — NÃO É JSON: {open(p).read()[:120]}'); raise SystemExit
if isinstance(d,dict) and 'exception' in d:
    print(f'{p}: ERRO {d.get("errorcode")} — {d.get("message","")[:90]}'); raise SystemExit
forma = f'lista[{len(d)}]' if isinstance(d,list) else 'obj{' + ','.join(list(d)[:6]) + '}'
print(f'{p}: {b} B | ~{b//4} tokens | {forma}')
if b > 200_000: print('  !! acima de 200 kB — não ler cru em hipótese nenhuma')
PY
