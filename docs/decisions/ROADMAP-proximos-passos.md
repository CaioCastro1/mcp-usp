# Roadmap — próximos passos, em ordem de prioridade

> Levantado em 14/09/2026, a partir de três pedidos do dono do fork mais um
> mapeamento de duas fontes: o `loyaniu/moodle-mcp` (35 estrelas, o único
> comparável real) e as **447 funções que o e-Disciplinas libera ao token**,
> medidas na conta de um aluno em 14/09.
>
> Isto **não** é o `BACKLOG-correcoes.md`. Lá fica dívida achada de passagem;
> aqui fica trabalho novo escolhido de propósito. Decisão fechada continua indo
> para o §9 do `SPEC1.md`.

Prioridade foi ordenada por **quanto destrava dividido pelo que custa**, e não
por quanto a ideia agrada. Por isso a licença vem antes de qualquer ferramenta
nova: ela custa dez minutos e hoje bloqueia tanto a distribuição quanto o
onboarding.

Cada item diz o que é **trabalho** e o que é **decisão**. Decisão não se
implementa por iniciativa de quem lê: ela volta para o dono do repositório.

---

## P0 — fundação: barato, e destrava o resto

### A1. Licença · **ADIADO por decisão de 14/09/2026**

O repositório **não tem licença nenhuma**, e por ora vai continuar assim: a
pergunta foi feita e a resposta foi "nenhuma por enquanto" (14/09/2026).

Fica registrado o que essa escolha implica, para que a próxima pessoa a levantar
o assunto não precise redescobrir: sem licença, o padrão legal é **todos os
direitos reservados** — ninguém pode usar, modificar ou redistribuir, mesmo com o
código público. Na prática isso alcança inclusive quem instalar seguindo o
*"Para quem acabou de ganhar acesso"* do README.

Vale reabrir junto com o B1, porque distribuir como pacote ou `.mcpb` torna a
lacuna visível para quem não conhece o projeto. O comparável `loyaniu` também não
tem licença; o `SaadRahman01/moodle-mcp` tem MIT.

Com o A1 adiado, o P0 é **A2 + A3**.

### A2. O furo no bloqueio permanente · trabalho · ~1 h

**Achado no mapeamento de 14/09, e é o único item desta lista que é risco e não
funcionalidade.** Duas funções que escrevem em nome do aluno estão vivas no
token e **não** estão no `BLOQUEIO_PERMANENTE` do §2.2:

| função | no site | no §2.2 |
|---|---|---|
| `mod_choice_submit_choice_response` | sim | **não** |
| `mod_feedback_process_page` | sim | **não** |

Hoje elas são barradas pela allowlist, que nega por omissão — e isso está certo,
é a primeira linha. Mas o §2.2 existe justamente como **segunda** camada, para o
dia em que alguém acrescentar algo à allowlist por engano. O próprio arquivo diz
isso: *"garante que um erro futuro na allowlist ainda não libere um destes
nomes"*. Responder enquete e enviar formulário de feedback em nome do aluno é
exatamente a classe que a lista cobre — `core_message_send_instant_messages` e
`mod_forum_add_discussion` já estão lá pelo mesmo motivo.

Cura: dois nomes na lista, com o motivo escrito, e um teste que reprove se
saírem. O T7 já trava o conjunto exato, então a mudança é visível.

Vale revisar a lista inteira contra as 447 na mesma passada — este mapeamento
olhou o que "preencher atividade" exigiria, não o conjunto todo.

### A3. Ferramenta `diagnostico` · trabalho · ~2 h

> **Correção de 14/09, depois de escrever este arquivo.** Isto foi proposto sem
> eu ter lido `notas/portabilidade-moodle.md` e `scripts/compatibilidade.sh`,
> que **já estavam na `main`**. O script responde a mesma família de pergunta
> **antes e sem credencial nenhuma**, e a nota já mediu 17 instituições.
> A ferramenta continua valendo, mas como **segundo passo**: o script diz se o
> site tem o serviço ligado, e a própria nota registra que verde lá *"NÃO
> promete que as ferramentas respondem bem"*. É essa distância que a ferramenta
> cobre, e só com token. Não substitui o script — aponta para ele.

Inspirada no `list_ws_functions` do `SaadRahman01`, e é a ideia mais barata das
duas leituras. Uma ferramenta que devolve **o que o Moodle de quem está rodando
de fato expõe**, lendo o campo `functions` do `core_webservice_get_site_info` —
chamada que o projeto já faz para derivar o `userid`, então **custa zero chamada
nova**.

O que ela responde, e hoje ninguém responde sem ler código:

- quantas funções o meu token alcança (na USP: 447);
- quais das que este servidor usa estão disponíveis aqui;
- qual release do Moodle (na USP: 5.0.8+);
- e, por tabela, **"isso funciona na minha faculdade?"**.

É pré-requisito honesto de tudo em P2: antes de escrever a ferramenta de notas,
esta diz se `gradereport_*` existe naquele site.

---

## P1 — os três pedidos do dono do fork

### B1. Rodar fora do Claude Code · trabalho + medição · ~1 dia

**Onde já está:** a PR #27 pôs metade do caminho de pé. O `scripts/servidor.sh`
resolve a própria raiz e sobe de qualquer `cwd` — verificado com cliente MCP real
a partir de `/tmp`, nos três servidores. O README ganhou a seção *Cliente que não
faz `cd`*, com `<CAMINHO-DO-CHECKOUT>`.

**O que falta, e é o que o §6.1 registra por leitura de documentação e nunca por
uso:** empacotar como **MCP Bundle (`.mcpb`)**. Duas coisas dependem de uma
instalação real numa máquina limpa e **não** de estimativa:

1. **Quanto atrito o runtime Python devolve.** O formato recomenda Node porque
   Node acompanha o Claude Desktop; Python não.
2. **Onde o `"sensitive": true` do `user_config` guarda o valor.** A spec do
   manifest diz "armazena com segurança" e não diz onde. O Invariante 3 quer
   saber, e a resposta muda se o caminho for aceitável.

Um degrau intermediário, mais barato que o `.mcpb` e que já entrega quase tudo:
publicar como pacote instalável com entry point, como o comparável faz
(`[project.scripts] moodle-mcp = "moodle_mcp.server:main"`). Vira `uvx`/`pipx` e
mata o `git clone` + venv do onboarding — o que faz deste item e do B2 o mesmo
trabalho, feito uma vez.

**Não esquecer:** o Claude Desktop roda em macOS e Windows, não Linux. Se o
`.mcpb` virar o caminho de distribuição, quem usa Linux fica com o fluxo de hoje
e não há nada escrito para essa pessoa.

### B2. Onboarding · trabalho · ~meio dia

O fluxo atual funciona — foi percorrido inteiro por uma segunda pessoa em
12/09/2026, do zero até as três ferramentas do Moodle respondendo ao vivo. As
fricções abaixo são as **medidas nessa passagem**, não hipóteses:

1. **O passo do link é o que trava.** O `token.sh` manda "botão direito no link →
   copiar endereço", mas a página do `launch.php` mostra uma caixa verde
   ("O seu cadastro foi confirmado"), um botão cinza ("Ambientes") e um link azul
   escrito *"Clique aqui se a aplicação não abrir automaticamente"*. Nada nela
   parece um token, e o texto do link sugere que ele é um plano B dispensável.
   Na primeira tentativa o que foi para o clipboard foi a URL do próprio
   `launch.php` — 137 bytes, que o decodificador recusou corretamente.
   **Cura barata:** o script citar o texto do link em voz alta e dizer para
   **não clicar** nele.
2. **Não há como conferir o clipboard antes de gastar a tentativa.** `pbpaste |
   cut -c1-21` mostra `moodlemobile://token=` sem expor nada. Isso merecia ser um
   passo do próprio script, ou pelo menos uma linha do README.
3. **`git clone` + venv.** Some com o B1, e é o argumento mais forte para fazer
   os dois juntos.
4. **Sem licença, ninguém pode legalmente usar o que acabou de instalar** (A1).

Não mexer: o script **não imprimir o token** e confirmar contra a USP antes de
gravar. As duas coisas são o que fazem "gravei" significar "funciona", e o
comparável não tem nenhuma das duas.

### B3. "Preencher atividade" · **DECISÃO, não trabalho**

> **RESPONDIDO em 15/09/2026, e o encaminhamento abaixo foi seguido.** A resposta
> foi **sim parcial**: as duas de `mod_assign` passam a ser chamáveis sob
> condição, as três de questionário continuam recusadas. Como manda o último
> parágrafo deste item, a resposta veio como **spec antes de uma linha de
> código** — `docs/superpowers/specs/2026-09-15-entrega-com-confirmacao-design.md`
> (PR #58) — e a decisão está no §9 do `SPEC1.md`, com a data. O texto abaixo
> fica como estava porque é o levantamento que sustentou a pergunta; o que mudou
> é que ela tem resposta. **A implementação não foi feita**: o
> `BLOQUEIO_PERMANENTE` continua com 40 nomes até ela entrar.

Este item colide de frente com o desenho do projeto, e por isso volta para o dono
antes de virar tarefa.

**O que é tecnicamente possível.** As funções existem e estão vivas no token —
medido em 14/09: `mod_assign_save_submission` (salva rascunho),
`mod_assign_submit_for_grading` (entrega), `mod_quiz_start_attempt`,
`mod_quiz_save_attempt`, `mod_quiz_process_attempt`. Não é questão de API.

**O que o projeto decidiu.** As cinco estão no `BLOQUEIO_PERMANENTE` do §2.2 —
a lista que o §2.2 define como válida **mesmo com `USP_MCP_ALLOW_WRITES` ligada**,
isto é, sem flag que libere. O Invariante 1 é read-only por padrão; estas cinco
não são "ainda não implementadas", são **recusadas por escrito**.

**Três coisas para pesar, e nenhuma é técnica:**

- Quem escolhe a função é um modelo interpretando linguagem ambígua. "Salva aí
  pra mim" e "entrega isso" são uma palavra de distância, e `submit_for_grading`
  **não tem desfazer**.
- Entrega feita por assistente é matéria de integridade acadêmica da USP, não do
  repositório. Quem liga isso assume esse risco em nome de quem usa.
- Ligar o rascunho sem a entrega (`save_submission` sem `submit_for_grading`) é
  uma posição intermediária defensável — mas os dois estão na mesma lista, e
  tirar um de lá é reabrir o §2.2, não configurar.

**Encaminhamento sugerido:** se a resposta for não, vale registrar no §9 que a
pergunta foi feita e respondida, com a data — hoje a lista diz *o quê* e não que
já houve pedido para reabri-la. Se for sim, isto precisa de um spec próprio antes
de uma linha de código, com o desenho da confirmação humana no meio do caminho.

**Alternativa que não colide e entrega quase o mesmo valor:** `mod_assign_get_submission_status`
(ver C2) responde *"eu já entreguei isso?"*, que é a pergunta que o aluno faz na
véspera. Ler o estado resolve a ansiedade; escrever resolve a preguiça.

---

## P2 — as três lacunas que o README declara, e que o comparável prova funcionarem

O `README.md` diz, hoje: *"O que ainda não existe: notas, 'já entreguei?', aviso
de professor"*. O `loyaniu/moodle-mcp` implementa as três, e eu conferi **uma a
uma** contra o e-Disciplinas em 14/09. Todas disponíveis:

| # | Ferramenta | Funções | e-Disciplinas |
|---|---|---|---|
| C1 | notas | `gradereport_overview_get_course_grades`, `gradereport_user_get_grade_items` | **sim** |
| C2 | já entreguei? | `mod_assign_get_submission_status` | **sim** |
| C3 | aviso de professor | `mod_forum_get_forums_by_courses`, `mod_forum_get_forum_discussions` | **sim** |
| C4 | o que mudou desde X | `core_course_get_updates_since` | **sim** |

**Armadilha medida:** o comparável chama `mod_forum_get_discussions`, que **não
existe** no Moodle 5.0 da USP. A função atual é `mod_forum_get_forum_discussions`.
Copiar a lista dele sem conferir dá erro em produção.

Ordem sugerida dentro do P2: **C2 antes de C1**. "Já entreguei?" é a pergunta da
véspera do prazo, conversa direto com o `o_que_vence` que já existe, e custa uma
função só. Notas é mais visível mas é consulta ocasional.

Cada uma entra pela porta de sempre: nome novo na allowlist com decisão no §9,
projeção medida em bytes, erro legível, e as três camadas de teste.

---

## P3 — além do comparável: o que saiu do mapeamento das 447

Nada aqui está no `loyaniu`. Saiu de ler a lista de funções que a USP expõe.

### D1. Notas de questionário sem tocar em tentativa · ~3 h

`mod_quiz_get_user_best_grade`, `mod_quiz_get_user_attempts`,
`mod_quiz_get_attempt_review` — todas de **leitura**, todas disponíveis. Dão nota
e revisão de questionário **sem** chegar perto de `start_attempt`.

Importa porque metade dos vencimentos reais é questionário: numa amostra de
14 dias, 3 dos 4 itens de `o_que_vence` eram `questionário`. A ferramenta de
notas do P2 (`gradereport_*`) cobre a nota final do curso; esta cobre o item.

### D2. `mod_folder` — fecha um item aberto do backlog · **FEITO em 15/09/2026**

`mod_folder_get_folders_by_courses` e `core_files_get_files` existem no site. O
backlog registra desde 31/08 que **não se sabe** se `core_course_get_contents`
expande o conteúdo de um `mod_folder`, e que três disciplinas amostradas não
tinham pasta nenhuma — três amostras sem pasta não provam ausência.

Uma disciplina que agrupe as listas numa Pasta é justamente o caso que `material`
precisa acertar e pode estar errando em silêncio hoje. Medir isso fecha a questão
com dado, que é como o §9 fecha as outras.

> **Feito em 15/09/2026, e a resposta foi "nada a consertar".** `core_course_get_contents` expande sim: as dez pastas de
> `PEA3301_2026_1sem` chegam com `contents` preenchido, e 54% dos arquivos daquela
> disciplina moram dentro de pasta. `material` já as mostra, porque itera o
> `contents` de todo módulo. **Nenhuma das duas funções entra na allowlist**: a de
> pastas descreve sem listar arquivo, que é menos do que já temos, e a de arquivos
> resolveria um problema inexistente. Medição em `notas/mod-folder.md`.

### D3. Anotações de ferramenta no protocolo · **FEITO em 15/09/2026**

Entrou na PR #63, e a decisão está registrada no §9 do `SPEC1.md` (15/09). As
treze ferramentas declaram `readOnlyHint`, `destructiveHint` e `openWorldHint`, e
`baixar_arquivo` declara também `idempotentHint`. O que o item não previa, e é o
que sobrou de aprendizado: `baixar_arquivo` **não** é read-only no sentido do
protocolo, porque ela grava no depósito em disco de quem chama, e o campo
pergunta se a ferramenta modifica o ambiente e não se ela escreve no Moodle.

`readOnlyHint` e `destructiveHint` são campos do MCP que o cliente lê para saber
que uma ferramenta é segura. O `SaadRahman01` declara; nós não. O Invariante 1
diz read-only, mas hoje isso é promessa em prosa — o protocolo tem campo para
dizer a mesma coisa de um jeito que a máquina entende.

Encaixe perfeito com a filosofia do projeto e uma das coisas mais baratas da lista.

### D4. CI · **FEITO em 15/09/2026**

Entrou na PR #60, e a decisão está registrada no §9 do `SPEC1.md` (15/09).
`.github/workflows/offline.yml` roda o `scripts/gate.sh` em cada push e em cada
pull request, em 3.11 e 3.14, com a camada `live` de fora como o item mandava. O
runner é **macOS**, e isso não é preferência: o primeiro CI que existiu rodou em
Linux e reprovou por 735 de 736, num teste que depende do sistema de arquivos não
separar NFD de NFC. Fechar essa linha do `BACKLOG-correcoes.md` libera o runner
Linux, que custa 10x menos minuto.

O `gate.sh` é melhor que o CI dos dois comparáveis — e só roda quando alguém
lembra. Uma action que rode a camada offline em cada push custa pouco. A camada
`live` **não** entra, pelo mesmo motivo que ela não entra no gate: um CI que
depende da USP estar de pé reprova PR por motivo errado.

### D5. Moodle genérico + pacote USP · **DECISÃO** · reorganização real

> **Correção de 14/09.** O levantamento abaixo foi escrito por leitura de
> código, e a `notas/portabilidade-moodle.md` (13/09, já na `main`) **já tinha
> medido isto melhor**: as 5 funções da allowlist são core upstream, o piso do
> projeto é **Moodle 3.3** (a função do calendário não existe em 2.9), e os
> pontos que travam fora da USP são **quatro**, não os três que listei — falta
> o fuso fixo em −3, e o de `shortname` tem um agravante que eu não tinha visto:
> `resolver` nunca olha `d.rotulo`, então num site com shortname
> `2026S2-BIO-101` procurar "BIO101" não acha, mesmo com a string literalmente
> lá. Leia a nota antes deste item; o que sobra aqui é a **decisão de escopo**,
> não o levantamento.

O servidor do Moodle já é quase genérico: as quatro funções são Moodle core, o
`MOODLE_URL` é configurável, e `resolver` casa sigla exata, prefixo ou pedaço do
nome, sem formato fixo. O que amarra na USP:

- `_URL_PADRAO = "https://edisciplinas.usp.br"` — default, não obrigação;
- `sigla = shortname.split("-")[0]` — convenção USP (`PTC3314-2026` → `PTC3314`),
  que **degrada bem**: num Moodle sem hífen a sigla vira o shortname inteiro;
- as descrições dizem "e-Disciplinas (Moodle da USP)" — e esse é o texto que o
  **modelo** lê para decidir se a ferramenta serve. Numa faculdade diferente ele
  pode concluir que não serve;
- a Senha Única é SSO da USP. O fluxo do `launch.php` é padrão Moodle e funciona
  em qualquer instalação com webservice ligado; a tela de login é que não.

`usp-rucard` e `usp-jupiter` são 100% USP e não têm como ser genéricos — bandejão
e JupiterWeb não existem em outra universidade.

Então **1 dos 3 servidores é portável com trabalho modesto**, e é o mais valioso.
Isto é decisão de escopo, não refactor: muda o que o projeto é.

---

## O que NÃO copiar do comparável

O `loyaniu` expõe `decompose_task`, `create_implementation_plan`,
`extract_assignment_requirements` e `find_relevant_materials`. Soam como as
ferramentas mais impressionantes da lista dele. São `re.findall(r"[a-zA-Z]{3,}")`
com as 20 primeiras palavras do enunciado, ranqueadas por palavra-chave.

Este projeto construiu isso e **reverteu no mesmo dia** — §9, 03/09/2026: *"busca
semântica é do modelo, não de heurística de string"*. O caminho já foi andado e a
volta está registrada. Copiar seria reabrir uma decisão fechada com dado.

Sendo justo com ele: essas ferramentas entregam **algo** hoje, mesmo que raso,
enquanto a aposta daqui depende de o modelo ser bom. É uma escolha, não um erro
dele — mas é uma escolha que este projeto já fez, para o outro lado.

Duas coisas dele que **valem** copiar, e já estão acima: a tabela declarativa
`DELETE_FIELDS` (campos removidos por função, num lugar só — mais auditável que
projeção espalhada por módulo) e a própria lista de funções, que é um mapa de
terreno que alguém já percorreu.

E uma que vale copiar ao contrário: ele manda o token na **query string de um
`GET`** (`requests.get(MOODLE_URL, params=...)`), o que o deixa no log de acesso
do servidor e de qualquer proxy no caminho. Aqui já vai por corpo de `POST`, e o
`token.sh` usa `curl -K -` para não passar em `argv`. Vale um teste que **trave**
isso, já que agora se sabe que é uma forma fácil de errar.
