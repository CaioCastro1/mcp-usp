# Quem clonou não é mantenedor — design

> 17/09/2026. O repositório ficou público hoje. A partir de hoje a maioria
> esmagadora de quem clona é **usuária**: baixou uma ferramenta para perguntar
> do bandejão e do prazo de aula. O `CLAUDE.md` — o arquivo que todo assistente
> lê ao abrir a pasta — foi escrito quando só existiam duas pessoas, as duas
> mantenedoras, e ainda fala com elas.
>
> Este spec não muda uma linha de `usp_mcp/`. Ele muda quem o repositório supõe
> estar do outro lado, e isso vale um documento antes da edição pelo mesmo
> motivo que o §2.2 valeu: é mudança de decisão, não configuração.

- **Prioridade:** alta — o defeito reproduz em toda sessão nova desde hoje
- **Arquivos:** `CLAUDE.md`, `docs/agents/PAPEL-DA-SESSAO.md` (novo),
  `docs/agents/CONVENTIONS.md`, `.github/CONTRIBUTING.md`, `README.md`,
  `tests/test_papel_da_sessao.py` (novo)

## Sintoma observado

Um amigo do dono clonou o repositório na máquina dele e abriu o assistente. O
assistente **se comportou como mantenedor**: tratou o repositório como dele,
propôs mexer no código, propôs abrir PR, propôs rever decisão do projeto.

A pessoa é usuária. Ela queria saber o que tem no bandejão.

Isso não é o assistente inventando: é ele lendo corretamente o que está escrito.
Nenhuma correção pontual de prompt resolve, porque o próximo clone lê o mesmo
arquivo.

## A causa, conferida

A leitura do dono é que o `CLAUDE.md` é a causa. Confere, e dá para apontar as
linhas:

| linha | o que o assistente conclui |
|---|---|
| "Este é o cérebro compartilhado de todas as sessões de IA" | *a sessão em que estou é uma das "sessões" do projeto* |
| "Toda comunicação com o Caio é em português" | *quem está do outro lado é o Caio* |
| "`SPEC1.md` é a autoridade do projeto" + §6 inteiro | *tenho de consultar e manter esses documentos* |
| §5 "Fluxo padrão de uma mudança": branch → PR → merge | *minha saída natural é uma PR* |
| §5 "Definição de Pronto": registrar decisão no §9 | *eu registro decisão neste projeto* |
| §4, item 10: "Ferramenta não nasce por conveniência" | *eu decido que ferramenta existe* |

Seis linhas, nenhuma errada, e juntas elas descrevem uma sessão de manutenção
como se fosse a única que existe. O arquivo nunca teve por que dizer o
contrário: quando ele foi escrito, era.

### O que há além do `CLAUDE.md`

Varri o que é rastreado e chega a quem clona. Três achados:

1. **`docs/agents/CONVENTIONS.md`.** O diretório se chama `agents/`, o que um
   assistente lê como "isto é para mim", e o arquivo abre dizendo que complementa
   as regras não-negociáveis. O conteúdo é inteiro de manutenção: gate, formato de
   commit, fluxo de merge, sigla de teste. O próprio `.github/CONTRIBUTING.md` já
   registra que ele "tem o nome errado para quem chega". É o segundo empurrão na
   mesma direção, e o mais forte depois do `CLAUDE.md`.
2. **`.mcp.json` versionado na raiz.** Um cliente MCP aberto dentro do checkout
   registra os três servidores sozinho. Isso é bom e fica como está — mas
   significa que abrir o assistente **dentro da pasta do projeto** é um caminho
   de uso comum, e não a assinatura de uma sessão de desenvolvimento. Some com a
   última chance de tratar "está dentro do checkout" como sinal.
3. **O prompt do caminho rápido do `README.md`** (a mensagem que a pessoa cola no
   Claude Code) é uma sessão de uso que clona, cria venv, edita `.env` e registra
   servidor. Ou seja: **mexer em arquivo não é a fronteira**. Um assistente em
   sessão de uso legitimamente escreve no disco. A fronteira é outra, e o §Desenho
   a nomeia.

`.github/CONTRIBUTING.md` e o `README.md` estão certos: os dois falam com quem
chega, e o README diz na terceira tela que não é preciso saber programar nem
contribuir com nada. O problema não está neles.

## Os sinais que existem de verdade no disco

A pergunta operacional é: ao abrir a pasta, o que um assistente pode olhar?

| # | sinal | o que ele de fato prova | serve? |
|---|---|---|---|
| 1 | `.env` existe com `MOODLE_TOKEN` preenchido | que a pessoa seguiu a *Configuração* do README, que é o passo **de quem usa** | **não** — e aponta para o lado contrário do esperado |
| 2 | `origin` aponta para `CaioCastro1/usp-mcp` | nada: é o que `git clone` escreve em todo clone, o do dono e o do amigo | **não** — informação zero |
| 3 | a pessoa tem permissão de push | responde à pergunta errada (ver abaixo) e custa rede, credencial do GitHub e possivelmente um prompt de autenticação | **não — e não medir** |
| 4 | `git worktree list` com mais de uma linha | `git clone` nunca cria worktree, e ninguém cria uma sem querer | **sim, quando presente** |
| 5 | branch local diferente de `main`, ou commit à frente de `origin/main` | mesma família do 4, um degrau mais fraco (um `git checkout -b` curioso existe) | **sim, quando presente** |
| 6 | `fixtures/moodle/raw/` no disco | é gitignorado: só existe em máquina que rodou `scripts/capture.sh` | **sim, quando presente** |
| 7 | existem `CLAUDE.md`, `SPEC1.md`, `docs/`, `tests/`, `scripts/gate.sh`, `.mcp.json` | nada: os seis são rastreados e vêm em todo clone | **não** — e é esta a armadilha |
| 8 | `.venv` com `pytest` instalado | nada: o caminho rápido do README manda `pip install -e ".[dev]"` | **não** |

Três coisas a dizer em voz alta sobre esta tabela.

**O sinal 2 é o que provavelmente enganou.** "O `origin` aponta para o
repositório do dono" soa como prova de pertencimento e é o oposto: é a definição
de um clone. Se ele valesse, valeria para todo mundo no planeta que rodasse o
comando do README.

**O sinal 3 responde à pergunta errada, e por isso não entra nem como opcional.**
Papel é **da sessão, não da pessoa**: o dono também usa este projeto para
perguntar do bandejão, e nessas horas ele não quer um assistente propondo PR.
Além disso, descobrir permissão de push exige uma ida à rede com credencial —
`git push --dry-run` é uma ação de escrita feita para colher uma informação — e
falharia em classificar um mantenedor que simplesmente não está autenticado
naquele minuto.

**Os sinais 4, 5 e 6 são assimétricos, e é isso que decide o desenho.** Presentes,
provam manutenção com falso-positivo próximo de zero. Ausentes, não provam nada:
manutenção em clone simples, na branch `main`, sem fixture crua, é o caso normal
de um contribuidor novo. Nenhum conjunto de sinais de disco distingue os dois
lados; eles só sabem confirmar um.

É o mesmo formato honesto do spec de 15/09: o hash do plano prova que o plano não
mudou, e **não** que há um humano na frente. Aqui, a worktree prova manutenção, e
não a ausência dela. Um desenho que finja o contrário é teatro.

## Desenho

### 1. O padrão é uso, e ele não é detectado — é assumido

Ao abrir a pasta sem nada dito, o assistente assume **sessão de uso**.

Não porque os sinais digam isso, mas porque a assimetria dos erros manda:

- errar para o lado de uso custa uma frase ("na verdade eu quero mexer no código")
  e nada mais acontece;
- errar para o lado de manutenção custa o que já custou: propor alterar código,
  abrir PR e rever decisão de projeto na máquina de quem não é mantenedor.

E porque, desde hoje, uso é o caso majoritário por margem larga.

### 2. O que troca o papel

**O pedido da pessoa.** É o único sinal confiável, e uma frase basta. "Quero
mexer no código", "vamos consertar isso", "abre uma PR" — dito uma vez, a sessão
é de manutenção e continua sendo.

**Os sinais 4, 5 e 6, quando presentes**, valem como o mesmo pedido, feito com as
mãos em vez da boca. Quem está numa worktree com branch aberta não deve ser
perguntado se é mantenedor: perguntar ali é atrito puro.

Não existe terceiro caminho. Nada de pedir prova, nada de checar identidade do
git contra a lista de autores, nada de ir à rede.

### 3. O que muda no comportamento

**Sessão de uso** — o padrão:

- ajuda a **instalar** (o caminho manual do README, o venv dentro do clone, os
  três comandos), a **configurar** (`scripts/token.sh`, `.env`, o registro do
  servidor no cliente) e a **usar** (perguntar, entender a resposta, entender o
  limite do que o projeto não responde);
- diagnostica: a ferramenta `diagnostico`, o `./scripts/gate.sh`, ler a mensagem
  de erro inteira. Isso é suporte, não manutenção;
- **não propõe mexer no código**, não propõe PR, não propõe rever decisão do
  projeto, não escreve no `SPEC1.md`, no `docs/` nem no `notas/`;
- quando o defeito é do projeto e não da instalação, o destino é **issue**, em
  <https://github.com/CaioCastro1/usp-mcp/issues>, e há um modelo para cada um dos
  dois relatos que cobrem quase tudo. Nunca commit, nunca "eu conserto aqui";
- o que vale sempre: nunca imprimir o valor do `MOODLE_TOKEN`, nem em log, nem em
  issue.

**Sessão de manutenção** — ao pedido, ou com os sinais 4/5/6:

- vale o `CLAUDE.md` inteiro como está hoje: os invariantes, o fluxo de branch →
  PR → merge, a Definição de Pronto, o gate antes do commit, o `CONVENTIONS.md`.
  Nada aqui afrouxa nada disso.

**A fronteira entre os dois não é "mexer em arquivo"** — o prompt do caminho
rápido do README manda o assistente clonar, criar venv e escrever no `.env`. A
fronteira é **o código versionado e as decisões do projeto**: o que vira diff,
PR, entrada no §9 do `SPEC1.md`.

### 4. Onde a instrução mora: nos dois, com divisão de trabalho

**No `CLAUDE.md`, uma seção §0 antes do §1.** É o único arquivo que todo
assistente lê ao abrir a pasta — pôr o padrão em qualquer outro lugar é confiar
que alguém vá procurá-lo, e quem está no papel errado não sabe que deveria. Antes
do §1 porque a seção **muda o sentido de tudo que vem depois**: o §5 descreve o
fluxo de PR, e sem o §0 esse fluxo lê-se como o destino natural de toda sessão.

Isso não viola a regra de ser curto e sem estado, e vale explicar por quê, já que
a regra custou dois dias de mapa errado:

- **não é estado.** Não diz em que fase o projeto está, o que já foi construído
  nem quantos testes passam. Não envelhece quando o projeto anda;
- **não duplica o `SPEC1.md`.** Não afirma fato sobre API nenhuma, então não há
  como divergir dele;
- **é curto por construção:** o §0 é o padrão e o gatilho, não o manual. O detalhe
  desce um nível, que é o que o rodapé do próprio arquivo manda fazer.

**Em `docs/agents/PAPEL-DA-SESSAO.md`, o detalhe.** A tabela de sinais com o
veredito de cada um, o que fazer numa sessão de uso, o que não fazer, e a válvula.
É o "COMO", e por convenção deste repositório o COMO mora em `docs/`.

Por que arquivo novo e não uma seção do `CONVENTIONS.md`: o `CONVENTIONS.md` é
inteiro de manutenção, e mandar uma sessão de uso lê-lo é entregar exatamente o
material que produziu o defeito. Ele ganha, em vez disso, **uma linha no topo**
dizendo para quem ele é — o que também cura o "nome errado para quem chega" que o
`CONTRIBUTING.md` já tinha registrado.

**No `README.md`, uma linha para a pessoa, não para o assistente.** Quem está do
outro lado do defeito é gente, e gente merece saber que pode dizer "eu só quero
usar". Vai em *Escopo e contribuição*, que é a seção do assunto; nada nas seções
que `D1`–`D3` guardam.

**No `.github/CONTRIBUTING.md`, a válvula.** Uma frase dizendo que o padrão é uso
e que basta pedir — para que quem de fato veio contribuir não interprete o §0 como
porta fechada.

Em nenhum dos quatro o conteúdo é copiado. Cópia diverge, e a divergência aparece
quando alguém confia nela — a regra já está escrita no `CONTRIBUTING.md` e vale
aqui.

## O que NÃO fazer

Isto é metade do desenho, e a metade que dá errado sozinha.

1. **Não virar cerca.** O README convida a contribuir e isso é bom e fica. O §0 é
   um **padrão**, não uma permissão: ele diz de onde a sessão parte, não o que ela
   pode. Uma frase troca, sem cerimônia e sem justificativa.
2. **Não pedir prova.** Nada de "você é mantenedor?", nada de conferir
   `git config user.email` contra a lista de autores, nada de exigir que alguém
   demonstre pertencimento. Um contribuidor novo é indistinguível de um usuário
   por qualquer sinal de disco, e é justamente ele quem não pode levar atrito.
3. **Não medir permissão de push.** Pelos três motivos da tabela: pergunta errada,
   custo de rede e credencial, e resposta que falha em quem não está autenticado.
4. **Não perguntar quando os sinais 4/5/6 já responderam.** Quem está numa
   worktree com branch aberta não deve ser interrogado.
5. **Não recusar ajuda técnica a quem usa.** Instalar, criar venv, editar `.env`,
   rodar `token.sh`, ler log, registrar servidor no cliente: tudo isso é uso. A
   fronteira é o código versionado e as decisões, não o teclado.
6. **Não pôr estado no `CLAUDE.md`** a pretexto desta mudança. O §0 é orientação
   de papel e nada mais.
7. **Não copiar o conteúdo entre os quatro arquivos.**

## Bateria de testes — `tests/test_papel_da_sessao.py`

Offline, puros, custam um `read_text` por arquivo, e entram no gate junto com o
resto. Sem marcador, pelo mesmo motivo do `tests/test_documentacao.py`: não são
allowlist nem forma contra fixture.

| id | teste | asserção |
|---|---|---|
| PS1 | `test_ps1_o_claude_md_declara_o_papel_antes_do_produto` | o `CLAUDE.md` tem a seção de papel e o índice dela é **menor** que o do `## 1. O produto`. Quem lê de cima para baixo decide o papel antes de decidir o que fazer |
| PS2 | `test_ps2_o_claude_md_aponta_para_o_detalhe_e_o_detalhe_existe` | o `CLAUDE.md` cita `docs/agents/PAPEL-DA-SESSAO.md` e o arquivo existe. Ponteiro morto é pior que ausência |
| PS3 | `test_ps3_o_detalhe_diz_quais_sinais_nao_servem` | `PAPEL-DA-SESSAO.md` nomeia `.env`, `origin` e push como sinais que **não** servem. É a parte mais fácil de apagar numa revisão de estilo, e é a que carrega o achado |
| PS4 | `test_ps4_o_conventions_declara_para_quem_e` | `docs/agents/CONVENTIONS.md` diz, antes da primeira seção, que é de sessão de manutenção |
| PS5 | `test_ps5_a_valvula_existe_nos_dois_lados` | o `CLAUDE.md` e o `.github/CONTRIBUTING.md` dizem que uma frase troca o papel, e o `README.md` continua convidando a abrir issue e PR. É o anti-cerca, e é a asserção que reprova se esta mudança virar portão |

`PS5` é a que mais importa. `PS1`–`PS4` afirmam que a orientação chegou; só a
`PS5` afirma que ela não fechou a porta que o README abre.

## Critério de parada

As cinco passam, `./scripts/gate.sh` passa 4/4, e a suíte não ganha nenhum
vermelho novo — a baseline desta branch é `1 failed, 940 passed, 11 skipped`, com
o vermelho em `test_t58_o_cru_quando_existe_reproduz_a_publicada[users_courses.json]`,
anterior a este trabalho e sendo consertado em outra frente.

O `CLAUDE.md` continua sem estado: nada do que entra aqui responde "em que pé
estamos".

## O que precisa ir para o §9

Esta branch não toca o `SPEC1.md`, por instrução. Fica registrado o que a próxima
sessão precisa escrever lá, com data de 17/09/2026:

1. que o repositório ficou público e que o papel padrão de uma sessão passou a ser
   **uso**, não manutenção;
2. que nenhum sinal de disco distingue os dois papéis — `.env` e `origin` apontam
   para o lado errado, e worktree/branch/`fixtures/moodle/raw/` só sabem confirmar
   manutenção, nunca negá-la;
3. que o papel é **da sessão e não da pessoa**: o dono também tem sessões de uso, e
   é por isso que permissão de push não é o critério.

O terceiro é o que evita a volta do defeito pelo caminho do meio, que seria trocar
"todo mundo é mantenedor" por "quem tem push é mantenedor".
