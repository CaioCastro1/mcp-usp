# usp-mcp

Ferramentas para responder perguntas sobre a vida acadêmica na USP: cardápio dos
bandejões, prazos e material do e-Disciplinas, catálogo de disciplinas do JupiterWeb.

Projeto não-oficial, sem nenhum vínculo com a Universidade de São Paulo. Usa APIs não
documentadas, descobertas por observação. Elas podem mudar ou sumir sem aviso, e "está
público" não equivale a "liberado para redistribuir" (ver Invariante 8 do `SPEC1.md`).

## Estado (14/09/2026)

Três servidores MCP rodando, sete ferramentas, todas verificadas contra a USP.

| Servidor | Ferramenta | Responde |
|---|---|---|
| `usp-rucard` | `bandejao` | O que tem no bandejão hoje, e onde vale a pena comer |
| `usp-moodle` | `o_que_vence` | O que tenho para entregar nos próximos N dias |
| `usp-moodle` | `material` | Que arquivos tem no espaço da disciplina: regras, listas, provas antigas |
| `usp-moodle` | `baixar_arquivo` | Baixa um desses arquivos e devolve o caminho dele no disco |
| `usp-moodle` | `diagnostico` | Se este servidor funciona no Moodle configurado, e o que o seu token alcança lá |
| `usp-jupiter` | `disciplina` | Créditos, carga horária, ementa e programa, pela sigla |
| `usp-jupiter` | `requisitos` | O que é preciso ter cursado antes, por currículo, e o que dá para cursar junto |

`baixar_arquivo` entrega o caminho, não o conteúdo. Quem lê o PDF é o agente que chamou,
com a ferramenta de leitura dele. Um blob em base64 custaria cerca de 302k tokens no PDF
médio, e extrair o texto no servidor perderia as figuras. Pior: numa lista manuscrita
escaneada isso devolveria 9 bytes e chamaria de sucesso (§9, 01/09 e 03/09). O arquivo cai
em `~/.cache/usp-mcp/moodle/`, fora do repositório.

### O que o projeto não responde, e por quê

Nota, histórico escolar, evolução do curso e saldo do RUCard ficam de fora. O motivo é
falta de caminho, não de trabalho. Medido em 14/09:

- A superfície pública estruturada do JupiterWeb é o catálogo de entrada. A grade
  curricular dos cursos de ingresso da Poli para no 5º semestre (medido em quatro cursos),
  e da ênfase (7º) e do módulo (9º) em diante não há grade, requisito nem código de curso
  alcançável.
- Dado pessoal exige a área logada, que não oferece token como o Moodle. Só sessão de
  navegador, com dois cookies e timeout de inatividade ainda não medido.

O roteiro para medir isso está em
`docs/superpowers/plans/2026-09-14-jupiter-sessao-recon.md`, com as regras que valem desde
a primeira requisição. Nada dele foi executado até agora.

Também não existem: notas, "já entreguei?", aviso de professor, histórico de cardápio,
saldo do cartão, horário, sala e vagas. `material` diz o nome, o tipo e o tamanho de cada
arquivo, mas não emite a URL interna dele. Endereço sem a credencial não abre, e quem
resolve isso é `baixar_arquivo`, sem nunca pôr o token numa URL.

Empacotar como MCP Bundle (`.mcpb`) segue sem teste. O §6.1 o descreve por leitura de
documentação, e ele é o degrau seguinte ao pacote que já existe.

Ferramenta não nasce por conveniência: o critério está no §5, e as questões abertas do §4
fecham com dado registrado no §9. Comece por `SPEC1.md`. Ele é a autoridade do projeto, e
o §9 registra cada decisão tomada, com o dado que a fechou e o que foi descartado.

- `usp_mcp/`, os servidores, um pacote por sistema
- `tests/`, três camadas: política e contrato offline, `live` atrás de env var
- `notas/`, análise por sistema, com custo medido em bytes e tokens
- `fixtures/`, respostas cruas capturadas (as do Moodle ficam fora do git, porque têm dado pessoal)
- `scripts/`, chamadores da descoberta e o gate de pré-commit
- `docs/decisions/BACKLOG-correcoes.md`, a dívida que está em aberto

## Como funciona

Cada servidor é um processo que fala MCP por stdio. O cliente sobe o processo, os dois
trocam JSON-RPC pela entrada e saída padrão, e ninguém abre porta de rede. Se você rodar
`usp-mcp-rucard` no terminal e a tela ficar parada, é isso mesmo: não há prompt nem
interface.

Quem escolhe a ferramenta é o modelo, lendo a descrição dela diante de uma pergunta em
português. Por isso as descrições usam o vocabulário de quem pergunta ("o que vence",
"que arquivos tem") e não o nome da função do Moodle por trás. Descrição ruim faz o modelo
não achar a ferramenta, por melhor que ela seja.

Entre o modelo e a USP existem duas travas. A primeira é uma allowlist: só saem daqui as
funções nomeadas nela, por igualdade exata, e o default é negar. A segunda é o bloqueio
permanente do §2.2, que vale mesmo com a flag de escrita ligada. Ele cobre o que não deve
ser chamado em hipótese nenhuma, como começar tentativa de prova, entregar trabalho ou
falar com terceiros em nome de quem usa. As duas existem porque o token alcança 447
funções neste site, e quem escolhe qual chamar é um modelo interpretando linguagem
ambígua.

A credencial do Moodle é pessoal e fica no `.env` da máquina de quem usa. Ela não viaja
para servidor hospedado nem para sandbox em nuvem, e é por isso que o Moodle roda local.
O RUCard e o Jupiter não usam credencial nenhuma.

Cada resposta é projetada antes de chegar ao modelo. A lista de disciplinas sai de 104.712
bytes para 7.816, e o resto do transporte fica no servidor. Payload cru enche a janela de
contexto com metadado que não responde a pergunta nenhuma, e o §9 registra a medição de
cada corte.

## Instalando

### Só usar

Quem só quer rodar os servidores não precisa de checkout.

```bash
pipx install <CAMINHO-OU-URL-DO-REPOSITORIO>
usp-mcp-rucard   # sobe o servidor stdio; ele fala JSON-RPC, não tem prompt
```

O cliente MCP aponta para o comando, sem `args` e sem caminho de projeto:

```json
{
  "mcpServers": {
    "usp-rucard": { "command": "usp-mcp-rucard" },
    "usp-jupiter": { "command": "usp-mcp-jupiter" },
    "usp-moodle": { "command": "usp-mcp-moodle" }
  }
}
```

São três comandos, e não um com argumento, de propósito: o nome de cada um é o mesmo
`serverInfo.name` que o servidor responde no `initialize`. O porquê está escrito no
`pyproject.toml`, ao lado da tabela.

Nem todo caminho acima foi exercitado. O que foi medido em 14/09/2026: `pip install -e`
num venv limpo, e os três comandos subindo a partir de `/tmp` com cliente MCP real, cada
um se anunciando com o próprio nome. `pipx`, `uvx` e instalar direto da URL do repositório
são portas que o `pyproject.toml` abre e que ninguém atravessou ainda. A distinção entre
"abre" e "foi usado" é a mesma que o §6.1 faz sobre o `.mcpb`. Se você rodar primeiro,
registre.

Só o código vem no pacote. O `.env` é seu, e a *Configuração* abaixo continua valendo.

### Mexer no código

Aqui o checkout é necessário, porque os scripts e a suíte moram nele.

```bash
git clone git@github.com:CaioCastro1/mcp-usp.git && cd mcp-usp
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./scripts/gate.sh
```

O `-e` aponta para este checkout. Nada é copiado para o site-packages, editar o código
muda o que os comandos sobem, e `usp-mcp-moodle`, `usp-mcp-jupiter` e `usp-mcp-rucard`
passam a existir em `.venv/bin/`. O extra `[dev]` acrescenta o `pytest`, que não é
dependência do produto.

O `cp` vem antes do gate porque sem `.env` ele reprova. A hash do RUCard é o único valor
que o gate precisa, e ela já vem preenchida no exemplo: é a chave embutida no app oficial,
pública e compartilhada, não credencial de ninguém. O token do Moodle nasce vazio e não
precisa ser preenchido para o gate passar, porque o gate roda offline.

O `.mcp.json` versionado já registra os três servidores, sem segredo. Abra um cliente MCP
neste diretório e pergunte. Cada entrada chama `scripts/servidor.sh <sistema>`, e quem
resolve a raiz do checkout é o script, não o cliente.

### Cliente que não faz `cd`

O `.mcp.json` é relativo de propósito: ele é versionado e compartilhado, e caminho
absoluto de máquina não entra em arquivo rastreado (Invariante 3 aplicado a caminho).
Relativo funciona em cliente que roda o servidor com o diretório de trabalho na raiz do
projeto, como o Claude Code faz. O Claude Desktop e afins não fazem, e lá o caminho
relativo falha com `no such file or directory`.

Para esses, aponte para o caminho absoluto do lançador. Ele é o único absoluto que
aparece, e mora no arquivo de config da sua máquina, não aqui:

```json
{
  "mcpServers": {
    "usp-rucard": {
      "command": "<CAMINHO-DO-CHECKOUT>/scripts/servidor.sh",
      "args": ["rucard"]
    },
    "usp-jupiter": {
      "command": "<CAMINHO-DO-CHECKOUT>/scripts/servidor.sh",
      "args": ["jupiter"]
    },
    "usp-moodle": {
      "command": "<CAMINHO-DO-CHECKOUT>/scripts/servidor.sh",
      "args": ["moodle"]
    }
  }
}
```

Troque `<CAMINHO-DO-CHECKOUT>` pela saída de `pwd` neste diretório. O `cd` de dentro do
script resolve o resto, inclusive achar o `.venv`, que é por diretório e não vem no git.

## Configuração

O `cp .env.example .env` da seção acima é o passo, e é um só. `RUCARD_HASH` já vem
preenchida. `MOODLE_TOKEN` nasce vazio e é o único valor a obter: é credencial pessoal,
nunca sai da máquina de quem usa (Invariante 4), e quem busca ele é `./scripts/token.sh`.

## Para quem acabou de ganhar acesso

O token é seu, não de quem te convidou. Cada pessoa traz o seu. Esse atrito não é
acidental: é o Invariante 4, e é o que permite este projeto existir sem ninguém confiar
credencial a ninguém.

**1. Monte o ambiente.** Siga *Mexer no código*, acima. Os passos 2 a 4 usam o checkout,
então ele é o caminho daqui em diante. Quem só quer usar o servidor pula o clone inteiro e
vai por *Só usar*.

**2. Pegue seu token do e-Disciplinas.** Um comando, com o navegador logado na Senha Única:

```bash
./scripts/token.sh
```

Ele abre o `launch.php` e a página do Moodle aparece com três coisas. Duas são chamariz: a
caixa verde "O seu cadastro foi confirmado" e o botão cinza "Ambientes". A que interessa é
o link azul escrito *"Clique aqui se a aplicação não abrir automaticamente"*. O texto
sugere que ele é um plano B dispensável, mas o endereço dele é o único lugar da página
onde o token existe.

Botão direito nesse link, "copiar endereço do link", volta no terminal e aperta Enter. Não
clique com o esquerdo: clicar tenta abrir o app do Moodle e não copia nada. Leva uns 20
segundos, sem DevTools e sem decodificar nada à mão.

Antes de decodificar, o script confere o que chegou. Se você copiou a URL da página em vez
da do link, que é o erro mais comum e o que aconteceu na primeira passagem de 12/09/2026,
ele para ali, explica a diferença entre a URL de ida e a de volta, e deixa o `.env`
intocado. A conferência mostra no máximo `moodlemobile://token=` e nunca um byte do que
vem depois.

Daí ele decodifica, confirma o token contra a USP em uma chamada e só então grava no
`.env`. Um token que não autentica não chega ao arquivo, e o `userid` sai da mesma
resposta. O valor do token nunca é impresso, nem parcial (Invariante 3).

Se você já tinha colado a URL no `.env` à mão e ela ficou torta, `./scripts/fix-token.sh`
normaliza. É idempotente e detecta quando já está nos 32 hex.

Existe um `--auto` que tenta capturar o redirect sozinho, com um handler temporário para
um esquema próprio. Ele funciona contra servidor de teste e nunca entregou contra o
e-Disciplinas, então não é o padrão (§9 do `SPEC1.md`, 11/09/2026).

**3. Confira sem gastar chamada nenhuma da sua conta.**

```bash
./scripts/gate.sh
.venv/bin/python -m usp_mcp.moodle.server --auto-verificar
```

O `--auto-verificar` diz se o `.env` foi achado, se o token está presente (sem mostrá-lo),
se o SDK está instalado e se os schemas casam. Nada disso toca a rede da USP.

**4. Ligue num cliente MCP.** O `.mcp.json` versionado já registra os três servidores sem
segredo nenhum: abra o Claude Code nesta pasta e pergunte. Para que valham em qualquer
pasta, registre no escopo de usuário:

```bash
R=$(pwd); for m in moodle jupiter rucard; do claude mcp add --scope user "usp-$m" -- $R/scripts/servidor.sh $m; done
```

Dois lugares onde nada disso funciona, e não é questão de configuração: sandbox em nuvem,
porque a rede da USP não sai de lá (§1.1), e conector remoto, porque o token não pode
viajar (Invariante 4) e o e-Disciplinas não oferece OAuth. O Moodle é local por desenho. O
RUCard e o Jupiter não usam credencial e poderiam ser hospedados, mas não estão (§6).

Seu token expira e é revogável em `edisciplinas.usp.br`, em gerenciar tokens. Se algo
parar de responder com `invalidtoken`, é isso: rode `./scripts/token.sh` de novo. Não há
caminho sem sessão de navegador, porque a conta autentica por Senha Única e o Moodle não
tem senha local para comparar (§1.3).
