# Erro mudo na fronteira MCP — a mensagem do domínio parava no stderr

> **Estado, 10/09/2026: SATISFEITO.** Implementado contra esta bateria e mergeado na
> PR #23. Um delta em relação ao que está escrito abaixo, e ele é informação: os três
> **E3 já passavam de saída**. Reter o texto de um crash sempre foi o comportamento
> certo do SDK — o defeito era só `ErroX` contar como crash. A bateria nasceu, então,
> `9 failed, 3 passed`, e não 12 vermelhos. Fica registrado porque um teste que passa
> desde o primeiro run merece dizer por quê, em vez de parecer verde vazio.
>
> Registrado no §9 do `SPEC1.md` e no `BACKLOG-correcoes.md`, entrada de 10/09.

- **Prioridade:** alta — derruba o Invariante 6 na fronteira MCP
- **Servidores atingidos:** os três (`rucard`, `jupiter`, `moodle`)

## Sintoma medido

Cliente MCP stdio real, `mcp 2.2.0`, 10/09/2026:

| chamada | o que o modelo recebe |
|---|---|
| `bandejao{"dia":"blergh"}` | `Error executing tool bandejao` (29 B) |
| `disciplina{"sigla":"XXX9999"}` | `Error executing tool disciplina` (31 B) |
| `o_que_vence{}` sem token | `Error executing tool o_que_vence` (32 B) |

As mensagens escritas para essas três situações existem e ficam **só no stderr**:

> `não entendi o dia 'blergh'. Use 'hoje', 'amanhã' ou uma data como 26/08/2026. O RUCard publica só a semana corrente…`
> `Disciplina inválida ou ainda não ativada !`
> `MOODLE_TOKEN ausente ou vazio — configure-o no .env (ver .env.example) antes de usar o cliente.`

## Causa raiz

Regressão do SDK, isolada por A/B no mesmo commit:

- `mcp==2.0.0` — `Tool.run` faz `except Exception as e: raise ToolError(f"Error executing tool {name}: {e}")`. A mensagem chega inteira.
- `mcp==2.2.0` — `Tool.run` separa dois ramos: `except (ToolError, ResourceError)` repassa o texto; `except Exception` levanta `UnexpectedToolError(f"Error executing tool {name}")` **sem** o texto, por decisão de segurança do SDK ("a crash: the exception's own text stays on the server").

`ErroRucard`, `ErroJupiter` e `ErroMoodle` herdam de `Exception`, então caem no ramo de crash. `requirements.txt` declara `mcp>=2,<3`: qualquer instalação nova hoje pega 2.2.0 e nasce muda.

## Cura

Nos três `main()`, a função registrada no SDK traduz o erro do domínio para o
`ToolError` do SDK — o canal que o SDK define para "falha prevista, mensagem é
para o modelo ler". `ErroX` continua sendo a moeda interna; a tradução acontece
**na fronteira**, que é onde ela pertence.

```python
from mcp.server.mcpserver.exceptions import ToolError   # existe em 2.0.0 e 2.2.0
...
    try:
        return chamar_ferramenta(...)
    except ErroRucard as exc:
        raise ToolError(str(exc)) from exc
```

Regras:

1. Só `ErroX` do próprio domínio é traduzido. Um `KeyError` continua sendo crash,
   e continua com o texto retido — é o comportamento certo do SDK.
2. Nada de `except Exception`. Traduzir tudo devolveria ao modelo o traceback
   que a `JupiterErro` existe para descartar (46 frames do Tomcat, 116x o custo).
3. A tradução mora no adaptador stdio, não em `chamar_ferramenta`: as funções
   puras rodam sem o SDK instalado (T43), e importar `mcp` no topo quebra a coleta.

## Bateria de testes — `tests/<sistema>/test_erro_no_fio.py`

Rodam `main()` em processo contra o SDK instalado, substituindo só `run()` —
mesmo molde de T45-T48/T78-T81. Offline, sem credencial, sem rede.

| id | teste | asserção |
|---|---|---|
| E1 | `test_e1_erro_de_dominio_chega_com_a_mensagem` | `call_tool` com argumento que o domínio recusa devolve `is_error=True` **e** o texto em português aparece em `content[0].text` |
| E2 | `test_e2_a_mensagem_nao_e_a_generica_do_sdk` | o texto não é apenas `Error executing tool <nome>`; tem > 60 caracteres e contém a cura escrita na mensagem original |
| E3 | `test_e3_crash_de_verdade_continua_retido` | erro que **não** é `ErroX` (monkeypatch levantando `RuntimeError("segredo")`) devolve `is_error=True` sem a palavra `segredo` no texto |
| E4 | `test_e4_a_traducao_nao_engole_a_classe` | `ToolError` levantado carrega a mensagem de `ErroX`, e `__cause__` é a exceção original |

Por servidor:

- **rucard** — E1/E2 com `{"dia": "blergh"}`, esperando `não entendi o dia`.
- **jupiter** — E1/E2 com um `Gravador` devolvendo a fixture `dwr-pubObterDisciplina-ERRO-sigla-inexistente.txt`, esperando `Disciplina inválida`.
- **moodle** — E1/E2 com `MOODLE_TOKEN` vazio no ambiente, esperando `MOODLE_TOKEN ausente ou vazio`.

E3 e E4 uma vez em cada servidor.

## Critério de parada

`.venv/bin/python -m pytest` verde, incluindo os 4 novos testes por servidor
(12 no total), **e** `./scripts/gate.sh` PASSOU.
