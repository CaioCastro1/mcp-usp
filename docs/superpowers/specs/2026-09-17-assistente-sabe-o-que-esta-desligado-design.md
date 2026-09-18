# O assistente sabe o que está desligado — design

> 17/09/2026. Defeito relatado pelo dono a partir de uso real: existe uma
> capacidade de escrita neste projeto (entregar atividade), desligada por padrão
> atrás de `USP_MCP_ENTREGA`, e **o assistente não sabia que ela existe**. Não
> recusou, não hesitou, não ofereceu — não chegou a considerar. A pessoa ficou
> sem saber que era possível.
>
> O pedido é o oposto, e é estreito: o assistente **sabe, e conta**. Não liga
> sozinho, nunca. Conta que existe, o que faz, o que custa, e como a pessoa liga
> se quiser.
>
> Este spec não desfaz a decisão de 15/09. Ele descobre por que aquela decisão
> produziu silêncio total, e conserta a causa em vez do sintoma.

## O que está decidido hoje, e por que está certo

`docs/superpowers/specs/2026-09-15-entrega-com-confirmacao-design.md`, camada E14:

> **com a flag desligada, as duas ferramentas novas não aparecem no `tools/list`.
> Ferramenta que aparece e sempre recusa ensina o modelo a tentar.**

O mecanismo do dano é concreto e vale a pena escrevê-lo em câmera lenta, porque
é ele que decide qual cura serve. O modelo vê um item na lista → escolhe →
gasta uma chamada → lê "não posso" → conclui que existe um caminho e que falta
achar o jeito de passar → tenta outro argumento, outra ferramenta, o shell. O
laço tem quatro passos, e o primeiro deles é **existir um item chamável**.

`tests/handshake/test_entrega_no_fio.py` (E14) trava isso pelo fio, e continua
travando. Nada aqui o enfraquece.

## O que foi medido para este spec

**1. O `tools/list` era o único canal pelo qual este servidor contava de si.**
Dez descritores, com nome, descrição e schema. Mais nada. Um servidor MCP que
não use outro campo do protocolo é, para o assistente, exatamente a sua lista de
ferramentas — e o que não está na lista não existe.

**2. O protocolo tem um segundo canal, e o SDK instalado o expõe.** Medido antes
de propor, como o pedido exige:

```
MCPServer.__init__(self, name=None, title=None, description=None,
                   instructions: str | None = None, ...)
```

Exercitado no fio, com um processo de verdade: `initialize` devolve o campo
`instructions` com o texto passado. E o contraprova importa tanto quanto: o
`usp-mcp-rucard`, que não passa o argumento, devolve `instructions: None`. O
campo viaja porque alguém o preencheu, não por acaso.

**3. Os dois canais são de naturezas diferentes, e é isso que resolve.**
`tools/list` é a superfície de **ação**: tudo que está lá é chamável, e um item
chamável que sempre recusa é a armadilha da medição acima. `instructions` é a
superfície de **informação**: chega uma vez, na abertura da conexão, e **não há
nada ali para chamar**. Uma frase em `instructions` não pode virar chamada
gasta, nem recusa lida, nem contorno procurado — o laço de quatro passos não tem
o primeiro.

**4. A `diagnostico` já existe, e a pessoa já é mandada a ela.** A descrição dela
diz "use ao configurar o servidor pela primeira vez" e "isso funciona no Moodle
da minha faculdade?". Ela responde sobre o SITE (que funções o token alcança), e
uma capacidade desligada por configuração **deste processo** não reprova nenhuma
linha da tabela dela: some sem deixar rastro. O comentário de
`usp_mcp/moodle/diagnostico.py` registrava a omissão como decidida, e a razão
escrita lá era exatamente a de E14.

**5. Um modelo com shell alcança o `.env`.** Já registrado em 15/09 e não
mudou. Esconder o nome da variável não é portão: é só tirar da pessoa uma
informação que o modelo obtém lendo um arquivo do repositório.

## Decisão: `instructions` é o canal, e a `diagnostico` é o eco

### O caminho escolhido

**`usp_mcp/moodle/server.py` passa `instructions=capacidades.instrucoes()` ao
`MCPServer`**, montado depois do `carregar_env()` porque o texto depende da
flag. E **`diagnostico` ganha um bloco em prosa no fim**, com a versão curta do
mesmo texto.

Módulo novo `usp_mcp/moodle/capacidades.py`, com a razão do desenho na docstring
e três funções: `escrita_ligada()` (delega para a política, que é quem lê o
ambiente), `estado_da_escrita(curto=…)` e `instrucoes()`.

### Por que isto NÃO reintroduz o defeito que E14 evitava

Esta é a pergunta que o spec existe para responder, e ela se responde pelo
mecanismo, não pela intenção:

1. **Nenhum item novo no `tools/list`.** Com a flag desligada o servidor anuncia
   as mesmas dez ferramentas de antes, byte por byte, nenhuma delas destrutiva.
   O teste G2 assere isso **no mesmo processo** em que G1 assere que o texto
   chegou — as duas metades sobre um handshake só, porque separadas elas
   deixariam de ser uma frase.
2. **Não há chamada a gastar nem recusa a ler.** O laço que ensina a insistir
   começa por uma tentativa; aqui não existe a tentativa. O modelo não pode
   "chamar" um parágrafo.
3. **O texto diz, em português, que não há o que tentar.** "Enquanto a variável
   não estiver no ambiente do servidor não há ferramenta nenhuma para chamar, e
   não há o que tentar." A cura de 15/09 tirava a informação para evitar a
   insistência; esta dá a informação e nega a insistência no mesmo fôlego.
4. **Não vira convite.** O texto não recomenda ligar, e um teste proíbe as
   palavras que o tornariam recomendação (`ligue`, `habilite`, `recomendo`,
   `basta`, `é só`). Ele diz de quem é a decisão — de quem responde pela conta —
   e diz que ligar por conta própria não é passo do assistente.
5. **Não entrega a receita.** Nenhum nome de função do Moodle sai neste texto,
   em nenhum dos dois estados, travado por teste na função pura e de novo no
   fio. É a mesma regra que já governa o diagnóstico, que conta as funções
   bloqueadas e não as nomeia: o nome de que a pessoa precisa é o da variável, e
   ele está lá.

### O texto, e as regras dele

Com a flag desligada, o `initialize` devolve:

```
Ferramentas de consulta ao e-Disciplinas (Moodle da USP). O que cada uma faz e
quando usá-la está na descrição dela; aqui vai só o que a lista de ferramentas
não tem como dizer.

Escrita: DESLIGADA. Este servidor só lê o e-Disciplinas agora. Existe uma
capacidade de escrita neste projeto — salvar o texto do rascunho de uma entrega,
e enviar uma entrega para correção — e ela está desligada, por isso as duas
ferramentas dela não estão nesta conexão. Quem liga é a pessoa dona do token,
pondo USP_MCP_ENTREGA=1 no arquivo .env do servidor e subindo o servidor de
novo. Enviar uma entrega para correção NÃO tem desfazer, nem por aqui nem pela
API do Moodle.

Conte isso a quem perguntar o que dá para fazer por aqui, ou a quem pedir para
entregar alguma coisa: que a capacidade existe, que está desligada, o que ela
custa, e que ligar é decisão de quem responde pela conta — não sua, e não deste
processo. Ligar por conta própria não é o caminho, e insistir também não:
enquanto a variável não estiver no ambiente do servidor não há ferramenta
nenhuma para chamar, e não há o que tentar. Com a escrita ligada, cada uma das
duas ainda pede duas chamadas — a primeira mostra o plano do que mudaria e não
escreve nada.
```

Três regras governam esse texto, e cada uma tem teste:

- **A abertura diz o que este campo não é.** `instructions` carrega só o que o
  `tools/list` não tem como carregar. O que cada ferramenta faz já viaja na
  descrição dela, para um cliente que já vai pedir a lista; repetir aqui é pagar
  os mesmos tokens duas vezes por conexão. Com teto de tamanho (C7), porque uma
  regra sem número vira o sétimo README do repositório.
- **É simétrico.** Com a flag ligada o texto muda e diz `LIGADA`, nomeia as duas
  ferramentas (que aí estão mesmo na lista) e repete o custo. Um texto que só
  falasse do estado desligado envelheceria calado justamente na máquina de quem
  ligou — e "o assistente sabe o que está ligado" é a mesma pergunta lida do
  outro lado.
- **Uma fonte só.** A versão curta que o diagnóstico usa é literalmente o começo
  da inteira (`startswith`, travado por C3), e não um resumo parecido. Duas
  cópias de um fato são uma que envelhece calada, e este repositório já pagou
  essa conta.

### O eco na `diagnostico`, e por que ele não basta sozinho

A `diagnostico` responde "o que daqui funciona no seu Moodle", e uma capacidade
desligada é metade dessa resposta que sumia sem rastro. Ela ganha o bloco curto
no fim — nos **dois** caminhos de saída, inclusive o que retorna cedo quando o
site não devolve a lista de funções, que é justamente onde a pessoa está
configurando pela primeira vez. A descrição da ferramenta passa a dizer que ela
informa o estado da escrita e de quem é a decisão de mudá-lo.

Mas a `diagnostico` é **pull**: ela só conta a quem a chamar. O defeito relatado
aconteceu numa conversa comum, sem ninguém diagnosticando nada. Ela é o segundo
lugar, não o primeiro.

## Os caminhos que foram considerados e recusados

**Uma ferramenta nova só para isso.** Recusada, e o `CLAUDE.md` diz por quê:
ferramenta não nasce por conveniência, o critério para existir é o §5 do
`SPEC1.md`. Pior: seria um item no `tools/list` que o modelo teria de escolher e
gastar uma chamada para ler um parágrafo estático — a forma mais cara possível
de entregar um texto que o protocolo já entrega de graça no handshake.

**A descrição de uma ferramenta de leitura vizinha (a de entregas, por
exemplo).** Recusada como caminho principal. A descrição de `ja_entreguei` é
lida por quem está escolhendo **o que chamar**; enfiar ali a existência de um
caminho de escrita é pôr a informação na superfície de ação, que é exatamente a
superfície que E14 protege. E o custo é permanente: viaja em todo `tools/list`
de toda conexão, ligada ou desligada a flag, para responder uma pergunta que
quase nunca é a pergunta daquela chamada. A menção que entrou na descrição da
`diagnostico` é de outra natureza — ela descreve o que aquela ferramenta
responde, que é literalmente o estado deste servidor, e é a única da lista de
quem isso é assunto.

**Mexer no `USP_MCP_ALLOW_WRITES` ou no padrão.** Fora de escopo e contra a
regra que não muda: o padrão continua não escrever.

## O que NÃO muda

- O padrão: sem `USP_MCP_ENTREGA=1` este servidor não escreve, e as duas
  ferramentas não existem no `tools/list`. E14 segue verde, e não foi tocado.
- As duas condições da escrita (flag **e** confirmação declarada por chamada) e
  as recusas que a flag não abre.
- As anotações de protocolo: nenhuma ferramenta nova, nenhum bloco alterado.
- O RUCard e o Jupiter não ganham `instructions`. Eles não têm escrita para
  ligar, e um campo com texto que não ajuda a agir é a má prática que a saída
  sem jargão (14/09) combateu. O dia em que um deles tiver algo que o
  `tools/list` não diga é o dia em que essa linha muda.

## Bateria de testes

Camada `politica`, offline, em `tests/moodle/test_capacidades.py`:

- **C1** desligada, o texto diz `DESLIGADA`, nomeia a variável, diz onde ela
  mora e declara que entregar não tem desfazer.
- **C2** ligada, o texto diz `LIGADA`, nomeia as duas ferramentas e **não** diz
  `DESLIGADA`.
- **C3** nos dois estados, a versão curta é o começo exato da inteira.
- **C4** nos dois estados, nenhum nome de função do Moodle aparece — nem da
  allowlist, nem do bloqueio permanente, nem da escrita confirmada.
- **C5** nos dois estados, nenhuma palavra de convite (`ligue`, `habilite`,
  `recomendo`, `basta`, `é só`).
- **C6** o texto diz que ligar por conta própria não é o caminho, e que não há o
  que insistir.
- **C7** as instruções cabem no teto de 1800 caracteres, nos dois estados.
- **C8** os nomes de ferramenta declarados em `capacidades.py` são os que o
  `listar_ferramentas()` anuncia com a flag ligada (as duas cópias não podem
  divergir, porque importar o `server` daqui fecharia ciclo).

Camada `contrato`, offline, em `tests/moodle/test_diagnostico.py`:

- **D7** o diagnóstico diz o estado desligado, com variável e custo, sem
  estragar a tabela por ferramenta.
- **D7b** com a flag ligada ele diz `Escrita: LIGADA` e não diz `DESLIGADA`.
- **D7c** o caminho que retorna cedo (site sem lista de funções) também diz o
  estado — é onde a pessoa está configurando, e um `return` antecipado engoliria
  o bloco sem ninguém ver.

Handshake, processo de verdade, em `tests/handshake/test_contexto_de_escrita.py`:

- **G1** com a flag em "0", o `initialize` traz `instructions` com o estado, a
  variável e o custo.
- **G2** no mesmo processo, o `tools/list` continua com dez ferramentas, nenhuma
  destrutiva, e nenhuma das duas de escrita. **Esta é a prova de que o modelo
  passa a saber sem passar a insistir.**
- **G3** com a flag em "1", o texto muda para `LIGADA` e cita as duas, que estão
  na lista daquele processo.
- **G4** nos dois valores da flag, as instruções no fio não nomeiam função do
  Moodle.

Os testes de 15/09 continuam valendo sem alteração: E14 e E14b não foram
tocados.

## Critério de parada

A suíte fica verde nas duas configurações da variável, com o mesmo vermelho
anterior e alheio (`test_t58_o_cru_quando_existe_reproduz_a_publicada
[users_courses.json]`, sendo consertado em outra frente) e nenhum novo.

Medido: `1 failed, 940 passed, 11 skipped` antes; `1 failed, 961 passed, 11
skipped` depois, idêntico com `USP_MCP_ENTREGA=1` e sem ela. Vinte e uma
asserções novas, zero vermelhos novos.

## O que precisa ir para o §9

Este spec não edita o `SPEC1.md` (fora do escopo desta frente). Fica registrado
aqui o que a decisão precisa carregar para lá:

1. Que o silêncio sobre a capacidade desligada era **consequência não prevista**
   da decisão de 15/09, e foi achado por uso real, não por revisão de código.
2. Que a cura separa os dois canais do protocolo — ação (`tools/list`) e
   informação (`instructions`) — e que é essa separação, e não a redação do
   texto, que impede a volta do defeito que E14 evita.
3. Que o padrão não mudou: a escrita continua desligada, e ligar continua sendo
   decisão de quem é dono do token. O que mudou é que agora a pessoa tem como
   saber que a decisão existe.

## Adendo de 18/09/2026: o texto acima ficou incompleto em uso real

Um dia depois de este texto entrar, o dono pediu ao assistente para entregar
uma atividade e ouviu que ele **não controlava isso e não sabia onde ficava o
`.env`**. O assistente fez o que o texto mandava; o texto é que faltou em duas
coisas, e as duas foram consertadas em `usp_mcp/moodle/capacidades.py`:

1. **Onde o arquivo está.** "No arquivo `.env` do servidor" não tem caminho, e o
   servidor sabe o caminho: `usp_mcp.env.achar_env()` devolve o `.env` que
   aquele processo lê. O texto passa a trazer o caminho absoluto, nos dois
   estados e na versão curta do diagnóstico. Com `achar_env()` em `None` o texto
   diz que não achou arquivo nenhum e por onde a variável entra então, em vez
   de inventar um caminho provável.
2. **"Não ligar por conta própria" não é "não ligar nunca".** O texto separa os
   dois casos com todas as letras: nem por iniciativa do assistente, nem por
   dedução do que a pessoa quis dizer (pedido de entrega não é pedido de
   ligar); e, quando a pessoa pede de forma inequívoca, o assistente pode editar
   aquele arquivo por ela. A mudança só vale depois de o servidor subir de novo.

Apontar para o `.env` obrigou uma regra de segurança no mesmo parágrafo: mexer
**só naquela linha** e **nunca imprimir o conteúdo do arquivo**, que guarda o
`MOODLE_TOKEN`. E, como quem abre o arquivo vê `USP_MCP_ALLOW_WRITES` logo
acima, o texto diz o que ela faz de verdade: não abre nada, nos três servidores.

O que não mudou: o padrão segue não escrever, as duas ferramentas seguem fora
do `tools/list` com a flag desligada (E14, G2), e a proibição de palavras de
recomendação (C5) continua intacta; a redação é que se curvou a ela. O teto do
C7 subiu de 1800 para 2600 caracteres por decisão, medido com um caminho de
fixture para não depender da máquina. Testes novos: C9 a C14 na função pura,
D7d no diagnóstico e G5 pelo fio. O texto vigente é o que
`capacidades.instrucoes()` devolve; a cópia acima é a de 17/09 e fica como
registro do que ficou faltando.
