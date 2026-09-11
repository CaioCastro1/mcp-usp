# `scripts/token.sh` — o §8 do `SPEC1.md` virado chamador

> Data: 10/09/2026. A autoridade continua sendo o `SPEC1.md`; este documento é o
> desenho de um script de setup e da suíte que especifica a parte dele que dá para
> especificar offline.
>
> **Três fatos do §1.3 do `SPEC1.md` são pressupostos deste desenho, não escolhas
> dele:** `login/token.php` com usuário e senha devolve `invalidlogin` porque a conta
> autentica por SSO; `managetoken.php` não mostra o valor do token nesta versão; e o
> valor só sai pelo fluxo de `launch.php` com o navegador logado. Se algum dos três
> cair, o script inteiro perde a razão de existir na forma descrita aqui.

## 1. O problema

O token do Moodle é a única credencial do projeto, e obter ele hoje é conhecimento
que mora em prosa: o §8 do `SPEC1.md`, dentro de um arquivo de 117 kB, num anexo
chamado "comandos que funcionaram".

Quem está fazendo o setup executa cinco passos manuais:

1. achar o §8 e montar a URL do `launch.php` à mão;
2. saber abrir o DevTools na aba Network antes de clicar;
3. copiar a linha `token=…` e decodificar com um one-liner de `pbpaste`;
4. editar o `.env` à mão — ou colar o valor cru e lembrar de rodar o `fix-token.sh`;
5. descobrir o `userid` e só então, no primeiro uso de verdade, saber se funcionou.

Três desses passos têm jeito silencioso de errar. O pior é o 4: colar a URL crua no
`.env` **funciona** até alguém rodar o `ws.sh`, que falha com `invalidtoken` sem
dizer que o problema é forma e não validade. O 5 é o que o Invariante 6 chama pelo
nome — a pessoa acha que configurou e descobre o contrário depois, com erro cru.

## 2. A decisão de escopo

**O script cobre o token e só o token.** Não faz venv, não faz `pip install`, não
roda o gate — isso já está no `README.md`, e um `setup.sh` que faz tudo duplicaria
essas três linhas num segundo lugar que envelhece separado.

**E ele confirma o token contra a USP: uma chamada.** Decisão do dono em 10/09/2026.
O argumento contra era o §1.1 — chamada ao vivo é decisão de quem tem a credencial,
não do script. O argumento que venceu: aqui quem roda o script **é** quem acabou de
colar a própria credencial de propósito, e o consentimento é o próprio ato de rodar.
Sem a chamada, "gravei o token" não significa "o token funciona", que é exatamente a
distinção que o passo 5 do problema descreve.

## 3. Os sete passos

| # | passo | por que assim |
|---|---|---|
| 1 | prepara o `.env` (copia do `.env.example` se faltar) e lê `MOODLE_URL` | quem clonou o repo não tem `.env`; falhar aqui é falhar no passo mais fácil de resolver |
| 2 | gera um **passaporte aleatório** em vez do `1234` fixo do §8 | o passaporte compõe o `siteid` do payload; com um próprio, o script confere o eco |
| 3 | **captura automática**: handler temporário para um esquema nosso recebe o redirect | ver §3.2 — sem DevTools, sem clipboard, sem colar |
| 4 | fallback manual, se a automática não entregar: `confirmed=1` + colar sem ecoar | a credencial não entra no scrollback do terminal |
| 5 | decodifica **em memória** e descarta o `privatetoken` | ver §4 |
| 6 | grava só os 32 hex no `.env`, com confirmação se já havia token | ver §5 |
| 7 | `core_webservice_get_site_info` e grava o `userid` da mesma resposta | uma chamada, não duas |

### 3.1 O passaporte confere, mas não bloqueia

O `siteid` do payload é `md5(wwwroot + passport)`. Com um passaporte gerado pelo
próprio script, dá para conferir se o payload colado responde àquela invocação — o
que pega o caso de colar uma URL de outra tentativa, de outra sessão, ou de outra
pessoa.

Essa fórmula está **recordada, não medida** contra o e-Disciplinas. Por isso a
conferência **avisa e segue**, em vez de reprovar: o §1.4 separa o que foi verificado
do que foi lembrado, e transformar memória em porta fechada é o jeito de reprovar um
setup legítimo por motivo errado. Quando alguém rodar isso com token real, o
diagnóstico que o script imprime é o dado que fecha a questão — e aí a conferência
pode virar bloqueio, com registro no §9.

### 3.2 A captura automática, e por que ela é a única porta

O pedido original virou um script com um passo manual no meio — "abra o DevTools na
aba Network" não é instrução de setup. A leitura do `admin/tool/mobile/launch.php` da
5.0 STABLE (mesma linha da 5.0.8+ do e-Disciplinas) mostrou o que é possível:

- **Linha 37:** `urlscheme` é validado com `^[a-zA-Z][a-zA-Z0-9-\+\.]*$`. Só caracteres
  de esquema — sem `:`, `/` nem `?`. **Um catcher em localhost é impossível:** não existe
  `urlscheme` que faça o Moodle redirecionar para `http://127.0.0.1:PORTA/?token=…`.
- **Linha 116:** `$location = "$urlscheme://token=$apptoken"`. O base64 sempre cai na
  posição de host, que é a razão do `urlscheme=http` corromper (§1.3).
- **Mas o regex aceita um esquema NOSSO.** `uspmcp` passa. Registrando um handler para
  ele, o navegador entrega a URL direto ao script.
- **Linhas 120-145:** com `confirmed=1` o Moodle **não** redireciona: renderiza uma
  página com um link cujo `href` é o `moodlemobile://token=…`. Isso melhora o fallback
  manual — "botão direito no link → copiar endereço" em vez de DevTools.
- **Linha 89:** `generate_token_for_current_user` devolve o token **existente** se já
  houver um para o serviço. Rodar o fluxo não cunha um segundo token a cada vez.
- **Linha 111:** `forcedurlscheme`, se configurado no site, **sobrescreve** nosso
  esquema — e aí o handler nunca dispara. É o principal motivo de o fallback existir.

Três obstáculos foram achados por medição, não por leitura, e cada um matava a ideia:

1. `osacompile` **não** gera `CFBundleIdentifier`, e sem ele o Launch Services registra
   o bundle mas nunca reivindica o esquema (`open` devolve `-10814`).
2. App em `/private/tmp` **também** não é reivindicado. Em `~/Library/Caches` é.
3. Entregue por Launch Services **e por redirect de navegador de verdade**, nenhum
   diálogo aparece — nem do macOS nem do Chrome.

**O handler escreve num FIFO, não em arquivo.** Um FIFO não tem armazenamento (`stat`
confirma tamanho 0), então o §4 abaixo continua valendo no caminho automático.

**A limpeza asserta a condição, não a mensagem.** O `trap` desregistra e apaga, e depois
confere que a contagem de claims do esquema voltou a zero. A primeira versão dessa
verificação casava a string de erro do `open` e reportou "ainda atende" numa máquina
limpa — um verificador que não distingue "sujo" de "saída inesperada" não verifica nada
(§6 do `CONVENTIONS.md`).

## 4. O `privatetoken` não toca o disco

O payload decodificado tem três partes: `siteid:::token:::privatetoken`. A terceira
habilita autologin — `tool_mobile_get_autologin_key` está na lista de **bloqueio
permanente** do §2.2, que a flag `USP_MCP_ALLOW_WRITES=1` não libera.

Disso vem uma restrição de desenho que parece detalhe e não é: **a decodificação
acontece em memória, e o base64 cru nunca é gravado.** O caminho mais curto de
implementar o script seria gravar o valor colado no `.env` e chamar o `fix-token.sh`
para normalizar depois. Esse caminho escreve o `privatetoken` no disco, ainda que por
um instante, num arquivo que ninguém audita depois de existir. O script decodifica
antes de escrever e grava só os 32 hex.

## 5. Sobrescrever token existente pede confirmação

Se o `.env` já tem um `MOODLE_TOKEN` válido de 32 hex, o script avisa e pergunta.

O motivo não é medo de perder o valor: é que o token antigo **continua ativo** no
`managetoken.php` depois de ser sobrescrito aqui. Trocar calado deixa dois tokens
vivos na conta e nenhum registro de qual está em uso — e quem quiser revogar o
antigo não tem como saber qual dos nomes de 16 caracteres da lista é ele.

## 6. Onde o código mora

`scripts/_capturar_redirect.sh` — a captura automática: monta o handler, registra,
abre o `launch.php`, espera no FIFO, desregistra no `trap`. Código de saída separa os
três desfechos: `0` capturou, `1` timeout (provável `forcedurlscheme`), `2` indisponível
nesta máquina. Falta de ferramenta e esquema já reivindicado por outro app dão `2` — não
erro: a resposta certa é cair no manual, não abortar o setup.

`scripts/_decodificar_token.py` — a decodificação sai de dentro do `fix-token.sh` e
vira unidade própria: lê URL ou base64 no stdin, imprime `siteid` e `wstoken` (nunca
o `privatetoken`), sai com mensagem legível em português quando a forma está errada.

`scripts/token.sh` — o fluxo guiado dos sete passos, em bash com heredoc de Python,
no mesmo molde do `fix-token.sh`.

`scripts/fix-token.sh` — **continua existindo**, com o propósito estreitado para o
caso "colei no `.env` à mão e ficou torto", e passa a chamar o helper.

A extração não é refatoração oportunista: sem ela o `token.sh` nasce com uma segunda
cópia da regra de formato do payload, e duas verdades sobre o mesmo formato divergem
na primeira vez que o Moodle mudar de versão.

## 7. A suíte

`tests/moodle/test_token_decode.py`, offline, sobre payload **sintético** montado no
próprio teste — `siteid:::<32 hex sintético>:::privatetoken`. Nenhum token real entra
em teste, nem higienizado.

O que ela especifica:

1. extrai o `wstoken` de URL completa (`moodlemobile://token=…`) e de base64 nu;
2. o `privatetoken` **não aparece no stdout** — a asserção é sobre a saída medida, não
   sobre a intenção do código. É o §4 virado teste;
3. forma errada reprova com mensagem legível e código de saída ≠ 0, não com stack
   trace: base64 inválido, payload com menos de duas partes, `parte[1]` fora de 32 hex;
4. base64 minusculizado — a armadilha do Chrome do §1.3 — reprova, em vez de gravar
   token corrompido.

O que ela **não** alcança: a captura automática e o fallback para o manual. Registrar
handler no Launch Services e abrir navegador não entram numa suíte que roda no gate —
seria um teste que muda o estado da máquina de quem commita. A regra 11 do `CLAUDE.md`
manda dizer isso em voz alta em vez de fingir cobertura, e o backlog registra a dívida.

**A verificação que existe para esses é medição à mão, registrada no §9:** o fluxo
inteiro rodou contra um Moodle de mentira em `127.0.0.1` que emite o mesmo `302` da
linha 149 do `launch.php`, com pty para o script ver um terminal. Capturou 151 bytes
idênticos ao que o servidor mandou, decodificou, verificou, gravou, cacheou o `userid`,
e a limpeza fechou com zero claims e zero diretório. O passo 6 também foi medido contra
a USP de verdade (§9, adendo de 10/09).

## 8. Documentação

Uma linha na seção "Configuração" do `README.md` apontando para o script, e uma nota
no §8 do `SPEC1.md` dizendo que o fluxo manual agora tem chamador. O passo a passo em
si vive **no script** — é o único lugar onde ele não envelhece calado, porque quem
mexe no fluxo mexe no arquivo que o descreve.

## 9. Fora de escopo, de propósito

- **Renovar token expirado sem navegador.** Não existe caminho: o `launch.php`
  autentica por sessão, e o §1.3 já registra que senha não serve.
- **O token de `Attendance`.** Outro serviço, outro token na conta, segundo escopo
  (§1.3). Faltas ficam fora deste token e o script não finge o contrário.
- **Venv, `pip`, gate.** Já no `README.md` (§2).
