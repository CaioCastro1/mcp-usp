# PAPEL DA SESSÃO — uso ou manutenção

> O detalhe do **§0 do `CLAUDE.md`**, que é onde o padrão está declarado. Aqui
> ficam os sinais com o veredito de cada um, o que fazer de um lado e do outro, e
> o que não fazer. O desenho e a medição que produziram este arquivo estão em
> `docs/superpowers/specs/2026-09-17-usuario-nao-e-mantenedor-design.md`.
>
> Vale para assistente e para gente. Não copia regra do `CLAUDE.md`: aponta.

## Por que este arquivo existe

Um amigo do dono clonou o repositório e abriu o assistente. O assistente se
comportou como mantenedor: tratou o repositório como dele, propôs mexer no
código, propôs abrir PR, propôs rever decisão do projeto. A pessoa queria saber o
que tem no bandejão.

O assistente não inventou nada — leu corretamente um `CLAUDE.md` escrito quando
só existiam duas pessoas no projeto, as duas mantenedoras. Desde 17/09/2026 o
repositório é público, e essa suposição deixou de valer para a maioria de quem
chega.

## O padrão: uso

Sem nada dito, a sessão é **de uso**. Não porque algum sinal prove isso, mas
porque os dois erros custam preços muito diferentes:

- tratar um mantenedor como usuário custa uma frase de correção;
- tratar um usuário como mantenedor é o defeito acima.

## Os sinais no disco, um por um

| # | sinal | o que ele de fato prova | serve? |
|---|---|---|---|
| 1 | `.env` existe com `MOODLE_TOKEN` preenchido | que a pessoa seguiu a *Configuração* do README — o passo **de quem usa** | **não**, e aponta para o lado contrário |
| 2 | `origin` aponta para `CaioCastro1/usp-mcp` | nada: é o que `git clone` escreve em todo clone | **não** |
| 3 | a pessoa tem permissão de push | pergunta errada, e custa rede + credencial do GitHub | **não — e não medir** |
| 4 | `git worktree list` com mais de uma linha | `git clone` não cria worktree, e ninguém cria uma sem querer | **sim, quando presente** |
| 5 | branch local fora da `main`, ou commit à frente de `origin/main` | mesma família do 4, um degrau mais fraco | **sim, quando presente** |
| 6 | `fixtures/moodle/raw/` no disco | é gitignorado: só existe em máquina que rodou `scripts/capture.sh` | **sim, quando presente** |
| 7 | existem `CLAUDE.md`, `SPEC1.md`, `docs/`, `tests/`, `scripts/gate.sh`, `.mcp.json` | nada: os seis são rastreados e vêm em todo clone | **não**, e é a armadilha |
| 8 | `.venv` com `pytest` instalado | nada: o caminho rápido do README manda `pip install -e ".[dev]"` | **não** |

Três leituras que a tabela não dá sozinha:

**O sinal 2 é o que engana.** "O `origin` aponta para o repositório do dono" soa
como prova de pertencimento e é a definição de um clone qualquer. Se valesse,
valeria para todo mundo que rodasse o comando do README.

**O sinal 3 responde à pergunta errada.** O papel é **da sessão, não da pessoa**:
o dono também usa este projeto para perguntar do bandejão, e nessas horas não
quer um assistente propondo PR. Descobrir permissão de push ainda exigiria ir à
rede com credencial — `git push --dry-run` é uma escrita feita para colher
informação — e classificaria errado um mantenedor que não está autenticado
naquele minuto.

**Os sinais 4, 5 e 6 são assimétricos.** Presentes, provam manutenção. Ausentes,
não provam nada: um contribuidor novo, em clone simples, na `main`, é
indistinguível de um usuário por qualquer sinal de disco. Eles confirmam
manutenção; nunca a negam.

## Sessão de uso: o que fazer

- **Instalar.** O caminho manual do README, o venv **dentro** do clone, o
  `pip install -e`, o `cp .env.example .env`, os três comandos `usp-mcp-*`.
- **Configurar.** `scripts/token.sh` para a chave do e-Disciplinas (o passo do
  navegador é da pessoa, e é ela quem clica), o registro dos três servidores no
  Claude Desktop, no Claude Code ou em outro cliente MCP.
- **Usar.** Ajudar a formular a pergunta, a entender a resposta e a entender o
  que o projeto **não** responde — a seção *O que o projeto não responde, e por
  quê* do README existe para isso.
- **Diagnosticar.** A ferramenta `diagnostico`, o `./scripts/gate.sh`, a mensagem
  de erro inteira.

## Sessão de uso: o que não fazer

- Não propor mexer no código, não propor PR, não propor rever decisão do projeto.
- Não escrever em `SPEC1.md`, `docs/`, `notas/` nem `usp_mcp/`.
- Não commitar. Se o defeito é do projeto e não da instalação, o destino é
  **issue**: <https://github.com/CaioCastro1/usp-mcp/issues>, onde há um modelo
  para cada um dos dois relatos que cobrem quase tudo — "a USP mudou e a
  ferramenta parou" e "meu token não funciona".
- Não imprimir, ecoar ou colar o valor do `MOODLE_TOKEN`, em lugar nenhum.

**A fronteira não é "mexer em arquivo".** O prompt do caminho rápido do README
manda o assistente clonar, criar venv e escrever no `.env`: isso é uso. A
fronteira é o **código versionado e as decisões do projeto** — o que vira diff,
PR ou entrada datada no §9 do `SPEC1.md`.

## Como a sessão vira de manutenção

Uma frase basta: "quero mexer no código", "vamos consertar isso", "abre uma PR".
Dita uma vez, a sessão é de manutenção e continua sendo. Os sinais 4, 5 e 6 valem
como o mesmo pedido feito com as mãos.

A partir daí vale o `CLAUDE.md` inteiro: os invariantes do §4, o fluxo branch →
PR → merge do §5, a Definição de Pronto, o `./scripts/gate.sh` antes do commit e
o `docs/agents/CONVENTIONS.md`. Nada aqui afrouxa nada disso. Quem vai abrir PR
lê o `.github/CONTRIBUTING.md`.

## Isto é um padrão, não uma cerca

O README convida a contribuir e esse convite fica. O §0 diz de onde a sessão
**parte**, não o que ela **pode**.

- Não peça prova. Nada de "você é mantenedor?", nada de comparar
  `git config user.email` com a lista de autores. Um contribuidor novo é
  exatamente quem não pode levar atrito.
- Não pergunte quando os sinais 4/5/6 já responderam.
- Não recuse ajuda técnica a quem usa: instalar, criar venv, editar `.env`, ler
  log e registrar servidor no cliente é tudo uso.
- Não transforme isto em estado no `CLAUDE.md`. O §0 é orientação de papel e nada
  mais.
