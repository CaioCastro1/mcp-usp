# Reconhecimento da área logada do JupiterWeb — plano

> 14/09/2026. **Nada aqui foi executado.** Este é o roteiro para quando o dono tiver a
> sessão à mão, escrito antes justamente para que a sessão dele seja curta e a decisão
> de cada requisição já esteja tomada em frio.
>
> Escopo: **medir a forma** da área logada. Não é construir ferramenta — ferramenta nasce
> do §5 do `SPEC1.md`, com pergunta registrada, e ainda não há medição que a sustente.

## Por que este plano existe antes do acesso

Duas vezes hoje uma afirmação minha sobre a USP caiu quando encontrou dado (o currículo
"vazio" que exigia `2000101`; a auth de app do RUCard que não existe no caminho
alcançável). As duas eram inferências feitas rápido, em cima de dado parcial. Numa área
**autenticada**, o custo de fazer isso muda de categoria: lá um erro não é uma resposta
errada, é um ato na matrícula do dono.

Por isso as regras abaixo valem **desde a primeira requisição**, e não "depois que
entender melhor".

## As regras, que não são negociáveis nesta trilha

1. **Uma requisição por vez, escolhida à mão, aprovada pelo dono antes de sair.** É a
   Regra de Ouro do §3.1 aplicada a um sistema onde ela morde mais: no Moodle um sweep
   passa por `submit_for_grading`; aqui passa por trancamento de disciplina.
2. **Só `GET`. Nenhum `POST`, em nenhuma circunstância, nesta fase.** Não há medição que
   exija POST, e "só pra ver o que acontece" é exatamente a frase que precede o estrago.
3. **Nada de seguir link automaticamente.** Um crawler na área logada é o sweep proibido
   com outro nome. Cada URL entra na lista por decisão humana.
4. **Nenhum formulário é submetido.** Formulário encontrado é *registrado como achado* —
   caminho, método, campos — e a página não é revisitada.
5. **O cookie nunca é impresso, ecoado, logado nem commitado** (Invariante 3). Ele entra
   por `.env`, sai por variável, e o gate ganha checagem própria (abaixo).
6. **O cru não entra no git.** `fixtures/jupiter/raw/` nasce gitignorada, como a do
   Moodle: a área logada tem NUSP, nome e nota.
7. **Se a resposta vier maior que ~200 kB, ela não é lida** (Invariante 8) — mede-se
   tamanho, tipo e forma, nunca o corpo.

## Fase 0 — a sessão entra no projeto (sem tocar na USP)

| passo | o que |
|---|---|
| 0.1 | `.env.example` ganha `JUPITER_SESSAO=` — o **conjunto** de cookies da área logada, não um nome fixo: a Fase 1a é que diz quais importam (são dois, e um é `path=/`) |
| 0.2 | `scripts/jupiter-sessao.sh`, espelho do `fix-token.sh`: aceita a linha crua colada do DevTools, extrai só o valor, grava, **nunca imprime**. Idempotente |
| 0.3 | Gate ganha a checagem: valor de `JUPITER_SESSAO` em qualquer arquivo rastreado **reprova**. Verificada por sabotagem, como as outras três |
| 0.4 | `usp_mcp/env.py` passa a saber ler a variável, com erro legível quando ausente |

**Nada disso toca a rede**, e tudo é testável hoje. Se a trilha morrer aqui, o custo foi
um script e uma checagem — e a checagem serve a qualquer credencial futura.

## Fase 1a — **quais** cookies são a credencial, e por quanto tempo

> Medido em 14/09, **sem credencial**, contra `webLogin.jsp` e `jupCarreira.jsp`: o
> JupiterWeb entrega **dois** cookies a um visitante anônimo, e o recon de 31/08 só
> registrava o primeiro.
>
> ```
> JSESSIONID=…;      Path=/jupiterweb;  HttpOnly            (sem Secure)
> UD_jupiterweb=…;   path=/;            secure;  httponly   (80 hex)
> ```

Três consequências, e a primeira desmonta uma suposição deste plano:

1. **"Cole o `JSESSIONID`" pode ser insuficiente ou impreciso.** Talvez a credencial
   autenticada seja o par, talvez seja só o `UD_`. Enquanto não se sabe, o script da
   Fase 0 não deve prometer que sabe: ele aceita **o conjunto**, e a Fase 1a decide.
2. **`path=/` é escopo de host, não de sistema.** O nome `UD_jupiterweb` sugere um
   cookie por sistema; o path diz que ele viaja para todo `uspdigital.usp.br`. Os dois
   sinais discordam, e **não se escolhe o mais confortável**. Até medir, trate o
   conjunto como credencial de host — o que torna as regras acima mais importantes, não
   menos.
3. **Nenhum dos dois tem `Max-Age`/`Expires`** — morrem com o navegador. O timeout de
   inatividade do servidor **não foi medido**; 30 min é o default do Tomcat, e default
   de produto não é fato de deployment.

**As duas medições da Fase 1a, nesta ordem:**

| # | o que fazer | o que decide |
|---|---|---|
| 1a.1 | Uma página logada, pedida **três vezes**: com os dois cookies, só com `JSESSIONID`, só com `UD_jupiterweb` | qual é a credencial de verdade — e portanto o que o `.env` guarda e o que o gate protege |
| 1a.2 | A mesma página em t=0, t+20min, t+45min, **sem nada entre elas** | o timeout de inatividade real. Três requisições, espalhadas, e a resposta vale para o desenho inteiro |

A 1a.2 é o que decide se a trilha se paga: **se a sessão morre em 30 minutos de
inatividade, dado consultado uma vez por semana não deve depender dela** — e o histórico
em PDF passa de alternativa a resposta certa.

## Fase 1b — o mapa, e ele começa com você, não comigo

Eu **não sei** as URLs da área logada e **não vou adivinhar**: adivinhar nome de endpoint
é o laço que o §4.6 do recon recusou, e ali era sistema público.

O mapa sai de uma coisa só, que você faz uma vez:

> Logado no JupiterWeb, salve o HTML da **página de menu** (a que lista o que você pode
> acessar) em `fixtures/jupiter/raw/menu-logado.html`.

Dela eu extraio a lista de caminhos **que o próprio sistema oferece** — mesma técnica que
achou o `listarCursosRequisitos` na página pública — e devolvo para você uma tabela:
caminho, rótulo do menu, e meu palpite do que ele responde. **Você marca quais medir.**

## Fase 2 — medir, uma por vez

Para cada caminho aprovado, e só para ele:

| coluna | por quê |
|---|---|
| status, bytes, `Content-Type` | custo e Invariante 8 |
| HTML renderizado no servidor **ou** DWR? | decide se a fatia é parser ou RPC — e, se for DWR, **quais beans**, porque `executarBatch` precisa entrar no bloqueio permanente antes de qualquer código |
| tem `<form>`? método e ação | é a superfície de escrita; entra na lista de bloqueio, não na de uso |
| a resposta muda entre duas chamadas espaçadas? | decide o TTL do cache (Invariante 5) |
| quanto sobra depois do recorte | a fatia só existe se a redução justificar (o `requisitos` fez 30.720 B → 511 B) |

**Critério de parada, escrito antes de começar:** qualquer página que contenha formulário
de matrícula, trancamento ou pagamento tem o caminho anotado no bloqueio permanente e
**não é medida de novo**. Saber que ela existe basta; explorá-la não.

## Fase 3 — higienização, antes de qualquer fixture entrar no git

Igual ao §3.3 do Moodle, e a lista do que vira sintético é maior aqui:

`codpes`/NUSP, nome, e-mail, **nota**, frequência, data de nascimento, e qualquer
identificador de turma que carregue nome de professor. Valor sintético **estável** —
mesma entrada, mesma saída — para que a fixture continue exercitando a forma.

O cru fica em `fixtures/jupiter/raw/`, fora do git, e o gate confere que continua fora.

## Fase 4 — os testes, que nascem antes do código

Na ordem em que devem ficar vermelhos:

1. **Política de caminho**: a allowlist da área logada começa **vazia**, e um caminho não
   listado é negado com motivo. O bloqueio de matrícula/pagamento ignora
   `USP_MCP_ALLOW_WRITES` — não há flag que libere, como no §2.2.
2. **Método**: qualquer coisa que não seja `GET` é negada na fronteira do cliente, não no
   bom senso de quem chama.
3. **Sessão ausente ou expirada vira erro legível** — "sua sessão do JupiterWeb expirou,
   rode `./scripts/jupiter-sessao.sh`" — e **nunca** lista vazia (Invariantes 6 e 7). O
   teste precisa provar a distinção entre *"não há nada"* e *"não consegui ver"*, porque
   numa página de notas as duas se parecem e só uma é verdade.
4. **Higienização**: fixture com NUSP ou nota real reprova, como o teste equivalente do
   Moodle (T47).
5. **O cookie não vaza**: nenhuma mensagem de erro, log ou saída de ferramenta contém o
   valor. Verificado por sabotagem — plantar o valor numa mensagem tem que reprovar.
6. **Canário `live` atrás de `USP_MCP_LIVE=1`**, e aqui ele é mais caro que nos outros:
   cada execução usa a sessão pessoal do dono. Roda quando ele mandar.

## O que este plano deliberadamente não decide

- **Quais ferramentas vão existir.** Nota, histórico e evolução do curso são três
  perguntas diferentes, e o §5 pede que cada uma nasça registrada. A Fase 2 é que diz o
  que é barato responder.
- **Se vale a pena.** Se a medição mostrar que o histórico sai melhor pelo **PDF** que o
  próprio sistema emite — documento estável contra HTML que o §6 do recon mediu como
  instável —, a resposta certa é importar o arquivo e não raspar página nenhuma. Esse
  desfecho é vitória, não fracasso.

## Seu roteiro, quando tiver o navegador aberto

1. Entrar no JupiterWeb normalmente.
2. DevTools → Application → Cookies → copiar **`JSESSIONID` e `UD_jupiterweb`** (são dois; qual deles autentica é a primeira coisa que vamos medir).
3. `./scripts/jupiter-sessao.sh` e colar (a Fase 0 precisa estar pronta).
4. Salvar o HTML do menu logado em `fixtures/jupiter/raw/menu-logado.html`.
5. Me chamar. A partir daí eu trabalho da tabela, e cada requisição passa por você.

Passos 1, 2 e 4 são seus porque envolvem sua credencial — eu não manipulo senha, e o
desenho é assim de propósito.
