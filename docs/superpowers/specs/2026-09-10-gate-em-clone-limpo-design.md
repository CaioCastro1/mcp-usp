# O gate num clone limpo — o `.env` que o README só pedia depois

> **Estado, 10/09/2026: SATISFEITO.** Implementado e mergeado na PR #26. Três deltas:
>
> 1. **O D2 do desenho era passável por deleção.** A asserção escrita abaixo (o bloco
>    *Rodando* não pede `MOODLE_TOKEN`) já passava, e some com o token do README inteiro
>    que ela continua passando. A que de fato reprovava é uma segunda, acrescentada: o
>    `MOODLE_TOKEN` continua **nomeado** na *Configuração*.
> 2. **Num clone limpo a checagem 1 também reprovava**, não só a 3, com `sem .env em
>    lugar nenhum — esta checagem não verificou nada`. Este desenho só registrava a 3.
>    As duas mensagens são verdadeiras e **nenhuma nomeia a cura** — é a justificativa
>    extra para a checagem 0 vir antes da 1, e está escrita no cabeçalho do script.
> 3. O `CLAUDE.md` resumia o gate como três checagens; passou a citar o `.env`.
>    Defasagem criada pela própria mudança, corrigida junto em vez de virar dívida.

- **Prioridade:** média — é o primeiro comando que alguém novo roda
- **Arquivos:** `README.md`, `scripts/gate.sh`

## Sintoma medido

Clone novo, seguindo o README ao pé da letra:

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt
./scripts/gate.sh
```

```
  3. suite offline                               FALHOU
       FAILED tests/rucard/test_politica.py::test_r8_o_valor_da_hash_nao_aparece_em_fonte_nenhum
       Failed: RUCARD_HASH não está no ambiente nem no .env: esta checagem não
       verificou nada. Checagem que não pôde rodar reprova, em vez de reportar OK.
gate: REPROVOU. Nao commite.
```

## Causa raiz

O `test_r8` está **certo** — "checagem que não pôde rodar reprova" é a mesma
regra do gate, e afrouxar isso seria trocar um vermelho honesto por um verde que
não verificou nada (Invariante 6). O defeito é de ordem: o README põe
`./scripts/gate.sh` na seção **Rodando** e só menciona `cp .env.example .env` na
seção **Configuração**, depois. Quem lê de cima para baixo reprova o gate na
primeira tentativa e não sabe por quê — a mensagem fala de `RUCARD_HASH`, não do
passo que faltou.

Segundo defeito, menor: o gate descobre a ausência do `.env` na checagem 3, a
mais cara das três, depois de rodar 364 testes. O próprio cabeçalho do script diz
que a ordem é "a mais barata que pode reprovar vem antes".

## Cura

1. **README** — a seção *Rodando* passa a trazer o `cp .env.example .env` **antes**
   do gate, com uma linha dizendo por quê (a hash do RUCard é pública e vem
   preenchida; o token do Moodle não, e não precisa estar para o gate passar).
2. **`scripts/gate.sh`** — nova checagem **0**, antes de tudo: `.env` existe e
   tem `RUCARD_HASH` com valor. Falha citando o comando exato. Custa um `test -f`
   e evita descobrir isso depois de 364 testes.
3. A checagem 0 **não** exige `MOODLE_TOKEN`: o gate roda só offline, e exigir
   credencial pessoal para commitar contraria o Invariante 4.

## Bateria de testes — `tests/test_documentacao.py` e `tests/test_gate.py`

| id | teste | asserção |
|---|---|---|
| D1 | `test_d1_o_readme_manda_criar_o_env_antes_do_gate` | no bloco `Rodando` do `README.md`, o índice de `cp .env.example .env` é menor que o de `scripts/gate.sh`. **Reprova hoje** |
| D2 | `test_d2_o_readme_nao_manda_preencher_o_token_para_o_gate` | o bloco `Rodando` não pede `MOODLE_TOKEN` — o gate é offline (Invariante 4) |
| D3 | `test_d3_o_gate_checa_o_env_antes_da_suite` | no fonte de `scripts/gate.sh`, a checagem do `.env` aparece antes da linha que roda o `pytest` |
| D4 | `test_d4_o_gate_reprova_sem_env_citando_a_cura` | roda `scripts/gate.sh` num clone temporário **sem** `.env`; sai com `rc != 0` e o stdout contém `cp .env.example .env` |
| D5 | `test_d5_o_gate_nao_exige_token_do_moodle` | mesmo clone temporário, agora **com** `.env` copiado do exemplo (`MOODLE_TOKEN` vazio): a checagem 0 passa |

D4/D5 usam `git worktree`/`git clone --local` para o clone temporário e não tocam
a rede. Se o `git` não estiver disponível, pulam declarando o motivo.

## Critério de parada

`.venv/bin/python -m pytest` verde, `./scripts/gate.sh` PASSOU, e um clone
limpo seguindo o README de cima para baixo chega no `gate: PASSOU` sem passo
extra nenhum — verificado à mão, em clone novo.
