#!/usr/bin/env bash
# Captura o redirect do launch.php do Moodle sem DevTools e sem copiar e colar.
#
# Uso:  _capturar_redirect.sh <url-do-launch> [esquema] [segundos]
#       stdout  = a URL capturada, uma linha (E A CREDENCIAL — quem chama nao imprime)
#       stderr  = diagnostico
#       codigo  = 0 capturou | 1 timeout | 2 indisponivel nesta maquina (caia no manual)
#
# COMO FUNCIONA. O `launch.php` valida o parametro `urlscheme` com
# `^[a-zA-Z][a-zA-Z0-9-+.]*$` (linha 37 da 5.0 STABLE), entao ele aceita um
# esquema NOSSO, e a linha 116 monta `"$urlscheme://token=$apptoken"`. Registrando
# um handler para esse esquema, o navegador entrega a URL direto para ca.
#
# Isso tambem e o motivo de um catcher em localhost ser IMPOSSIVEL: o regex proibe
# `:`, `/` e `?`, entao nao existe `urlscheme` que faca o Moodle redirecionar para
# `http://127.0.0.1:PORTA/?token=…`. E com `urlscheme=http` o base64 cai na posicao
# de HOST, que o Chrome minusculiza (§1.3). O esquema proprio e a unica porta.
#
# TRES COISAS MEDIDAS EM 10/09/2026, cada uma um obstaculo que quase matou isto:
#
#   1. `osacompile` NAO gera `CFBundleIdentifier`, e sem ele o Launch Services
#      registra o bundle mas nunca reivindica o esquema (`open` da -10814).
#   2. App em `/private/tmp` tambem nao e reivindicado. Em `~/Library/Caches` e:
#      o dump do LS passa a dizer `claimed schemes: uspmcp:`.
#   3. Entregue por Launch Services, NENHUM dialogo do macOS aparece.
#
# O VALOR NAO TOCA O DISCO. O handler escreve num FIFO, que nao tem armazenamento
# (`stat` confirma tamanho 0). Isso preserva o §4 do desenho: o base64 carrega o
# `privatetoken`, e ele nao pode existir em arquivo.

set -uo pipefail

URL="${1:?uso: $0 <url-do-launch> [esquema] [segundos]}"
ESQUEMA="${2:-uspmcp}"
ESPERA="${3:-120}"

LSREG=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
DIR="$HOME/Library/Caches/usp-mcp-token"   # NAO mude para /tmp: ver medicao 2
APP="$DIR/UspMcpToken.app"
FIFO="$DIR/redirect.fifo"
BUNDLE_ID="co.lastro.uspmcp.tokenhandler"

diag() { printf '   %s\n' "$1" >&2; }

# Falta de ferramenta nao e erro: e "caia no caminho manual".
for f in osacompile open; do
  command -v "$f" >/dev/null 2>&1 || { diag "sem \`$f\` nesta maquina — captura automatica indisponivel"; exit 2; }
done
[ -x "$LSREG" ] || { diag "sem lsregister — captura automatica indisponivel"; exit 2; }
[ -x /usr/libexec/PlistBuddy ] || { diag "sem PlistBuddy — captura automatica indisponivel"; exit 2; }

claims() { "$LSREG" -dump 2>/dev/null | grep -c "claimed schemes:.*$ESQUEMA:" || true; }

# QUEM reivindica o esquema, por identificador de bundle, um por linha. No dump do
# LS o `identifier:` vem antes do `claimed schemes:` do mesmo registro.
donos() {
  "$LSREG" -dump 2>/dev/null | awk -v esq="$ESQUEMA" '
    /^[ \t]*identifier:/ { id = $2 }
    $0 ~ ("claimed schemes:.*" esq ":") { if (id != "") print id }
  ' | sort -u
}

# Se algo JA atende o esquema, nao sequestramos — MAS e preciso saber quem.
# Contar claims sem olhar o identificador confunde "outro app e o dono legitimo"
# (o app oficial do Moodle e dono de `moodlemobile`) com "sobrou registro nosso de
# uma execucao anterior". O segundo caso e comum: o Launch Services demora a podar
# a entrada depois que o .app some do disco, e recusar por causa dele trava o
# script por um lixo que e nosso. Medido em 11/09/2026, numa rodada de verdade.
alheios=$(donos | grep -v "^$BUNDLE_ID$" || true)
if [ -n "$alheios" ]; then
  diag "outro app ja reivindica \`$ESQUEMA://\` — nao vou sobrepor:"
  printf '%s\n' "$alheios" | sed 's/^/     /' >&2
  exit 2
fi
if [ "$(claims)" -gt 0 ]; then
  diag "havia registro obsoleto do nosso proprio handler; vou sobrepor com um novo"
fi

limpar() {
  local codigo=$?
  pkill -f UspMcpToken 2>/dev/null
  [ -d "$APP" ] && "$LSREG" -u "$APP" >/dev/null 2>&1
  rm -rf "$DIR"
  # A verificacao asserta a CONDICAO (o esquema deixou de ser reivindicado), nao
  # uma mensagem de erro do `open`. Um verificador que casa string reporta susto
  # quando a saida muda de forma — foi o que aconteceu no prototipo de 10/09.
  local restou; restou=$(claims)
  if [ "$restou" -gt 0 ]; then
    diag "ATENCAO: \`$ESQUEMA://\` continua reivindicado ($restou) apos a limpeza."
    diag "Remova a mao:  $LSREG -u '$APP' ; rm -rf '$DIR'"
  fi
  return $codigo
}
trap limpar EXIT INT TERM

rm -rf "$DIR"; mkdir -p "$DIR"; chmod 700 "$DIR"
mkfifo -m 600 "$FIFO"

cat > "$DIR/h.applescript" <<AS
on open location this_URL
	do shell script "printf '%s\\n' " & quoted form of this_URL & " > " & quoted form of "$FIFO"
end open location
AS
osacompile -o "$APP" "$DIR/h.applescript" 2>/dev/null \
  || { diag "osacompile falhou — captura automatica indisponivel"; exit 2; }
rm -f "$DIR/h.applescript"

/usr/libexec/PlistBuddy \
  -c "Add :CFBundleIdentifier string $BUNDLE_ID" \
  -c "Add :LSUIElement bool true" \
  -c "Add :CFBundleURLTypes array" \
  -c "Add :CFBundleURLTypes:0:CFBundleURLName string USP MCP token" \
  -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" \
  -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string $ESQUEMA" \
  "$APP/Contents/Info.plist" >/dev/null \
  || { diag "PlistBuddy falhou — captura automatica indisponivel"; exit 2; }

"$LSREG" -f "$APP" >/dev/null 2>&1
for _ in 1 2 3 4 5 6 7 8 9 10; do
  [ "$(claims)" -gt 0 ] && break
  sleep 0.5
done
if [ "$(claims)" -eq 0 ]; then
  diag "o Launch Services nao reivindicou \`$ESQUEMA://\` — captura automatica indisponivel"
  exit 2
fi
diag "handler pronto: o navegador vai entregar o redirect direto para o script"

# fd 3 em read-write: nao bloqueia na abertura e garante um leitor para o handler,
# que senao travaria no `>` do FIFO.
exec 3<> "$FIFO"
# `open` EM SEGUNDO PLANO, de proposito. Medido em 11/09/2026 numa rodada real:
# com um dialogo modal aberto no Safari (um "cannot open the page" de uma tentativa
# anterior), o `open` NAO retorna — e o script ficou presO 6 minutos sem nunca
# chegar no `read`, cujo timeout e quem deveria governar a espera. Em primeiro
# plano, um modal esquecido na tela trava o setup inteiro sem dizer por que.
# O preco e perder o codigo de saida do `open`: a falha passa a aparecer como
# timeout, e a mensagem la embaixo cita as duas causas.
open "$URL" >/dev/null 2>&1 &
diag "abri o launch.php no navegador. Se ele perguntar se pode abrir o handler, aceite."
diag "Se houver um dialogo modal esquecido no navegador, feche-o: enquanto ele"
diag "estiver aberto, o navegador nao processa URL nova."
diag "esperando o redirect (ate ${ESPERA}s)..."

if IFS= read -t "$ESPERA" -r capturado <&3; then
  exec 3>&-
  printf '%s\n' "$capturado"     # stdout: a credencial. quem chama nao imprime.
  diag "capturado ($(printf '%s' "$capturado" | wc -c | tr -d ' ') bytes)"
  exit 0
fi
exec 3>&-
diag "nada chegou em ${ESPERA}s. Duas causas, nesta ordem de probabilidade:"
diag "  1. o navegador nao chegou a seguir o redirect — sessao expirada e parou"
diag "     na Senha Unica, ou um dialogo modal esquecido bloqueando a janela;"
diag "  2. \`forcedurlscheme\` ligado no site (linha 111 do launch.php): ele"
diag "     sobrescreve o nosso esquema e o handler nunca dispara."
exit 1
