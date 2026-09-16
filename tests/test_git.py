"""G1-G5: o único lugar que pergunta ao git "está ignorado?" responde certo.

Os 12 vermelhos do BUG-2 não eram sobre `.gitignore` coisa nenhuma: eram um
`rc=128` ("is outside repository", porque o diretório acentuado está em NFD no
disco e o Python entrega NFC) lido como se fosse "sim, está ignorado". A suíte
acusava a causa errada, e num checkout ASCII ficava verde — o mesmo commit,
duas respostas, dependendo do nome de uma pasta acima do repositório.

Por isso a bateria mora aqui, ao lado do helper, e não dentro de uma trilha:
o que ela protege é `tests/git.py`, que agora é o único a saber falar com o
subcomando do git. G3 é o teste que reprovava; G5 é o que impede a volta.

Nem esta docstring escreve o nome do subcomando por extenso: G5 varre o fonte
de `tests/` inteiro, e este arquivo está dentro da varredura. Ver a nota no G5.
"""
import ast
import os
import pathlib
import shutil
import stat
import subprocess
import unicodedata

import pytest

from tests.git import esta_ignorado

pytestmark = pytest.mark.politica

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# Versionado (dado público do Jupiter) e cru gitignorado (dado pessoal, §3.3).
# O segundo NÃO existe em worktree novo — e não precisa: o git responde sobre
# o caminho, não sobre o arquivo. É o que o gate já faz na checagem 2.
VERSIONADO = RAIZ / "fixtures" / "jupiter" / "dwr-pubObterDisciplina-PSI3323.txt"
IGNORADO = RAIZ / "fixtures" / "moodle" / "raw" / "action_events.json"


def test_g1_arquivo_versionado_nao_esta_ignorado():
    assert esta_ignorado(VERSIONADO, RAIZ) is False, (
        f"{VERSIONADO.name} é fixture versionada da fatia e apareceu como "
        "ignorada. Ou o .gitignore engordou demais, ou a pergunta voltou a ser "
        "feita de um jeito que confunde erro com resposta."
    )


def test_g2_arquivo_ignorado_e_reconhecido():
    # É a checagem 2 do gate.sh, agora com asserção dentro da suíte: lá ela
    # protege o commit, aqui ela protege o helper — se `esta_ignorado` passasse
    # a devolver False para tudo, G1 sozinho continuaria verde.
    assert esta_ignorado(IGNORADO, RAIZ) is True, (
        "fixtures/moodle/raw/ deixou de ser ignorada (§3.3) — é o cru com dado "
        "pessoal não higienizado."
    )


def test_g3_caminho_com_acento_nao_vira_falso_positivo(tmp_path):
    """O teste que reprovava. Repositório de verdade, dentro de pasta NFD.

    O APFS é insensível a normalização: se um `ação` em NFC já existisse ali,
    criar o NFD reusaria a entrada antiga e o teste ficaria verde sem ter
    reproduzido nada. Por isso o diretório acentuado é criado do zero, em NFD
    explícito, dentro de um `tmp_path` que ninguém tocou — e o que se passa ao
    helper é a forma NFC, que é a que o `pathlib` entrega na máquina real.

    Offline por construção: `git init` local, nenhuma rede. Limpa a árvore que
    criou no `finally`, sem depender da retenção do `tmp_path`.
    """
    acentuado = tmp_path / unicodedata.normalize("NFD", "ação")
    repo = acentuado / "repo"
    try:
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / ".gitignore").write_text("cru/\n", encoding="utf-8")
        (repo / "cru").mkdir()
        (repo / "cru" / "bruto.json").write_text("{}", encoding="utf-8")
        (repo / "fixture.txt").write_text("dado público", encoding="utf-8")

        # A raiz do jeito que o Python a entrega: NFC. No disco ela está em NFD.
        raiz_nfc = pathlib.Path(unicodedata.normalize("NFC", str(repo)))
        assert str(raiz_nfc) != str(repo), (
            "o diretório não ficou em NFD no disco — sem isso este teste não "
            "reproduz o BUG-2 e passaria por engano"
        )

        # O BUG-2 exige um sistema de arquivos INSENSÍVEL a normalização: é ele
        # que faz a mesma pasta atender pelas duas grafias, e é daí que vem o
        # `rc=128` que o helper tinha de aprender a não ler como "ignorado". No
        # ext4 as duas grafias são duas pastas, a de NFC não existe, e o que se
        # mediria aqui seria outra coisa — um caminho ausente, não o bug.
        #
        # A checagem é empírica e não por nome de sistema operacional, porque o
        # que decide é o sistema de ARQUIVOS: um volume ext4 montado num Mac
        # separaria as duas grafias, e um APFS não separa em máquina nenhuma.
        if not raiz_nfc.exists():
            pytest.skip(
                "este sistema de arquivos separa NFD de NFC, então as duas "
                "grafias são dois diretórios e o BUG-2 não tem como acontecer "
                "aqui. Não é cobertura perdida por descuido: o defeito é de "
                "sistema insensível a normalização (APFS, e o NTFS por outro "
                "caminho), e é lá que este teste precisa rodar. O G4 e o G5, "
                "que guardam o tratamento de rc inesperado e a rota única para "
                "o subcomando, rodam em qualquer sistema e continuam valendo."
            )

        assert esta_ignorado(raiz_nfc / "fixture.txt", raiz_nfc) is False
        assert esta_ignorado(raiz_nfc / "cru" / "bruto.json", raiz_nfc) is True
    finally:
        shutil.rmtree(acentuado, ignore_errors=True)


def test_g4_rc_inesperado_vira_erro_e_nao_resposta(tmp_path, monkeypatch):
    """`rc` que não é 0 nem 1 não pode virar "está ignorado" calado.

    Um `git` de mentira no PATH devolvendo 128 é o jeito determinístico de
    provar isso: o 128 real depende de um checkout acentuado, e a asserção não
    pode depender de onde a suíte foi clonada — foi justamente essa dependência
    que fez o bug existir num lugar e não no outro.
    """
    falso = tmp_path / "bin"
    falso.mkdir()
    (falso / "git").write_text("#!/bin/sh\necho 'fatal: de mentira' >&2\nexit 128\n")
    (falso / "git").chmod(falso.joinpath("git").stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{falso}{os.pathsep}{os.environ['PATH']}")

    with pytest.raises(RuntimeError) as e:
        esta_ignorado(VERSIONADO, RAIZ)
    assert "128" in str(e.value), (
        f"o erro tem que citar o rc para não mandar a próxima sessão adivinhar: "
        f"{e.value}"
    )


def test_g5_nenhuma_chamada_a_check_ignore_usa_caminho_absoluto():
    """A pergunta mora em UM lugar — este é o teste que impede a volta.

    Procura a agulha só onde ela é CHAMADA: dentro de uma lista de argumentos
    de `subprocess`. A primeira versão varria o texto inteiro do arquivo e
    reprovava `tests/test_gate.py`, que só cita o subcomando numa docstring
    explicando por que um diretório copiado à mão não é repositório — prosa
    não fala com o git. Uma regra que proíbe documentar a coisa que ela
    protege é uma regra que alguém desliga; esta olha a árvore.

    A agulha continua montada por concatenação: escrita inteira, o literal
    apareceria no fonte deste arquivo e a varredura textual de quem vier
    depois voltaria a se auto-acusar.
    """
    agulha = "check-" + "ignore"
    permitido = RAIZ / "tests" / "git.py"

    reincidentes = []
    for fonte in sorted(RAIZ.glob("tests/**/*.py")):
        if fonte == permitido:
            continue
        texto = fonte.read_text(encoding="utf-8")
        if agulha not in texto:
            continue  # nem cita: não há o que examinar
        arvore = ast.parse(texto, filename=str(fonte))
        for no in ast.walk(arvore):
            # `subprocess.run(["git", "check-ignore", ...])` e parentes: o que
            # importa é o literal estar numa sequência de argumentos, não a
            # função ter um nome específico — `run`, `check_output` e um
            # wrapper local caem todos aqui.
            if not isinstance(no, (ast.List, ast.Tuple)):
                continue
            if any(
                isinstance(e, ast.Constant) and e.value == agulha
                for e in no.elts
            ):
                reincidentes.append(fonte.relative_to(RAIZ))
                break

    assert reincidentes == [], (
        f"{[str(p) for p in reincidentes]} voltaram a falar com o git direto. "
        "Use tests.git.esta_ignorado: fora dele a chamada nasce com caminho "
        "absoluto (rc=128 em pasta acentuada) e com o rc de erro lido como "
        "resposta de negócio — os dois defeitos do BUG-2."
    )
