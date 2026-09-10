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
./scripts/gate.sh
```

O `.mcp.json` versionado já registra os três servidores, sem segredo. Abra um cliente
MCP neste diretório e pergunte.

## Configuração

O RUCard e o Jupiter não pedem credencial nenhuma — copie `.env.example` para `.env` e
eles já funcionam. Só o Moodle precisa de token, e ele é pessoal: nunca sai da máquina
de quem usa (Invariante 4).

```bash
./scripts/token.sh
```

O script guia os sete passos do fluxo de `launch.php` (§8 do `SPEC1.md`), decodifica o
payload sem nunca imprimir o valor, **confirma o token contra a USP em uma chamada** e
só então grava no `.env` — um token que não autentica não chega ao arquivo. Se você já
tinha editado o `.env` à mão e o valor ficou torto, `./scripts/fix-token.sh` conserta.

O token expira e é revogável em `/user/managetoken.php` → Reconfigurar. Renovar é rodar
o script de novo: não há caminho sem sessão de navegador, porque a conta autentica por
Senha Única e o Moodle não tem senha local para comparar (§1.3).
