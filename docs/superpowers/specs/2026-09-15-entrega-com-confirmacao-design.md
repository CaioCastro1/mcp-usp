# Entregar atividade com confirmação humana explícita — design

> 15/09/2026. Este spec **reabre o §2.2**. Duas das cinco funções que a lista de
> bloqueio permanente recusa por escrito passam a ser chamáveis sob condição.
> Isso não é configuração, é mudança de decisão, e por isso existe um spec antes
> de uma linha de código.
>
> O pedido é do dono do fork, com a condição dele: *confirmação humana
> explícita*. O trabalho deste documento é descobrir o que essa frase pode
> significar de verdade num servidor MCP, e dizer em voz alta onde ela não
> alcança.

## O que está decidido hoje

`usp_mcp/moodle/politica.py:101` lista quarenta funções no `BLOQUEIO_PERMANENTE`.
Cinco delas são o assunto aqui:

| função | o que faz | tem desfazer? |
|---|---|---|
| `mod_assign_save_submission` | salva rascunho da entrega | sim, salvando de novo |
| `mod_assign_submit_for_grading` | entrega para correção | **não** |
| `mod_quiz_start_attempt` | abre tentativa de questionário | **não**, e consome tentativa |
| `mod_quiz_save_attempt` | salva respostas da tentativa aberta | sim, enquanto aberta |
| `mod_quiz_process_attempt` | finaliza a tentativa | **não** |

`decidir` (`politica.py:178`) recusa as cinco antes de olhar a allowlist, e
recusa **mesmo com `permitir_escrita=True`**. A docstring diz isso com todas as
letras: a flag "não é usada aqui para liberar nada".

As cinco estão vivas no token, medido em 14/09. O caminho de escrita foi
exercitado ponta a ponta fora do projeto em 15/09, num questionário sem nota.
Não é questão de API. É questão de decisão.

## O que foi medido para este spec

**1. O protocolo tem elicitação, e ela não garante um humano.**
`mcp 2.2.0` expõe `Context.elicit(message, schema)`. A docstring do próprio SDK
diz: *"If the client is an agent, it might decide how to handle the elicitation,
either by asking the user or automatically generating a response."*

Isto é decisivo. Elicitação é a forma certa de **apresentar** a pergunta, e é a
coisa errada para **ser** a garantia. Um cliente pode responder sozinho, dentro
da especificação, sem nada de errado acontecer.

**2. Tudo que o servidor diz ao modelo, o modelo pode repetir.**
Um código de confirmação impresso na saída da ferramenta chega ao modelo junto
com o resto do texto. Ele pode devolvê-lo na chamada seguinte sem que nenhum
humano tenha lido. Qualquer desenho que trate esse código como prova de presença
humana está errado.

**3. Dentro do Claude Code o modelo tem shell.**
Arquivo de confirmação, variável de ambiente, marca com prazo: tudo isso é
alcançável por `Bash`. Não existe portão do lado do servidor que um modelo com
shell não possa abrir.

**4. O estado anterior da entrega é legível e rico.**
`mod_assign_get_submission_status`, capturado em 15/09 em
`fixtures/moodle/submission_status_ec1.json`, traz em `lastattempt`: `status`,
`canedit`, `cansubmit`, `locked`, `gradingstatus`, `extensionduedate`,
`timelimit`, `teamsubmission`, e a lista de arquivos por `filearea`. Dá para
montar um plano fiel do que mudaria, **sem escrever nada**.

**5. `teamsubmission` existe no retorno.**
Entrega de grupo escreve em nome de outras pessoas, que não estão na conversa e
não consentiram. É uma classe diferente de ação.

## O modelo de ameaça, escrito antes do desenho

O que este desenho protege contra: **acidente e ambiguidade.** "Salva aí pra mim"
e "entrega isso" são uma palavra de distância, e a segunda não tem volta.

O que este desenho **não** protege contra: um modelo que decidiu entregar e tem
shell. Ver o item 3 acima.

Dizer isso aqui não é derrotismo, é o que separa um portão honesto de um teatro.
Um portão que promete mais do que cumpre é pior do que nenhum, porque faz quem
liga a flag baixar a guarda.

## Desenho

### Camada 1. Verbos separados, nunca um booleano

Duas ferramentas distintas, com nomes que não se confundem:

- `salvar_rascunho` chama `mod_assign_save_submission`;
- `entregar` chama `mod_assign_submit_for_grading`.

Nada de `acao: "salvar" | "entregar"`. Um enum põe as duas a uma letra de
distância na cabeça de quem gera a chamada, que é exatamente o risco medido.

### Camada 2. Plano e execução em duas invocações

`entregar` **nunca escreve na primeira chamada.** A primeira devolve um plano:

```
Plano de entrega — PTC3314, EC-1
  estado agora: rascunho, editável, não travado
  prazo: 18/09/2026 23:59 (faltam 3 dias)
  arquivos anexados: lista-1.pdf (240 kB)
  o que muda: rascunho passa a "entregue para correção"
  isto NÃO tem desfazer pela API

Para confirmar, chame de novo com confirmacao="a3f9c1"
```

O `a3f9c1` é o começo de um hash do plano: id da atividade, `status`, conjunto de
arquivos com tamanho, e `timemodified`. Ele **não é prova de humano** (ver medição
2). Ele é prova de que o plano não mudou entre a leitura e a escrita. Se alguém
anexou outro arquivo, se o prazo foi prorrogado, se a entrega já estava entregue,
o hash muda e a segunda chamada é recusada com o plano novo.

Esta é a camada que resolve o problema real que temos: estado velho virando
escrita errada.

### Camada 3. Elicitação como apresentação

Entre o plano e a escrita, `Context.elicit` com o texto do plano e um esquema de
um campo só. É onde um cliente com humano na frente mostra a pergunta.

Recusa explícita (`action == "decline"`) cancela. Cliente que não suporta
elicitação **não** bloqueia o fluxo: a camada 2 continua valendo. O código trata
a ausência de suporte como "não pude perguntar", que é diferente de "perguntei e
disseram não", e diz qual dos dois aconteceu.

### Camada 4. A flag nova, e por que não a antiga

`USP_MCP_ALLOW_WRITES` está documentada nos três servidores como flag que não
abre nada. Reaproveitá-la muda em silêncio o significado de uma linha que existe
em `rucard/politica.py`, `jupiter/politica.py` e `moodle/politica.py`, e que os
testes de cada um afirmam.

Entra `USP_MCP_ENTREGA`, desligada por padrão, só no Moodle. E um conjunto novo
em `politica.py`:

```python
ESCRITA_CONFIRMADA = frozenset({
    "mod_assign_save_submission",
    "mod_assign_submit_for_grading",
})
```

`decidir` ganha um terceiro caminho, entre o bloqueio e a allowlist: função em
`ESCRITA_CONFIRMADA` é permitida **somente** se a flag estiver ligada e o call
site declarar que passou pela confirmação. As duas saem do `BLOQUEIO_PERMANENTE`,
que cai de 40 para 38 nomes.

### Camada 5. Recusas que a flag não abre

Mesmo com tudo ligado, `entregar` recusa e diz por quê:

- `teamsubmission` verdadeiro, porque escreve em nome de terceiros;
- `locked` verdadeiro ou `cansubmit` falso, porque o site já disse não;
- `status` já `submitted`, porque não há o que entregar;
- plano com zero arquivos, porque entregar vazio é o acidente mais caro e mais
  silencioso da lista.

## O que não entra nesta fase

As três de questionário ficam no `BLOQUEIO_PERMANENTE`. A razão é de desenho, não
de conforto: para entrega de atividade existe um estado anterior legível e um
rascunho que se sobrescreve, então dá para mostrar um plano fiel. Para tentativa
de questionário não existe rascunho, `start_attempt` já é irreversível, e o plano
honesto seria "vou abrir uma tentativa e não sei dizer o que acontece depois".

Fica anotado para a Fase 2 que `mod_quiz_get_quizzes_by_courses` devolve
`attempts`, com `0` para tentativas ilimitadas. Um portão de questionário que
comece exigindo `attempts == 0` é a versão defensável, e é por onde a Fase 2
deve começar se ela existir.

## Bateria de testes

Camada `politica`, offline:

- **E1** `decidir("mod_assign_submit_for_grading")` sem flag é recusa, e o motivo
  cita a flag pelo nome.
- **E2** com `USP_MCP_ENTREGA=1` mas sem confirmação declarada, ainda é recusa.
- **E3** com flag e confirmação, é permitida.
- **E4** as três de questionário são recusadas nas três combinações acima.
- **E5** `BLOQUEIO_PERMANENTE` tem 38 nomes e não contém as duas de assign.
- **E6** `ESCRITA_CONFIRMADA` e `ALLOWLIST` são disjuntos, e nenhum nome de
  `ESCRITA_CONFIRMADA` está no bloqueio permanente.

Camada `contrato`, offline, contra a fixtura capturada:

- **E7** primeira chamada de `entregar` não toca o transporte. Cliente dublê que
  registre qualquer `mod_assign_submit_for_grading` reprova.
- **E8** o hash do plano muda quando muda o conjunto de arquivos, quando muda o
  `status`, e quando muda o `timemodified`.
- **E9** confirmação com hash velho é recusada, e a mensagem traz o plano novo.
- **E10** `teamsubmission`, `locked`, `cansubmit` falso, `status` já entregue e
  lista de arquivos vazia: cinco recusas, cinco mensagens distintas.
- **E11** cliente sem suporte a elicitação não bloqueia, e a saída distingue "não
  pude perguntar" de "perguntaram e recusaram".
- **E12** `salvar_rascunho` e `entregar` são ferramentas separadas no
  `tools/list`, e nenhuma das duas aceita parâmetro que escolha entre salvar e
  entregar.

Camada `live`, atrás de `USP_MCP_LIVE=1` **e** `USP_MCP_ENTREGA=1`:

- **E13** plano de uma atividade real bate com o que o site diz, sem escrever.
  Escrita ao vivo não entra na suíte: um teste que entrega atividade de verdade
  é o próprio acidente que este spec existe para evitar.

Handshake:

- **E14** com a flag desligada, as duas ferramentas novas não aparecem no
  `tools/list`. Ferramenta que aparece e sempre recusa ensina o modelo a tentar.

## Critério de parada

As catorze passam, o `gate.sh` passa 4/4, e a suíte inteira fica verde com a flag
desligada **e** com ela ligada. A contagem de ferramentas do Moodle vai de 10 para
12 só quando a flag está ligada.

## O que precisa ir para o §9

Três registros, com data:

1. que a pergunta do §2.2 foi feita e **respondida com sim parcial**, em 15/09;
2. que duas funções saíram do bloqueio permanente e para onde foram;
3. que a confirmação humana é forte contra acidente e fraca contra um modelo com
   shell, e que essa fraqueza é conhecida e aceita, e não um descuido.

O terceiro é o que mais importa. Ele é a diferença entre alguém ligar a flag
sabendo o que ligou, e alguém ligar achando que comprou uma garantia.
