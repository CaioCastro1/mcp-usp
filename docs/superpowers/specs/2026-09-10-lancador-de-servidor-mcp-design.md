# O lançador do servidor MCP — subir de qualquer cwd sem caminho de máquina no git

> **Estado, 10/09/2026: SATISFEITO.** Implementado e mergeado na PR #27. Dois deltas:
>
> 1. **A cura não é caminho absoluto no `.mcp.json`.** O arquivo é versionado e
>    compartilhado, e caminho de máquina em arquivo rastreado é o Invariante 3 aplicado
>    a caminho em vez de segredo. O que entrou foi um lançador, `scripts/servidor.sh`,
>    que resolve a própria raiz: o `.mcp.json` segue relativo e limpo, e o único
>    absoluto que existe é o do script, no arquivo de config da máquina de quem usa.
> 2. **O `-e PYTHONPATH=` do passo do README saiu junto.** Ele existia porque o comando
>    antigo rodava o interpretador de fora do checkout; o lançador entra nele antes de
>    subir o servidor. Verificado subindo os três servidores de `/tmp`, com a variável
>    removida do ambiente.
>
> O `SPEC1.md` §6.1 **não** foi reescrito: o `.mcpb` não quebra com isto (o
> `manifest.json` tem o próprio `${__dirname}`), mas agora existe um entrypoint com
> nome, e quem for empacotar decide se o manifest chama o lançador ou o interpretador.
> Ficou como linha de backlog, decisão de §9.

- **Prioridade:** baixa hoje, alta no dia em que o `.mcpb` do §6.1 for tentado
- **Arquivos:** `.mcp.json`, `scripts/servidor.sh` (novo), `README.md`

## Sintoma medido

```json
{ "command": ".venv/bin/python", "args": ["-m", "usp_mcp.rucard.server"] }
```

De outro diretório:

```
$ cd /tmp && .venv/bin/python -m usp_mcp.rucard.server
zsh: no such file or directory: .venv/bin/python     (rc=127)
```

Funciona no Claude Code, que roda o servidor com o `cwd` no diretório do projeto.
Não funciona em nenhum cliente que não faça isso — o Claude Desktop entre eles,
que é justamente o alvo do empacotamento `.mcpb` pesquisado no §6.1.

## Causa raiz

O `.mcp.json` é versionado e compartilhado, então **não pode** trazer o caminho
absoluto da máquina de ninguém (é a mesma razão do Invariante 3, aplicada a
caminho em vez de segredo). Mas caminho relativo transfere para o cliente uma
premissa que nem todo cliente cumpre. O `.mcp.json` de hoje não escolheu entre as
duas coisas: ficou com a que falha calada fora do Claude Code.

## Cura

Um lançador que resolve o próprio diretório, `scripts/servidor.sh`:

```sh
#!/usr/bin/env bash
# Sobe um servidor MCP deste checkout, de qualquer cwd.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m "usp_mcp.$1.server"
```

- `.mcp.json` passa a chamar `scripts/servidor.sh` com `rucard`/`jupiter`/`moodle`.
  Segue relativo e segue funcionando no Claude Code — sem caminho de máquina no git.
- Quem usa um cliente que não faz `cd` aponta para o **caminho absoluto do
  script**, e o `cd` de dentro dele resolve o resto. É o único absoluto que
  aparece, e ele fica no arquivo de config da máquina de quem usa, não no repo.
- O `README` ganha o trecho de config para esse caso, com um `<CAMINHO-DO-CHECKOUT>`
  explícito em vez de um caminho real.
- Se o `.venv` não existir, o lançador diz qual comando o cria — hoje o erro é
  `no such file or directory`, que não ensina nada (Invariante 6).

## Bateria de testes — `tests/test_lancador.py`

| id | teste | asserção |
|---|---|---|
| L1 | `test_l1_o_lancador_sobe_de_outro_cwd` | roda `scripts/servidor.sh rucard` com `cwd=tmp_path`, manda um `initialize` MCP por stdin e lê a resposta: `serverInfo.name == "usp-mcp-rucard"`. **Reprova hoje** (não existe lançador) |
| L2 | `test_l2_os_tres_servidores_sobem_pelo_lancador` | idem para `jupiter` e `moodle`; cada um se identifica com o próprio nome |
| L3 | `test_l3_o_mcp_json_aponta_para_o_lancador` | todo `command` em `.mcp.json` é `scripts/servidor.sh`, e o `args` nomeia um sistema que existe em `usp_mcp/` |
| L4 | `test_l4_nenhum_caminho_de_maquina_no_mcp_json` | `.mcp.json` não contém `/Users/`, `/home/`, `C:\` — a mesma asserção que T2 já faz nos conftests |
| L5 | `test_l5_sem_venv_a_falha_diz_a_cura` | roda o lançador com um `checkout` temporário sem `.venv`; `rc != 0` e a saída cita `python3 -m venv .venv` |
| L6 | `test_l6_o_lancador_recusa_sistema_desconhecido` | `scripts/servidor.sh bandejao` sai com `rc != 0` citando os três nomes válidos — não tenta importar `usp_mcp.bandejao.server` |

L1/L2 pulam sem o SDK instalado (a suíte roda sem ele) e não tocam a rede:
`initialize` é respondido antes de qualquer `chamar_ferramenta`.

## Critério de parada

`.venv/bin/python -m pytest` verde, `./scripts/gate.sh` PASSOU, e os três
servidores sobem por `scripts/servidor.sh` a partir de `/tmp` — verificado à mão.
