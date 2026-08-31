"""Camada 2 — projeção: transformar 528 kB de transporte em 7 kB de resposta.

O teste de custo aqui é três asserções, não uma, e o motivo está medido:
a RAZÃO de redução é instável (63,5× a 81,1× conforme a amostra), porque o
objeto `course` de 9,5 kB é repetido por evento e a razão acaba medindo quantos
eventos compartilham disciplina. O que é estável é o lado projetado — 201 a 205
bytes por evento em quatro amostras, ±2% — e a asserção categórica, que é a que
de fato trava a regressão.
"""
from __future__ import annotations

import json

import pytest

from usp_mcp.moodle import projecao

pytestmark = pytest.mark.contrato


def test_a_fixture_e_a_que_as_notas_mediram(eventos_brutos):
    """T11 — âncora. Se a fixture trocar, os números abaixo mudam de sentido."""
    assert len(eventos_brutos["events"]) == 35


def test_teto_absoluto_com_folga_declarada(eventos_brutos, caminho_fixture):
    """T12 — o custo projetado cabe no orçamento.

    Medido: 7.102 B para 35 eventos. Teto em 10.000 B — folga de ~40%, declarada
    aqui e não escondida, para absorver variação de composição da amostra.
    """
    r = projecao.projetar_eventos(eventos_brutos)
    bytes_projetados = len(json.dumps(r.como_dicionario(), ensure_ascii=False).encode())
    assert bytes_projetados <= 10_000, (
        f"projeção cresceu para {bytes_projetados} B (medido em 7.102 B). "
        "Algum campo gordo voltou para a saída."
    )


def test_bytes_por_evento_ficam_na_faixa_estavel(eventos_brutos):
    """T13 — a asserção que não envelhece.

    Quatro amostras dos mesmos eventos deram 205, 201, 201 e 203 B/evento. A
    faixa 180–230 tolera variação real de nome e URL sem tolerar um campo novo.
    """
    r = projecao.projetar_eventos(eventos_brutos)
    total = len(json.dumps(r.como_dicionario(), ensure_ascii=False).encode())
    por_evento = total / len(r.vencimentos)
    assert 180 <= por_evento <= 230, f"{por_evento:.0f} B/evento fora da faixa medida"


def test_nenhum_objeto_course_sobrevive(eventos_brutos):
    """T14 — a categórica, e a mais importante das três.

    88% do payload cru era um `course` de 9,5 kB repetido a cada evento. A única
    forma de o custo explodir de novo é a repetição voltar. Um teto numérico
    demora a perceber isso; esta asserção percebe na hora.
    """
    r = projecao.projetar_eventos(eventos_brutos)
    saida = json.dumps(r.como_dicionario(), ensure_ascii=False)
    for campo_gordo in ('"course"', '"summary"', '"courseimage"', '"description"'):
        assert campo_gordo not in saida, f"{campo_gordo} voltou para a projeção"


def test_cada_vencimento_tem_so_o_que_responde_a_pergunta(eventos_brutos):
    """T15 — o conjunto de chaves é exatamente o declarado."""
    r = projecao.projetar_eventos(eventos_brutos)
    assert r.vencimentos
    for v in r.vencimentos:
        assert set(v.como_dicionario()) == {"nome", "quando", "disciplina", "tipo", "url"}


def test_data_sai_em_horario_de_sao_paulo(eventos_brutos):
    """T16 — `timesort` é epoch int. Ler em UTC erra o dia por 3 horas.

    Uma entrega que vence 23h59 de domingo em São Paulo é 02h59 de segunda em
    UTC. "O que vence domingo" passaria a mentir.
    """
    r = projecao.projetar_eventos(eventos_brutos)
    for v in r.vencimentos:
        assert v.quando.tzinfo is not None, "data ingênua — sem fuso"
        assert v.quando.utcoffset().total_seconds() == -3 * 3600


def test_ordenado_por_vencimento_crescente(eventos_brutos):
    """T17 — o que vence primeiro aparece primeiro."""
    r = projecao.projetar_eventos(eventos_brutos)
    quandos = [v.quando for v in r.vencimentos]
    assert quandos == sorted(quandos)


def test_cobertura_e_declarada_na_saida(eventos_brutos):
    """T18 — Invariante 6: a saída diz o que ela NÃO sabe.

    Medido na Fase 1: o calendário só conhece assign (17) e quiz (18), eventtype
    só `due` e `close`. Prova presencial que o professor não modelou no Moodle
    não existe ali. Devolver a lista sem dizer isso mente por omissão.
    """
    r = projecao.projetar_eventos(eventos_brutos)
    assert r.cobertura
    assert "presencial" in r.cobertura.lower()
    assert set(v.tipo for v in r.vencimentos) <= {"assign", "quiz"}


def test_evento_sem_data_nao_vira_1970(eventos_brutos):
    """T19 — `timesort` ausente ou 0 é tratado, não convertido.

    A Fase 1 não viu nenhum `duedate = 0` no semestre corrente, mas o campo
    aceita 0 e epoch 0 vira 01/01/1970 — uma entrega "atrasada há 56 anos" no
    topo da lista.
    """
    quebrado = {"events": [dict(eventos_brutos["events"][0], timesort=0)]}
    r = projecao.projetar_eventos(quebrado)
    assert not r.vencimentos or r.vencimentos[0].quando is None
    assert r.sem_data == 1


def test_lista_vazia_e_resultado_legitimo_e_marcado(eventos_brutos):
    """T20 — zero evento é resposta, não falha — mas tem de ser distinguível."""
    r = projecao.projetar_eventos({"events": []})
    assert r.vencimentos == []
    assert r.vazio_por == "sem_eventos_no_periodo"
