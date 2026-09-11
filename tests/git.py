"""Um só lugar para a pergunta "este arquivo está ignorado pelo git?".

Existe porque a pergunta estava escrita em três lugares e nos dois da suíte
estava escrita errada — do mesmo jeito, com os mesmos dois defeitos somados.
Espalhada, ela não tinha onde ser consertada uma vez só.
"""
import pathlib
import subprocess


def esta_ignorado(caminho, raiz) -> bool:
    """Responde sim ou não; qualquer outra coisa vira erro, não resposta.

    Duas propriedades, cada uma curando um defeito medido (BUG-2):

    1. **Caminho relativo à raiz.** No macOS o nome de diretório acentuado
       fica no disco em NFD (`Programação`) e o que o Python
       entrega é NFC (`Programação`). O git compara byte a byte, não acha o
       prefixo do repositório e responde `rc=128 ... is outside repository` —
       para arquivo ignorado E versionado, indistintamente. Relativo à raiz
       não carrega o prefixo acentuado e responde certo nas duas formas.
    2. **`rc` fora de `{0,1}` é erro nosso.** O contrato do `check-ignore` é
       0=ignorado, 1=não ignorado; o resto é falha da ferramenta. Ler um 128
       como se fosse resposta de negócio é o Invariante 6 ao contrário —
       transforma "não consegui perguntar" em "está ignorado" e faz o teste
       acusar a causa errada, que foi exatamente o que custou o BUG-2.
    """
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(pathlib.Path(caminho).relative_to(raiz))],
        cwd=raiz,
        capture_output=True,
        text=True,
    )
    if r.returncode not in (0, 1):
        raise RuntimeError(
            f"git check-ignore não respondeu sim nem não (rc={r.returncode}): "
            f"{r.stderr.strip()}"
        )
    return r.returncode == 0
