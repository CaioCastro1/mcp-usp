# usp-mcp

Feito por Caio Castro & João Pedro Gunthen

Consulta em português a sistemas acadêmicos da USP: o cardápio dos bandejões, os prazos e
o material do e-Disciplinas, e o catálogo de disciplinas do JupiterWeb.

Ele não tem interface própria. Você o conecta a um assistente e passa a poder perguntar em
linguagem comum. A resposta vem dos sistemas da USP, no momento da pergunta.

Qualquer assistente que fale MCP serve. Este guia mostra os passos com o Claude, porque é
o que os autores usam, e a seção *Onde ele funciona* conta o resto.

Projeto não-oficial, sem nenhum vínculo com a Universidade de São Paulo.

## O que ele responde

| Pergunta que você faz | Onde ele busca |
|---|---|
| "O que tem no bandejão hoje, na sexta ou na semana inteira?" | Cardápio dos quatro restaurantes, com horário e preço |
| "Quais matérias eu tenho?" | Suas disciplinas no e-Disciplinas: as do semestre primeiro, com a sigla que as outras perguntas usam |
| "O que eu tenho para entregar essa semana?" | Tarefas e questionários do e-Disciplinas, com prazo |
| "Que arquivos tem em PTC3314?" | Lista o material da disciplina: regras, listas, provas antigas |
| "Baixa a lista 2 pra mim" | Baixa o arquivo e diz onde ele ficou no seu computador |
| "Já entreguei o EP1?" | O que você já enviou, o que ficou só como rascunho e se saiu no prazo |
| "Perdi algum prazo?" | O que já venceu e o e-Disciplinas não registra como entregue, rascunho salvo incluído |
| "Como estou de nota?" | As notas que o professor lançou no e-Disciplinas, de todas as disciplinas ou item a item de uma |
| "O professor avisou alguma coisa?" | Os recados nos fóruns da disciplina, o mural de avisos primeiro |
| "Mudou alguma coisa desde ontem?" | O que mexeu na disciplina nos últimos dias: arquivo novo, tópico novo, prazo alterado |
| "Quantos créditos vale MAC0110?" | Créditos, carga horária e ementa pela sigla; programa, bibliografia e avaliação sob pedido |
| "O que preciso ter feito antes de MAT2454?" | Pré-requisitos, pelo seu currículo |

Bandejão e JupiterWeb funcionam para qualquer pessoa. O e-Disciplinas mostra as **suas**
disciplinas, então ele precisa de uma chave sua, e obter essa chave dá um pouco mais de
trabalho. A seção *Configuração* explica.

## Onde ele funciona

O programa roda no seu computador, e o assistente fala com ele ali mesmo. Três lugares
costumam ser confundidos por terem o mesmo nome, e a diferença entre eles decide se a
instalação vai dar certo:

| Onde você pergunta | Funciona? |
|---|---|
| Claude Desktop, que é o **chat** no aplicativo de computador | sim, e é onde entra o bloco de configuração da próxima seção |
| Claude Code, no terminal ou na aba Code do aplicativo | sim, e o registro é por linha de comando |
| claude.ai aberto no **navegador** | não |

O navegador fica de fora porque, do lado do site, não existe nada capaz de conversar com um
programa que está na sua máquina. Não é um defeito à espera de conserto: é a outra face de
uma decisão registrada do projeto, que é a sua chave do e-Disciplinas nunca sair do seu
computador. Pelo navegador nem o bandejão responde, e ele nem chave usa.

O Claude aparece nesse quadro porque é o assistente que os autores usam, e não porque o
projeto precise dele. Por dentro, isto aqui é um servidor MCP comum, o padrão aberto que os
assistentes usam para falar com ferramentas, e não há uma linha de código escrita para um
assistente em particular. A seção *Detalhes técnicos*, no fim do arquivo, diz o que foi
medido a esse respeito.

## Instalando

Este é um MCP: um conjunto de ferramentas que um assistente passa a saber usar. A
instalação tem duas partes. Primeiro você baixa o projeto para o seu computador, e isso é
igual para todo mundo. Depois você avisa o assistente que ele existe, e esse segundo passo
muda conforme o lugar do quadro acima.

### O caminho rápido

Se você já tem o Claude Code, mande a mensagem abaixo para ele e pule o resto desta seção.
Ele instala, configura e te guia no único passo que precisa da sua mão.

```text
Instale o usp-mcp neste computador e me conecte a ele.

1. Clone https://github.com/CaioCastro1/mcp-usp em ~/usp-mcp, crie um venv em
   ~/usp-mcp/.venv e instale com `pip install -e ".[dev]"`. Copie o `.env.example` para
   `.env`, na mesma pasta, e rode `./scripts/gate.sh` para confirmar que ficou tudo certo.
2. Registre os três servidores (moodle, jupiter, rucard) no meu Claude Code, no escopo
   de usuário, apontando para os comandos em ~/usp-mcp/.venv/bin/.
3. O e-Disciplinas precisa de uma chave pessoal minha. Rode `./scripts/token.sh` e me
   explique, passo a passo, o que eu preciso fazer no navegador. Não tente fazer esse
   passo sozinho: ele exige que eu clique.
4. No fim, chame a ferramenta `diagnostico` e me diga o que ficou funcionando.
```

### O caminho manual

Você vai precisar do Python 3.11 ou mais novo. Para saber qual você tem, abra o terminal e
cole:

```bash
python3 --version
```

Se o Terminal responder que não conhece o comando `python3`, ou se o número for menor que
3.11, instale a versão atual pelo site python.org antes de seguir. Com uma versão mais
antiga, o passo de instalação abaixo falha com uma mensagem do pip que não explica o
motivo.

Depois cole estes quatro comandos, um de cada vez:

```bash
git clone https://github.com/CaioCastro1/mcp-usp.git ~/usp-mcp
python3 -m venv ~/usp-mcp/.venv
~/usp-mcp/.venv/bin/pip install -e ~/usp-mcp
cp ~/usp-mcp/.env.example ~/usp-mcp/.env
```

O primeiro baixa o projeto para uma pasta chamada `usp-mcp` dentro da sua pasta pessoal. O
segundo cria, dentro dela, um ambiente isolado, sem alterar o Python nem os programas já
instalados no computador. O terceiro instala o projeto nesse ambiente. O quarto cria o
arquivo de configuração a partir do modelo que vem no projeto: ele já traz preenchida a
única coisa que o bandejão precisa, e é nele que a sua chave do e-Disciplinas vai ficar
guardada depois.

Tudo fica junto em `~/usp-mcp`, de propósito. O programa lê o arquivo de configuração de
dentro dessa pasta, então não instale o projeto em outro lugar separado dela. Para
desinstalar, basta apagar a pasta.

Se o Terminal disser que não conhece o comando `git`, no Mac ele mesmo oferece instalar na
hora: aceite, espere terminar e repita o primeiro comando.

Para conferir se deu certo:

```bash
ls ~/usp-mcp/.venv/bin | grep usp
```

Tem que aparecer `usp-mcp-jupiter`, `usp-mcp-moodle` e `usp-mcp-rucard`.

Agora avise o assistente que eles existem. Em qualquer um dos caminhos abaixo você troca
`SEU-USUARIO` pelo nome da sua conta no computador; se não souber qual é, o comando
`whoami` no Terminal responde.

**No Claude Desktop**, a configuração mora num arquivo. Pelo menu, o caminho até ele é
Configurações, depois Desenvolvedor, depois o botão que edita a configuração (em inglês,
Settings e Developer). Se preferir abrir o arquivo direto, no Mac ele é

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

e no Linux, `~/.config/Claude/claude_desktop_config.json`. Se ele estiver vazio, cole isto
inteiro:

```json
{
  "mcpServers": {
    "usp-rucard": { "command": "/Users/SEU-USUARIO/usp-mcp/.venv/bin/usp-mcp-rucard" },
    "usp-jupiter": { "command": "/Users/SEU-USUARIO/usp-mcp/.venv/bin/usp-mcp-jupiter" },
    "usp-moodle": { "command": "/Users/SEU-USUARIO/usp-mcp/.venv/bin/usp-mcp-moodle" }
  }
}
```

Se já tiver alguma coisa escrita, não troque o conteúdo pelo de cima: as três linhas `usp-`
entram dentro do `mcpServers` que já está lá, depois do que já existe, com uma vírgula
separando uma da outra.

**No Claude Code**, não há arquivo para editar à mão. Cole estes três comandos no Terminal,
um de cada vez:

```bash
claude mcp add usp-rucard --scope user -- /Users/SEU-USUARIO/usp-mcp/.venv/bin/usp-mcp-rucard
claude mcp add usp-jupiter --scope user -- /Users/SEU-USUARIO/usp-mcp/.venv/bin/usp-mcp-jupiter
claude mcp add usp-moodle --scope user -- /Users/SEU-USUARIO/usp-mcp/.venv/bin/usp-mcp-moodle
```

O `--scope user` é o que faz o registro valer em qualquer pasta, e não só na que você
estiver quando rodar o comando.

**Em outro assistente que fale MCP**, a ideia é a mesma: apontar o programa para os três
comandos que apareceram no passo anterior. Onde essa configuração se escreve muda de
assistente para assistente, e quem diz é a documentação de cada um.

No Linux, o começo do caminho é `/home/` em vez de `/Users/` nos dois blocos. Os comandos
desta seção foram escritos para Mac e Linux; no Windows os caminhos são outros e este guia
ainda não os cobre.

Feche e abra o assistente. Pronto: bandejão e JupiterWeb já respondem. O e-Disciplinas
ainda vai reclamar que falta a chave, e é a próxima seção.

Se algo não funcionar, peça ao assistente para rodar a ferramenta `diagnostico`. Ela diz o
que está no lugar e o que não está.

## Configuração

Só o e-Disciplinas precisa disto. Bandejão e JupiterWeb funcionam sem nada.

A chave é sua e pessoal, e cada pessoa obtém a dela. Ela nunca sai do seu computador, e é
por isso que ninguém pode te dar uma pronta.

O script que a obtém já está no seu computador, na pasta do projeto que a instalação
baixou. Cole no terminal:

```bash
~/usp-mcp/scripts/token.sh
```

Se você instalou pelo caminho rápido, a pasta é a mesma.

Ele abre uma página do e-Disciplinas no seu navegador. Você precisa já estar logado na
Senha Única. A página mostra três coisas, e duas são distração: a caixa verde "O seu
cadastro foi confirmado" e o botão cinza "Ambientes". O que importa é o link azul escrito
"Clique aqui se a aplicação não abrir automaticamente".

Clique nele com o **botão direito** e escolha "copiar endereço do link". Não clique com o
esquerdo: isso tenta abrir o aplicativo do Moodle e não copia nada. Volte no Terminal e
aperte Enter.

O script confere o que você copiou, testa a chave contra a USP e só então guarda. Se você
copiou o endereço errado, ele avisa e não estraga nada. A chave nunca aparece na tela.

Se quem roda o script é o assistente, e não você no Terminal, não há Enter para apertar:
o script fica de vigia no clipboard por até 90 segundos, lendo o que está lá a cada meio
segundo, e segue sozinho assim que aparecer um endereço que comece com
`moodlemobile://token=`. Ele avisa disso antes de começar. Só esse endereço faz o script
agir; qualquer outra coisa que você copiar nesse intervalo ele ignora, sem guardar,
mostrar ou dizer o tamanho, e o que já estava no clipboard antes não conta. Se você
copiar o endereço errado, ele diz o que veio errado e continua esperando. Passados os 90
segundos sem o endereço, ele para de ler e diz como entregar depois:
`pbpaste | ~/usp-mcp/scripts/token.sh`. Para rodar sem essa vigia, defina
`USP_MCP_VIGIA_SEGUNDOS=0` antes do comando. Num computador sem ferramenta de clipboard
(sem `pbpaste`, `wl-paste` nem `xclip`) a vigia não existe e o script diz isso.

Ela fica guardada no arquivo `~/usp-mcp/.env`, na linha `MOODLE_TOKEN`. É o mesmo
arquivo que o programa lê, então não há nada para copiar de um lugar para outro: feche e
abra o assistente e o e-Disciplinas passa a responder. Você não precisa abrir esse
arquivo, mas se um dia abrir, é essa a linha.

Ela vence com o tempo e pode ser cancelada em `edisciplinas.usp.br`, em gerenciar tokens.
Se um dia o e-Disciplinas parar de responder, rode `~/usp-mcp/scripts/token.sh` de novo.

## Usando

Depois de conectado, é só perguntar. Alguns exemplos do que funciona:

- "o que tem no bandejão da Física hoje no jantar?"
- "que dia tem lasanha essa semana?"
- "tem alguma coisa vencendo nos próximos 3 dias?"
- "quais arquivos tem em PTC3314?"
- "baixa o EP1 de PTC3314 e me explica o que ele pede"
- "quantos créditos vale MAC0110 e qual é a ementa?"

A última encadeia duas coisas: o projeto baixa o PDF e o assistente lê o arquivo para
responder.

Se você pedir algo que ele não sabe, a resposta diz o que faltou em vez de inventar. Vale
ler a seção *O que o projeto não responde* antes de concluir que quebrou.

## Como funciona

Cada um dos três comandos é um programa que fica em segundo plano aguardando perguntas do
assistente. Quem conversa com ele é o assistente, não você: executá-lo direto no terminal
não produz saída, porque não é para ser usado assim.

Quem decide qual ferramenta usar é o assistente, lendo a descrição de cada uma diante da
sua pergunta. Por isso as descrições são escritas na linguagem de quem pergunta, e não com
o nome técnico da função por trás.

O acesso à USP é limitado de propósito. De todas as operações que a sua chave permitiria,
só um punhado está liberado aqui, e por padrão todas são de leitura. Começar uma prova,
responder questionário ou mandar mensagem em seu nome estão bloqueados e continuam
bloqueados mesmo se alguém ligar a permissão de escrita. Entregar trabalho é a única
exceção que pode ser ligada, e a seção *Entregando trabalho* explica com que cuidados. O
motivo de tanta cerca é simples: quem escolhe o que chamar é um assistente interpretando
uma frase ambígua, e "manda ver a lista de exercícios" não pode ter caminho até entregar o
trabalho.

A sua chave do e-Disciplinas fica só no seu computador. Ela não vai para nenhum servidor,
nem para a nuvem. É por isso que o e-Disciplinas só funciona rodando local.

As respostas da USP são enxugadas antes de chegar ao assistente. A lista de disciplinas,
por exemplo, sai de 104.712 bytes para 7.816: o resto é metadado que não responde pergunta
nenhuma e só ocuparia espaço.

## Entregando trabalho

Por padrão o projeto só lê. Entregar trabalho no e-Disciplinas é a única exceção que pode
ser ligada, e ela vem desligada: enquanto você não ligar, essas ferramentas nem aparecem
para o assistente.

Para ligar, ponha `USP_MCP_ENTREGA=1` no arquivo `.env` e reinicie.

Aparecem então duas coisas separadas: salvar rascunho e entregar para correção. São duas
de propósito, porque "salva aí" e "entrega isso" estão a uma palavra de distância e só uma
das duas tem volta.

Entregar nunca acontece no primeiro pedido. O primeiro devolve um plano: qual atividade,
que arquivos estão anexados, qual é o prazo e o que exatamente vai mudar. Só o segundo
pedido, confirmando aquele plano, escreve. Se alguma coisa mudou entre um e outro, a
confirmação é recusada e o plano volta atualizado.

Três coisas para saber antes de ligar:

- Entregar para correção não tem desfazer, nem aqui nem pelo site.
- Salvar rascunho só funciona em atividade de texto online. Enviar arquivo não existe neste
  projeto, e é o formato mais comum na prática. Essa metade vai recusar a maioria dos casos,
  dizendo o motivo.
- Trabalho em grupo é recusado, porque a entrega valeria também por pessoas que não estão
  na conversa.

A confirmação em duas etapas protege contra acidente e contra frase ambígua. Ela não é um
cadeado: quem roda o projeto dentro de um assistente que também tem acesso ao terminal
pode contornar qualquer trava que o programa tente impor. Ligar ou não é decisão sua, e
vale tomá-la sabendo disso.

## O que o projeto não responde, e por quê

Histórico escolar, evolução do curso e saldo do RUCard ficam de fora. O motivo é falta de
caminho, não de trabalho. Medido em 14/09/2026:

- A parte pública e organizada do JupiterWeb é o catálogo de entrada. A grade dos cursos de
  ingresso da Poli para no 5º semestre (verificado em quatro cursos), e da ênfase (7º) e do
  módulo (9º) em diante não há grade, requisito nem código de curso alcançável.
- Dado pessoal exige a área logada, que não oferece chave como o Moodle. Só sessão de
  navegador, com dois cookies e um tempo de expiração ainda não medido.

O roteiro para medir isso está em
`docs/superpowers/plans/2026-09-14-jupiter-sessao-recon.md`. Nada dele foi executado.

Também não existem: histórico de cardápio, saldo do cartão, horário, sala e vagas.

Aviso de professor passou a existir em 14/09, e cobre o que foi escrito no fórum da
disciplina. Recado dado em sala e não postado não chega até lá, e nem o projeto nem o
e-Disciplinas têm como saber dele. Quem escreveu cada tópico não sai na resposta: o fórum é
o único lugar do e-Disciplinas em que a resposta traz nome de outras pessoas, e esses nomes
param aqui.

As notas que o projeto mostra são as que o professor lançou no e-Disciplinas, e só elas.
Prova corrigida no papel, nota combinada em aula e o histórico oficial da USP não estão
ali, e nenhuma soma que o projeto fizesse seria a sua média de verdade. O comentário
escrito do professor também não sai: a resposta avisa quando existe um para você ler na
página da disciplina.

A lista de disciplinas é a do e-Disciplinas, e o e-Disciplinas não é a sua matrícula
oficial. O que separa uma matéria "em andamento" de uma encerrada ali são as datas que o
professor declarou no espaço da disciplina: trancamento e cancelamento não chegam até lá, e
uma matéria sem data declarada aparece à parte, dizendo que não dá para saber. Matéria de
semestre passado continua na lista, com a sigla, porque você ainda pergunta sobre ela.

"Já entreguei o EP1?" responde só sobre tarefa. Questionário não entra, e prova marcada só
no quadro da sala não existe em sistema nenhum. A resposta diz isso quando você pergunta.

A lista do que ficou para trás é a mesma coisa vista pelo outro lado, e ela tem um limite
que vale ler devagar: o projeto sabe o que está registrado no e-Disciplinas, não o que você
fez. Entrega no papel, por e-mail, num sistema do laboratório, ou que o professor recebeu e
nunca lançou no site, não aparece como enviada. Por isso a resposta nunca diz que você não
entregou: ela diz que não há registro, e manda confirmar. Quando o professor já lançou a
nota sem receber arquivo, ela separa esse caso e não conta como falta.

Uma limitação que costuma confundir: ao listar material, o projeto diz o nome, o tipo e o
tamanho de cada arquivo, mas não devolve o endereço dele. Endereço sem a credencial não
abre, e quem baixa de fato é a ferramenta de download, sem nunca pôr a sua chave num
endereço.

## Rodando a partir do código

Esta seção é para quem vai mexer no código. Quem só quer usar, inclusive o e-Disciplinas,
já tem tudo o que precisa pela seção *Instalando*: ela baixa o projeto inteiro, e o
script da chave vem junto.

O repositório é público para ler, baixar e usar, sob licença MIT: você pode usar, modificar
e redistribuir, desde que mantenha o aviso de autoria. O texto completo está no arquivo
`LICENSE`. Mudanças necessitam de aprovação. Sugestão é bem-vinda pelo caminho normal do
GitHub: abra uma issue, ou um fork com pull request.

```bash
git clone git@github.com:CaioCastro1/mcp-usp.git && cd mcp-usp
uv venv
uv pip install -e ".[dev]"
cp .env.example .env
./scripts/gate.sh
```

`uv` cria o mesmo `.venv/` que `python3 -m venv` criaria (é o que `scripts/servidor.sh` e o
`.mcp.json` procuram), com uma diferença que importa neste Mac: instala por hardlink a partir
de um cache único, então dez checkouts não custam dez cópias do SDK. Se não tiver `uv`,
`python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` continua funcionando.

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

Três servidores MCP, treze ferramentas, quinze com a escrita de entrega ligada.
Comunicação por stdio, JSON-RPC, um processo por servidor. As treze têm medição contra a
USP de verdade registrada no §9 do `SPEC1.md`. As quatro de 14/09 (`avisos`, `o_que_mudou`,
`disciplinas` e `atrasadas`) nasceram numa cópia sem chave, contra resposta escrita à mão
ou capturada em agosto, e foram medidas ao vivo no mesmo dia; a metade de `atrasadas` que
era escrita à mão, o estado de cada entrega, virou captura real em 15/09
(`fixtures/moodle/submission_status_ec1.json`). As duas de entrega não entram em teste ao
vivo em fase nenhuma, de propósito.

Nada aqui é escrito para um assistente específico. A dependência de execução é uma só, o
`mcp`, que é o SDK oficial do protocolo, e a única vez em que a palavra Claude aparece
dentro de `usp_mcp/` é numa docstring citando o `CLAUDE.md`. A versão do protocolo é
negociada com quem chega, e não fixada numa só. Medido em 16/09/2026, nos três servidores:
cliente pedindo `2024-11-05` recebe `2024-11-05`, pedindo `2025-03-26` recebe `2025-03-26`
e pedindo `2025-06-18` recebe `2025-06-18`. Outros clientes MCP, como Cursor, Windsurf,
Zed, Continue e a extensão do VS Code, falam esse mesmo protocolo. Isso é o que se sabe
pelo protocolo em comum, e não o relato de alguém que tenha rodado este projeto dentro
deles: ninguém rodou ainda.

| Servidor | Ferramentas |
|---|---|
| `usp-rucard` | `bandejao` |
| `usp-moodle` | `o_que_vence`, `material`, `baixar_arquivo`, `diagnostico`, `ja_entreguei`, `notas`, `avisos`, `o_que_mudou`, `disciplinas`, `atrasadas` |
| `usp-moodle`, só com `USP_MCP_ENTREGA=1` | `salvar_rascunho`, `entregar` |
| `usp-jupiter` | `disciplina`, `requisitos` |

A superfície é allowlist: só saem daqui as funções nomeadas nela, por igualdade exata de
nome, e o default é negar. Sobre ela existe o bloqueio permanente do §2.2, que vale mesmo
com `USP_MCP_ALLOW_WRITES` ligada. A sua chave alcança 447 funções neste site, e é esse
número que faz as duas camadas existirem.

**As duas ferramentas que escrevem não existem por padrão.** `salvar_rascunho` e `entregar`
só aparecem no `tools/list` com `USP_MCP_ENTREGA=1` no ambiente. Desligada, elas não
existem, e não é o caso de uma ferramenta visível que recusa. Ligada, cada uma ainda exige
duas chamadas: a primeira devolve um plano do que mudaria, com um código; a segunda,
repetindo o código, é a que escreve. Se o estado mudar no e-Disciplinas entre as duas, o
código não confere e a resposta traz o plano novo em vez de escrever. Isso é forte contra
acidente e **fraco contra um modelo com shell**, e essa fraqueza é conhecida e aceita: quem
liga a flag precisa saber o que ligou.

`baixar_arquivo` entrega o caminho e não o conteúdo. Um blob em base64 custaria cerca de
302k tokens no PDF médio, e extrair o texto no servidor perderia as figuras. Numa lista
manuscrita escaneada isso devolveria 9 bytes e chamaria de sucesso (§9, 01/09 e 03/09). O
arquivo cai em `~/.cache/usp-mcp/moodle/`.

São três comandos e não um com argumento: o nome de cada um é o mesmo `serverInfo.name`
que o servidor responde no `initialize`. O porquê está no `pyproject.toml`.

Medido em 14/09/2026: instalação editável num venv limpo, e os três comandos subindo de
`/tmp` com cliente MCP real. Em 16/09/2026 o caminho manual da seção *Instalando* foi
percorrido inteiro numa pasta limpa, com ambiente vazio: a hash do bandejão chega ao
comando instalado a partir do `.env` do clone, e `scripts/token.sh` grava no mesmo
arquivo. Instalar o pacote sozinho, fora do clone (`pip install git+...`), não funciona:
o programa procura o `.env` na pasta do projeto, e em `site-packages` não há nenhum. Era o
que este README ensinava até 16/09. `pipx` e `uvx` não foram exercitados, e
`pip install --user` é barrado pelo PEP 668 no Python do Homebrew. Empacotar como MCP
Bundle (`.mcpb`) segue sem teste, descrito no §6.1 por leitura de documentação.

Ferramenta não nasce por conveniência: o critério está no §5, e as questões abertas do §4
fecham com dado registrado no §9. O `SPEC1.md` é a autoridade do projeto.

- `usp_mcp/`, os servidores, um pacote por sistema
- `tests/`, quatro camadas: política, contrato e handshake offline, `live` atrás de env var
- `notas/`, análise por sistema, com custo medido em bytes e tokens
- `fixtures/`, respostas capturadas; as do Moodle só entram no git depois de higienizadas, e o cru delas (`fixtures/moodle/raw/`) fica fora
- `scripts/`, chamadores da descoberta e o gate de pré-commit
- `docs/decisions/BACKLOG-correcoes.md`, a dívida que está em aberto
