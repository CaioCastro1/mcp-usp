#!/usr/bin/env bash
# Chamador do web service do Moodle — é o §8 do SPEC1.md em arquivo, nada além.
#
# Uso:  ./scripts/ws.sh <funcao> [param=valor ...]
#       ./scripts/ws.sh core_webservice_get_site_info
#       ./scripts/ws.sh core_enrol_get_users_courses "userid=$MOODLE_USERID"
#
# Regra de ouro (§3.1): uma função por invocação, escolhida à mão. Este script
# não itera sobre lista de funções de propósito — um sweep sobre as ~400 chega
# em submit_for_grading e start_attempt com o token do dono.
#
# Erro cru vai para stdout sem filtro (Invariante 6). Não engole nada.

set -euo pipefail
# Não basta olhar `./.env`: ele é gitignorado, então `git worktree add` não o
# copia e um worktree não tem o dele — o de verdade está no checkout principal,
# e `usp_mcp.env.achar_env` sobe até o `.git` de verdade para achá-lo. É a mesma
# cura que o `token.sh`, o `fix-token.sh` e a checagem 0 do gate já usam; aqui o
# defeito doía calado, porque o erro mandava "copie .env.example para .env" para
# quem já tinha o `.env` preenchido no lugar certo (W1).
#
# Falha de import não é engolida: sem poder perguntar, seguir em frente daria de
# novo a cura errada, e silêncio perde para erro legível (Invariante 6).
PY_BIN=".venv/bin/python"
[ -x "$PY_BIN" ] || PY_BIN="python3"
if ! ENV_FILE=$(PYTHONPATH="$(pwd)" "$PY_BIN" -c \
     'from usp_mcp.env import achar_env; a = achar_env(); print(a or "")' 2>&1); then
  echo "não consegui localizar o .env — usp_mcp.env não importou:" >&2
  printf '%s\n' "$ENV_FILE" | sed 's/^/  /' >&2
  exit 1
fi
[ -n "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

: "${MOODLE_URL:=https://edisciplinas.usp.br}"

if [ -z "${MOODLE_TOKEN:-}" ]; then
  echo "MOODLE_TOKEN vazio. Copie .env.example para .env e preencha." >&2
  echo "Como obter o token: §8 do SPEC1.md." >&2
  exit 1
fi

if [ $# -lt 1 ]; then
  echo "uso: $0 <funcao> [param=valor ...]" >&2
  exit 2
fi

fn="$1"; shift
args=(); for kv in "$@"; do args+=(--data-urlencode "$kv"); done

curl -sS "$MOODLE_URL/webservice/rest/server.php" \
  --data-urlencode "wstoken=$MOODLE_TOKEN" \
  --data-urlencode "wsfunction=$fn" \
  --data-urlencode "moodlewsrestformat=json" \
  ${args[@]+"${args[@]}"}
