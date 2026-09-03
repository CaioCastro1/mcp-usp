# Empacotar e distribuir — o que a pesquisa de 03/09/2026 achou

> Pesquisa feita porque o dono quer que **outras pessoas** usem isto ("colocar um
> conector no Claude"), e o `§6 do SPEC1.md` estava com "linguagem, runtime,
> transporte e hospedagem" em aberto desde o começo. A decisão continua aberta; o
> que mudou é que agora existe dado.
>
> Fontes no fim. Nada aqui foi testado — é leitura de documentação, e a diferença
> importa: o item 9 do `CLAUDE.md` vale para isto também.

## 1. A pergunta não era uma só

"Publicar um conector" junta três coisas que este projeto precisa separar:

| | o que é | serve para o Moodle? |
|---|---|---|
| **Conector remoto** | servidor HTTPS na internet, acessado pela infra da Anthropic | **Não** |
| **MCP Bundle (`.mcpb`)** | servidor local empacotado, stdio, instala com um clique | **Sim** |
| **Diretório de conectores** | vitrine curada, hoje com 950+ servidores | talvez, e não é o primeiro passo |

## 2. Por que o conector remoto está fora, para o Moodle

Três bloqueios independentes, e nenhum é preferência:

1. **A rede da USP não sai da nuvem** (§1.1, medido em 31/08): proxy de egress com
   allowlist, `curl` devolve `000` ou `403`. Quem faz o fetch teria de ser o servidor
   hospedado, e ele não alcança `edisciplinas.usp.br`.
2. **O token não pode ir** (Invariante 4). Um conector remoto autenticado exige OAuth
   2.0, e o e-Disciplinas não nos dá um fluxo OAuth — dá um token pessoal de web
   service. Mandar esse token para um servidor nosso é exatamente o que o Invariante 4
   proíbe.
3. **Submissão ao diretório exige organização Team ou Enterprise**, com permissão de
   Directory ou Libraries.

Para **RUCard e Jupiter** o raciocínio se inverte: são dado público, sem credencial
pessoal, e o §6 já dizia que podem ser hospedados. Se algum dia houver conector
remoto neste projeto, é deles — não do Moodle.

## 3. O que é um MCP Bundle, e por que ele encaixa

Um `.mcpb` é um zip com o servidor e um `manifest.json`. Instala com duplo clique,
arrastar para a janela, ou pelas configurações. Roda **local, por stdio**, funciona
offline, e **não usa OAuth**.

Isso não é um caminho alternativo ao §6 — é o §6 escrito por outra pessoa. A frase
"o token fica na máquina de quem usa, cada pessoa traz o seu" descreve exatamente o
modelo do `.mcpb`.

### O que ele resolve e hoje é atrito nosso

**A configuração do token.** O manifest declara um bloco `user_config`, e o Claude
Desktop **gera a tela de configuração sozinho**. Para segredo existe
`"sensitive": true`, que mascara o campo e, nas palavras da spec, "armazena com
segurança" — a spec **não diz onde** (keychain, credential manager, arquivo cifrado),
e isso é uma questão aberta que importa para o Invariante 3.

O valor chega ao processo por **variável de ambiente**:

```json
"env": { "MOODLE_TOKEN": "${user_config.moodle_token}" }
```

Ou seja: **nenhuma linha do nosso código muda.** `usp_mcp/env.py` já lê
`MOODLE_TOKEN` de `os.environ`, e usa `setdefault`, então quem já está no ambiente
ganha do `.env` — que é precisamente o comportamento necessário aqui.

Hoje, para outra pessoa usar isto, ela precisa: clonar o repo, criar um venv,
instalar dependências, copiar o `.env.example`, gerar o token, colar no arquivo, e
editar a configuração do cliente MCP. Com um `.mcpb`, ela dá um clique e digita o
token num campo.

## 4. O obstáculo, e ele é concreto

**A documentação recomenda Node.js com força**, e o motivo não é gosto: o Node
**vem junto com o Claude Desktop** no macOS e no Windows, então o usuário não instala
runtime nenhum. Nosso servidor é Python.

Python é suportado — o manifest tem `compatibility.runtimes.python` com semver
(`">=3.8,<4.0"`), e existe um tipo baseado em **UV** que dispensa declarar a versão —
mas o usuário precisa ter o runtime. Isso devolve parte do atrito que o `.mcpb`
existe para eliminar, e **quanto de atrito exatamente é a coisa a medir**, não a
estimar.

Duas outras restrições registradas: o Claude Desktop roda em **macOS e Windows** (não
Linux), e o `.mcpb` é descrito na documentação como **"secondary distribution path"** —
o diretório prefere servidores remotos.

## 5. Cache em disco: não há padrão, e há uma peça que faltava

O protocolo **não trata de ciclo de vida de arquivo**. Verificado por inspeção do SDK
`mcp` instalado quando avaliamos entregar blob: não há noção de cache, quota ou
limpeza. O cliente também não tem como saber que `~/.cache/usp-mcp/` existe — ele
recebe uma string e abre um arquivo.

Os precedentes são ad-hoc. O mais concreto achado é o `mcp-clip`, que faz três coisas:
TTL, limpeza **no startup** para órfãos de instâncias anteriores, e limpeza antes de
cada operação que cria arquivo.

**A limpeza no startup é a peça que faltava no nosso raciocínio.** A objeção
registrada em 03/09 contra limpar automaticamente era o risco de sumir com um arquivo
sendo lido. No startup isso não acontece: o servidor sobe antes de qualquer leitura
da sessão. O TTL do `mcp-clip` é de 1 hora porque o dado dele é efêmero; o nosso é
material de disciplina, que muda por semestre — o TTL tem de ser colado na taxa de
mudança do dado (Invariante 5), não copiado.

## 6. O que fazer, e em que ordem

1. **Empacotar o Moodle como `.mcpb` com runtime UV e instalar numa máquina limpa.**
   É o menor passo que exercita o caminho inteiro e **mede** o atrito do Python em vez
   de estimá-lo. Mede também onde o `sensitive: true` guarda o valor, que a spec não diz.
2. **Limpeza no startup com TTL longo**, agora que a objeção caiu.
3. **Diretório por último**, se for o caso — exige organização paga e, para o Moodle,
   provavelmente não é o destino.

## Fontes

- [Build a desktop extension with MCPB](https://claude.com/docs/connectors/building/mcpb)
- [MCPB Manifest Spec](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)
- [MCPB repository](https://github.com/modelcontextprotocol/mcpb)
- [Submitting to the Connectors Directory](https://claude.com/docs/connectors/building/submission)
- [Adopting the MCP Bundle format (.mcpb)](https://blog.modelcontextprotocol.io/posts/2025-11-20-adopting-mcpb/)
- [mcp-clip — TTL e limpeza no startup](https://glama.ai/mcp/servers/@standardbeagle/mcp-clip/blob/8cf387f862c56cf2b8952e54adeda226210a728b/tasks/todo.md)
