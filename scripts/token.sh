#!/usr/bin/env bash
# Obtem o MOODLE_TOKEN e grava no .env — o §8 do SPEC1.md virado chamador.
#
# Uso:  ./scripts/token.sh              # guiado, interativo
#       pbpaste | ./scripts/token.sh    # se voce ja copiou a URL do redirect
#       ./scripts/token.sh --sobrescrever   # trocar token que ja funciona, sem perguntar
#
# Sete passos, na ordem em que estao no desenho de 10/09/2026
# (docs/superpowers/specs/2026-09-10-script-token-moodle-design.md):
#
#   1. prepara o .env            5. decodifica EM MEMORIA
#   2. gera um passaporte        6. confirma o token contra a USP (1 chamada)
#   3. abre o launch.php         7. grava so os 32 hex no .env
#   4. recebe sem ecoar
#
# Tres coisas que este script nao faz, de proposito:
#
#   - Nunca imprime o valor do token, nem parcial (Invariante 3). O diagnostico
#     fala de forma — quantos caracteres, quantas partes, confere ou nao.
#   - Nunca grava o base64 cru no disco. Ele carrega o `privatetoken`, que
#     habilita `tool_mobile_get_autologin_key` (bloqueio permanente do §2.2) —
#     decodificar antes de escrever e o que impede o valor de existir em arquivo.
#   - Nunca passa o token em argv. `ps aux` e legivel por qualquer processo do
#     usuario; o passo 6 manda o campo por `curl -K -`, que le do stdin. Medido
#     em 10/09/2026 contra um servidor local: o campo chega no corpo do POST.
#
# Nao renova token expirado sem navegador: `launch.php` autentica por sessao, e
# o §1.3 registra que senha nao serve (SSO). Nao trata o token de `Attendance`.

set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

FN="core_webservice_get_site_info"

# --sobrescrever: trocar um token que ja funciona sem a pergunta do passo 1.
# Existe porque `pbpaste | ./scripts/token.sh` nao tem terminal para perguntar.
sobrescrever=0
for arg in "$@"; do
  case "$arg" in
    --sobrescrever) sobrescrever=1 ;;
    -h|--ajuda|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "opcao desconhecida: $arg (use --ajuda)" >&2; exit 2 ;;
  esac
done

titulo() { printf '\n\033[1m%s\033[0m\n' "$1"; }
nota()   { printf '   %s\n' "$1"; }
aviso()  { printf '   \033[33m! %s\033[0m\n' "$1"; }

# ------------------------------------------------------------- 1. prepara o .env
titulo "1/7  .env"
if [ ! -f .env ]; then
  [ -f .env.example ] || { echo "sem .env e sem .env.example — repo incompleto" >&2; exit 1; }
  cp .env.example .env
  nota "criei .env a partir do .env.example (ele esta no gitignore)"
else
  nota ".env ja existe"
fi

set -a; . ./.env; set +a
: "${MOODLE_URL:=https://edisciplinas.usp.br}"
nota "MOODLE_URL=$MOODLE_URL"

# Um token que ja funciona nao se sobrescreve calado: o antigo CONTINUA ativo em
# managetoken.php, e trocar sem avisar deixa dois vivos na conta e nenhum
# registro de qual esta em uso. A lista de la mostra o NOME (16 chars), nao o valor.
if grep -qE '^MOODLE_TOKEN=[a-f0-9]{32}$' .env; then
  aviso "o .env ja tem um MOODLE_TOKEN com forma valida."
  nota "O token antigo NAO e revogado por isto — revogue em:"
  nota "  $MOODLE_URL/user/managetoken.php  ->  Reconfigurar"
  if [ "$sobrescrever" = "1" ]; then
    nota "--sobrescrever passado: seguindo."
  elif [ -t 0 ] && [ -r /dev/tty ]; then
    printf '   Sobrescrever? [s/N] '
    read -r resp < /dev/tty
    case "$resp" in [sSyY]*) ;; *) echo "   abortado, nada mudou."; exit 0 ;; esac
  else
    # Sem terminal nao ha como perguntar, e sobrescrever calado e exatamente o
    # que esta confirmacao existe para impedir. Reprovar dizendo a cura.
    echo "   Sem terminal para confirmar (voce pipou algo para o script)." >&2
    echo "   Rode sem pipe, ou passe --sobrescrever se e isso que voce quer." >&2
    exit 1
  fi
fi

# --------------------------------------------------------- 2. gera o passaporte
# O §8 usa `passport=1234` fixo. Um passaporte proprio permite conferir o eco:
# o `siteid` do payload e md5(wwwroot + passaporte), entao um payload de outra
# tentativa ou de outra sessao aparece. Ver §3.1 do desenho — confere e avisa,
# NAO bloqueia: a formula esta recordada, nao medida contra o e-Disciplinas.
passaporte=$("$PY" -c 'import secrets; print(secrets.randbelow(9*10**9) + 10**9)')
url="$MOODLE_URL/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=$passaporte&urlscheme=moodlemobile"

# ------------------------------------------------------------ 3. abre o launch
titulo "2/7  abra esta URL no navegador que esta LOGADO na Senha Unica"
printf '\n   %s\n\n' "$url"
nota "ANTES de abrir: DevTools (Cmd+Opt+I) -> aba Network, deixe aberta."
nota "Ao abrir, o Moodle redireciona para 'moodlemobile://token=<base64>'."
nota "Nenhum app atende esse esquema, entao o navegador bloqueia — e a linha"
nota "bloqueada na aba Network e exatamente o que voce precisa copiar."
nota ""
nota "Nao troque por urlscheme=http: nessa forma o base64 cai na posicao de"
nota "host da URL, o Chrome minusculiza host, e base64 e sensivel a caixa —"
nota "o token chega corrompido com a forma certa (§1.3 do SPEC1.md)."

if [ -t 0 ]; then
  printf '\n   Enter para eu abrir no navegador padrao (ou Ctrl+C para colar a mao): '
  read -r _ < /dev/tty
  if command -v open >/dev/null 2>&1; then open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$url"
  else nota "sem 'open'/'xdg-open' — abra a URL acima a mao"
  fi
fi

# ------------------------------------------------------ 4. recebe sem ecoar
titulo "3/7  cole a URL do redirect"
valor=""
if [ -t 0 ]; then
  nota "Nada aparece na tela enquanto voce cola — o valor e a credencial e nao"
  nota "deve ficar no scrollback do terminal."
  printf '\n   Cole e aperte Enter (ou Enter direto para eu ler do clipboard): '
  IFS= read -rs valor < /dev/tty || true
  printf '\n'
  if [ -z "$valor" ]; then
    if command -v pbpaste >/dev/null 2>&1; then valor=$(pbpaste)
    elif command -v wl-paste >/dev/null 2>&1; then valor=$(wl-paste)
    elif command -v xclip >/dev/null 2>&1; then valor=$(xclip -selection clipboard -o)
    else nota "sem pbpaste/wl-paste/xclip nesta maquina"
    fi
    [ -n "$valor" ] && nota "li do clipboard ($(printf '%s' "$valor" | wc -c | tr -d ' ') bytes)"
  fi
else
  valor=$(cat)   # pbpaste | ./scripts/token.sh
  nota "li do stdin ($(printf '%s' "$valor" | wc -c | tr -d ' ') bytes)"
fi

# ------------------------------------------------- 5. decodifica em memoria
titulo "4/7  decodifica"
# A regra do formato mora em _decodificar_token.py, em um lugar so — o
# fix-token.sh usa o mesmo helper. Ele imprime siteid/wstoken/partes e NUNCA o
# privatetoken; se a forma estiver errada, ele mesmo diz o que fazer no stderr.
if ! campos=$(printf '%s' "$valor" | "$PY" scripts/_decodificar_token.py); then
  exit 1
fi
unset valor

siteid=$(printf '%s\n' "$campos"  | sed -n 's/^siteid=//p')
wstoken=$(printf '%s\n' "$campos" | sed -n 's/^wstoken=//p')
partes=$(printf '%s\n' "$campos"  | sed -n 's/^partes=//p')
nota "payload trazia $partes parte(s); wstoken tem forma de 32 hex. OK."
[ "$partes" -ge 3 ] && nota "privatetoken descartado sem sair do decodificador (§2.2)."

titulo "5/7  confere o passaporte"
esperado=$("$PY" -c 'import hashlib,sys; print(hashlib.md5((sys.argv[1]+sys.argv[2]).encode()).hexdigest())' \
  "$MOODLE_URL" "$passaporte")
if [ "$siteid" = "$esperado" ]; then
  nota "confere: o payload responde a ESTA invocacao."
else
  aviso "nao confere com md5(wwwroot+passaporte)."
  nota "Isto e AVISO, nao bloqueio: a formula esta recordada e nao medida contra"
  nota "o e-Disciplinas (§1.4). Duas leituras possiveis, e o passo 6 desempata:"
  nota "  - se o passo 6 autenticar, o token esta bom e a formula e que esta"
  nota "    errada aqui (wwwroot com/sem barra, com/sem www). Registre no §9."
  nota "  - se o passo 6 falhar, voce colou um payload de outra tentativa."
fi

# --------------------------------------------- 6. confirma contra a USP (1 chamada)
titulo "6/7  confirma contra a USP — UMA chamada ($FN)"
nota "Esta chamada fica no log da sua conta. E ela que faz 'gravei o token'"
nota "significar 'o token funciona' — sem ela, voce descobre no primeiro uso."
# O token vai por `curl -K -` (stdin), nunca em argv: ps aux e legivel.
# Verificar ANTES de gravar e o que impede o .env de guardar token que nao autentica.
if ! resp=$(printf 'data-urlencode = "wstoken=%s"\n' "$wstoken" | curl -sS -K - \
      "$MOODLE_URL/webservice/rest/server.php" \
      --data-urlencode "wsfunction=$FN" \
      --data-urlencode "moodlewsrestformat=json"); then
  echo "   curl falhou — a rede nao respondeu. O .env NAO foi tocado." >&2
  exit 1
fi

# Erro do Moodle chega como HTTP 200 com errorcode no corpo (§9, 01/09/2026):
# quem checar status entrega JSON de erro achando que e sucesso.
if ! userid=$(printf '%s' "$resp" | "$PY" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.stderr.write("   a resposta nao e JSON. Cru, sem filtro (Invariante 6):\n")
    sys.exit(1)
if "exception" in d or "errorcode" in d:
    sys.stderr.write("   o Moodle recusou: %s / %s\n"
                     % (d.get("errorcode", "?"), d.get("message", "?")))
    sys.exit(1)
uid = d.get("userid")
if not uid:
    sys.stderr.write("   autenticou mas nao trouxe userid — forma inesperada.\n")
    sys.exit(1)
for campo in ("sitename", "fullname", "username", "release"):
    if d.get(campo):
        sys.stderr.write("   %-9s %s\n" % (campo + ":", d[campo]))
print(uid)'); then
  echo "   O .env NAO foi tocado: o token nao autentica e nao vale gravar." >&2
  echo "   Refaca do passo 2 — o mais comum e a sessao do navegador ter expirado." >&2
  exit 1
fi
nota "userid derivado do proprio token (nunca configurado a mao — §2 do CONVENTIONS)."

# -------------------------------------------------------- 7. grava so os 32 hex
titulo "7/7  grava no .env"
# O token vai por env var, nao por argv, pelo mesmo motivo do passo 6.
WSTOKEN="$wstoken" "$PY" - <<'PYW'
import os, re
tok = os.environ["WSTOKEN"]
linhas = open(".env", encoding="utf-8").read().splitlines(keepends=True)
saida, achou = [], False
for l in linhas:
    if re.match(r"^\s*MOODLE_TOKEN\s*=", l):
        saida.append(f"MOODLE_TOKEN={tok}\n"); achou = True
    else:
        saida.append(l)
if not achou:
    if saida and not saida[-1].endswith("\n"):
        saida.append("\n")
    saida.append(f"MOODLE_TOKEN={tok}\n")
open(".env", "w", encoding="utf-8").writelines(saida)
print("   MOODLE_TOKEN gravado" + ("" if achou else " (linha nova)") + ". Valor nao impresso.")
PYW

mkdir -p .cache
printf '%s\n' "$userid" > .cache/userid
nota ".cache/userid preenchido — scripts/userid.sh ja acha o cache pronto"

titulo "pronto"
nota "Confira com uma chamada sua:  ./scripts/ws.sh $FN | head -c 300"
nota "Revogar este token:           $MOODLE_URL/user/managetoken.php -> Reconfigurar"
nota "Invariante 4: essa credencial e pessoal e nao sai desta maquina."
