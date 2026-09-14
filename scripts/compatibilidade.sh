#!/usr/bin/env bash
# Responde, para UM site Moodle qualquer, se o servidor deste projeto tem chance
# de funcionar lá — em UMA requisicao, SEM credencial nenhuma.
#
# Uso:  ./scripts/compatibilidade.sh https://moodle.ggte.unicamp.br
#       ./scripts/compatibilidade.sh                # usa o MOODLE_URL do .env
#
# POR QUE ISTO EXISTE. A pergunta "o nosso Moodle funciona na Unicamp?" tinha
# duas respostas possiveis antes deste script: deduzir pelo codigo-fonte, ou
# tentar e descobrir no erro. A primeira erra (o servico mobile e decisao do
# ADMIN do site, nao do Moodle — medido em 13/09/2026: Monash tem o Moodle e
# tem o servico DESLIGADO). A segunda exige token, e token exige autenticar numa
# instituicao que talvez nem seja sua.
#
# `tool_mobile_get_public_config` resolve isso porque o core a declara
# `loginrequired => false` e `ajax => true` (admin/tool/mobile/db/services.php):
# e a chamada que o app oficial faz ANTES de qualquer login, para saber como
# desenhar a tela de entrada. Nao carrega token, nao toca dado de ninguem, e
# devolve exatamente os dois campos que decidem a compatibilidade.
#
# O QUE ELE NAO RESPONDE, e isto e metade do valor (Invariante 6). Verde aqui
# significa "o transporte existe e esta ligado" — nao significa que as tres
# ferramentas vao dar resposta util. Os quatro pontos que sobram estao em
# notas/portabilidade-moodle.md §4, e tres deles so aparecem com token na mao:
# convencao de `shortname`, fuso, e `slasharguments`. Prometer mais do que o
# probe mede seria o falso "ta tudo certo" que o Invariante 7 proibe.

set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

URL="${1:-}"
if [ -z "$URL" ]; then
  # Sem argumento, cai no alvo do projeto — mas dizendo qual e, porque "rodei sem
  # argumento e deu verde" nao pode ser confundido com "testei a minha faculdade".
  ENVF=$(PYTHONPATH="$(pwd)" "$PY" -c \
    'from usp_mcp.env import achar_env; a=achar_env(); print(a or "")' 2>/dev/null || true)
  [ -n "$ENVF" ] && { set -a; . "$ENVF"; set +a; }
  URL="${MOODLE_URL:-https://edisciplinas.usp.br}"
  echo "sem argumento: usando MOODLE_URL=$URL"
fi
URL="${URL%/}"   # barra no fim quebra a checagem de origem do download (§4 da nota)

printf '\n\033[1m%s\033[0m\n' "$URL"
echo "  uma requisicao, sem credencial (tool_mobile_get_public_config)"
echo

# -L segue redirect: varios sites respondem no host canonico, e um 302 nao e "nao
# e Moodle". O timeout e curto porque a resposta e pequena e a espera longa aqui
# so esconde um host errado.
resposta=$(curl -sSL -m 20 -H 'Content-Type: application/json' \
  "$URL/lib/ajax/service-nologin.php?info=tool_mobile_get_public_config" \
  -d '[{"index":0,"methodname":"tool_mobile_get_public_config","args":{}}]' \
  2>/dev/null | head -c 20000) || {
    echo "  a rede nao respondeu. Isto NAO diz nada sobre o site — so que daqui" >&2
    echo "  nao deu para alcanca-lo. Confira a URL e tente de novo." >&2
    exit 2
  }

# A resposta vai por env var, nao por pipe: `"$PY" -` le o PROGRAMA do stdin, e o
# heredoc abaixo ocupa esse canal — um pipe aqui chegaria vazio e o script diria
# "nao e JSON" para todo site do mundo. Mesma forma do passo 7 do token.sh.
RESPOSTA="$resposta" ALVO="$URL" "$PY" - <<'PYV'
import json, os, sys

URL = os.environ["ALVO"]
raw = os.environ["RESPOSTA"]

V, A, X = "\033[32m", "\033[33m", "\033[31m"
R = "\033[0m"

def linha(cor, marca, texto):
    print(f"  {cor}{marca}{R} {texto}")

try:
    corpo = json.loads(raw)
except ValueError:
    # HTML no lugar de JSON e o caso comum de URL errada — e "URL errada" e
    # "servico desligado" pedem acoes diferentes. Nao colapsar os dois.
    linha(X, "?", "a resposta nao e JSON.")
    print()
    print("  Quase sempre isto e a URL errada, NAO um site incompativel: o")
    print("  endereco precisa ser a raiz do Moodle (o `wwwroot`), sem caminho.")
    print(f"  Recebido de {URL}: {raw[:70]!r}")
    sys.exit(2)

try:
    item = corpo[0] if isinstance(corpo, list) else corpo
    dados = item["data"]
except (KeyError, IndexError, TypeError):
    erro = ""
    if isinstance(corpo, list) and corpo and isinstance(corpo[0], dict):
        erro = str(corpo[0].get("error") or corpo[0].get("exception") or "")
    linha(X, "X", "e um Moodle, mas recusou a chamada publica.")
    if erro:
        print(f"      {erro[:160]}")
    print()
    print("  Sem `tool_mobile_get_public_config` nao da para medir daqui. O admin")
    print("  do site desabilitou a chamada ou o plugin `tool_mobile`.")
    sys.exit(1)

nome = dados.get("sitename") or "(sem nome)"
ws = dados.get("enablewebservices")
mobile = dados.get("enablemobilewebservice")
login = dados.get("typeoflogin")
launch = dados.get("launchurl") or ""

print(f"  site         {nome}")
print(f"  wwwroot      {dados.get('wwwroot') or URL}")
print()

linha(V if ws else X, "OK" if ws else "X ", f"web services habilitados         (enablewebservices={ws})")
linha(V if mobile else X, "OK" if mobile else "X ",
      f"servico mobile habilitado        (enablemobilewebservice={mobile})")

# O `typeoflogin` nao aprova nem reprova nada: ele diz QUAL caminho de token
# usar. Tratar SSO como problema seria errado — a USP e SSO e e o caso que ja
# funciona. Ele entra no relatorio como instrucao, nao como nota.
CAMINHO = {
    1: ("formulario no proprio app",
        "existe o caminho curto: um POST em /login/token.php com usuario, senha e\n"
        "     service=moodle_mobile_app devolve o token direto. Nao precisa do launch.php."),
    2: ("navegador",
        "o token sai pelo launch.php, como na USP — ./scripts/token.sh serve, so\n"
        "     troque o MOODLE_URL."),
    3: ("navegador embutido (tipico de SSO)",
        "SSO: senha nao serve, o token sai pelo launch.php — e o caso do\n"
        "     e-Disciplinas. ./scripts/token.sh serve, so troque o MOODLE_URL."),
}

# So instruir sobre token quando ha token a obter. Com o servico mobile
# desligado, `/login/token.php` e `launch.php` recusam — imprimir o passo a passo
# aqui seria mandar a pessoa bater numa porta que este mesmo script acabou de
# medir como fechada.
if ws and mobile:
    rotulo, instrucao = CAMINHO.get(login, (f"desconhecido ({login})",
        "modo de login nao catalogado aqui; o launch.php e a aposta mais segura."))
    print()
    print(f"  login        {rotulo}")
    print(f"     {instrucao}")
    if launch:
        print(f"     launch.php: {launch}")

print()
if ws and mobile:
    linha(V, "==>", "O TRANSPORTE FUNCIONA AQUI.")
    print()
    print("  As 5 funcoes da nossa allowlist sao core do Moodle e entram sozinhas")
    print("  em qualquer site com o servico mobile ligado (notas/portabilidade-")
    print("  moodle.md §2). O piso e Moodle 3.3.")
    print()
    print(f"  {A}Mas verde aqui nao e verde nas ferramentas.{R} Quatro pontos do NOSSO")
    print("  codigo ainda assumem o e-Disciplinas, e tres deles so aparecem com")
    print("  token na mao (§4 da nota):")
    print("    - `shortname` no formato SIGLA-ano: fora da USP a busca por sigla pode")
    print("      nao achar disciplina que existe")
    print("    - fuso fixo em -3: prazo sai deslocado, e deslocado calado")
    print("    - `slasharguments=0`: arquivo vira link com URL vazia")
    print()
    print("  Proximo passo, com o token deste site:")
    print(f"    MOODLE_URL={URL} ./scripts/ws.sh core_webservice_get_site_info")
    sys.exit(0)

linha(X, "==>", "NAO FUNCIONA AQUI, e nao ha o que consertar do nosso lado.")
print()
if ws and not mobile:
    print("  O site tem web services, mas o servico mobile esta DESLIGADO. E uma")
    print("  decisao do administrador do Moodle da instituicao, nao uma limitacao")
    print("  do Moodle nem do nosso codigo — medido em Monash (13/09/2026).")
else:
    print("  Os web services estao desligados no site inteiro.")
print()
print("  Unica saida: pedir ao admin do site. Nenhum token existe enquanto isso.")
sys.exit(1)
PYV
