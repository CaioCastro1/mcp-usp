# Os links que o professor deixa no texto da página — design

> 17/09/2026. Fecha um achado do dono em uso real: perguntou pelos slides de uma
> disciplina, `material` respondeu "não tem nenhum", e os slides estavam num link
> dentro de um bloco de texto da página ("Informações do Cap 1/Cap 2", com o link
> para o Google Drive no meio da frase). No Moodle esse bloco é um módulo `label`.

## O que foi medido, antes de qualquer desenho

Sobre as duas capturas versionadas de `core_course_get_contents`, e sem tocar a
rede (a camada live é decisão do dono, não desta trilha):

| | PSI3323 | PTC3314 |
|---|---|---|
| bytes crus | 53.614 | 94.803 |
| seções / módulos | 16 / 32 | 20 / 75 |
| módulos por `modname` | `resource` 22, `url` 7, `forum` 2, `assign` 1 | `resource` 51, `quiz` 13, `assign` 4, `choicegroup` 3, `forum` 2, `url` 2 |
| **módulos `label`, `page`, `folder`** | **0, 0, 0** | **0, 0, 0** |
| módulos com `description` não vazio (bytes) | 4 (1.986) | 20 (6.233) |
| seções com `summary` não vazio (bytes) | 11 (14.313) | 19 (9.958) |
| **`href` ou `http` em qualquer texto** | **0** | **0** |
| módulos com chave `intro` | 0 | 0 |
| projeção de `material` hoje | 6.439 B, 29 itens | 10.380 B, 53 itens |

A higienização (`scripts/higienizar.py`) troca e-mail, contexto `/user/`,
parâmetro de segredo, hex de 32 e honorífico; **não** apaga `href` nem `description`,
então a fixture é fiel ao cru neste ponto: as duas disciplinas capturadas não usam
bloco de texto, e nenhum professor delas deixou link em texto.

**Logo, o caso relatado não está na amostra.** O defeito é confirmado por leitura do
código, não por reprodução:

- `projetar_material` lê **só** `contents[]` de cada módulo (`filename`, `filesize`,
  `mimetype`, `timemodified`, `fileurl`), mais `name` de módulo e de seção. Descarta
  `description` e `summary` inteiros.
- Um `label` não tem `contents` (o Moodle só preenche `contents` para módulo que
  exporta arquivo: `resource`, `url`, `folder`, `page`, `book`, `imscp`). Então ele
  cai em `sem_conteudo`, e o rodapé de `material` o declara como "atividade, não
  arquivo, com consulta própria" — o que é falso duas vezes para um bloco de texto.
- O link dentro do `description` do `label` é a única cópia dele no payload. Some.

O que a medição **não** dá: o custo real, em bytes, na disciplina que motivou a
queixa. Ele fica por medir quando ela for capturada (`./scripts/capture.sh`, decisão
do dono, porque a chamada fica no log da conta). O teste L1 trava o fato de que a
amostra não tem `label`: no dia em que uma captura com `label` entrar, ele fica
vermelho e é a hora de trocar o sintético pelo dado.

## Decisões, com a razão de cada uma

### 1. Não é ferramenta nova. É `material` ficando completo

O `CLAUDE.md` diz que ferramenta não nasce por conveniência, e o §5 do `SPEC1.md`
exige pergunta que o dono faz de verdade, resolvida em uma chamada. A pergunta aqui
é a mesma que `material` já responde, nas palavras do dono: "que material tem", "onde
estão os slides". O link no texto é material por definição do próprio dono
(descobrir o acervo). Uma ferramenta à parte obrigaria o modelo a duas chamadas para
uma pergunta, e a resposta de `material` continuaria falsa quando dissesse "não tem".

A descrição da ferramenta no `server.py` ganha a frase "os links que ele deixou no
meio do texto da página da disciplina" e o exemplo "onde estão os slides", porque é
pela descrição que o modelo decide chamá-la.

### 2. De onde se extrai: `description` de qualquer módulo e `summary` de seção

Os dois campos têm a mesma forma (HTML do editor do Moodle) e são "o texto da
página". O `label` é o caso que motivou, mas um `href` no `description` de um `quiz`
ou de um `resource` é material do mesmo jeito, e tratar só `label` seria fatiar por
`modname` uma regra que é sobre o campo. `intro` não existe em `get_contents`
(medido: zero chaves), e por isso não é lido.

Só `<a href>`. `src` de imagem não é link (imagem não é o que o professor clica), e
URL em texto plano sem âncora não é extraída: o filtro do Moodle que a transforma em
link roda na renderização, não no web service, e sem amostra não há como saber se
ela chega assim. Fica registrado como fora de escopo até haver dado.

O extrator (`texto.links`) mora em `usp_mcp/moodle/texto.py`, ao lado de `sem_html`,
que ele usa para o título da âncora. A docstring daquele módulo previa exatamente
isto: uma semântica de "o que é marcação e o que é texto" por servidor. O `href`
passa por `unescape` porque o Moodle grava `&amp;` e a URL com `&amp;` literal não é
a que o professor colou.

### 3. Material ou ruído: três classes, e a que não sai é contada

| o `href` | classe | o que acontece |
|---|---|---|
| não começa com `http(s)://` (`#topo`, `mailto:`, `javascript:`, caminho relativo) | ignorar | contado no rodapé |
| contém `/webservice/` ou `pluginfile.php` | arquivo | vira `Item` de arquivo interno: nome sai, URL não; `baixar_arquivo` o alcança |
| host do próprio Moodle, ou caminho `/mod/`, `/course/`, `/user/`, `/grade/`, `/login/`, `/my/`, `/calendar/`, `/theme/` | ignorar | contado no rodapé |
| qualquer outro | externo | vira `Item` de link, URL inteira |

O host do Moodle é **derivado do payload** (`modicon` e `url` de cada módulo,
`fileurl` dos `resource`), não de configuração: vale para o Moodle de outra
faculdade sem ninguém dizer qual é o host. O caminho relativo entra como segunda
rede porque o editor do Moodle às vezes grava o link sem host.

Por que link para dentro do Moodle não é material: o que ele aponta ou já está na
lista (um `resource`), ou é atividade que o rodapé já declara (`forum`, `quiz`), ou é
outra turma. E é endereço que só abre com sessão no navegador, coisa que o modelo não
tem. `mailto:` é e-mail de pessoa, que não atravessa a fronteira por outro motivo.

O arquivo embutido no texto (um PDF que o professor arrastou para dentro do bloco)
chega como `href` para `…/webservice/pluginfile.php/<contextid>/mod_label/intro/…`.
É o mesmo prefixo que a allowlist de `cliente.baixar` já exige para os `resource`,
então ele entra no acervo como `Item` com `fileurl_bruta` e `fileid`, e
`baixar_arquivo` o baixa **sem uma linha nova no cliente** (L6). Tamanho e data não
vêm (o `href` é só a URL); o tipo sai da extensão via `mimetypes`, que é o que há.

URL repetida não sai duas vezes: se `contents` de um módulo `url` já publica a URL
que o `description` dele repete (o padrão do editor do Moodle), o link do texto é
pulado sem contar como ignorado, porque o destino está na lista (L7).

### 4. O texto ao redor: sai o que o Moodle já condensou, não o bloco

O texto ao redor é o que dá sentido ao link, e emiti-lo inteiro custaria mais que a
projeção: os `summary` de PSI3323 somam 14.313 B e os `description` 1.986 B, contra
6.439 B da resposta inteira. Emitir o texto triplicaria a saída para uma disciplina
que hoje não tem link nenhum nele.

O que sai por link são três coisas, e duas já existiam:

- o **título da âncora** como nome do item (é o que o professor escreveu sobre o
  link: "slides do Cap 1");
- o **`name` do módulo** como rótulo, pela `rotulo_do_modulo` que já existe. Para um
  `label`, o Moodle define `name` como os primeiros ~50 caracteres do próprio texto,
  sem marcação: é o começo do bloco, já cortado, sem custo novo;
- a **seção** onde ele mora, que a lista já agrupa.

Medido no sintético com a forma real: um bloco de 2 kB com um link produz a mesma
resposta que um de 20 B com o mesmo link (L12). Cada link custa **+122 B**; o
primeiro custa +699 B porque paga as duas linhas fixas de rodapé.

Fica de fora, por falta de amostra: recortar o parágrafo (`<p>`, `<li>`) que contém a
âncora, para o caso em que o link mora no fim de um bloco longo e os 50 caracteres do
`name` não o descrevem. É a evolução natural se a captura real mostrar que o `name`
não basta.

### 5. Quando acha o link mas não sabe o que é

Âncora que embrulha só uma imagem tem título vazio; âncora cujo texto é a própria
URL (ou `www.…`) não diz nada além do endereço. Nos dois casos a saída **não
inventa**: o nome vira o host (`youtu.be`, `drive.google.com`), a linha declara
`[link, sem título no texto]`, e a URL sai inteira (L8). O rótulo do módulo, quando
há, continua sendo o contexto.

### 6. O rodapé diz o que a leitura do texto fez, e o que deixou de fora

Três linhas, cada uma só quando a contagem é maior que zero:

- "N dos itens acima estavam no texto da página da disciplina, não publicados como
  arquivo ou link: o nome é o texto do link e o parêntese, quando há, é o começo do
  bloco de texto onde ele estava." Para quem lê saber como interpretar a linha.
- "N link(s) no texto da página apontam para dentro do próprio e-Disciplinas (outra
  atividade ou página do curso), para e-mail ou para âncora da própria página, e não
  foram listados: não são material." O que foi cortado, dito.
- "N bloco(s) de texto da página não têm link nenhum e ficaram de fora: são texto,
  não arquivo nem link." Avisa que a página tem texto que esta ferramenta não mostra
  (um "não haverá aula dia 20", por exemplo), sem pagar por ele.

As três valem também quando a lista fica **vazia**: uma disciplina cuja página só tem
texto sem link, ou só links para dentro do Moodle, é vazio legítimo, mas é vazio com
explicação (L5, L9). E `label` sai de `sem_conteudo`: bloco de texto não é atividade,
e "têm consulta própria" era falso para ele.

## Custo, e por que ele é aceitável

- Nas duas capturas reais: **zero bytes** de diferença (6.439 e 10.380 B antes e
  depois), porque não há link em texto nelas.
- Por link no texto, sintético com a forma real: **+122 B**, mais +577 B uma vez pelas
  linhas de rodapé.
- Zero chamadas a mais: tudo sai do `core_course_get_contents` que `material` já
  pede. O Invariante 5 não é tocado.
- `busca` casa também com o título do link (L4): "slides" acha "slides do Cap 1".

O que ele evita é a resposta falsa: o dono pergunta pelos slides, a ferramenta diz
que não há, e há.

## Testes

`tests/moodle/test_links_no_texto.py`, L1–L12, offline, entram no gate:

- L1 (parametrizado nas duas capturas reais): zero `label`, zero `href`, e a
  projeção não muda. É o teste que avisa quando a amostra passar a cobrir o caso.
- L2–L4: link externo em `label` vira item com título, URL, contexto e seção; a
  resposta o mostra e o rodapé diz de onde veio; `busca` o acha.
- L5: link para dentro do Moodle, relativo, `#`, `mailto:`, `javascript:` não são
  material, e o rodapé conta os seis.
- L6: arquivo embutido no texto sai sem URL (nenhum `pluginfile.php`, `/webservice/`
  ou `token` no texto, como T68b) e `baixar_arquivo` o baixa pela mesma allowlist.
- L7: sobre a captura real, o `description` de um `url` repetindo a própria URL não
  gera item novo.
- L8: sem título vira host + declaração; `src` de imagem não sai.
- L9: texto sem link fica de fora, contado, e "atividades" não aparece.
- L10: link no `summary` da seção entra na seção, sem rótulo de módulo.
- L11: o extrator traduz entidade no `href`, tira marcação do título e ignora âncora
  sem `href`.
- L12: bloco longo e curto produzem a mesma resposta; uma linha de link custa menos
  de 250 B.

T66, T67, T71 e T68b/T68c continuam verdes sem mudança: a fixture não tem `label`, e
o texto que chega ao modelo continua sem URL interna.

## O que fica de fora, e por quê

- **Captura da disciplina que motivou a queixa.** Precisa do token do dono e fica no
  log da conta; é decisão dele. Sem ela, o custo real e a suficiência do `name` como
  contexto ficam por confirmar.
- **URL em texto plano, sem âncora.** Sem amostra que mostre se o web service a
  entrega já convertida em `<a>`.
- **Recorte do parágrafo que contém a âncora.** Só vale o custo se o `name` do
  `label` se mostrar insuficiente no dado real.
- **`page` e `folder`.** Zero nas capturas. `page` traz `index.html` em `contents` e
  hoje sai como "arquivo"; é outro assunto.
- **`SPEC1.md` e `README.md`** não são tocados nesta trilha, por instrução: outras
  frentes mexem neles. O fato para o §9 é este documento.
