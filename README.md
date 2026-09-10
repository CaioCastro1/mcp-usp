# usp-mcp

Ferramentas para responder perguntas sobre a vida acadêmica na USP — cardápio dos
bandejões, prazos e material do e-Disciplinas, catálogo de disciplinas do JupiterWeb.

**Projeto não-oficial, sem nenhum vínculo com a Universidade de São Paulo.** Usa APIs
não documentadas, descobertas por observação. Elas podem mudar ou sumir sem aviso, e
"está público" não equivale a "liberado para redistribuir" — ver Invariante 8 do
`SPEC1.md`.

## Estado — 09/09/2026

**Três servidores MCP rodando, cinco ferramentas, todas verificadas contra a USP.**

| Servidor | Ferramenta | Responde |
|---|---|---|
| `usp-rucard` | `bandejao` | O que tem no bandejão hoje, e onde vale a pena comer |
| `usp-moodle` | `o_que_vence` | O que tenho para entregar nos próximos N dias |
| `usp-moodle` | `material` | Que arquivos tem no espaço da disciplina — regras, listas, provas antigas |
| `usp-moodle` | `baixar_arquivo` | Baixa um desses arquivos e devolve o caminho dele no disco |
| `usp-jupiter` | `disciplina` | Créditos, carga horária, ementa e pré-requisito, pela sigla |

`baixar_arquivo` entrega o **caminho**, não o conteúdo: quem lê o PDF é o agente que
chamou, com a ferramenta de leitura dele. Blob em base64 custaria ~302k tokens no PDF
médio; extrair o texto no servidor perderia as figuras — e devolveria 9 bytes para uma
lista manuscrita escaneada, chamando isso de sucesso (§9, 01/09 e 03/09). O arquivo cai
em `~/.cache/usp-mcp/moodle/`, fora do repositório.

O Moodle é entrypoint **local** por carregar credencial pessoal; o Jupiter e o RUCard não
usam credencial nenhuma e por isso seguem candidatos a servidor hospedado (§6 do
`SPEC1.md`). Suíte: testes offline em segundos — incluindo um handshake stdio que sobe
cada servidor de verdade — mais uma camada `live` atrás de `USP_MCP_LIVE=1` que fala com
a USP.

**O que ainda não existe:** notas, "já entreguei?", aviso de professor — e nada de
histórico de cardápio, saldo do cartão, horário, sala ou vagas. `material` diz o nome, o
tipo e o tamanho de cada arquivo, mas **não** emite a URL interna dele: endereço sem a
credencial não abre, e é `baixar_arquivo` que resolve isso sem nunca pôr o token numa URL.
Instalar continua sendo `git clone` + venv: empacotar como MCP Bundle (`.mcpb`) está
pesquisado no §6.1 e **não** testado. Nenhuma ferramenta nasce por conveniência: o
critério está no §5, e as questões abertas do §4 fecham com dado registrado no §9.

Comece por `SPEC1.md` — ele é a autoridade do projeto, e o §9 registra cada decisão
tomada, com o dado que a fechou e o que foi descartado.

- `usp_mcp/` — os servidores, um pacote por sistema
- `tests/` — três camadas: política e contrato offline, `live` atrás de env var
- `notas/` — análise por sistema, com custo medido em bytes e tokens
- `fixtures/` — respostas cruas capturadas (as do Moodle ficam fora do git: têm dado pessoal)
- `scripts/` — chamadores da descoberta e o gate de pré-commit
- `docs/decisions/BACKLOG-correcoes.md` — a dívida que está em aberto

## Rodando

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt
cp .env.example .env
./scripts/gate.sh
```

O `cp` vem **antes** do gate porque sem `.env` ele reprova: a hash do RUCard é o único
valor que o gate precisa, e ela já vem preenchida no exemplo — é a chave embutida no
app oficial, pública e compartilhada, não credencial de ninguém. O token do Moodle
nasce vazio e **não** precisa ser preenchido para o gate passar: ele roda offline e não
toca a USP. Para de fato usar o servidor do Moodle, veja *Configuração*.

O `.mcp.json` versionado já registra os três servidores, sem segredo. Abra um cliente
MCP neste diretório e pergunte. Cada entrada chama `scripts/servidor.sh <sistema>`, e é
o script que resolve a raiz do checkout — não o cliente.

### Cliente que não faz `cd`

O `.mcp.json` é relativo de propósito: ele é versionado e compartilhado, e caminho
absoluto de máquina não entra em arquivo rastreado (Invariante 3 aplicado a caminho).
Relativo funciona em cliente que roda o servidor com o diretório de trabalho na raiz do
projeto — o Claude Code faz isso. **Claude Desktop e afins não fazem**, e lá o caminho
relativo falha com `no such file or directory`.

Para esses, aponte para o **caminho absoluto do lançador**. Ele é o único absoluto que
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
script resolve o resto — inclusive achar o `.venv`, que é por diretório e não vem no git.

## Configuração

O `cp .env.example .env` da seção acima é o passo, e é um só. `RUCARD_HASH` já vem
preenchida. `MOODLE_TOKEN` nasce vazio e é o único valor a colar à mão: é credencial
pessoal, nunca sai da máquina de quem usa (Invariante 4), e o §8 do `SPEC1.md` diz
como obtê-lo.

## Para quem acabou de ganhar acesso

O token é **seu**, não de quem te convidou — cada pessoa traz o seu. Isso não é atrito
acidental: é o Invariante 4, e é o que permite este projeto existir sem ninguém confiar
credencial a ninguém.

**1. Clone e monte o ambiente.** O `.venv` é por diretório e não vem no git.

```bash
git clone git@github.com:CaioCastro1/mcp-usp.git && cd mcp-usp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt
```

**2. Pegue seu token do e-Disciplinas.** Logado no navegador, com DevTools → Network
aberto, acesse:

```
https://edisciplinas.usp.br/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=1234&urlscheme=moodlemobile
```

A página tenta abrir o app do Moodle. O que interessa é a URL da linha `token=…` no
Network — copie ela inteira, sem tentar decodificar na mão.

**3. Cole no `.env` e normalize.**

```bash
cp .env.example .env
# cole a URL inteira em MOODLE_TOKEN= e rode:
./scripts/fix-token.sh
```

O script decodifica a URL e grava só o `wstoken` de 32 hex, e é idempotente — rodar duas
vezes não estraga nada. Ele **nunca imprime o valor do token**, só diagnóstico de forma
(Invariante 3). Se você já tiver os 32 hex, pule: ele detecta e não mexe.

**4. Confira sem gastar chamada nenhuma da sua conta.**

```bash
./scripts/gate.sh
.venv/bin/python -m usp_mcp.moodle.server --auto-verificar
```

O `--auto-verificar` diz se o `.env` foi achado, se o token está presente (sem mostrá-lo),
se o SDK está instalado e se os schemas casam. **Nada disso toca a rede da USP.**

**5. Ligue num cliente MCP.** O `.mcp.json` versionado já registra os três servidores sem
segredo nenhum: abra o Claude Code **nesta pasta** e pergunte. Para que valham em qualquer
pasta, registre no escopo de usuário:

```bash
R=$(pwd); for m in moodle jupiter rucard; do claude mcp add --scope user "usp-$m" -- $R/scripts/servidor.sh $m; done
```

O `-e PYTHONPATH=` que esta linha carregava saiu junto: ele existia porque o comando antigo rodava o interpretador de fora do checkout, e o lançador entra nele antes de subir o servidor.

**Onde isso NÃO vai funcionar, e não é configuração:** sandbox em nuvem (a rede da USP não
sai de lá, §1.1) e conector remoto (o token não pode viajar, Invariante 4 — e o
e-Disciplinas não oferece OAuth). Moodle é local, por desenho. RUCard e Jupiter não usam
credencial e poderiam ser hospedados; não estão (§6).

**Seu token expira e é revogável** em `edisciplinas.usp.br` → gerenciar tokens. Se algo
parar de responder com `invalidtoken`, é isso — refaça o passo 2.
