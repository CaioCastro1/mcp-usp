# usp-mcp

Um jeito de perguntar, em português, coisas da vida acadêmica na USP: o que tem no
bandejão hoje, o que você tem para entregar essa semana, que arquivos o professor subiu no
e-Disciplinas, quantos créditos vale uma disciplina e qual é o pré-requisito dela.

Você não usa isto direto. Ele se liga num assistente (o Claude, por exemplo) e passa a ser
uma coisa que o assistente sabe consultar. Aí você pergunta normal, como perguntaria para
um amigo, e a resposta vem do sistema da USP de verdade.

Projeto não-oficial, sem nenhum vínculo com a Universidade de São Paulo.

## O que ele responde

| Pergunta que você faz | Onde ele busca |
|---|---|
| "O que tem no bandejão hoje?" | Cardápio dos quatro restaurantes, com horário e preço |
| "O que eu tenho para entregar essa semana?" | Tarefas e questionários do e-Disciplinas, com prazo |
| "Que arquivos tem em PTC3314?" | Lista o material da disciplina: regras, listas, provas antigas |
| "Baixa a lista 2 pra mim" | Baixa o arquivo e diz onde ele ficou no seu computador |
| "Quantos créditos vale MAC0110?" | Créditos, carga horária, ementa e programa, pelo JupiterWeb |
| "O que preciso ter feito antes de MAT2454?" | Pré-requisitos, pelo seu currículo |

Bandejão e JupiterWeb funcionam para qualquer pessoa. O e-Disciplinas mostra as **suas**
disciplinas, então ele precisa de uma chave sua, e obter essa chave dá um pouco mais de
trabalho. A seção *Configuração* explica.

## Instalando

Duas coisas antes de começar. Isto roda no Terminal do seu computador, Mac ou Linux, e
não tem tela nem botão. E você precisa de um assistente que aceite conectar ferramentas,
como o Claude Desktop ou o Claude Code.

Abra o Terminal e cole estes dois comandos, um de cada vez:

```bash
python3 -m venv ~/usp-mcp
~/usp-mcp/bin/pip install git+https://github.com/CaioCastro1/mcp-usp.git
```

O primeiro cria uma pastinha isolada na sua conta, para não bagunçar nada que já esteja no
computador. O segundo baixa o programa lá dentro.

Se o Terminal responder que não conhece o comando `python3`, é porque ele ainda não está
instalado na sua máquina. Instale primeiro, pelo site python.org, e repita os dois
comandos.

Para conferir se deu certo:

```bash
ls ~/usp-mcp/bin | grep usp
```

Tem que aparecer `usp-mcp-jupiter`, `usp-mcp-moodle` e `usp-mcp-rucard`.

Agora avise o assistente que eles existem. No Claude Desktop, abra as configurações de
conectores e cole isto, trocando `SEU-USUARIO` pelo nome da sua conta no computador (se
não souber, o comando `whoami` no Terminal responde):

```json
{
  "mcpServers": {
    "usp-rucard": { "command": "/Users/SEU-USUARIO/usp-mcp/bin/usp-mcp-rucard" },
    "usp-jupiter": { "command": "/Users/SEU-USUARIO/usp-mcp/bin/usp-mcp-jupiter" },
    "usp-moodle": { "command": "/Users/SEU-USUARIO/usp-mcp/bin/usp-mcp-moodle" }
  }
}
```

Feche e abra o assistente. Pronto: bandejão e JupiterWeb já respondem. O e-Disciplinas
ainda vai reclamar que falta a chave, e é a próxima seção.

Se algo não funcionar, peça ao assistente para rodar a ferramenta `diagnostico`. Ela diz o
que está no lugar e o que não está.

## Configuração

Só o e-Disciplinas precisa disto. Bandejão e JupiterWeb funcionam sem nada.

A chave é sua e pessoal, e cada pessoa obtém a dela. Ela nunca sai do seu computador, e é
por isso que ninguém pode te dar uma pronta.

Para obtê-la você precisa do projeto baixado inteiro, e não só do programa instalado
acima, porque o script que faz isso não vem junto no pacote. Siga *Rodando a partir do
código* até o fim do primeiro bloco de comandos, e depois rode:

```bash
./scripts/token.sh
```

Ele abre uma página do e-Disciplinas no seu navegador. Você precisa já estar logado na
Senha Única. A página mostra três coisas, e duas são distração: a caixa verde "O seu
cadastro foi confirmado" e o botão cinza "Ambientes". O que importa é o link azul escrito
"Clique aqui se a aplicação não abrir automaticamente".

Clique nele com o **botão direito** e escolha "copiar endereço do link". Não clique com o
esquerdo: isso tenta abrir o aplicativo do Moodle e não copia nada. Volte no Terminal e
aperte Enter.

O script confere o que você copiou, testa a chave contra a USP e só então guarda. Se você
copiou o endereço errado, ele avisa e não estraga nada. A chave nunca aparece na tela.

Ela fica guardada num arquivo chamado `.env`, na linha `MOODLE_TOKEN`. Você não precisa
abrir esse arquivo, mas se um dia abrir, é essa a linha.

Ela vence com o tempo e pode ser cancelada em `edisciplinas.usp.br`, em gerenciar tokens.
Se um dia o e-Disciplinas parar de responder, rode `./scripts/token.sh` de novo.

## Usando

Depois de conectado, é só perguntar. Alguns exemplos do que funciona:

- "o que tem no bandejão da Física hoje no jantar?"
- "tem alguma coisa vencendo nos próximos 3 dias?"
- "quais arquivos tem em PTC3314?"
- "baixa o EP1 de PTC3314 e me explica o que ele pede"
- "quantos créditos vale MAC0110 e qual é a ementa?"

A última é a que mostra a graça da coisa: ele baixa o PDF e o próprio assistente lê o
arquivo para te responder.

Se você pedir algo que ele não sabe, a resposta diz o que faltou em vez de inventar. Vale
ler a seção *O que o projeto não responde* antes de concluir que quebrou.

## Como funciona

Cada um dos três comandos é um programinha que fica esperando o assistente perguntar. Eles
não abrem site, não abrem porta de rede e não têm tela. Se você rodar um deles no Terminal
e não acontecer nada, é assim mesmo.

Quem decide qual ferramenta usar é o assistente, lendo a descrição de cada uma diante da
sua pergunta. Por isso as descrições são escritas na linguagem de quem pergunta, e não com
o nome técnico da função por trás.

O acesso à USP é limitado de propósito. De todas as operações que a sua chave permitiria,
só um punhado está liberado aqui, e todas são de leitura. Coisas como começar uma prova,
entregar um trabalho ou mandar mensagem em seu nome estão bloqueadas e continuam
bloqueadas mesmo se alguém ligar a permissão de escrita. O motivo é simples: quem escolhe
o que chamar é um assistente interpretando uma frase ambígua, e "manda ver a lista de
exercícios" não pode ter caminho até entregar o trabalho.

A sua chave do e-Disciplinas fica só no seu computador. Ela não vai para nenhum servidor,
nem para a nuvem. É por isso que o e-Disciplinas só funciona rodando local.

As respostas da USP são enxugadas antes de chegar ao assistente. A lista de disciplinas,
por exemplo, sai de 104.712 bytes para 7.816: o resto é metadado que não responde pergunta
nenhuma e só ocuparia espaço.

## O que o projeto não responde, e por quê

Nota, histórico escolar, evolução do curso e saldo do RUCard ficam de fora. O motivo é
falta de caminho, não de trabalho. Medido em 14/09/2026:

- A parte pública e organizada do JupiterWeb é o catálogo de entrada. A grade dos cursos de
  ingresso da Poli para no 5º semestre (verificado em quatro cursos), e da ênfase (7º) e do
  módulo (9º) em diante não há grade, requisito nem código de curso alcançável.
- Dado pessoal exige a área logada, que não oferece chave como o Moodle. Só sessão de
  navegador, com dois cookies e um tempo de expiração ainda não medido.

O roteiro para medir isso está em
`docs/superpowers/plans/2026-09-14-jupiter-sessao-recon.md`. Nada dele foi executado.

Também não existem: aviso de professor, "já entreguei isso?", histórico de cardápio, saldo
do cartão, horário, sala e vagas.

Uma limitação que costuma confundir: ao listar material, o projeto diz o nome, o tipo e o
tamanho de cada arquivo, mas não devolve o endereço dele. Endereço sem a credencial não
abre, e quem baixa de fato é a ferramenta de download, sem nunca pôr a sua chave num
endereço.

## Rodando a partir do código

Você precisa desta seção em dois casos: se quiser usar o e-Disciplinas, porque o script
que busca a chave só existe aqui, ou se for mexer no código.

O repositório é público para ler, baixar e usar. Quem aprova mudança nele somos nós dois,
o Caio e eu, então ninguém de fora ganha acesso de escrita. Sugestão é bem-vinda pelo
caminho normal do GitHub: abra uma issue, ou um fork com pull request.

```bash
git clone git@github.com:CaioCastro1/mcp-usp.git && cd mcp-usp
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./scripts/gate.sh
```

O `cp` vem antes do gate porque sem `.env` ele reprova. A hash do RUCard é o único valor
que o gate precisa, e ela já vem preenchida no exemplo: é a chave embutida no app oficial,
pública e compartilhada, não credencial de ninguém. O gate roda offline e não toca a USP.

O `.mcp.json` versionado registra os três servidores sem segredo nenhum. Abra um cliente
MCP neste diretório e pergunte. Cada entrada chama `scripts/servidor.sh <sistema>`, e quem
resolve a raiz do checkout é o script, não o cliente.

Cliente que não faz `cd` no diretório do projeto, como o Claude Desktop, precisa do
caminho absoluto do lançador:

```json
{
  "mcpServers": {
    "usp-rucard": {
      "command": "<CAMINHO-DO-CHECKOUT>/scripts/servidor.sh",
      "args": ["rucard"]
    }
  }
}
```

O `.mcp.json` é relativo de propósito, porque é versionado e caminho absoluto de máquina
não entra em arquivo rastreado. O absoluto fica no arquivo de config da sua máquina.

### Detalhes técnicos

Três servidores MCP, sete ferramentas, todas verificadas contra a USP. Comunicação por
stdio, JSON-RPC, um processo por servidor.

| Servidor | Ferramentas |
|---|---|
| `usp-rucard` | `bandejao` |
| `usp-moodle` | `o_que_vence`, `material`, `baixar_arquivo`, `diagnostico` |
| `usp-jupiter` | `disciplina`, `requisitos` |

A superfície é allowlist: só saem daqui as funções nomeadas nela, por igualdade exata de
nome, e o default é negar. Sobre ela existe o bloqueio permanente do §2.2, que vale mesmo
com `USP_MCP_ALLOW_WRITES` ligada. A sua chave alcança 447 funções neste site, e é esse
número que faz as duas camadas existirem.

`baixar_arquivo` entrega o caminho e não o conteúdo. Um blob em base64 custaria cerca de
302k tokens no PDF médio, e extrair o texto no servidor perderia as figuras. Numa lista
manuscrita escaneada isso devolveria 9 bytes e chamaria de sucesso (§9, 01/09 e 03/09). O
arquivo cai em `~/.cache/usp-mcp/moodle/`.

São três comandos e não um com argumento: o nome de cada um é o mesmo `serverInfo.name`
que o servidor responde no `initialize`. O porquê está no `pyproject.toml`.

Medido em 14/09/2026: instalação num venv limpo a partir da URL do repositório, e os três
comandos subindo de `/tmp` com cliente MCP real. `pipx` e `uvx` não foram exercitados, e
`pip install --user` é barrado pelo PEP 668 no Python do Homebrew. Empacotar como MCP
Bundle (`.mcpb`) segue sem teste, descrito no §6.1 por leitura de documentação.

Ferramenta não nasce por conveniência: o critério está no §5, e as questões abertas do §4
fecham com dado registrado no §9. O `SPEC1.md` é a autoridade do projeto.

- `usp_mcp/`, os servidores, um pacote por sistema
- `tests/`, três camadas: política e contrato offline, `live` atrás de env var
- `notas/`, análise por sistema, com custo medido em bytes e tokens
- `fixtures/`, respostas cruas capturadas (as do Moodle ficam fora do git, porque têm dado pessoal)
- `scripts/`, chamadores da descoberta e o gate de pré-commit
- `docs/decisions/BACKLOG-correcoes.md`, a dívida que está em aberto
