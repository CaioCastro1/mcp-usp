# Como contribuir

O README convida a abrir issue ou pull request. Este arquivo diz o que é preciso
para que a sua PR seja aceita.

Ele é curto de propósito. Quase tudo que você precisa saber está em
[`docs/agents/CONVENTIONS.md`](docs/agents/CONVENTIONS.md), que tem o nome errado
para quem chega: o arquivo é das convenções do repositório, e vale para gente
tanto quanto para agente. Aqui ficam só as regras que não se negociam, com o
ponteiro para onde cada uma é explicada. **O detalhe não é copiado**, porque
cópia diverge do original e a divergência aparece justamente quando alguém
confia nela.

Leia também o [`CLAUDE.md`](CLAUDE.md), que tem os comandos do dia a dia e as
regras críticas em uma página. A autoridade sobre qualquer fato do projeto é o
`SPEC1.md`.

## As quatro que não se negociam

**1. `./scripts/gate.sh` verde antes de commitar.** O gate checa o `.env`, se
algum segredo entrou em arquivo rastreado, se o cru com dado pessoal continua
ignorado, e a suíte offline inteira. Ele não toca a rede da USP e não pede
credencial nenhuma. Se ele reprovar, o problema é o código ou o dado: nunca
afrouxe uma checagem para passar. O que cada checagem faz e por que ela está
naquela ordem está no §4 do `CONVENTIONS.md`.

**2. Escreva em português.** Código, comentário, nome de teste, mensagem de erro,
PR e issue. O projeto responde perguntas em português a quem estuda na USP, e a
mensagem que o usuário lê sai do mesmo lugar que o comentário que você escreve.

**3. Mensagem de commit no formato `tipo(escopo): descrição`**, com o tipo entre
`feat`, `fix`, `chore`, `docs` e `test`. Branch curta saindo da `main`, PR para a
`main`, e nunca force-push na `main`. Trabalho em várias etapas tem um desenho
próprio, com uma branch guarda-chuva, descrito no §5 do `CONVENTIONS.md`.

**4. Decisão fechada vira entrada datada no registro de decisões.** O registro é
o §9 do `SPEC1.md`, e a entrada diz a data, o dado que fechou a questão e o que
foi descartado. Isso vale para decisão sobre conhecimento (um fato novo sobre uma
API da USP, uma questão aberta que fechou) tanto quanto para decisão sobre
código. Medição longa e análise vão para `notas/`. O que não está registrado
existe só na janela de quem conversou, e some.

## Antes de abrir a PR

Vale reler a Definição de Pronto do §5 do `CLAUDE.md`. Em resumo: o dado que
sustenta a mudança está registrado, nenhum segredo nem dado pessoal entrou no
git, e o que você achou de passagem foi para
[`docs/decisions/BACKLOG-correcoes.md`](docs/decisions/BACKLOG-correcoes.md) em
vez de virar desvio.

Duas coisas que costumam surpreender quem chega:

- **O `.venv` é por diretório e não vem no git.** Todo checkout novo precisa do
  seu. O README tem a sequência exata.
- **Você precisa clonar, não baixar o ZIP.** O gate pergunta ao git quais
  arquivos estão rastreados e quais estão ignorados, e sem `.git` ele reprova
  logo no primeiro passo dizendo isso.

Nunca imprima, ecoe ou cole o valor de um `MOODLE_TOKEN`, nem em issue, nem em
PR, nem em log. Ele é credencial pessoal de uma pessoa e cada chamada feita com
ele fica no log da conta dela.

## Issue

Dois relatos cobrem quase tudo que chega, e os dois ficam melhores com a mesma
informação: o que você pediu ao assistente, o que veio, e o que você esperava.

- **A USP mudou e a ferramenta parou.** Diga qual pergunta parou de funcionar e
  cole a mensagem de erro inteira. Se souber, diga desde quando.
- **Meu token não funciona.** Diga em que passo do `./scripts/token.sh` você
  travou e o que apareceu na tela. **Não cole o token.**

Mudança no código precisa de aprovação do dono do repositório. Sugestão é
bem-vinda pelo caminho normal do GitHub, em
<https://github.com/CaioCastro1/mcp-usp/issues>.
