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

# Nada do corpo da requisição vai pelo argv do `curl`: tudo entra por `curl -K -`,
# que lê a configuração do stdin. Argumento de processo não é privado — enquanto
# o `curl` roda, qualquer processo da máquina lê o argv dele com `ps aux` —, e
# aqui passava `--data-urlencode "wstoken=$MOODLE_TOKEN"`. O token é credencial
# pessoal do dono (Invariante 4) e cada chamada feita com ele fica no log da
# conta dele na USP; o Invariante 3 diz que esse valor não se lê, não se imprime
# e não se ecoa, e argv é eco. O passo 6 do `token.sh` já tinha resolvido isto
# pelo mesmo caminho: uma cura no repositório, não duas.
#
# POR QUE TUDO E NÃO SÓ O TOKEN. `wsfunction` e os parâmetros do usuário não são
# segredo, e tirar só o token teria funcionado. Duas rotas para montar o mesmo
# corpo é que não compensam: são dois lugares para errar o escape, e a regra
# vira "o token sai, o resto fica", que ninguém confere de fora sem ler o script
# inteiro. Com uma rota só, a invariante é mecânica e verificável — nenhum
# `--data-urlencode` no argv — e é exatamente essa que o
# `tests/test_token_fora_do_argv.py` afirma. O bônus é que um parâmetro que por
# acaso carregue algo sensível (ninguém prometeu que não) também não vaza.
#
# A URL fica no argv de propósito: ela é pública, está no `.env.example`, e é o
# que faz o processo ser reconhecível no `ps` de quem está depurando.

# O arquivo de configuração do `curl` NÃO é o shell. Dentro de aspas duplas ele
# desfaz `\\`, `\"`, `\t`, `\n`, `\r` e `\v`, e qualquer outra barra invertida
# some levando o caractere seguinte junto. Como este script repassa parâmetro
# arbitrário do usuário, `caminho=C:\temp` e `nota=ele disse "oi"` montariam uma
# linha de configuração diferente da pedida — e o `curl` obedeceria a ela sem
# reclamar. Chamada silenciosamente errada é o pior resultado possível
# (Invariante 6), então escapamos os seis antes de escrever. Quebra de linha
# vira `\n` pela mesma razão e mais uma: solta, ela terminaria a linha no meio
# das aspas.
escapar_para_config() {
  local v=$1
  v=${v//\\/\\\\}
  v=${v//\"/\\\"}
  v=${v//$'\t'/\\t}
  v=${v//$'\n'/\\n}
  v=${v//$'\r'/\\r}
  v=${v//$'\v'/\\v}
  printf '%s' "$v"
}

parametro() { printf 'data-urlencode = "%s"\n' "$(escapar_para_config "$1")"; }

{
  parametro "wstoken=$MOODLE_TOKEN"
  parametro "wsfunction=$fn"
  parametro "moodlewsrestformat=json"
  for kv in "$@"; do parametro "$kv"; done
} | curl -sS -K - "$MOODLE_URL/webservice/rest/server.php"
