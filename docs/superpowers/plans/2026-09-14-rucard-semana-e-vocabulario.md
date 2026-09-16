# Semana numa chamada e vocabulário de quem pergunta — Plano de Implementação

> **Para quem executa:** implemente tarefa por tarefa, na ordem em que estão escritas.
> Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** a ferramenta `bandejao` passa a entender `dia="sexta"`, `dia="semana"` e
`restaurantes=["prefeitura"]`, responde a semana inteira numa chamada de ferramenta com 5
requisições HTTP, e deixa de repetir em cada refeição o item que está em todas.

**Arquitetura:** tudo em `usp_mcp/rucard/ferramentas.py` (resolução de dia e de
restaurante, `bandejao_semana`) e `usp_mcp/rucard/server.py` (schema, descrição,
`formatar` com rodapé de itens comuns, `formatar_semana`, despacho). `politica.py` e
`cliente.py` não mudam: a allowlist continua por **id**, e o alias é traduzido para id
antes de chegar nela.

**Stack:** Python 3.13, stdlib. Testes com pytest, offline, contra fixture.

**Spec:** `docs/superpowers/specs/2026-09-14-rucard-semana-e-vocabulario-design.md` — leia
antes de começar.

**Pré-requisito:** o plano `2026-09-14-rucard-aviso-no-cardapio.md` já mergeado na
`main` (este plano edita as mesmas funções e assume `_itens_e_opcao` com 4 valores).

## Restrições globais

- **Nenhuma requisição de rede na suíte.** Tudo com o `Gravador` de `tests/rucard/conftest.py`.
- **Nenhuma rota, nenhuma allowlist, nenhuma requisição a mais.** A semana inteira custa
  5 requisições (1 catálogo + 4 menus), e há teste que trava isso (Invariante 5).
- **O `enum` declarado e o `Literal` de `main()` têm de ser iguais.** O handshake H8
  (`tests/handshake/test_stdio.py`) compara os dois no fio; rode-o sempre que tocar o schema.
- **A projeção estruturada não perde item.** A fatoração de itens comuns é só no texto.
- **Português** em docstring, mensagem e comentário.
- **Antes de cada commit:** `./scripts/gate.sh` verde.
- **Mensagem de commit:** `feat|fix|test|docs(rucard): descrição`. Se o seu harness pedir
  uma linha de coautoria, acrescente-a ao fim.
- **Branch:** `feat/rucard-semana-e-vocabulario`, saindo da `main`.
- Suíte: `.venv/bin/python -m pytest tests/rucard tests/handshake -q`.

---

### Tarefa 1: `resolver_dia` entende nome de dia, "depois de amanhã" e artigo

**Arquivos:**
- Modificar: `usp_mcp/rucard/ferramentas.py` — função `resolver_dia` (linhas ~72-93) e
  constantes acima dela
- Testar: `tests/rucard/test_bandejao.py`

**Interfaces:**
- Produz: `segunda_da_semana(dia: date) -> date`, `dias_da_semana(hoje: date) -> list[date]`,
  constante `SEMANA = "semana"`. `resolver_dia` mantém a assinatura `(bruto: str, hoje: date) -> date`.

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/rucard/test_bandejao.py`:

```python
# --- R43: o dia como a pessoa fala -------------------------------------------


@pytest.mark.parametrize(
    "pedido,esperado",
    [
        ("sexta", datetime.date(2026, 8, 28)),
        ("sexta-feira", datetime.date(2026, 8, 28)),
        ("na sexta", datetime.date(2026, 8, 28)),
        ("SEX", datetime.date(2026, 8, 28)),
        ("segunda", datetime.date(2026, 8, 24)),  # já passou na quarta: mesma semana
        ("terca", datetime.date(2026, 8, 25)),
        ("sábado", datetime.date(2026, 8, 29)),
        ("no sabado", datetime.date(2026, 8, 29)),
        ("dom", datetime.date(2026, 8, 30)),
        ("depois de amanhã", datetime.date(2026, 8, 28)),
    ],
)
def test_r43_nome_de_dia_resolve_para_o_dia_dessa_semana(pedido, esperado):
    assert ferramentas.resolver_dia(pedido, hoje=QUARTA) == esperado


def test_r43b_dias_da_semana_vao_de_segunda_a_domingo():
    dias = ferramentas.dias_da_semana(QUARTA)
    assert len(dias) == 7
    assert dias[0] == SEGUNDA and dias[-1] == DOMINGO


def test_r43c_no_domingo_segunda_ainda_e_a_semana_que_o_rucard_publica():
    # No domingo 30/08 o RUCard ainda publica 24/08–30/08: "segunda" é 24/08, não 31/08.
    assert ferramentas.resolver_dia("segunda", hoje=DOMINGO) == SEGUNDA


def test_r43d_semana_nao_e_um_dia_e_a_funcao_diz_isso():
    with pytest.raises(ErroRucard) as exc:
        ferramentas.resolver_dia("semana", hoje=QUARTA)
    assert "bandejao_semana" in str(exc.value)
```

E, no topo do arquivo, troque `from usp_mcp.rucard.erros import RucardIndisponivel` por
`from usp_mcp.rucard.erros import ErroRucard, RucardIndisponivel`.

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/rucard/test_bandejao.py -q -k r43
```
Esperado: os parametrizados de nome de dia falham com `ErroRucard: não entendi o dia`;
R43b falha com `AttributeError: ... has no attribute 'dias_da_semana'`.

- [ ] **Passo 3: implementar**

Em `usp_mcp/rucard/ferramentas.py`, substitua a função `resolver_dia` inteira (e só ela)
por este bloco, que acrescenta as constantes e as duas funções auxiliares antes dela:

```python
# Nome de dia da semana → datetime.weekday(). Com e sem "-feira", com e sem
# acento, e a abreviação de três letras — é assim que a pergunta chega ("na
# sexta", "sábado", "qui"). Resolve para o dia DESSA semana, passado ou futuro,
# porque é a única semana que tem cardápio.
_NOMES_DIA: dict[str, int] = {
    "segunda": 0, "segunda-feira": 0, "seg": 0,
    "terça": 1, "terca": 1, "terça-feira": 1, "terca-feira": 1, "ter": 1,
    "quarta": 2, "quarta-feira": 2, "qua": 2,
    "quinta": 3, "quinta-feira": 3, "qui": 3,
    "sexta": 4, "sexta-feira": 4, "sex": 4,
    "sábado": 5, "sabado": 5, "sáb": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}
# "na sexta", "no sábado", "nesta quinta": o artigo não muda o dia.
_ARTIGO_DE_DIA = re.compile(r"^(na|no|nesta|neste|nessa|nesse|esta|este|essa|esse|a|o)\s+")

# O valor de `dia` que pede os sete dias. Quem o atende é `bandejao_semana`.
SEMANA = "semana"


def segunda_da_semana(dia: date) -> date:
    """A segunda-feira da semana de `dia`. A semana do RUCard vai de seg a dom."""
    return dia - timedelta(days=dia.weekday())


def dias_da_semana(hoje: date) -> list[date]:
    """Os sete dias, segunda a domingo, da semana de `hoje`."""
    segunda = segunda_da_semana(hoje)
    return [segunda + timedelta(days=i) for i in range(7)]


def resolver_dia(bruto: str, hoje: date) -> date:
    """"hoje", "amanhã", "sexta", `DD/MM/AAAA` ou `AAAA-MM-DD` → data.

    Aceita as duas formas de data porque as duas chegam: a brasileira é a que a
    pessoa digita e a que a API publica, e a ISO é a que um modelo tende a
    normalizar sozinho. Nome de dia resolve para o dia DESSA semana, mesmo que já
    tenha passado — "o que teve na segunda" é pergunta válida na quarta, e a
    semana corrente é a única com cardápio. Aceitar só uma forma transforma
    pergunta boa em erro.
    """
    texto = _ARTIGO_DE_DIA.sub("", (bruto or "hoje").strip().lower())
    if texto in ("hoje", "hj"):
        return hoje
    if texto in ("amanhã", "amanha"):
        return hoje + timedelta(days=1)
    if texto in ("depois de amanhã", "depois de amanha"):
        return hoje + timedelta(days=2)
    if texto == "ontem":
        return hoje - timedelta(days=1)
    if texto in _NOMES_DIA:
        return segunda_da_semana(hoje) + timedelta(days=_NOMES_DIA[texto])
    if texto == SEMANA:
        raise ErroRucard(
            "'semana' cobre os sete dias e é atendido por `bandejao_semana`, "
            "não por `bandejao`. Pela ferramenta MCP, dia='semana' já faz isso."
        )
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m"):
        try:
            lido = datetime.strptime(texto, formato).date()
        except ValueError:
            continue
        return lido.replace(year=hoje.year) if formato == "%d/%m" else lido
    raise ErroRucard(
        f"não entendi o dia {bruto!r}. Use 'hoje', 'amanhã', um dia da semana "
        "como 'sexta', 'semana' para os sete dias, ou uma data como 26/08/2026. "
        "O RUCard publica só a semana corrente, então data de outra semana não "
        "tem cardápio — nem no passado, nem no futuro."
    )
```

- [ ] **Passo 4: rodar os testes**

```bash
.venv/bin/python -m pytest tests/rucard -q
```
Esperado: tudo verde (R26/R26b/R27 continuam: "hoje", "amanhã" e data não mudaram).

- [ ] **Passo 5: commit**

```bash
git add usp_mcp/rucard/ferramentas.py tests/rucard/test_bandejao.py
git commit -m "feat(rucard): 'sexta', 'depois de amanhã' e 'na sexta' viram data da semana corrente"
```

---

### Tarefa 2: restaurante por nome

**Arquivos:**
- Modificar: `usp_mcp/rucard/ferramentas.py` — constantes novas e função
  `resolver_restaurantes`; em `bandejao`, a linha `ids = [str(i) for i in (restaurantes or politica.RUS_PERMITIDOS)]`
- Testar: `tests/rucard/test_bandejao.py`

**Interfaces:**
- Produz: `NOMES_RU: tuple[str, ...] = ("central", "prefeitura", "fisica", "quimicas")`
  (é o `enum` que a Tarefa 3 declara), `ALIASES_RU: dict[str, str]`,
  `resolver_restaurantes(pedidos) -> list[str]` (ids, sem repetição, na ordem pedida).

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/rucard/test_bandejao.py`:

```python
# --- R44: o restaurante como a pessoa fala -----------------------------------


def test_r44_restaurante_por_nome_ou_por_id():
    assert ferramentas.resolver_restaurantes(["Prefeitura", "6", "fisica"]) == ["7", "6", "8"]
    assert ferramentas.resolver_restaurantes(["Químicas", "quimicas", "9"]) == ["9"]
    assert ferramentas.resolver_restaurantes(["PUSP-CB", "pusp"]) == ["7"]
    assert ferramentas.resolver_restaurantes(None) == ["6", "7", "8", "9"]
    assert ferramentas.resolver_restaurantes([]) == ["6", "7", "8", "9"]


def test_r44b_nome_desconhecido_e_erro_legivel_citando_os_quatro():
    with pytest.raises(ErroRucard) as exc:
        ferramentas.resolver_restaurantes(["each"])
    for palavra in ("each", "central", "prefeitura", "fisica", "quimicas"):
        assert palavra in str(exc.value)


def test_r44c_bandejao_aceita_o_nome_e_so_pede_aquele_ru(chamar):
    resposta, transporte = chamar(restaurantes=["prefeitura"], refeicao="almoco")
    assert [ru["id"] for ru in resposta["restaurantes"]] == ["7"]
    assert transporte.rotas() == ["restaurants", "menu/7"]


def test_r44d_o_enum_declarado_e_exatamente_a_lista_de_nomes():
    assert ferramentas.NOMES_RU == ("central", "prefeitura", "fisica", "quimicas")
    assert set(ferramentas.ALIASES_RU.values()) == set(ferramentas.NOMES_RU_PARA_ID.values())
    for nome in ferramentas.NOMES_RU:
        assert nome in ferramentas.ALIASES_RU
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/rucard/test_bandejao.py -q -k r44
```
Esperado: 4 FAILED com `AttributeError: ... 'resolver_restaurantes'` / `'NOMES_RU'`.

- [ ] **Passo 3: implementar**

Em `usp_mcp/rucard/ferramentas.py`, logo depois de `_ROTULO_REFEICAO = {...}`, acrescente:

```python
# O vocabulário de quem pergunta, e o id que a allowlist entende. `politica`
# continua decidindo POR ID (§1.2: name/alias é exibição); aqui só se traduz a
# entrada do usuário antes de qualquer política. Sem acento nos nomes canônicos
# porque são valores de enum que trafegam em JSON digitado por modelo — com
# acento também são aceitos.
NOMES_RU_PARA_ID: dict[str, str] = {
    "central": "6", "prefeitura": "7", "fisica": "8", "quimicas": "9",
}
NOMES_RU: tuple[str, ...] = tuple(NOMES_RU_PARA_ID)
ALIASES_RU: dict[str, str] = {
    **NOMES_RU_PARA_ID,
    "pusp": "7", "pusp-cb": "7", "puspcb": "7", "pusp-c": "7",
    "física": "8",
    "químicas": "9", "quimica": "9", "química": "9",
}


def resolver_restaurantes(pedidos) -> list[str]:
    """Nomes e/ou ids → ids, sem repetição, na ordem pedida. Vazio → os quatro.

    Nome desconhecido é erro legível AQUI, antes da política: passar "each" adiante
    como se fosse id devolveria a mensagem de id inexistente, que é a cura errada.
    """
    if not pedidos:
        return list(politica.RUS_PERMITIDOS)
    ids: list[str] = []
    for pedido in pedidos:
        chave = str(pedido).strip().lower()
        if chave.isdigit():
            id_ = chave
        elif chave in ALIASES_RU:
            id_ = ALIASES_RU[chave]
        else:
            raise ErroRucard(
                f"não conheço o restaurante {pedido!r}. Use {', '.join(NOMES_RU)} "
                "— ou omita para comparar os quatro."
            )
        if id_ not in ids:
            ids.append(id_)
    return ids
```

Em `bandejao`, troque
`    ids = [str(i) for i in (restaurantes or politica.RUS_PERMITIDOS)]`
por
`    ids = resolver_restaurantes(restaurantes)`.

- [ ] **Passo 4: rodar os testes**

```bash
.venv/bin/python -m pytest tests/rucard -q
```
Esperado: tudo verde. (Os testes antigos passam ids numéricos, que continuam aceitos.)

- [ ] **Passo 5: commit**

```bash
git add usp_mcp/rucard/ferramentas.py tests/rucard/test_bandejao.py
git commit -m "feat(rucard): 'prefeitura', 'central', 'fisica', 'quimicas' resolvem para o id do RU"
```

---

### Tarefa 3: o schema e a descrição que o modelo lê

**Arquivos:**
- Modificar: `usp_mcp/rucard/server.py` — `listar_ferramentas()` (descrição e as
  propriedades `dia` e `restaurantes`) e o `anotar(...)` dentro de `main()`
- Modificar: `tests/rucard/test_server_mcp.py` — R38 e R38b

**Interfaces:**
- Consome: `ferramentas.NOMES_RU` (Tarefa 2).
- Produz: `inputSchema.properties.restaurantes.items.enum == ["central", "prefeitura", "fisica", "quimicas"]`.

- [ ] **Passo 1: atualizar os testes (falham primeiro)**

Em `tests/rucard/test_server_mcp.py`, em `test_r38_descricao_fala_a_lingua_de_quem_pergunta`,
troque
`    for vocabulario in ("bandejão", "almoço", "jantar", "hoje"):`
por
`    for vocabulario in ("bandejão", "almoço", "jantar", "hoje", "prefeitura", "sexta", "semana"):`

Em `test_r38b_o_schema_declara_os_quatro_rus_e_nao_convida_a_inventar_id`, troque o bloco

```python
    enumerado = propriedades["restaurantes"]["items"]["enum"]
    assert enumerado == ["6", "7", "8", "9"], (
        "o schema é onde o modelo aprende que só existem quatro RUs aqui. Sem "
        "enum, ele inventa id e recebe negativa da allowlist — erro certo pela "
        "via mais cara."
    )
```
por
```python
    enumerado = propriedades["restaurantes"]["items"]["enum"]
    assert enumerado == ["central", "prefeitura", "fisica", "quimicas"], (
        "o schema é onde o modelo aprende que só existem quatro RUs aqui, e "
        "pelo NOME que a pessoa fala — id numérico é detalhe da API. Sem enum, "
        "ele inventa e recebe negativa da allowlist: erro certo pela via mais cara."
    )
    descricao_do_dia = propriedades["dia"]["description"].lower()
    assert "sexta" in descricao_do_dia and "semana" in descricao_do_dia
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/rucard/test_server_mcp.py -q -k r38
```
Esperado: 2 FAILED.

- [ ] **Passo 3: implementar**

Em `usp_mcp/rucard/server.py`, dentro de `listar_ferramentas()`:

(a) substitua o valor de `"description"` por:

```python
            "description": (
                "Cardápio dos bandejões da USP na Cidade Universitária — Central, "
                "Prefeitura (PUSP-CB), Física e Químicas. Diz o que tem no almoço "
                "e no jantar de um dia, com calorias, preço de aluno, horário e a "
                "opção do dia (marcada como vegetariana quando o RU marca), nos "
                "quatro restaurantes de uma vez, para comparar onde vale a pena "
                "comer. Com dia='semana' traz os sete dias numa chamada só. Use "
                "para 'o que tem no bandejão hoje', 'o que tem na sexta?', 'que "
                "dia tem lasanha essa semana?', 'vale a pena almoçar na "
                "Prefeitura?', 'que horas fecha o jantar', 'o das Químicas abre "
                "no sábado?'. LIMITES: só a semana corrente (não há cardápio de "
                "outra semana, nem passada nem futura); não há cardápio de café "
                "da manhã publicado, só o horário; e nada de saldo, extrato ou "
                "recarga do cartão."
            ),
```

(b) substitua a propriedade `"dia"` por:

```python
                    "dia": {
                        "type": "string",
                        "description": (
                            "'hoje', 'amanhã', um dia da semana ('sexta', "
                            "'sábado'), 'semana' para os sete dias de segunda a "
                            "domingo, ou uma data como 26/08/2026. Nome de dia é "
                            "o dessa semana, mesmo que já tenha passado: só a "
                            "semana corrente tem cardápio."
                        ),
                        "default": "hoje",
                    },
```

(c) substitua a propriedade `"restaurantes"` por:

```python
                    "restaurantes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["central", "prefeitura", "fisica", "quimicas"],
                        },
                        "description": (
                            "Quais bandejões: central (Central), prefeitura "
                            "(PUSP-CB, o da Prefeitura do campus), fisica "
                            "(Física), quimicas (Químicas). Omita para comparar "
                            "os quatro."
                        ),
                    },
```

(d) em `main()`, no `anotar(...)`, troque
`            "restaurantes": list[Literal["6", "7", "8", "9"]] | None,`
por
`            "restaurantes": list[Literal["central", "prefeitura", "fisica", "quimicas"]] | None,`

- [ ] **Passo 4: rodar suíte e handshake**

```bash
.venv/bin/python -m pytest tests/rucard tests/handshake -q
```
Esperado: tudo verde. H8 confirma que o `enum` novo chega ao fio.

- [ ] **Passo 5: commit**

```bash
git add usp_mcp/rucard/server.py tests/rucard/test_server_mcp.py
git commit -m "feat(rucard): o modelo escolhe o RU pelo nome, e a descrição cita 'sexta', 'semana' e 'Prefeitura'"
```

---

### Tarefa 4: item comum a todas as refeições sai uma vez, no rodapé

**Arquivos:**
- Modificar: `usp_mcp/rucard/server.py` — `_linha_da_refeicao` e `formatar`
- Testar: `tests/rucard/test_server_mcp.py`

**Interfaces:**
- Produz: `_itens_comuns(refeicoes: list[dict]) -> set[str]`;
  `_linha_da_refeicao(nome_ru, qual, dados, comuns=frozenset())`.

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/rucard/test_server_mcp.py`:

```python
@pytest.mark.contrato
def test_r47_item_comum_a_todas_as_refeicoes_sai_uma_vez_no_rodape(
    gravador, respostas_da_fatia
):
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    texto = server.chamar_ferramenta("bandejao", {"dia": "24/08/2026"}, cliente=cliente)

    # Em 24/08 os sete pratos abertos têm "Minipão / refresco" e o arroz: uma vez cada.
    assert texto.count("Minipão / refresco") == 1
    assert texto.count("Arroz / feijão / arroz integral") == 1
    (rodape,) = [l for l in texto.splitlines() if l.startswith("Em todas as refeições acima:")]
    assert "Minipão / refresco" in rodape and "Arroz / feijão / arroz integral" in rodape
    assert "Iscas de tilápia empanadas" in texto, "o que varia continua na linha"


@pytest.mark.contrato
def test_r47b_com_uma_refeicao_so_nao_ha_rodape_e_a_linha_fica_inteira(
    gravador, respostas_da_fatia
):
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    texto = server.chamar_ferramenta(
        "bandejao",
        {"dia": "24/08/2026", "refeicao": "almoco", "restaurantes": ["central"]},
        cliente=cliente,
    )
    assert "Em todas as refeições" not in texto
    linha = next(l for l in texto.splitlines() if "Iscas de tilápia" in l)
    assert "Minipão / refresco" in linha and "Arroz / feijão / arroz integral" in linha
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/rucard/test_server_mcp.py -q -k r47
```
Esperado: R47 FAILED (`count == 7`); R47b PASSED por enquanto (ainda não há rodapé) — ele
existe para travar o comportamento depois.

- [ ] **Passo 3: implementar**

Em `usp_mcp/rucard/server.py`:

(a) acrescente antes de `_linha_da_refeicao`:

```python
def _itens_comuns(refeicoes: list[dict]) -> set[str]:
    """Itens presentes em TODAS as refeições abertas — e só com duas ou mais.

    Regra estrita de propósito: "na maioria" exigiria marcar exceções, e o ganho
    medido (~20 B por refeição) não paga a complexidade. Com uma refeição só não
    há o que fatorar. A projeção estruturada não muda: isto é só texto.
    """
    abertas = [r for r in refeicoes if r.get("situacao") == "aberto" and r.get("itens")]
    if len(abertas) < 2:
        return set()
    return set.intersection(*(set(r["itens"]) for r in abertas))
```

(b) em `_linha_da_refeicao`, mude a assinatura para
`def _linha_da_refeicao(nome_ru: str, qual: str, dados: dict, comuns=frozenset()) -> list[str]:`
e troque o bloco

```python
    if dados.get("itens"):
        linhas.append("  " + " · ".join(dados["itens"]))
```
por
```python
    itens = [i for i in dados.get("itens") or () if i not in comuns]
    if itens:
        linhas.append("  " + " · ".join(itens))
```

(c) substitua `formatar` inteira por:

```python
def formatar(resposta: dict) -> str:
    """Texto para o modelo ler. Compacto, e com o que não se sabe no fim."""
    linhas = [f"Bandejão — {resposta['dia_semana']} {resposta['data']}"]

    refeicoes = [
        ru["refeicoes"][qual]
        for ru in resposta["restaurantes"]
        for qual in resposta["refeicoes"]
        if ru["refeicoes"].get(qual)
    ]
    comuns = _itens_comuns(refeicoes)

    for ru in resposta["restaurantes"]:
        for qual in resposta["refeicoes"]:
            dados = ru["refeicoes"].get(qual)
            if dados:
                linhas.extend(_linha_da_refeicao(ru["nome"], qual, dados, comuns))

    if comuns:
        linhas.append("Em todas as refeições acima: " + " · ".join(sorted(comuns)))

    # Invariante 7: o que a ferramenta NÃO sabe vai junto, nunca por omissão.
    for aviso in resposta.get("avisos") or ():
        linhas.append(f"⚠ {aviso}")

    return "\n".join(linhas)
```

- [ ] **Passo 4: rodar os testes**

```bash
.venv/bin/python -m pytest tests/rucard -q
```
Esperado: tudo verde (R41 procura "Iscas de tilápia empanadas", que continua na linha;
R37b tem teto de 4.500 B, e o texto só encolheu).

- [ ] **Passo 5: commit**

```bash
git add usp_mcp/rucard/server.py tests/rucard/test_server_mcp.py
git commit -m "feat(rucard): item presente em todas as refeições sai uma vez, no rodapé"
```

---

### Tarefa 5: a semana inteira numa chamada

**Arquivos:**
- Modificar: `usp_mcp/rucard/ferramentas.py` — `bandejao_semana` e `CAMPOS_SEMANA` (novos,
  depois de `bandejao`)
- Modificar: `usp_mcp/rucard/server.py` — `formatar_semana` (nova), `_SITUACAO_CURTA`
  (nova), `chamar_ferramenta` (despacho e parâmetro `hoje`)
- Testar: `tests/rucard/test_bandejao.py`, `tests/rucard/test_server_mcp.py`

**Interfaces:**
- Consome: `dias_da_semana` (Tarefa 1), `resolver_restaurantes` (Tarefa 2), `_itens_comuns`
  e `_ROTULO` (Tarefa 4 / já existente em `server.py`).
- Produz: `bandejao_semana(refeicao="todas", restaurantes=None, *, cliente, hoje=None) -> dict`
  com chaves `CAMPOS_SEMANA = ("inicio", "fim", "refeicoes", "dias", "avisos")`, onde cada
  item de `dias` é `{"data", "dia_semana", "restaurantes"}` (o mesmo `restaurantes` de
  `bandejao`). `chamar_ferramenta(nome, argumentos, *, cliente=None, hoje=None) -> str`.

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/rucard/test_bandejao.py`:

```python
# --- R45: a semana inteira numa chamada --------------------------------------


def test_r45_bandejao_semana_tem_sete_dias_e_avisos_sem_repeticao(
    gravador, respostas_da_fatia
):
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    semana = ferramentas.bandejao_semana(refeicao="todas", cliente=cliente, hoje=QUARTA)

    assert set(semana) == set(ferramentas.CAMPOS_SEMANA)
    assert semana["inicio"] == "24/08/2026" and semana["fim"] == "30/08/2026"
    assert [d["dia_semana"] for d in semana["dias"]] == [
        "seg", "ter", "qua", "qui", "sex", "sáb", "dom"
    ]
    assert semana["refeicoes"] == ["almoco", "jantar"]
    assert len(semana["avisos"]) == len(set(semana["avisos"])), "aviso repetido entre dias"
    # O domingo do 9 tem almoço e não tem jantar (R29b), visto pela semana.
    domingo = semana["dias"][6]
    (ru9,) = [r for r in domingo["restaurantes"] if r["id"] == "9"]
    assert ru9["refeicoes"]["almoco"]["situacao"] == "aberto"
    assert ru9["refeicoes"]["jantar"]["situacao"] == "nao_serve"


def test_r45b_a_semana_inteira_custa_cinco_requisicoes(gravador, respostas_da_fatia):
    transporte = gravador(respostas_da_fatia)
    cliente = ClienteRucard(transporte, hash_rucard=HASH_DE_TESTE)
    ferramentas.bandejao_semana(refeicao="todas", cliente=cliente, hoje=SEGUNDA)
    # Invariante 5: o /menu já devolve a semana, e o cliente cacheia por RU.
    assert sorted(transporte.rotas()) == ["menu/6", "menu/7", "menu/8", "menu/9", "restaurants"]
```

No fim de `tests/rucard/test_server_mcp.py`:

```python
@pytest.mark.contrato
def test_r46_dia_semana_e_uma_chamada_de_ferramenta_com_os_sete_dias(
    gravador, respostas_da_fatia
):
    transporte = gravador(respostas_da_fatia)
    cliente = ClienteRucard(transporte, hash_rucard=HASH_DE_TESTE)
    texto = server.chamar_ferramenta(
        "bandejao", {"dia": "semana", "refeicao": "almoco"}, cliente=cliente, hoje=SEGUNDA
    )

    assert texto.startswith("Bandejão — semana de 24/08/2026 a 30/08/2026")
    assert "sex 28/08" in texto
    assert "Lombo com molho de limão" in texto, "terça no Central: um dia que não é hoje"
    assert "CENTRAL · almoço" in texto and "QUÍMICAS · almoço" in texto
    assert "jantar" not in texto.lower()
    assert sorted(transporte.rotas()) == ["menu/6", "menu/7", "menu/8", "menu/9", "restaurants"]


@pytest.mark.contrato
def test_r46b_dia_fechado_na_semana_e_uma_palavra_nao_um_paragrafo(
    gravador, respostas_da_fatia
):
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    texto = server.chamar_ferramenta(
        "bandejao",
        {"dia": "semana", "refeicao": "almoco", "restaurantes": ["central"]},
        cliente=cliente, hoje=SEGUNDA,
    )
    linha = next(l for l in texto.splitlines() if l.strip().startswith("sáb 29/08"))
    assert linha.strip() == "sáb 29/08: não serve"


@pytest.mark.contrato
@pytest.mark.parametrize("refeicao,teto", [("almoco", 6_500), ("todas", 11_000)])
def test_r46c_o_texto_semanal_tem_teto(gravador, respostas_da_fatia, refeicao, teto):
    # Medido em 14/09/2026 sobre as fixtures da Fase 1: 4.818 B (almoço) e
    # 8.381 B (almoço e jantar), 4 RUs × 7 dias. Folga de ~30%.
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    texto = server.chamar_ferramenta(
        "bandejao", {"dia": "semana", "refeicao": refeicao}, cliente=cliente, hoje=SEGUNDA
    )
    assert len(texto.encode()) <= teto, f"{refeicao}: {len(texto.encode())} B"
    assert len(texto.splitlines()) < 80
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/rucard -q -k "r45 or r46"
```
Esperado: R45/R45b FAILED (`AttributeError: bandejao_semana`); R46* FAILED
(`TypeError: ... unexpected keyword argument 'hoje'`).

- [ ] **Passo 3: implementar `bandejao_semana`**

Em `usp_mcp/rucard/ferramentas.py`, depois da função `bandejao` e antes de
`_ficha_para_saida`, acrescente:

```python
CAMPOS_SEMANA = ("inicio", "fim", "refeicoes", "dias", "avisos")


def bandejao_semana(refeicao: str = "todas", restaurantes=None, *, cliente,
                    hoje: date | None = None) -> dict:
    """Os sete dias da semana corrente, segunda a domingo, numa resposta só.

    É a mesma pergunta do §5 ("o que tem, e onde vale a pena") com outro recorte
    de tempo — "que dia tem lasanha?" — e por isso não é outra ferramenta. Chama
    `bandejao` uma vez por dia; o cliente cacheia o `/menu` por RU, então a semana
    inteira custa as mesmas 5 requisições de um dia (há teste que trava isso).
    Avisos iguais entre dias saem uma vez.
    """
    hoje = hoje if hoje is not None else datetime.now(FUSO_SAO_PAULO).date()
    respostas = [
        bandejao(
            dia=d.strftime("%d/%m/%Y"), refeicao=refeicao, restaurantes=restaurantes,
            cliente=cliente, hoje=hoje,
        )
        for d in dias_da_semana(hoje)
    ]

    avisos: list[str] = []
    for resposta in respostas:
        for aviso in resposta["avisos"]:
            if aviso not in avisos:
                avisos.append(aviso)

    return {
        "inicio": respostas[0]["data"],
        "fim": respostas[-1]["data"],
        "refeicoes": respostas[0]["refeicoes"],
        "dias": [
            {k: r[k] for k in ("data", "dia_semana", "restaurantes")} for r in respostas
        ],
        "avisos": avisos,
    }
```

- [ ] **Passo 4: implementar `formatar_semana` e o despacho**

Em `usp_mcp/rucard/server.py`:

(a) troque a linha de import `from .ferramentas import bandejao` por
`from .ferramentas import SEMANA, bandejao, bandejao_semana`.

(b) depois de `formatar`, acrescente:

```python
# Situação de refeição não aberta, numa palavra: na semana são até 28 linhas de
# dia, e a frase inteira do `detalhe` em cada uma custaria mais que o cardápio.
# O detalhe continua na projeção estruturada.
_SITUACAO_CURTA = {
    "nao_serve": "não serve",
    "fechado": "fechado",
    "indisponivel": "indisponível",
    "sem_cardapio_publicado": "sem cardápio publicado",
}


def formatar_semana(resposta: dict) -> str:
    """Texto da semana para o modelo ler: um bloco por RU e refeição, um dia por
    linha. Horário fica na linha do dia, não no cabeçalho do RU — o 9 fecha o
    jantar às 19:45 em dia útil e às 19:00 no sábado, e um horário só mentiria."""
    linhas = [f"Bandejão — semana de {resposta['inicio']} a {resposta['fim']}"]
    dias = resposta["dias"]
    refeicoes_pedidas = resposta["refeicoes"]

    todas = [
        ru["refeicoes"][qual]
        for d in dias
        for ru in d["restaurantes"]
        for qual in refeicoes_pedidas
        if ru["refeicoes"].get(qual)
    ]
    comuns = _itens_comuns(todas)

    # A ordem dos RUs é a do primeiro dia em que cada um aparece: um RU pode
    # faltar num dia (semana não publicada) sem sumir do texto.
    ordem: list[tuple[str, str]] = []
    for d in dias:
        for ru in d["restaurantes"]:
            if (ru["id"], ru["nome"]) not in ordem:
                ordem.append((ru["id"], ru["nome"]))

    for id_ru, nome in ordem:
        for qual in refeicoes_pedidas:
            preco = next(
                (
                    ru["refeicoes"][qual].get("preco_aluno")
                    for d in dias
                    for ru in d["restaurantes"]
                    if ru["id"] == id_ru and ru["refeicoes"].get(qual, {}).get("preco_aluno")
                ),
                None,
            )
            cabecalho = f"{nome} · {_ROTULO[qual]}"
            if preco:
                cabecalho += f" · R$ {preco} (aluno)"
            linhas.append(cabecalho)

            for d in dias:
                rotulo_dia = f"{d['dia_semana']} {d['data'][:5]}"
                ru = next((r for r in d["restaurantes"] if r["id"] == id_ru), None)
                if ru is None:
                    linhas.append(f"  {rotulo_dia}: sem cardápio publicado para este dia")
                    continue
                dados = ru["refeicoes"].get(qual)
                if not dados:
                    continue
                if dados["situacao"] != "aberto":
                    curta = _SITUACAO_CURTA.get(dados["situacao"], dados["situacao"])
                    linhas.append(f"  {rotulo_dia}: {curta}")
                    continue
                partes = [rotulo_dia]
                if dados.get("horario"):
                    partes.append(dados["horario"])
                if dados.get("calorias"):
                    partes.append(f"{dados['calorias']} kcal")
                itens = [i for i in dados.get("itens") or () if i not in comuns]
                linha = "  " + " · ".join(partes) + ": " + " · ".join(itens)
                if dados.get("opcao"):
                    marca = (
                        " [marcada como vegetariana]"
                        if dados.get("opcao_vegetariana_marcada") else ""
                    )
                    linha += f" | Opção: {dados['opcao']}{marca}"
                linhas.append(linha)

    if comuns:
        linhas.append("Em todas as refeições acima: " + " · ".join(sorted(comuns)))

    for aviso in resposta.get("avisos") or ():
        linhas.append(f"⚠ {aviso}")

    return "\n".join(linhas)
```

(c) em `chamar_ferramenta`, mude a assinatura para
`def chamar_ferramenta(nome: str, argumentos: dict, *, cliente=None, hoje=None) -> str:`
e substitua o `return formatar(bandejao(...))` final por:

```python
    dia = argumentos.get("dia", "hoje")
    refeicao = argumentos.get("refeicao", "todas")
    restaurantes = argumentos.get("restaurantes")

    if (dia or "hoje").strip().lower() == SEMANA:
        return formatar_semana(
            bandejao_semana(
                refeicao=refeicao, restaurantes=restaurantes, cliente=cliente, hoje=hoje
            )
        )

    return formatar(
        bandejao(
            dia=dia, refeicao=refeicao, restaurantes=restaurantes,
            cliente=cliente, hoje=hoje,
        )
    )
```

Acrescente à docstring de `chamar_ferramenta` a frase:
`` `hoje` é injetável só para os testes da semana: sem ele, "semana" seria a de quem roda o teste. ``

- [ ] **Passo 5: rodar tudo**

```bash
.venv/bin/python -m pytest tests/rucard tests/handshake -q
```
Esperado: tudo verde.

- [ ] **Passo 6: olhar a saída semanal**

```bash
.venv/bin/python - <<'PY'
import datetime
from tests.rucard.conftest import Gravador, HASH_DE_TESTE, texto
from usp_mcp.rucard import server
from usp_mcp.rucard.cliente import ClienteRucard
r = {"restaurants": texto("restaurantes"), **{f"menu/{n}": texto(f"menu_{n}") for n in "6789"}}
cli = ClienteRucard(Gravador(r), hash_rucard=HASH_DE_TESTE)
print(server.chamar_ferramenta("bandejao", {"dia": "semana", "refeicao": "almoco"}, cliente=cli, hoje=datetime.date(2026, 8, 24)))
PY
```
Esperado: 4 blocos (um por RU), 7 linhas de dia em cada, `sáb 29/08: não serve` nos três
que não abrem no sábado, rodapé `Em todas as refeições acima: Minipão / refresco`.

- [ ] **Passo 7: commit**

```bash
git add usp_mcp/rucard/ferramentas.py usp_mcp/rucard/server.py tests/rucard/test_bandejao.py tests/rucard/test_server_mcp.py
git commit -m "feat(rucard): dia='semana' traz os sete dias numa chamada, com 5 requisições"
```

---

### Tarefa 6: registro, README e PR

**Arquivos:**
- Modificar: `SPEC1.md` (fim do §9)
- Modificar: `README.md` (linha da tabela de ferramentas: `usp-rucard | bandejao`)
- Modificar: `usp_mcp/rucard/ferramentas.py` (docstring do módulo)

- [ ] **Passo 1: §9 do `SPEC1.md`**

No fim do arquivo:

```markdown
### 14/09/2026 — `bandejao` entende "sexta", "semana" e "Prefeitura"

Revisão de má prática nos dois servidores públicos. Medido na saída real: "que dia tem
lasanha essa semana?" custava 5 a 7 chamadas de ferramenta (~1.000 B cada) porque `dia`
só aceitava `hoje`/`amanhã`/data; "o que tem na sexta?" obrigava o modelo a calcular a
data; e "bandejão da Prefeitura" exigia saber que Prefeitura = PUSP-CB = id `7`, que a
descrição não dizia.

**Decisão:** (a) `dia` aceita nome de dia da semana (resolve para o dia DESSA semana,
passado ou futuro — é a única com cardápio), `depois de amanhã`, artigo na frente, e
`semana`; (b) `restaurantes` tem `enum` de **nomes** (`central`, `prefeitura`, `fisica`,
`quimicas`), traduzidos para id antes da política, que segue por id (§1.2); (c)
`bandejao_semana` responde os sete dias numa chamada — **5 requisições HTTP**, as mesmas
de um dia, porque o `/menu` já devolve a semana e o cache é por RU (teste R45b trava);
(d) item presente em todas as refeições abertas sai uma vez, num rodapé, só no texto.

**Medido (fixtures da Fase 1, 4 RUs):** semana/almoço 4.818 B, semana/almoço+jantar
8.381 B; tetos 6.500 B e 11.000 B (R46c). O único item comum à semana inteira é
`Minipão / refresco` — o arroz varia (`feijão preto`), e por isso a fatoração é estrita
(interseção), não "na maioria". Testes R43–R47.
```

- [ ] **Passo 2: README**

Em `README.md`, na tabela de ferramentas, troque a linha do `bandejao` por:

```markdown
| `usp-rucard` | `bandejao` | O que tem no bandejão hoje, na sexta ou na semana inteira, e onde vale a pena comer |
```

- [ ] **Passo 3: docstring do módulo**

Em `usp_mcp/rucard/ferramentas.py`, depois do parágrafo `**O dia se escolhe por data, não
por índice.**`, acrescente:

```
**A semana é a mesma pergunta.** "Que dia tem lasanha?" não é outra ferramenta: é
`bandejao` sete vezes, uma por dia, com o `/menu` vindo do cache — 5 requisições, as
mesmas de um dia. Nome de dia ("sexta") resolve para o dia DESSA semana, porque é a
única que existe no RUCard.
```

- [ ] **Passo 4: gate, commit e PR**

```bash
./scripts/gate.sh
git add SPEC1.md README.md usp_mcp/rucard/ferramentas.py
git commit -m "docs(spec): §9 — bandejao por nome de dia, por semana e por nome de RU"
git push -u origin feat/rucard-semana-e-vocabulario
gh pr create --base main --title "feat(rucard): semana numa chamada, dia por nome, RU por nome" --body "Spec: docs/superpowers/specs/2026-09-14-rucard-semana-e-vocabulario-design.md. Plano: docs/superpowers/plans/2026-09-14-rucard-semana-e-vocabulario.md. Depende do PR do comunicado no cardápio."
```
Esperado: `gate: PASSOU`.
