#!/usr/bin/env bash
# Obtem o MOODLE_TOKEN e grava no .env — o §8 do SPEC1.md virado chamador.
#
# Uso:  ./scripts/token.sh              # guiado, interativo
#       pbpaste | ./scripts/token.sh    # se voce ja copiou a URL do redirect
#       ./scripts/token.sh --sobrescrever   # trocar token que ja funciona, sem perguntar
#       ./scripts/token.sh --auto           # tenta capturar o redirect sozinho (ver abaixo)
#       ./scripts/token.sh --navegador="Google Chrome"   # so com --auto
#
# Sete passos, na ordem em que estao no desenho de 10/09/2026
# (docs/superpowers/specs/2026-09-10-script-token-moodle-design.md):
#
#   1. prepara o .env            5. decodifica EM MEMORIA
#   2. gera um passaporte        6. confirma o token contra a USP (1 chamada)
#   3. pega o redirect           7. grava so os 32 hex no .env
#   4. (manual por padrao)
#
# O PADRAO e o caminho manual, e ele esta MEDIDO contra o e-Disciplinas (§9,
# 11/09/2026): com `confirmed=1` o Moodle nao redireciona, mostra uma pagina com
# um link, e o endereco DESSE link e o token — "botao direito -> copiar endereco"
# no lugar do DevTools. Leva ~20 s.
#
# Duas fricoes desse passo foram MEDIDAS numa passagem real de um segundo usuario
# em 12/09/2026, e o passo 3 as trata: (a) a pagina tem tres elementos e nenhum
# parece um token, entao o script cita o texto do link em voz alta e avisa para
# NAO clicar nele — clicar tenta abrir o app e nao copia nada; (b) nao havia como
# conferir o clipboard antes de entregar, entao o script confere sozinho e
# reconhece o erro nº 1, que e colar a URL do proprio launch.php.
#
# `--auto` tenta antes a captura de scripts/_capturar_redirect.sh, que registra um
# handler para um esquema nosso e recebe o redirect direto do navegador. Ela
# funciona contra duble e NUNCA entregou contra a USP — por isso nao e o padrao.
# Se nao entregar em 120 s, cai no manual sozinha.
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
# --manual: pular a captura automatica e colar a URL do redirect a mao.
# O PADRAO E O MANUAL, por decisao de 11/09/2026 (§9). A captura automatica
# funciona contra duble e NUNCA foi verificada contra o e-Disciplinas: tres
# tentativas reais, tres falhas antes de o navegador entregar o redirect. Deixa-la
# ligada por padrao custaria 120 s de espera em toda execucao, num caminho que
# pode nem existir neste site (`forcedurlscheme`, linha 111, nao e observavel de
# fora). O manual leva ~20 s e esta medido. `--auto` tenta a captura primeiro.
manual=1
# --navegador="Google Chrome": abrir num navegador especifico. Vale so com --auto.
# Medido: o Chrome pede confirmacao e o padrao do sistema nao.
navegador=""
for arg in "$@"; do
  case "$arg" in
    --sobrescrever) sobrescrever=1 ;;
    --manual) manual=1 ;;
    --auto) manual=0 ;;
    --navegador=*) navegador="${arg#--navegador=}" ;;
    -h|--ajuda|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "opcao desconhecida: $arg (use --ajuda)" >&2; exit 2 ;;
  esac
done

titulo() { printf '\n\033[1m%s\033[0m\n' "$1"; }
nota()   { printf '   %s\n' "$1"; }
aviso()  { printf '   \033[33m! %s\033[0m\n' "$1"; }

# ------------------------------------------------------------- 1. prepara o .env
titulo "1/7  .env"
# NAO basta olhar ./.env. O `.env` e gitignorado, entao `git worktree add` nao o
# copia e um worktree novo nao tem o dele — mas o lado Python acha o do checkout
# principal subindo os diretorios (usp_mcp.env.achar_env). Se este script criasse
# um ./.env no worktree, ele SOMBREARIA o de verdade: o token iria para um arquivo
# que some com o worktree, e o `.env` que o projeto usa ficaria sem nada. E o mesmo
# defeito que a primeira versao do gate teve (§4 do CONVENTIONS.md).
# Engolir a falha aqui daria o pior desfecho: ENV_FILE vazio, um .env novo criado
# no lugar errado, e a aparencia de sucesso. Se nao da para localizar, pare.
if ! ENV_FILE=$(PYTHONPATH="$(pwd)" "$PY" -c \
     'from usp_mcp.env import achar_env; a = achar_env(); print(a or "")' 2>&1); then
  echo "nao consegui localizar o .env — usp_mcp.env nao importou:" >&2
  printf '%s\n' "$ENV_FILE" | sed 's/^/  /' >&2
  exit 1
fi

if [ -z "$ENV_FILE" ]; then
  [ -f .env.example ] || { echo "sem .env e sem .env.example — repo incompleto" >&2; exit 1; }
  cp .env.example .env
  ENV_FILE="$(pwd)/.env"
  nota "nenhum .env encontrado; criei a partir do .env.example (esta no gitignore)"
else
  nota "gravando no .env que o projeto ja enxerga:"
  nota "  $ENV_FILE"
fi

set -a; . "$ENV_FILE"; set +a
: "${MOODLE_URL:=https://edisciplinas.usp.br}"
nota "MOODLE_URL=$MOODLE_URL"

# Um token que ja funciona nao se sobrescreve calado: o antigo CONTINUA ativo em
# managetoken.php, e trocar sem avisar deixa dois vivos na conta e nenhum
# registro de qual esta em uso. A lista de la mostra o NOME (16 chars), nao o valor.
if grep -qE '^MOODLE_TOKEN=[a-f0-9]{32}$' "$ENV_FILE"; then
  aviso "o .env ja tem um MOODLE_TOKEN com forma valida."
  nota "Na pratica isto costuma ser troca por si mesmo: a linha 89 do launch.php"
  nota "chama generate_token_for_current_user, que devolve o token EXISTENTE do"
  nota "servico em vez de cunhar um novo. Medido em 11/09/2026 numa rodada real —"
  nota "o valor gravado veio byte a byte igual ao que ja estava aqui."
  nota "Token novo so nasce se a conta ainda nao tiver um para este servico; nesse"
  nota "caso o antigo continua ativo e se revoga em:"
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
base="$MOODLE_URL/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=$passaporte"

# Duas URLs para os dois caminhos, e a diferenca esta no `urlscheme`:
#   automatico: esquema NOSSO, que um handler temporario atende (ver
#               scripts/_capturar_redirect.sh). O navegador entrega direto.
#   manual:     `confirmed=1` faz o launch.php NAO redirecionar — ele renderiza
#               uma pagina com o link cujo href E o `moodlemobile://token=…`
#               (linhas 120-145 da 5.0 STABLE). Entao a instrucao vira "botao
#               direito no link -> copiar endereco", em vez de abrir o DevTools.
url_auto="$base&urlscheme=uspmcp"
url_manual="$base&urlscheme=moodlemobile&confirmed=1"

# ------------------------------------- 3+4. pega o redirect: automatico ou manual
titulo "2/7  pegar o redirect do launch.php"
valor=""

if [ "$manual" = "0" ] && [ -t 0 ]; then
  nota "Tentando captura automatica. Como funciona: registro um handler temporario"
  nota "para \`uspmcp://\`, abro o launch.php com esse esquema, e o navegador"
  nota "entrega o redirect direto para o script — sem DevTools e sem colar nada."
  nota "O handler e desregistrado no fim, inclusive se voce abortar com Ctrl+C."
  nota ""
  if valor=$(USP_MCP_NAVEGADOR="$navegador" ./scripts/_capturar_redirect.sh "$url_auto" uspmcp 120); then
    titulo "3/7  recebido sem passar pelo terminal nem pelo clipboard"
    nota "captura automatica OK — nada foi colado e nada ficou no scrollback."
  else
    valor=""
    aviso "a captura automatica nao entregou; seguindo no caminho manual."
  fi
fi

if [ -z "$valor" ]; then
  titulo "2/7  (manual) abra esta URL no navegador LOGADO na Senha Unica"
  printf '\n   %s\n\n' "$url_manual"
  nota "Com \`confirmed=1\` o Moodle nao redireciona: ele mostra uma pagina, e o"
  nota "ENDERECO de um dos links dela e o token — nao precisa de DevTools."
  nota ""
  # Qual link. A instrucao antiga dizia "o link" e a pagina tem tres coisas
  # clicaveis: numa passagem real de um segundo usuario em 12/09/2026 o que foi
  # para o clipboard foi a URL da propria pagina. Nada ali se parece com um
  # token, e o texto do link certo promete ser um plano B dispensavel — por isso
  # ele e citado em voz alta, e por isso os dois chamarizes sao nomeados para
  # serem ignorados de proposito, em vez de ficarem de fora da instrucao.
  nota "A pagina tem tres coisas, e so UMA interessa:"
  nota "  caixa verde  'O seu cadastro foi confirmado'   -> ignore"
  nota "  botao cinza  'Ambientes'                       -> ignore"
  nota "  link azul    'Clique aqui se a aplicacao nao abrir automaticamente'"
  nota "               -> E ESTE. O texto promete plano B e mente: e o unico"
  nota "                  lugar da pagina onde o token existe."
  nota ""
  aviso "NAO CLIQUE nesse link. Clicar tenta abrir o app e nao copia nada."
  nota "Botao DIREITO em cima dele -> 'Copiar endereco do link'. So isso."
  nota ""
  nota "Se a pagina nao aparecer e o navegador tentar abrir um app, ai o caminho e"
  nota "o DevTools (Cmd+Opt+I) -> aba Network -> a linha bloqueada para"
  nota "\`moodlemobile://token=…\` e o que copiar."
  nota ""
  nota "Nao troque por urlscheme=http: nessa forma o base64 cai na posicao de host"
  nota "da URL, o Chrome minusculiza host, e base64 e sensivel a caixa — o token"
  nota "chega corrompido com a forma certa (§1.3 do SPEC1.md)."

  titulo "3/7  cole a URL do link"
  if [ -t 0 ]; then
    if command -v open >/dev/null 2>&1; then open "$url_manual" 2>/dev/null || true; fi
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
      [ -n "$valor" ] && nota "li do clipboard."
    fi
  else
    valor=$(cat)   # pbpaste | ./scripts/token.sh
    nota "li do stdin."
  fi

  # --------------------------- confere o clipboard ANTES de gastar a tentativa
  # Fricao medida na mesma passagem de 12/09/2026: nao havia como olhar o que
  # estava no clipboard antes de entregar. Da para fazer a mao com
  # `pbpaste | cut -c1-21`, que mostra `moodlemobile://token=` e nada alem — mas
  # quem esta SEGUINDO o script nao tem por que inventar esse comando, entao ele
  # vira passo daqui. Custa zero e roda antes de qualquer decodificacao.
  #
  # O QUE PODE SER IMPRESSO, e isto e o Invariante 3 e nao estilo: no maximo o
  # prefixo do esquema, e SO quando o valor comeca exatamente com ele. Tudo
  # depois de `token=` e a credencial. Quando nao confere, a saida fala de forma
  # — quantos bytes — e nunca dos bytes: um `cut -c1-21` incondicional num base64
  # nu imprimiria 21 caracteres de token no scrollback.
  #
  # So existe no caminho manual. Na captura automatica o valor vem do navegador
  # com o esquema NOSSO (`uspmcp://`), nao passa por clipboard nenhum, e conferir
  # contra `moodlemobile://` ali daria alarme falso em toda rodada boa.
  ESQUEMA='moodlemobile://token='
  bytes=$(printf '%s' "$valor" | wc -c | tr -d ' ')
  if [ "$(printf '%s' "$valor" | cut -c1-${#ESQUEMA})" = "$ESQUEMA" ]; then
    nota "confere: comeca com \`$ESQUEMA\`, $bytes bytes no total."
  else
    aviso "o que chegou ($bytes bytes) NAO comeca com \`$ESQUEMA\`."
    case "$valor" in
      *launch.php*)
        # O caso medido, e o unico em que da para afirmar o que aconteceu.
        nota "Isto e a URL de IDA (a da pagina que voce abriu), e nao a de VOLTA."
        nota "As duas sao URLs, e e por isso que se confundem; so a segunda"
        nota "carrega o token."
        nota "Volte a pagina, BOTAO DIREITO no link azul 'Clique aqui se a"
        nota "aplicacao nao abrir automaticamente' -> 'Copiar endereco do"
        nota "link', e rode este script de novo. Nao clique com o esquerdo."
        nota "O .env NAO foi tocado."
        exit 1 ;;
    esac
    nota "Colar so o base64, sem o esquema na frente, tambem vale — o passo 4/7"
    nota "decide. Se nao for isso, refaca do passo 2."
  fi
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
  nota "Isto e AVISO, nao bloqueio. E ELE SO CARREGA INFORMACAO se a URL que voce"
  nota "abriu foi a que ESTE script acabou de imprimir: o passaporte e por"
  nota "invocacao, entao um payload vindo de outra rodada — sua, da mesma conta,"
  nota "perfeitamente valida — nao confere e esta tudo certo. Aconteceu em"
  nota "11/09/2026, e o token autenticou no passo 6."
  nota "Se a URL foi a deste script, sobram duas leituras e o passo 6 desempata:"
  nota "  - autenticou: a formula e que esta errada aqui (wwwroot com/sem barra,"
  nota "    com/sem www). Registre no §9."
  nota "  - falhou: o payload nao e desta conta."
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
WSTOKEN="$wstoken" ENV_FILE="$ENV_FILE" "$PY" - <<'PYW'
import os, re
tok = os.environ["WSTOKEN"]
alvo = os.environ["ENV_FILE"]
linhas = open(alvo, encoding="utf-8").read().splitlines(keepends=True)
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
open(alvo, "w", encoding="utf-8").writelines(saida)
print("   MOODLE_TOKEN gravado" + ("" if achou else " (linha nova)") + ". Valor nao impresso.")
PYW

# O cache mora junto do .env, pelo mesmo motivo: e o checkout que o projeto usa.
CACHE_DIR="$(dirname "$ENV_FILE")/.cache"
mkdir -p "$CACHE_DIR"
printf '%s\n' "$userid" > "$CACHE_DIR/userid"
nota "$CACHE_DIR/userid preenchido — scripts/userid.sh ja acha o cache pronto"

titulo "pronto"
nota "Confira com uma chamada sua:  ./scripts/ws.sh $FN | head -c 300"
nota "Revogar este token:           $MOODLE_URL/user/managetoken.php -> Reconfigurar"
nota "Invariante 4: essa credencial e pessoal e nao sai desta maquina."
