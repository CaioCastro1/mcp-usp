"""S1: nenhum arquivo do pacote se declara esqueleto.

`tests/rucard/conftest.py` e `tests/jupiter/conftest.py` definem
`SENTINELA_ESQUELETO = "ESQUELETO-FASE2"` e o `fonte_de` de cada um recusa ler
um módulo que ainda traga a marca. É o que impede uma varredura de fonte
("nada de hash", "nada de GET") de passar verde contra um arquivo vazio. Só que
o guarda só olha os módulos que algum teste manda ler. Medido em 16/09/2026: a
marca sobreviveu **exatamente** nos dois arquivos que nenhum `fonte_de` cobre,
`usp_mcp/rucard/erros.py` (o sentinela literal) e `usp_mcp/moodle/__init__.py`
("ESQUELETO. Nada aqui está implementado", sobre um pacote com dez ferramentas
e centenas de testes). Um cabeçalho que afirma que o código não existe é estado
escrito em dois lugares (§9, 31/08), e envelheceu calado por duas semanas.

Este teste fecha o furo pelo lado de fora: varre `usp_mcp/**/*.py` inteiro, em
vez de esperar que alguém peça a fonte de cada módulo. A agulha é a palavra, e
não só o sentinela com sufixo, porque o texto do Moodle era "ESQUELETO." sem o
"-FASE2" e passaria pela constante. Offline, custa um `read_text` por arquivo,
e entra no gate junto com o resto.
"""
from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PACOTE = RAIZ / "usp_mcp"

AGULHA = "ESQUELETO"


def test_s1_nenhum_modulo_do_pacote_se_declara_esqueleto():
    arquivos = sorted(PACOTE.rglob("*.py"))
    # Anti-vácuo: um glob que não acha nada deixaria o teste verde sem ter
    # lido arquivo nenhum (mesma regra do U2 e do D1).
    assert len(arquivos) >= 3, f"o glob achou só {len(arquivos)} arquivo(s) em {PACOTE}"

    marcados = [
        str(a.relative_to(RAIZ))
        for a in arquivos
        if AGULHA in a.read_text(encoding="utf-8")
    ]
    assert not marcados, (
        "arquivo(s) do pacote ainda se declaram esqueleto:\n  "
        + "\n  ".join(marcados)
        + "\nO código existe e é exercitado pela suíte; um cabeçalho dizendo o "
        "contrário é a divergência de estado que o §9 de 31/08 registra como a "
        "mais cara. Reescreva o docstring dizendo o que o módulo é."
    )
