# Mensagem pelo Moodle: ler, enviar, ou nenhum dos dois

> 17/09/2026. O pedido do dono foi *"mandar mensagem via Moodle ia ser legal"*.
>
> Este documento existe porque esse pedido **não é uma ferramenta nova**. As
> funções de envio de mensagem do Moodle estão no `BLOQUEIO_PERMANENTE`, a lista
> que o §2.2 define como negada mesmo com a variável de escrita ligada. Elas
> foram postas lá por decisão escrita, na mesma linha das de fórum, sob a razão
> *"falam com terceiros em nome do usuário"*. Atender o pedido é **reabrir uma
> decisão de política**, pela segunda vez na vida do projeto.
>
> A primeira vez foi em 15/09/2026, com
> `docs/superpowers/specs/2026-09-15-entrega-com-confirmacao-design.md`. Este
> spec segue o formato daquele de propósito: levantamento primeiro, modelo de
> ameaça antes do desenho, e o que o desenho **não** protege dito em voz alta.
>
> **Zero linhas de produção.** Nenhuma chamada ao e-Disciplinas foi feita para
> escrever isto (Regra de Ouro, §3.1). Tudo abaixo saiu do código deste
> repositório, do `SPEC1.md` e de `notas/moodle-catalogo.md`.
>
> A decisão não é deste documento. É do dono. O trabalho aqui é entregar a ele
> a pergunta bem posta, com os números certos, e uma recomendação que ele possa
> recusar sabendo o que está recusando.

## 1. O que está decidido hoje, conferido no código

`usp_mcp/moodle/politica.py`, nesta branch, tem três conjuntos:

| conjunto | tamanho | o que é |
|---|---:|---|
| `ALLOWLIST` | 11 | a superfície de leitura; igualdade exata de nome, sem outra condição |
| `BLOQUEIO_PERMANENTE` | 38 | negado antes de qualquer outra checagem, sem flag que libere |
| `ESCRITA_CONFIRMADA` | 2 | as duas de `mod_assign` que saíram do bloqueio em 15/09 |

**Três nomes de mensagem estão no bloqueio permanente hoje:**

| função | desde | razão escrita no §2.2 |
|---|---|---|
| `core_message_send_instant_messages` | 31/08/2026 | "falam com terceiros em nome do usuário" |
| `core_message_send_messages_to_conversation` | 31/08/2026 (commit `892f6b1`) | idem, e o §2.2 chama atenção para serem **dois** caminhos: "bloquear só `send_instant_messages` deixa o outro aberto" |
| `core_message_create_contact_request` | 14/09/2026, pela auditoria das 447 funções | idem, "mesma classe dos dois caminhos de mensagem acima" |

**Zero funções de mensagem estão na `ALLOWLIST`.** Conferido com
`politica.ALLOWLIST`: nenhum nome contém `message`. Nenhuma ferramenta do
servidor do Moodle lê mensagem hoje.

**O tamanho da família.** `notas/moodle-catalogo.md` (31/08/2026, produzido sem
nenhuma chamada) conta **41 funções em `core_message_*`**, a maior família do
catálogo: 21 de leitura e 20 de escrita. Somando as famílias vizinhas,
`message_popup_*` (2) e `message_airnotifier_*` (4), são **47 funções** no
assunto "mensagem e notificação". Das 47, três estão bloqueadas. As outras 44
são negadas pela allowlist, por omissão.

**Existe uma quarta decisão escrita, e ela é sobre leitura.** O §6.10 do
catálogo, "leitura que não é escrita mas também não é inócua", pede por escrito
que o bloco inteiro de leitura de `core_message_*` **não entre na allowlist**, e
que, se algum dia entrar, entre com justificativa. A razão registrada lá:
*"conversa privada é o dado mais sensível que este token alcança"*. Isso não é
bloqueio permanente, é um pedido de cuidado registrado. Mas ele existe, e quem
decidir tem de saber que existe.

## 2. A assimetria que muda a pergunta: ler não reabre o §2.2, enviar reabre

Este é o achado mais importante deste levantamento, e ele reorganiza o pedido
inteiro.

- **Enviar mensagem** exige tirar nome do `BLOQUEIO_PERMANENTE`. É o
  procedimento de 15/09: spec, decisão do dono, registro no §9, e o §2.2 muda de
  tamanho.
- **Ler mensagem** não exige nada disso. Nenhuma função de leitura de mensagem
  está bloqueada. Ler é um **acréscimo de allowlist**, o caminho ordinário que
  `avisos`, `notas`, `ja_entreguei` e `o_que_mudou` já percorreram: uma decisão
  de §9 com a medição que a sustenta.

Os dois pedidos foram para o mesmo saco porque a palavra "mensagem" é a mesma.
Eles não são o mesmo pedido, não custam o mesmo e não correm o mesmo risco.

## 3. Onde o valor provavelmente está, e é do lado da leitura

**O canal por onde o professor de fato fala com a turma já está coberto.** A
ferramenta `avisos` existe desde 14/09/2026 e lê o fórum de avisos. A medição
que a justificou está no §9 e em `notas/fase1-moodle.md`: o anúncio da "Prova
Prática P1" de PSI3323 estava no fórum *Avisos* e a prova **não** estava no
calendário. Prova presencial não vira evento de calendário, e é sobre ela que o
professor escreve no mural.

O próprio catálogo, ao mapear a pergunta *"O professor avisou alguma coisa desde
ontem?"*, dá o caminho de fórum como principal e
`message_popup_get_popup_notifications` como **alternativa**. O caminho de fórum
foi o escolhido, foi medido, e está no ar.

**O que sobra para a mensagem privada é um caso mais estreito do que o pedido
sugere:** o professor, o monitor ou o colega que escreveu para o dono
*individualmente*, fora do mural. Isso acontece, mas com que frequência **nunca
foi medido neste projeto**, e o §5 do `SPEC1.md` é explícito: ferramenta existe
para responder pergunta que o dono faz de verdade. Medir custa zero chamada de
web service: abrir `edisciplinas.usp.br` e contar as conversas privadas dos
últimos 60 dias.

Registro isso como a única lacuna de dado deste spec, e ela é do lado de quem
decide, não do lado de quem escreve.

## 4. O modelo de ameaça, escrito antes do desenho

O precedente de 15/09 fez isto antes de desenhar, e o §9 registra que esse
parágrafo é "o que mais precisa sobreviver". Repito o exercício para mensagem, e
o resultado é pior em cinco eixos.

**1. Quem escolhe o alvo, e de onde ele vem.** Para entregar, o alvo é um
`assignid` que a própria leitura devolveu: a ferramenta leu a lista de
atividades e o dono apontou uma. Para enviar, o alvo é uma **pessoa**, e
traduzir *"manda pro professor de PCS3335"* em um `touserid` passa por busca por
nome (`core_message_message_search_users`, `core_message_search_contacts`, ou
`core_enrol_get_enrolled_users`, que o §6.10 já barra por trazer a turma inteira
com e-mail). Homônimo, monitor com sobrenome parecido, professor de outra turma
da mesma sigla: o erro de resolução **não aparece no plano**, porque o plano
mostra exatamente o nome que o modelo escolheu. Um plano que exibe a escolha
errada com confiança é pior que nenhum plano.

**2. Quem escreve o conteúdo.** Na entrega, o conteúdo é um arquivo que o dono
produziu, com nome e tamanho conferíveis. Na mensagem, o conteúdo é **gerado
pelo modelo**, e não existe artefato anterior contra o qual conferir. O tom, o
que ficou implícito, o que o modelo inferiu sobre uma nota ou sobre um colega:
nada disso tem original.

**3. Quem paga a conta.** Entrega errada atinge o dono, e só. Mensagem errada
atinge **o destinatário**, que não está na conversa e não consentiu, e atinge a
reputação de quem assina, que é o dono. É uma classe de dano diferente, não um
grau a mais da mesma.

**4. "Sem desfazer" aqui é pior do que lá.** `mod_assign_submit_for_grading`
não tem desfazer pela API, mas tem caminho humano: falar com o professor e pedir
reabertura. Mensagem enviada não tem nem um nem outro. O catálogo registra que
`core_message_delete_message_for_all_users` existe no site (§6.4) e apaga do lado
do outro, e ela está fora da allowlist, mas apagar **não desnotifica**: o e-mail
e o push já saíram no segundo do envio. Desfazer aqui é apagar a prova, não o
ato.

**5. O precedente já traçou esta fronteira, e traçou do lado de fora.** A Camada
5 do spec de 15/09 lista cinco recusas que a flag ligada não abre. A primeira
delas é `teamsubmission` verdadeiro, *"porque escreve em nome de terceiros que
não estão na conversa"*.

Mandar mensagem é **sempre** esse caso. Cem por cento das vezes.

Abrir envio não estende o precedente. Contradiz a única recusa que ele declarou
inegociável mesmo com tudo ligado. Se `teamsubmission` é motivo suficiente para
recusar uma entrega que o dono pediu, mandar um texto para a caixa de outra
pessoa não pode ser motivo insuficiente.

## 5. O que a confirmação em duas etapas resolveria, e o que não

O precedente é claro sobre o alcance dela, e as três medições que o moldaram
continuam valendo aqui sem mudar uma vírgula:

1. `Context.elicit` existe, e a docstring do próprio SDK avisa que um cliente que
   seja agente pode responder sozinho, dentro da especificação. Elicitação é
   forma de apresentar a pergunta, nunca a garantia.
2. Tudo que o servidor diz ao modelo, o modelo pode repetir. O código de
   confirmação volta na chamada seguinte sem que ninguém tenha lido.
3. Dentro do Claude Code o modelo tem shell. Arquivo, variável de ambiente e
   marca com prazo são todos alcançáveis por `Bash`.

**O que ela resolveria:** acidente e ambiguidade. *"Avisa o professor"* e
*"manda uma mensagem pro professor"* são coisas diferentes, e uma pausa entre a
intenção e o envio pega parte disso. Isso é real e não é pouco.

**O que ela não resolveria, e é o ponto deste spec:** a camada que resolvia o
problema real no precedente era a **segunda**, não a confirmação. O §9 de 15/09
diz com todas as letras: *"O acidente medido não é 'o modelo entregou de
propósito', é estado velho virando escrita errada"*. O hash do plano existe para
travar `status`, `timemodified` e conjunto de arquivos entre a leitura e a
escrita.

**Mensagem não tem estado anterior.** Não há rascunho que se sobrescreve, não há
`status` para comparar, não há `timemodified`. O hash de um plano de mensagem
provaria apenas que o destinatário e o texto **não mudaram entre as duas chamadas
do mesmo modelo**, que continua com a mesma interpretação. Contra destinatário
errado o hash não faz nada: ele **congela o erro, não o detecta**.

Sobra a Camada 3, a apresentação, que o próprio precedente classifica como não
sendo cadeado.

Em uma frase: **para mensagem, o desenho de 15/09 fica estritamente mais fraco,
enquanto o dano fica estritamente maior.** Um portão que promete mais do que
cumpre é pior que portão nenhum, porque faz quem liga a flag baixar a guarda.
Essa frase é do precedente. Aplicada aqui, ela aponta para o outro lado.

## 6. Alternativas, do mais barato ao mais caro

**A. Nada novo.** `avisos`, `o_que_mudou`, `o_que_vence` e `atrasadas` já cobrem
o canal medido por onde o professor fala com a turma. Custo zero, risco zero, e
entrega a maior parte do que o pedido quer dizer na prática.

**B. Só o contador de não lidas, sem conteúdo e sem identidade.**
`core_message_get_unread_conversation_counts` e
`message_popup_get_unread_popup_notification_count`, as duas classificadas
`livre` pelo catálogo, que é a classe de "leitura sem terceiro identificável".
Responde *"tem coisa nova me esperando no e-Disciplinas?"* e manda o dono para o
site. **Nenhuma palavra escrita por terceiro entra no contexto do modelo**, e
nenhum nome. É acréscimo de allowlist, não reabertura do §2.2.

**C. Listar quem mandou e quando, sem conteúdo.** Esta é a alternativa que
parece intermediária e não é, e vale dizer por quê. `avisos` **já descarta
autoria de propósito**: `userfullname`, `usermodifiedfullname`, `userid` e as
URLs de foto não saem, por decisão registrada no §9 de 14/09, e a omissão é
declarada ao leitor para que ninguém atribua ao professor o que um colega
escreveu. Uma ferramenta cujo produto **é** o nome de quem mandou inverte essa
decisão e entrega ao modelo justamente o eixo mais identificável, quem fala com
quem e quando, sem entregar a resposta, que é o quê. Custo de precedente alto,
valor baixo. Recomendo descartar esta.

**D. Ler o conteúdo das conversas.** Não reabre o §2.2, mas seria o acréscimo de
allowlist mais pesado da história do projeto, contra um pedido escrito em
contrário no §6.10 do catálogo. Se um dia for feito, precisa de decisão de §9 com
a mesma seriedade de uma reabertura, e de uma resposta honesta a "o que acontece
com a mensagem privada de um colega depois que ela entra no contexto de um
modelo e no log de uma sessão".

**E. Enviar.** Reabre o §2.2 e contradiz a Camada 5 do precedente.

## 7. Recomendação

**Não para o envio. Agora, com data, e registrada como a segunda vez que a
pergunta foi feita.** Os três nomes de mensagem ficam no `BLOQUEIO_PERMANENTE`,
que continua com 38. A razão não é conforto nem excesso de zelo: é que o desenho
que tornou a entrega aceitável não transporta. Lá havia estado anterior legível,
rascunho que se sobrescreve, alvo vindo da própria leitura e dano restrito a
quem pediu. Aqui não há nenhum dos quatro. E a recusa por `teamsubmission`, que o
precedente declarou inegociável, é a descrição exata do que uma mensagem é.

**Sim para a alternativa B, condicionada a uma medição que custa zero chamada.**
Antes de escrever código, o dono abre `edisciplinas.usp.br`, olha a caixa de
mensagens e responde: nos últimos 60 dias, quantas conversas privadas com
professor ou monitor existem? Se a resposta for zero ou quase, nem o contador se
justifica, pelo critério 1 do §5, e a resposta certa é a alternativa A. Se houver
volume real, o contador entra como décima segunda e décima terceira funções da
allowlist.

**O que eu diria ao dono em uma frase:** o valor do pedido está quase todo do
lado da leitura, a leitura que ele mais quer já existe e se chama `avisos`, e o
que falta é um sino, não uma boca.

## 8. Se a alternativa B for aceita, o que ela precisaria

Esboço, não bateria fechada. A bateria completa se escreve quando a decisão
existir, e não antes.

- **M1.** Os três nomes de mensagem seguem no `BLOQUEIO_PERMANENTE`, e a
  contagem continua 38. Um teste que reprove se algum sair.
- **M2.** As duas funções de contagem entram na `ALLOWLIST` (11 para 13), e
  nenhuma outra de `core_message_*` entra. O conjunto exato fica travado, como o
  T7 já faz hoje.
- **M3.** A saída não contém nome, `userid`, foto nem uma palavra escrita por
  terceiro. O instrumento já existe: a varredura por conteúdo do §3.3.
- **M4.** Zero não vira "não tem nada" calado. "Nenhuma não lida" e "não consegui
  perguntar" são respostas diferentes e precisam sair diferentes (Invariantes 6
  e 7).
- **M5.** A ferramenta não aceita parâmetro de destinatário nem de texto, em
  forma nenhuma. Nem opcional, nem dentro de um dicionário. O que não existe no
  schema não é tentado pelo modelo.
- **Live**, atrás de `USP_MCP_LIVE=1`, só leitura, e só do contador.

Custo de resposta em tokens: **não medido**, porque nenhuma chamada foi feita
para este spec. Medir é uma invocação de `capture.sh`, que imprime medida e não
payload, e é decisão do dono por ser a credencial dele.

## 9. O que precisa ir para o §9, se a recomendação for aceita

Três registros, com data de 17/09/2026:

1. que o §2.2 foi questionado pela **segunda** vez, agora sobre mensagem, e a
   resposta foi **não para o envio**, com os três nomes e o motivo;
2. que ler e enviar são decisões de natureza diferente neste projeto, e que ler
   mensagem **nunca esteve no bloqueio permanente**: é allowlist, e o §6.10 do
   catálogo já pedia cuidado por escrito;
3. que o desenho de confirmação de 15/09 **não transporta** para mensagem, porque
   a camada que resolvia o problema real dependia de estado anterior legível, e
   mensagem não tem estado anterior.

O terceiro é o que mais importa. Sem ele, a próxima sessão lê "já reabrimos o
§2.2 uma vez com confirmação em duas etapas" e conclui que o caminho está aberto
para qualquer escrita, o que é exatamente a leitura errada.

## 10. Dívida colateral encontrada de passagem

`notas/moodle-catalogo.md` está desatualizado em dois pontos sobre esta família,
e os dois afirmam que o projeto está **mais aberto** do que está:

- o §4.1 diz "24 escritas, das quais o §2.2 bloqueia **uma**" e marca
  `core_message_send_messages_to_conversation` como "não bloqueado". Ela está no
  `BLOQUEIO_PERMANENTE` desde 31/08/2026, commit `892f6b1`, e hoje são **três**
  bloqueadas na família. A tabela por função, no fim do documento, repete o erro:
  só `send_instant_messages` aparece como `bloqueada-§2.2`;
- o §6.4, "a categoria do §2.2 está furada", lista
  `send_messages_to_conversation` e `create_contact_request` entre os nomes que
  faltam. As duas entraram.

Registrado no `docs/decisions/BACKLOG-correcoes.md`, sem desvio de tarefa.
