#!/usr/bin/env bash
# Deriva o MOODLE_USERID do token, via core_webservice_get_site_info.
# Cacheia em .cache/userid porque site_info custa ~7.800 tokens e o valor não muda
# enquanto o token for o mesmo. `--refresh` força nova chamada.
set -euo pipefail
mkdir -p .cache
if [ "${1:-}" != "--refresh" ] && [ -s .cache/userid ]; then
  cat .cache/userid; exit 0
fi
resp=$(./scripts/ws.sh core_webservice_get_site_info)
uid=$(printf '%s' "$resp" | python3 -c '
import json,sys
d=json.load(sys.stdin)
if "exception" in d:
    sys.stderr.write("erro do Moodle: %s\n" % d.get("errorcode","?")); sys.exit(1)
uid=d.get("userid")
if not uid: sys.stderr.write("site_info nao trouxe userid\n"); sys.exit(1)
print(uid)')
printf '%s\n' "$uid" > .cache/userid
printf '%s\n' "$uid"
