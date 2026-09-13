# `check-ignore` em caminho gravado em NFD — 12 testes reprovando pela causa errada

> **Estado, 10/09/2026: SATISFEITO.** Implementado e mergeado na PR #24. **Dois deltas,
> os dois medidos, e o primeiro muda o diagnóstico deste documento:**
>
> 1. **O gatilho não é "acento no caminho", é NFD no disco.** Uma worktree criada com o
>    nome em NFC fica verde; o que reproduz é o diretório ter sido *gravado* em NFD. No
>    macOS o APFS é insensível a normalização, então o G3 precisa criar a árvore com
>    `unicodedata.normalize("NFD", …)` num diretório-base que ainda não exista — e
>    carrega um `assert` que reprova caso essa premissa caia. Onde o texto abaixo diz
>    "pasta acentuada", leia "pasta gravada em NFD".
> 2. **O G5 nasceu largo demais.** A primeira versão varria o texto inteiro dos arquivos
>    de `tests/` e reprovava `tests/test_gate.py` (da PR #26), que cita o subcomando
>    numa **docstring**. Prosa não fala com o git, e uma regra que proíbe documentar a
>    coisa que ela protege é uma regra que alguém desliga. O G5 final lê AST e procura o
>    literal só dentro de lista/tupla de argumentos.
>
> Um achado que sobreviveu ao conserto e vale o olho de quem mexer aqui: **depois da
> refatoração, T3 e R3 sozinhos ficam cegos a esta classe de bug.** Com um helper que
> devolvesse `bool` sem a guarda de `rc`, um `128` viraria `False` viraria "não
> ignorado" e os dois passariam — medido. Quem os mantém honestos é a guarda de `rc`
> dentro de `tests/git.py`, não a asserção deles.

- **Prioridade:** alta — `gate.sh` reprova num clone limpo, por motivo errado
- **Arquivos:** `tests/jupiter/test_fixtures.py`, `tests/rucard/test_fixtures.py`

## Sintoma medido

Mesmo commit (`7ee6efc`), duas máquinas:

| checkout | resultado |
|---|---|
| `~/Desktop/Programação/mcp-usp` | `12 failed, 352 passed` |
| `/private/tmp/.../ascii-test` | `0 failed, 363 passed` |

Falham `test_t3_fatia_nao_depende_de_arquivo_fora_do_git` (4 params) e
`test_r3_...` (8 params), com a mensagem "está no .gitignore" — que é falsa:
`git check-ignore` com caminho **relativo** responde `rc=1` (não ignorado) para
todos eles.

## Causa raiz

```python
r = subprocess.run(["git", "check-ignore", "-q", str(p)], cwd=RAIZ, ...)
assert r.returncode == 1, f"{p.name} está no .gitignore..."
```

`p` é absoluto, montado a partir de `pathlib.Path(__file__).resolve()`. No macOS
o nome no disco é **NFD** (`Programac ̧a ̃o`) e o caminho que o Python entrega é
**NFC**. O git compara byte a byte, não acha o prefixo do repositório e responde:

```
rc=128  fatal: '…/Programação/…' is outside repository at '…/Programac ̧a ̃o/mcp-usp'
```

`128 != 1`, então o assert dispara — e reporta a causa errada. Dois defeitos
somados: caminho absoluto onde relativo bastava, e um `rc` de erro lido como
resposta de negócio. É a mesma família do bug de acento já fechado em 31/08
(T83, NFD na resolução de disciplina) sobrevivendo na suíte em vez de no produto.

## Cura

Um só lugar para a pergunta "este arquivo está ignorado?", em `tests/git.py`:

```python
def esta_ignorado(caminho, raiz) -> bool:
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(Path(caminho).relative_to(raiz))],
        cwd=raiz, capture_output=True, text=True,
    )
    if r.returncode not in (0, 1):
        raise RuntimeError(
            f"git check-ignore não respondeu sim nem não (rc={r.returncode}): "
            f"{r.stderr.strip()}"
        )
    return r.returncode == 0
```

Duas propriedades que o código de hoje não tem: caminho **relativo à raiz**
(imune a NFD/NFC) e `rc` fora de `{0,1}` vira erro próprio, não "está ignorado".

Os dois `test_*_fixtures.py` passam a chamar `esta_ignorado`. `scripts/gate.sh`
já usa caminho relativo na checagem 2 e não muda.

## Bateria de testes — `tests/test_git.py`

| id | teste | asserção |
|---|---|---|
| G1 | `test_g1_arquivo_versionado_nao_esta_ignorado` | `esta_ignorado(fixtures/jupiter/dwr-pubObterDisciplina-PSI3323.txt)` é `False` |
| G2 | `test_g2_arquivo_ignorado_e_reconhecido` | `esta_ignorado(fixtures/moodle/raw/action_events.json)` é `True` — a checagem 2 do gate, agora com asserção |
| G3 | `test_g3_caminho_com_acento_nao_vira_falso_positivo` | cria `tmp_path/"ação"/repo`, `git init`, um `.gitignore`, e verifica que os dois casos acima respondem certo dentro de um caminho acentuado. **É este que reprova hoje.** |
| G4 | `test_g4_rc_inesperado_vira_erro_e_nao_resposta` | com `git` fora do PATH (ou caminho fora do repo), `esta_ignorado` levanta `RuntimeError` citando o `rc` — nunca devolve `False` calado |
| G5 | `test_g5_nenhuma_chamada_a_check_ignore_usa_caminho_absoluto` | varre o fonte de `tests/` e falha se `check-ignore` aparecer em qualquer arquivo que não seja `tests/git.py` |

E os 12 testes que hoje reprovam passam a passar **no checkout acentuado**.

## Critério de parada

`.venv/bin/python -m pytest` verde **rodado de um checkout sob diretório gravado em NFD**
(num checkout cujo caminho contenha um diretório gravado em NFD), e
`./scripts/gate.sh` PASSOU no mesmo lugar.
