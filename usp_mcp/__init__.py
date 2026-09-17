"""usp-mcp — ferramentas para a vida acadêmica na USP. Projeto não-oficial.

Sem `server.py` nesta raiz, de propósito: o §6 do SPEC1.md separa entrypoint
local com credencial (Moodle, stdio) de servidor público cacheável (Jupiter,
RUCard). Cada um tem o seu, dentro do subpacote.
"""

from importlib.metadata import PackageNotFoundError, version as _versao_instalada

__all__ = ["VERSAO", "AGENTE"]


def _versao() -> str:
    """A versão do pacote instalado, perguntada em vez de repetida.

    Ela é declarada num lugar só, o `pyproject.toml`, e até 17/09/2026 era
    **copiada à mão** para dentro do User-Agent dos dois clientes. As cópias
    ficaram em `0.1` e o pacote foi para `1.0.0` em 15/09 sem que nada
    reclamasse: o número não quebra chamada nenhuma, a USP não o lê, e por isso
    a divergência não tinha como aparecer. É a forma mais calada de mentira que
    este projeto guarda — a única coisa que ele diz sobre si mesmo do lado de
    lá, desatualizada.

    Fora de instalação (checkout solto, sem `pip install -e`) não há metadado
    para perguntar. Nesse caso o agente diz que não sabe, em vez de chutar um
    número: quem administra o sistema do outro lado prefere um identificador
    honesto a um errado.
    """
    try:
        return _versao_instalada("usp-mcp")
    except PackageNotFoundError:
        return "0+sem-instalacao"


VERSAO = _versao()

# Identificável e com contato, como o §9 do recon do Jupiter recomenda: quem
# administra o sistema tem que conseguir saber quem está batendo, e falar com
# alguém. Um só aqui, e não um por cliente, porque dois literais iguais em
# arquivos diferentes divergem — foi assim que a versão envelheceu.
AGENTE = f"usp-mcp/{VERSAO} (nao-oficial; +https://github.com/CaioCastro1/usp-mcp)"
