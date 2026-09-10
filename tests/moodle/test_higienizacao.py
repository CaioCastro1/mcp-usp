"""Camada 2 — a fixture versionada é segura e reproduzível.

Estes são os únicos testes da suíte que passam HOJE: `scripts/higienizar.py`
existe. Servem de piso — se eles ficarem vermelhos, nenhum outro teste significa
coisa alguma, porque o insumo deixou de ser confiável.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.git import esta_ignorado
from tests.moodle.conftest import CRU_EVENTOS, RAIZ

pytestmark = pytest.mark.contrato

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def test_a_fixture_versionada_nao_tem_email(caminho_fixture):
    """T45 — §3.3 e Invariante 3."""
    texto = caminho_fixture.read_text(encoding="utf-8")
    if "@" not in texto:  # o regex é quadrático em texto longo sem arroba
        return
    for m in RE_EMAIL.findall(texto):
        assert m.endswith("exemplo.invalid"), f"e-mail real na fixture: domínio de {m}"


def test_a_fixture_versionada_nao_contem_segredo_do_env(caminho_fixture):
    """T46 — a asserção nunca imprime o valor que procura."""
    texto = caminho_fixture.read_text(encoding="utf-8")
    vazados = [
        nome
        for nome in ("MOODLE_TOKEN", "MOODLE_USERID", "RUCARD_HASH")
        if (v := os.environ.get(nome)) and len(v) >= 4 and v in texto
    ]
    assert vazados == [], f"segredo presente na fixture: {vazados}"


def test_a_fixture_esta_no_git_e_o_cru_nao(caminho_fixture):
    """T47 — a separação do .gitignore é o que torna a suíte portátil."""
    def rastreado(p: Path) -> bool:
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(p.relative_to(RAIZ))],
            cwd=RAIZ, capture_output=True,
        )
        return r.returncode == 0
    assert rastreado(caminho_fixture), "fixture higienizada fora do git"
    # A chamada era relativa e por isso escapou do BUG-2 — mas passa pelo helper
    # do mesmo jeito: a regra é UM lugar que sabe perguntar (G5), não "os que
    # estavam errados". Sobrando um segundo lugar certo, o próximo call site
    # copia dele e o absoluto volta.
    assert esta_ignorado(
        RAIZ / "fixtures" / "moodle" / "raw" / "action_events.json", RAIZ
    ), "fixtures/moodle/raw/ deixou de ser ignorada"


def test_higienizar_e_estavel(tmp_path):
    """T48 — mesmo id → mesmo valor falso (§3.3), duas execuções byte-idênticas.

    Sem isso, cada regeneração produz um diff gigante e a fixture vira ruído no
    histórico.
    """
    if not CRU_EVENTOS.exists():
        pytest.skip(f"cru ausente ({CRU_EVENTOS}) — só existe na máquina do dono")
    saidas = []
    for i in range(2):
        destino = tmp_path / f"s{i}.json"
        subprocess.run(
            [sys.executable, "scripts/higienizar.py", str(CRU_EVENTOS), str(destino)],
            cwd=RAIZ, check=True, capture_output=True,
        )
        saidas.append(destino.read_bytes())
    assert saidas[0] == saidas[1]


def test_higienizar_preserva_forma_e_comprimento(tmp_path):
    """T49 — o requisito que o §3.3 não tem e o teste de custo exige.

    Se o higienizador encolher os textos, a fixture deixa de sustentar a
    asserção de bytes/evento — trocar um `summary` de 9 kB por uma frase curta
    apagaria justamente o custo que a projeção existe para resolver.
    """
    if not CRU_EVENTOS.exists():
        pytest.skip(f"cru ausente ({CRU_EVENTOS}) — só existe na máquina do dono")
    destino = tmp_path / "s.json"
    subprocess.run(
        [sys.executable, "scripts/higienizar.py", str(CRU_EVENTOS), str(destino)],
        cwd=RAIZ, check=True, capture_output=True,
    )
    cru = json.loads(CRU_EVENTOS.read_text(encoding="utf-8"))
    lim = json.loads(destino.read_text(encoding="utf-8"))

    def forma(n):
        if isinstance(n, dict):
            return {k: forma(v) for k, v in n.items()}
        if isinstance(n, list):
            return ("lista", len(n), [forma(v) for v in n[:1]])
        return type(n).__name__

    assert forma(cru) == forma(lim)
    a, b = cru["events"][0]["course"], lim["events"][0]["course"]
    assert len(b["summary"].encode()) == len(a["summary"].encode())
    assert len(b["fullname"].encode()) == len(a["fullname"].encode())
