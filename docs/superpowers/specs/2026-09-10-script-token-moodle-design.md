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
| 3 | abre a URL do `launch.php` **e imprime ela** | a pessoa pode precisar do navegador logado na Senha Única, não do padrão do sistema |
| 4 | recebe o valor **sem ecoar**: clipboard primeiro, `read -rs` como fallback | a credencial não entra no scrollback do terminal |
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

O que ela **não** alcança, e o desenho diz em voz alta: os passos 3, 4, 6 e 7 do
script. Abrir navegador, ler clipboard, escrever `.env` e falar com a USP não são
testáveis offline, e a regra 11 do `CLAUDE.md` já cobrou o preço de confundir "a
suíte está verde" com "o entrypoint funciona". A verificação desses quatro é rodar o
script de verdade, uma vez, na máquina do dono.

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
