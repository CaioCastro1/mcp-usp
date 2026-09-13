# A guarda da Regra de Ouro — de valor congelado a propriedade, e para dentro do gate

> **Estado, 10/09/2026: SATISFEITO.** Implementado e mergeado na PR #25. O delta é o
> mais importante deste documento: **P1-P5 nasceram verdes, e isso é o diagnóstico.**
>
> A propriedade que a Regra de Ouro afirma nunca foi violada — a camada `live` sempre
> chamou uma função só, literal, dentro da allowlist. O que estava quebrado era a
> *forma* da guarda: ela congelava um valor que o §9 previa crescer, e morava numa
> camada que o gate não roda. P1-P5 não descobrem violação nova; elas passam a checar a
> coisa certa, no lugar onde alguém vê quando ela quebrar.
>
> O que prova que não são verde vazio: P1 tem asserção anti-vácuo (reprova se o regex
> parar de achar chamada nenhuma), P3 lê AST em vez de casar texto, P4 reprova se
> alguém devolver as guardas para trás do `USP_MCP_LIVE=1` — e as duas sabotagens
> rodadas: função de escrita na allowlist reprova P5, nome trocado em `test_live.py`
> reprova P1.

- **Prioridade:** média (a guarda em si é alta — ela protege a credencial do dono)
- **Arquivos:** `tests/moodle/test_live.py`, `tests/moodle/test_politica.py`

## Sintoma medido

```
FAILED tests/moodle/test_live.py::test_a_camada_live_so_alcanca_a_allowlist
  assert frozenset({'core_calendar…','core_webservice_get_site_info',
                    'core_enrol_get_users_courses','core_course_get_contents'})
      == frozenset({'core_calendar_get_action_events_by_timesort'})
```

Reprova **sem token e sem rede** — é asserção pura. Reprova em qualquer máquina,
desde que a `ALLOWLIST` cresceu de 1 para 4 (31/08, registrado no §9).

## Causa raiz

Dois defeitos, e o segundo é o que importa.

1. **A asserção congelou um valor, não uma propriedade.** T51 diz proteger a
   Regra de Ouro do §3.1 ("uma função, escolhida à mão, uma chamada por
   execução"), mas o que ele escreveu foi `ALLOWLIST == {um nome}`. A allowlist
   crescer é evento previsto e registrado; o teste tratou isso como violação.

2. **A guarda mora na camada que o gate não roda.** `scripts/gate.sh` exclui
   `live` de propósito e com razão (um gate que depende da USP estar de pé
   reprova commit por motivo errado). Consequência: esta asserção não rodou em
   nenhum dos commits desde 31/08. Uma guarda que só roda atrás de
   `USP_MCP_LIVE=1` apodrece calada — que é exatamente o modo de falha que o
   backlog já registrou três vezes para o `main()`.

## Cura

A propriedade que a Regra de Ouro realmente afirma, checável **offline**, em
`tests/moodle/test_politica.py`:

- toda função que a camada `live` chama por nome está na `ALLOWLIST`;
- nenhum nome do `BLOQUEIO_PERMANENTE` aparece no fonte da camada `live`;
- a camada `live` não itera sobre `politica.ALLOWLIST` — a Regra de Ouro proíbe
  sweep, e "escolhida à mão" quer dizer nome literal no fonte.

`test_a_camada_live_so_alcanca_a_allowlist` sai de `test_live.py` (onde não roda)
e vira essas três asserções em `test_politica.py` (onde o gate as roda). O `§3.1`
continua sendo a autoridade; muda só quem verifica, e quando.

## Bateria de testes — `tests/moodle/test_politica.py`

| id | teste | asserção |
|---|---|---|
| P1 | `test_p1_a_camada_live_so_chama_funcao_da_allowlist` | extrai por regex todo `cliente_real.chamar("<nome>"` de `tests/moodle/test_live.py`; cada `<nome>` está em `ALLOWLIST`. Falha citando o nome intruso |
| P2 | `test_p2_nenhum_nome_bloqueado_aparece_na_camada_live` | nenhum dos 23 nomes de `BLOQUEIO_PERMANENTE` é substring do fonte de `test_live.py` |
| P3 | `test_p3_a_camada_live_nao_faz_sweep` | `politica.ALLOWLIST` não aparece dentro de `for`/comprehension no fonte de `test_live.py` — a Regra de Ouro é nome literal, não iteração |
| P4 | `test_p4_a_guarda_da_regra_de_ouro_roda_offline` | os testes P1-P3 não carregam a marca `live`; falha se alguém devolvê-los para trás da env var |
| P5 | `test_p5_a_allowlist_e_so_de_leitura` | toda função da `ALLOWLIST` casa com um prefixo de leitura conhecido (`core_calendar_get_`, `core_webservice_get_`, `core_enrol_get_`, `core_course_get_`) — cresce sem apodrecer, e barra `_save_`/`_submit_`/`_add_` entrando por engano |

P1 e P5 verificados por sabotagem: inserir `core_message_send_instant_messages`
na `ALLOWLIST` faz P5 reprovar; trocar o nome chamado em `test_live.py` faz P1
reprovar.

## Critério de parada

`.venv/bin/python -m pytest` verde, `./scripts/gate.sh` PASSOU, e
`USP_MCP_LIVE=1 pytest -m live tests/moodle` não reprova mais por esta causa
(segue exigindo token para o T50, que é o certo).
