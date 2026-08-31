# Suíte de testes do MCP do Moodle — desenho

Data: 31/08/2026 · Branch: `claude/moodle-mcp-tests-e77611`

## 1. O que é

Especificação executável da Fase 2 do Moodle, escrita antes da implementação.
99 testes; 91 vermelhos por construção, 6 verdes (o piso da fixture), 2 pulados
(camada live). Roda em 0,46 s.

**Não** é a Fase 2 inteira. É uma **fatia vertical** de uma ferramenta,
`o_que_vence`, ponta a ponta. O §5 do `SPEC1.md` manda não decidir número e nome
de ferramenta por conveniência; uma fatia vertical fecha o red→green de verdade
em vez de deixar seis ferramentas vermelhas por semanas.

## 2. Escolhas, com o motivo

| Decisão | Motivo |
|---|---|
| Python + pytest | O repo já é bash + python3 (`reduzir.py`, o bloco dentro do `capture.sh`). Sem `package.json`, sem build step. |
| Fatia vertical `o_que_vence` | Critérios 1–3 do §5. É a pergunta com mais dado medido na Fase 1 e a que tem o argumento de custo mais forte. |
| Fonte: web service, não iCal | O iCal exigiria um segundo segredo (calendar export token) e devolve ICS sem `courseid` utilizável. O WS liga em `ja_entreguei` e `notas` depois. |
| Núcleo puro + adaptador MCP fino | O valor da suíte está em projeção e política, que não têm nada a ver com protocolo. A fronteira MCP leva 3 testes; o SDK não é dependência de teste. |
| Três marcadores (`politica`/`contrato`/`live`) | Eixo ortogonal ao arquivo. `politica` (58) roda sem fixture e sem rede; `contrato` (41) contra a fixture; `live` (2) só com `USP_MCP_LIVE=1`. |

## 3. A fixture, e uma exigência que o §3.3 não tem

`scripts/higienizar.py` é o §3.3 em código — não existia. Gera
`fixtures/moodle/action_events.json` (versionada) a partir do cru gitignorado.

Duas propriedades:

1. **Preserva a forma** — mesmas chaves, tipos e contagem. É o que o §3.3 pede.
2. **Preserva o comprimento em bytes** — e isto o §3.3 *não* pede. É requisito do
   teste de custo: trocar um `summary` de 9 kB por uma frase curta apagaria
   justamente o custo que a projeção existe para resolver.

Verificado: forma idêntica, 35 eventos, projeção byte-a-byte igual à do cru
(7.102 B), duas execuções byte-idênticas, zero e-mail real, zero segredo do
`.env`.

**Fixture ausente FALHA, não pula.** Um skip produziria verde sem ter testado
nada — o Invariante 6 aplicado à própria suíte. A única exceção é o *cru*, que é
legitimamente local à máquina do dono; os dois testes que dependem dele pulam com
o motivo escrito, e o `conftest` procura o cru no worktree, no checkout principal
e em `USP_MCP_MOODLE_RAW`.

## 4. O teste de custo é três asserções, não uma

Medido sobre a fixture, com subamostras dos mesmos eventos:

| eventos | cru | projetado | razão | B/evento |
|---:|---:|---:|---:|---:|
| 5 | 65.229 B | 1.027 B | 63,5 | 205 |
| 10 | 149.208 B | 2.011 B | 74,2 | 201 |
| 20 | 325.984 B | 4.022 B | 81,1 | 201 |
| 35 | 541.022 B | 7.102 B | 76,2 | 203 |

**A razão é a parte instável** — varia 28% e nem é monotônica, porque o `course`
de 9,5 kB é repetido por evento e a razão acaba medindo quantos eventos
compartilham disciplina na amostra. Fixar asserção sobre ela é frouxo ou
quebradiço.

Então: (a) teto absoluto de 10.000 B com a folga de ~40% declarada no teste;
(b) **180–230 B por evento projetado**, que é a faixa estável; (c) a categórica —
nenhum objeto `course`, `summary` ou `description` sobrevive à projeção. A (c) é
a que trava a regressão, porque a única forma de o custo explodir de novo é a
repetição voltar.

Correção de número que circulou antes: o **1000:1** é o enquadramento de
`notas/fase1-moodle.md` (cru vs. os 132 B/evento dos campos mínimos). A projeção
que a suíte descreve é **76:1** — o mesmo 1,3% que o §9 de 31/08 já registrava.

## 5. Invariantes que viraram teste executável

| Inv. | Como |
|---|---|
| 1 — read-only | Nenhuma escrita emitida, nem com `USP_MCP_ALLOW_WRITES=1`, no cliente e na ferramenta. |
| 2 — allowlist | Os 26 nomes do §2.2 parametrizados; bloqueio ignora a flag; `set_favourite_courses` negada apesar de se declarar `read`; sem regra de prefixo; superfície travada em exatamente 1 função; política aplicada **na fronteira do cliente**, não na ferramenta. |
| 3 — segredos | Token ausente de `repr`, `str`, `vars` e mensagem de erro; token no corpo e nunca na URL; varredura da fixture por segredo do `.env` sem imprimir valor. |
| 6 — erro legível | Lista vazia rotulada com o porquê (`vazio_por`); erro de credencial propaga em vez de virar zero; token inválido diz como renovar; 5 modos de falha distintos. |
| 7 — sem limite silencioso | Janela declarada na saída; `truncado` verdadeiro quando corta e **falso quando não corta**. |
| §3.1 — Regra de Ouro | Uma invocação emite uma requisição; o cliente **não tem** método que itere funções (asserção sobre `dir`). |

## 6. Limitações declaradas

- **Não existe fixture de erro do Moodle.** A Fase 1 só capturou respostas
  bem-sucedidas; varredura por `debuginfo`/`backtrace`/`exception`/`errorcode`
  deu zero em todas. Logo os testes de erro asseguram **o contrato da camada**,
  nunca a forma do erro do Moodle, que segue não verificada. Capturar um
  `invalidtoken` real é barato e seguro — backlog, fora desta fatia.
- **Um ponto de amostra só** para o teto de custo. As subamostras não contam:
  são os mesmos eventos. Um segundo `action_events` exigiria chamada nova ao web
  service, e a Regra de Ouro vale mais que o segundo ponto.
- **A higienização não é anonimização forte.** A substituição vem de hash do
  valor original: não é reversível a partir da saída, mas não resiste a quem já
  tenha lista de candidatos. Serve ao que o §3.3 pede.
- **Cache/TTL (Invariante 5) fora de escopo.** A fatia faz uma chamada por
  invocação e o dado do calendário muda todo dia, não todo semestre.

## 7. Acordos com a suíte do Jupiter

Combinado com a sessão irmã para os worktrees não colidirem no merge:

- `tests/moodle/` e `tests/jupiter/`, simétricos.
- `usp_mcp/moodle/server.py` e `usp_mcp/jupiter/server.py`; **raiz do pacote sem
  server**. É o §6 do `SPEC1.md` virando estrutura de diretório: entrypoint local
  com credencial de um lado, servidor público cacheável do outro.
- Marcador `@pytest.mark.live` + `USP_MCP_LIVE=1` nos dois. O que decidiu não foi
  o nome: sem a env var o skip **diz o motivo por escrito** em vez de o teste
  sumir da coleta.
- `cliente.py` é o mesmo conceito nos dois (transporte + allowlist na fronteira).

Convergência que vale registrar porque veio de dados que não se parecem: no
Moodle o numerador é ruidoso (o `course` repetido); no Jupiter não há redução a
medir (o payload **é** a resposta, razão ~1,8×). Nos dois casos a conclusão foi a
mesma — **o que trava regressão é asserção categórica, não numérica.**

## 8. Próximo passo

Implementar contra a suíte, na ordem: `politica` → `erros`/`cliente` →
`projecao` → `o_que_vence` → `server`. A camada `politica` é a que dá mais
segurança por linha escrita e não depende de nada.
