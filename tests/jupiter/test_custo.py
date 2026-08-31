"""T34-T37: custo.

Uma asserção de razão de redução foi desenhada e DESCARTADA por medição
(§4.6 do spec): a razão do Jupiter é ~1,8x, não os 11,5x do recon — esses
comparam DWR com HTML, não DWR com a projeção. Contra o próprio DWR quase
não há o que reduzir, porque o payload É a resposta.

O que sobrou: teto absoluto, o núcleo estruturado (spread de 9%) e uma
trava CATEGÓRICA, que é o que de fato impede regressão.
"""
import json

import pytest

from usp_mcp.jupiter import cliente, dwr, ferramentas

pytestmark = pytest.mark.contrato

# Medido em 31/08: 2.148 B (PSI3323) e 3.615 B (PTC3314). Folga de ~38%
# sobre a maior das duas amostras — duas, não uma: a maior é quase o dobro
# da menor com a MESMA forma.
TETO_SAIDA_B = 5000

# Medido: 179 B e 164 B, spread de 9%. É a parte que a ferramenta controla;
# o texto livre varia 77% e é a resposta em si.
NUCLEO = (
    "sigla",
    "nome",
    "creditos_aula",
    "creditos_trabalho",
    "carga_horaria_total",
    "tipo",
    "ativacao",
)
NUCLEO_MIN_B, NUCLEO_MAX_B = 140, 210


def tamanho(o):
    return len(json.dumps(o, ensure_ascii=False).encode())


def saida(gravador, bruto, sigla):
    return ferramentas.disciplina(sigla, cliente=cliente.ClienteJupiter(gravador([bruto])))


@pytest.mark.parametrize("qual,sigla", [("psi", "PSI3323"), ("ptc", "PTC3314")])
def test_t34_teto_absoluto_com_folga_declarada(gravador, psi3323, ptc3314, qual, sigla):
    d = saida(gravador, psi3323 if qual == "psi" else ptc3314, sigla)
    assert tamanho(d) <= TETO_SAIDA_B, f"{sigla}: {tamanho(d)} B > {TETO_SAIDA_B} B"


@pytest.mark.parametrize("qual,sigla", [("psi", "PSI3323"), ("ptc", "PTC3314")])
def test_t35_nucleo_estruturado_e_estavel(gravador, psi3323, ptc3314, qual, sigla):
    d = saida(gravador, psi3323 if qual == "psi" else ptc3314, sigla)
    n = {k: d[k] for k in NUCLEO}
    assert NUCLEO_MIN_B <= tamanho(n) <= NUCLEO_MAX_B, f"núcleo de {sigla}: {tamanho(n)} B"


@pytest.mark.parametrize("qual,sigla", [("psi", "PSI3323"), ("ptc", "PTC3314")])
def test_t36_conjunto_de_chaves_e_exatamente_o_declarado(
    gravador, psi3323, ptc3314, qual, sigla
):
    # A trava que não envelhece. T34 e T35 são numéricos; esta é categórica,
    # e é a única forma de o custo explodir de novo (campo a mais sobrevivendo).
    d = saida(gravador, psi3323 if qual == "psi" else ptc3314, sigla)

    desconhecidas = set(d) - set(ferramentas.CAMPOS_SAIDA)
    assert not desconhecidas, f"campos fora do declarado: {sorted(desconhecidas)}"

    despejo = json.dumps(d, ensure_ascii=False)
    for vazamento in ("stackTrace", "javaClassName", "nomdisepa", "pgmrsudisepa"):
        assert vazamento not in despejo
    assert not [k for k in d if k.endswith(("_es", "epa"))]


def test_t37_erro_nunca_custa_mais_que_sucesso(gravador, psi3323, erro):
    sucesso = tamanho(saida(gravador, psi3323, "PSI3323"))

    c = cliente.ClienteJupiter(gravador([erro]))
    with pytest.raises(dwr.JupiterErro) as exc:
        ferramentas.disciplina("ZZZ9999", cliente=c)
    projetado = tamanho({"erro": exc.value.mensagem})

    assert projetado < sucesso, (
        f"erro projetado {projetado} B >= sucesso {sucesso} B. O erro cru são "
        "~1.978 tokens contra ~17 da mensagem: 116x, e é a resposta ERRADA."
    )
