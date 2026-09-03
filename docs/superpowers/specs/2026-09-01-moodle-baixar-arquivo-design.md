# `baixar_arquivo` — a terceira ferramenta do Moodle

> Data: 01/09/2026. A autoridade continua sendo o `SPEC1.md`; este documento é o
> desenho de uma fatia vertical e da suíte que a especifica.
> Segue os moldes das trilhas anteriores de propósito: mesma separação
> `politica`/`cliente`/ferramenta/`server`, mesmas camadas de teste, mesmo padrão
> de erro legível.
>
> **Duas decisões do §9 do `SPEC1.md` (01/09/2026) são pressupostos deste desenho,
> não escolhas dele:** o download de arquivo funciona com o token no corpo do POST,
> e a ferramenta entrega o **caminho** do arquivo em disco, não o conteúdo. Se
> alguma das duas cair, este documento cai junto.

## 1. O problema

`material` responde "que arquivos tem no espaço da disciplina" e para aí, de
propósito: em 31/08 o download nunca tinha sido verificado, e emitir a URL interna
era a única forma conhecida de dar acesso — o que poria a credencial no contexto do
modelo (Invariante 3). A ferramenta lista o acervo e não entrega nada dele.

A pergunta que fica sem resposta é a continuação natural: *"me dá a lista 2 de
PSI3323"*, *"abre a apostila do amp op"*, *"quais foram as provas anteriores"*.

Três fatos medidos em 01/09 (§9 e `notas/fase1-moodle.md`) desbloqueiam isso:

1. **O token não precisa ir na URL.** O corpo do POST autentica igual. A premissa
   contrária estava escrita no §9 de 31/08 e na docstring de `material.py`, e dela
   se derivava o bloqueio inteiro.
2. **Erro de credencial chega como HTTP 200** com `Content-Type: application/json`
   e um `errorcode`. Não é 4xx. Quem checar status entrega JSON de erro achando que
   é PDF.
3. **O `filesize` declarado em `contents` bate exato** com os bytes recebidos.

## 2. A decisão que dá forma à ferramenta

**O MCP baixa e devolve o caminho; quem lê é o agente que chamou.** Registrada no
§9 em 01/09, a partir da pergunta do dono. As alternativas foram descartadas com
número:

| entrega | custo no PDF médio (838 kB) |
|---|---|
| blob base64 no canal MCP | **~302.000 tokens** |
| texto extraído no servidor | ~2.679 tokens, **e perde as figuras** |
| **caminho em disco** | **~50 tokens** |

"Perde as figuras" não é detalhe neste acervo: são PDFs de eletrônica — circuitos,
formas de onda, esquemas. Os slides medidos têm **280–440 B de texto por página**;
são quase só imagem. Extrair texto devolveria uma casca com aparência de sucesso,
que é a pior forma de violar o Invariante 6.

**Consequência de distribuição.** O §6 já decide que dado autenticado mora em
entrypoint local stdio, com cada pessoa trazendo o seu token. Publicar o projeto
significa distribuir o **pacote**, não hospedar um serviço — e nesse modelo o
servidor sempre roda na máquina de quem pergunta, então o caminho em disco vale
para qualquer usuário, não só para o dono. Cliente remoto sem filesystem
compartilhado fica fora, bloqueado antes por rede (§1.1) e credencial
(Invariante 4) — não pelo formato da resposta.

Por isso a função pura devolve **bytes + metadados** e não sabe o que é disco: se
um dia houver cliente remoto, `resources/read` reaproveita a mesma função sem
reescrita. Isso não é construir para o futuro; é não amarrar o download à escrita.

## 3. Superfície

```
baixar_arquivo(disciplina: str, nome: str, todos: bool = False)
```

| parâmetro | o que é |
|---|---|
| `disciplina` | sigla como no e-Disciplinas (PSI3323) ou pedaço do nome. Mesma resolução de `material` |
| `nome` | trecho do nome do arquivo, como aparece em `material`. Casamento por substring normalizada |
| `todos` | `False` (padrão) baixa um e recusa ambiguidade; `True` baixa o conjunto casado até o teto |

**Descrição para o modelo** (vocabulário de quem pergunta, não da API — T43 é o
precedente): fala em "baixar", "abrir", "pegar o PDF", "a lista", "a apostila", "a
prova anterior", e diz explicitamente que devolve um **caminho de arquivo local que
o próprio assistente deve abrir em seguida**.

O verbo no nome é deliberado: `material` lista e não tem efeito colateral;
`baixar_arquivo` grava em disco. O nome avisa.

## 4. Fluxo

1. **Resolve sigla → `courseid`** com `disciplinas.resolver`. Sigla que não resolve
   levanta erro **sem gastar chamada** — o padrão que `material` já pratica.
2. **`core_course_get_contents(courseid)`** — já está na allowlist; a política não
   muda. Reusa `material.projetar_material` em vez de duplicar a travessia
   seção→módulo→conteúdo, acrescentando ao `Item` os campos que o download precisa e
   que hoje são jogados fora: `fileurl_bruta` (a `fileurl` como veio), `fileid`,
   `mimetype`, e o nome da seção e do módulo, para o desempate. O campo se chama
   `fileurl_bruta` e não `fileurl_interna` porque a `fileurl` de um `url` externo
   passa pelo mesmo campo — é a **ausência de `fileid`** que distingue link de
   arquivo do webservice, não o nome do campo.

   **Cuidado que essa mudança exige, e ele tem um teste com nome:** acrescentar
   `fileurl` ao `Item` **não pode** fazer a saída de `material` emitir a URL interna.
   T68 é exatamente esse guarda e T69 é o outro lado (link externo sai inteiro).
   `_url_publica` continua sendo o único caminho para o que é *impresso*; o campo
   novo é para consumo interno de `arquivo.py`. Rode T68 e T69 depois de mexer no
   `Item` — se passarem sem você ter pensado neles, verifique por sabotagem que
   ainda alcançam o código.
3. **Casa `nome`** com a mesma normalização NFD de `disciplinas._normalizar` — a que
   o bug do acento de 31/08 ensinou. Casamento é substring, case-insensitive,
   sem-acento.
4. **Decide pelo número de casamentos:**
   - **0** → erro legível com o total de itens da disciplina, para distinguir "nada
     com esse nome" de "disciplina vazia" (o mesmo par que `material` já separa).
   - **1** → baixa.
   - **N e `todos=False`** → recusa e lista os candidatos com **seção + módulo +
     tamanho**. Não com o `fileid`: id não diz nada a quem lê.
   - **N e `todos=True`** → baixa até o teto, declarando o que ficou fora.
5. **Item que é link externo** (`modname == "url"`, sem `pluginfile.php`) não é
   baixado: devolve a URL, que já sai hoje por `material`, e diz que é link.
6. **Baixa**: POST em `fileurl` com `token` no corpo, form-urlencoded.
7. **Valida** antes de entregar (§6 abaixo).
8. **Grava** no depósito e devolve caminho + metadados.

## 5. Módulos

| arquivo | responsabilidade | depende de |
|---|---|---|
| `usp_mcp/moodle/arquivo.py` | orquestra: resolve, casa, decide, chama o download, monta a resposta. Função pura, não sabe o que é MCP | `disciplinas`, `material`, `deposito`, cliente injetado |
| `usp_mcp/moodle/deposito.py` | onde grava, como nomeia, o teto, o reuso do que já está em disco | só stdlib |
| `ClienteMoodle.baixar()` (novo método) | o transporte do download e a restrição de origem | — |

`deposito.py` existe separado porque "onde o byte mora" é uma decisão com regra
própria (caminho, sanitização, TTL, teto) que não tem nada a ver com casar nomes de
arquivo. Mantê-los juntos faria `arquivo.py` crescer para além do que se lê de uma
vez.

### 5.1 O que `arquivo.py` devolve

Dataclasses congeladas, no molde de `material.RespostaMaterial`:

```
Baixado:   nome, tipo, mimetype, tamanho, caminho (Path), fileid, secao, modulo, reusado
Link:      nome, url            # item externo, não baixado
Recusado:  nome, motivo         # teto, ou erro por arquivo no modo plural
RespostaArquivo:
    texto: str                  # o que o modelo lê
    baixados: tuple[Baixado, ...]
    links: tuple[Link, ...]
    recusados: tuple[Recusado, ...]
    candidatos: tuple[...] | None   # preenchido só na ambiguidade recusada
```

`texto` é a saída para o modelo; os campos estruturados existem para a suíte
assertar sem parsear texto — o mesmo motivo pelo qual `RespostaMaterial` tem
`total`/`mostrados`/`vazio_por`.

## 6. As regras que não são negociáveis

### 6.1 O cliente só baixa de `{self.url}/webservice/pluginfile.php`

A mais importante, e o motivo é forte: **o token vai no corpo do POST**. Uma
`fileurl` apontando para outro host mandaria a credencial do dono para lá. A
allowlist do §2 é por nome de função de web service e **não alcança este caminho**,
porque o download não é uma função de web service — então esta é a allowlist do
download, e mora no cliente pelo mesmo motivo que a outra: o cliente é o único
lugar por onde toda requisição passa.

A checagem roda **antes de qualquer I/O**, e o teste asserta que o transporte não
foi chamado — não que a saída deu erro.

### 6.2 `filename` é entrada não confiável e nunca compõe caminho

Na amostra de PSI3323 nenhum `filename` tem `/` ou `..`, e `filepath` é sempre `/`.
Uma amostra não prova ausência — este repo já registrou esse erro três vezes. O
nome vai para o disco como slug com whitelist `[A-Za-z0-9._-]`, truncado, e a
unicidade fica no **diretório**, não no nome:

```
~/.cache/usp-mcp/moodle/<courseid>/<fileid>-<timemodified>/<slug>.<ext>
```

- **Fora do repositório**, padrão XDG: numa instalação via `pip` não existe
  repositório, e material do professor não deve ficar dentro da árvore de trabalho
  protegido só pelo `.gitignore`.
- **`timemodified` no caminho** faz o Invariante 5 valer de graça: arquivo já
  baixado e não modificado não é rebaixado — o reuso é a existência do diretório.
- **`fileid`** (o primeiro segmento depois de `pluginfile.php/`) resolve a colisão
  real: em PSI3323, `Dicas para a Prova.pdf` existe **duas vezes**, com ids
  diferentes (9599793 na seção *Geral*, 9599833 na *AULA 6*).

**Campos ausentes têm regra, não improviso.** `timemodified` ausente ou `0` vira o
literal `0` no caminho — o efeito é que o arquivo é rebaixado sempre, que é o lado
seguro do erro. `fileid` que não puder ser extraído da `fileurl` é falha de
premissa: erro legível, sem gravar nada. Extensão vem do `filename`; sem extensão,
o slug fica sem sufixo (o mimetype vai na resposta de qualquer jeito).

### 6.3 Erro de credencial chega como HTTP 200

Duas validações, ambas obrigatórias antes de gravar:

1. **Content-type não pode ser JSON.** Se for, o corpo é lido como erro do Moodle e
   traduzido **pela mesma função** que `chamar` usa hoje — o bloco que hoje mora
   embutido em `chamar` (o `if "errorcode" in resposta`) sai para um helper interno
   e passa a ser chamado pelos dois. Duplicar a tradução criaria duas mensagens
   diferentes para `invalidtoken`, e a divergência apareceria justamente no dia em
   que o token expirar. Refatoração pequena e coberta pelos testes de erro
   existentes (T52/T56/T57).
2. **Os bytes recebidos batem com o `filesize` declarado.** Divergência é erro, não
   entrega parcial. Arquivo truncado entregue como bom é o pior resultado possível:
   o agente lê e responde com meia verdade.

### 6.4 Tetos, e nada de limite silencioso

| teto | valor | por quê |
|---|---|---|
| por arquivo | 50 MB | maior medido: 6,3 MB. Folga de 8x |
| plural: arquivos | 10 | os 19 PDFs da disciplina somam 15,9 MB |
| plural: bytes | 100 MB | — |

Como o `filesize` vem na listagem, a recusa acontece **antes de baixar**. O que
ficou fora do teto é **nomeado na resposta** (Invariante 7), nunca omitido.

**A ordem do corte é determinística**: a ordem em que os itens aparecem na
listagem (seção, depois módulo, depois conteúdo) — a mesma que `material` imprime.
Nada de "os menores primeiro" nem de ordenação implícita: quem lê a lista em
`material` e pede `todos=True` recebe o prefixo do que viu.

**Arquivo interno sem `filesize` utilizável** (ausente ou `0`) não pode ser recusado
por antecipação: baixa com corte no teto por arquivo e, se o corte for atingido,
falha com erro dizendo que o arquivo excede o teto. Não grava truncado.

## 7. Erros legíveis (Invariante 6)

| situação | resposta |
|---|---|
| sigla não resolve | erro de `disciplinas.resolver`, sem gastar chamada |
| nenhum arquivo casa | "Nenhum arquivo com `X` no nome. A disciplina tem N itens" — distingue de disciplina vazia |
| vários casam, `todos=False` | lista seção + módulo + tamanho de cada candidato, e diz como repetir |
| item é link externo | não baixa, devolve a URL e explica que é link, não arquivo |
| acima do teto | nome, tamanho e teto, antes de baixar |
| JSON com HTTP 200 | erro do Moodle traduzido (`invalidtoken` → instrução de regerar o token) |
| tamanho divergente | erro dizendo esperado × recebido; nada é gravado |
| host fora do e-Disciplinas | recusa explicando que o download só sai para o e-Disciplinas |
| disco sem permissão | erro dizendo o caminho tentado |

Toda resposta bem-sucedida carrega o aviso de que **o arquivo está em disco e quem
o abre é o assistente que chamou** — sem isso, um cliente que não saiba ler arquivo
local recebe um caminho e não entende o que fazer com ele.

## 8. Suíte — escrita antes da implementação

Continuando a numeração do repo (o último é T83). Camadas: `politica` e `contrato`
offline; nada de rede na suíte padrão.

| id | o que trava |
|---|---|
| T84 | sigla que não resolve levanta erro **sem** chamar o transporte |
| T85 | nome que não casa: erro nomeia o total de itens da disciplina |
| T86 | um casamento: baixa, grava, devolve o caminho |
| T87 | **colisão real**: `"dicas"` casa com dois na fixture; recusa listando **seção e módulo** de cada |
| T88 | mesma colisão com `todos=True`: baixa os dois, em diretórios distintos por `fileid` |
| T89 | casamento é normalizado (NFD): `"formulario"` casa com `"Formulário…"` |
| T90 | link externo não é baixado; devolve a URL e o rótulo de link |
| T91 | **URL de outro host é recusada antes de qualquer I/O** — asserta que o transporte **não foi chamado** |
| T92 | `filename` com `../` e com `/` (fabricado) não escapa do diretório do depósito |
| T93 | resposta JSON com HTTP 200 vira erro legível; nada é gravado |
| T94 | tamanho divergente do `filesize` vira erro; nada é gravado |
| T95 | arquivo já em disco com o mesmo `fileid-timemodified` **não** é rebaixado (transporte não chamado) |
| T96 | `timemodified` diferente **é** rebaixado, em diretório novo |
| T97 | acima do teto por arquivo: recusa **antes** de baixar, pelo `filesize` |
| T98 | `todos=True` acima do teto de contagem/bytes: baixa o que cabe e **nomeia** o que ficou fora |
| T99 | o token nunca aparece na URL, no caminho gravado, nem em nenhuma mensagem de erro |
| T100 | a ferramenta aparece em `listar_ferramentas` com descrição e parâmetros anotados (`adaptador.anotar`) |
| T101 | `chamar_ferramenta` roteia `baixar_arquivo` com cliente injetado, sem credencial |
| H10 | handshake stdio: a ferramenta aparece no fio com o schema certo e `disciplina`/`nome` obrigatórios |

**Precedentes que a suíte tem de honrar**, cada um comprado com um bug:

- **Asserte sobre o que foi enviado, não sobre a saída** — o dublê devolve o que o
  teste mandou. T91 e T95 valem pelo transporte *não* chamado; T97 pela ausência de
  requisição.
- **Uma disciplina só não prova resolução** — T86 e T87 usam ids distintos, pela
  mesma armadilha que T72 e T47 caíram.
- **Ausência de default é o que torna o parâmetro obrigatório no fio** — H6 pegou
  isso em `material` depois de T78–T81 passarem. `disciplina` e `nome` **não têm
  default**; `todos` tem.
- **Verifique cada asserção por sabotagem** da produção antes de considerá-la
  pronta.

## 9. Fora de escopo, declarado

- **Extração de texto e `pypdf`.** Fechado por descarte no §9 de 01/09: quem lê é o
  agente. Nenhuma dependência de runtime nova — o projeto segue só com `mcp`.
- **MCP Resources.** A função pura já devolve bytes + metadados, então adicionar
  depois não reescreve nada. Hoje não há cliente que a exercite.
- **`mod_folder`.** Segue questão aberta do §4: PSI3323 não tem nenhum. A ferramenta
  trata o que a listagem entregar; se uma Pasta aparecer e `get_contents` não a
  expandir, é a mesma lacuna que `material` já tem, não uma nova.
- **`.docx`, `.jpeg`, `octet-stream`.** São baixados como qualquer arquivo — o
  servidor não precisa entender o formato. O que o cliente sabe abrir é limite dele,
  e a resposta diz o mimetype para que ele decida.
- **OCR** e **limpeza automática do depósito por idade**. A segunda vira linha de
  backlog: hoje o depósito só cresce, e apagá-lo à mão é seguro por construção.

## 10. Definição de pronto

1. `./scripts/gate.sh` verde, incluindo o handshake.
2. Verificada **ao vivo** contra pelo menos duas disciplinas, com um caso de
   ambiguidade e um de reuso de cache — a suíte não alcança o transporte real, e
   isso já custou o bug do timeout de 15 s.
3. Decisão e medição registradas no §9 do `SPEC1.md`; achado colateral no
   `BACKLOG-correcoes.md`.
4. Nenhum segredo nem dado pessoal não higienizado no git.
