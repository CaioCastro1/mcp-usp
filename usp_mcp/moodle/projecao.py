"""Projeção: 528 kB de transporte viram ~7 kB de resposta.

Medido em notas/: `core_calendar_get_action_events_by_timesort` devolve um objeto
`course` de ~9,5 kB por evento (88% do payload cru), porque o Moodle repete a
ementa inteira da disciplina em cada item do calendário. A pergunta que este
módulo responde — "o que vence, quando, em que disciplina" — não precisa dessa
ementa; precisa de cinco campos por evento. Este módulo é a fronteira que separa
o transporte do que responde à pergunta (razão medida: 63,5x a 81,1x conforme a
amostra, porque `course` é repetido por evento e a razão mede quanta disciplina
é compartilhada; o lado estável é ~201-205 B/evento projetado).

Por que `activityname` e não `name`: `name` é a frase longa pronta para exibição
("X está marcado(a) para esta data"), redundante com `disciplina` + `tipo` e
mais cara em bytes. `activityname` é só o título da atividade.

Por que `url` e não `viewurl`: mesmo destino, `viewurl` é uma string mais longa.

Por que o fuso é literal -3 (`timezone(timedelta(hours=-3))`) e não um fuso
nomeado (`zoneinfo.ZoneInfo("America/Sao_Paulo")`): o Brasil não observa
horário de verão desde 2019, então o offset de São Paulo é -3h o ano inteiro
hoje — mas um fuso *nomeado* carrega histórico de transição e pode, a
depender da base tzdata, produzir um offset diferente em datas fora do
presente. O teste exige exatamente -3h; um literal fixo garante isso sem
depender de como a base de fusos do sistema está versionada.

Invariante 6 (erro legível vence silêncio; sem limite silencioso): a saída
sempre declara `cobertura` (o que o calendário do Moodle sabe e o que não sabe)
e `sem_data` (quantos eventos foram descartados por não terem uma data usável).
Lista vazia por ausência real de eventos é marcada em `vazio_por`, para não se
confundir com uma falha silenciosa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# Offset fixo do Brasil hoje (sem horário de verão desde 2019). Ver docstring
# do módulo para por que isto não é um fuso nomeado.
FUSO_SAO_PAULO = timezone(timedelta(hours=-3))

# O que o calendário do Moodle modela: só entrega de tarefa e tentativa de
# questionário geram evento de calendário. Prova presencial, apresentação
# oral etc. não passam por aqui porque o professor não lança isso no Moodle.
COBERTURA = (
    "Só entregas modeladas no e-Disciplinas (tarefa e questionário) aparecem "
    "aqui. Prova ou trabalho presencial que o professor não lançou lá não "
    "entra nesta lista."
)


@dataclass(frozen=True)
class Vencimento:
    """Um evento de calendário já reduzido ao que responde "o que vence"."""

    nome: str
    quando: datetime | None
    disciplina: str
    tipo: str
    url: str

    def como_dicionario(self) -> dict:
        # .isoformat() em vez do datetime cru: json.dumps não serializa
        # datetime sozinho, e o contrato pede string (ou None).
        return {
            "nome": self.nome,
            "quando": self.quando.isoformat() if self.quando is not None else None,
            "disciplina": self.disciplina,
            "tipo": self.tipo,
            "url": self.url,
        }


@dataclass(frozen=True)
class Resultado:
    """Saída de `projetar_eventos`: vencimentos mais o que a lista NÃO cobre."""

    vencimentos: list[Vencimento] = field(default_factory=list)
    cobertura: str = COBERTURA
    sem_data: int = 0
    vazio_por: str | None = None

    def como_dicionario(self) -> dict:
        return {
            "vencimentos": [v.como_dicionario() for v in self.vencimentos],
            "cobertura": self.cobertura,
            "sem_data": self.sem_data,
            "vazio_por": self.vazio_por,
        }


def data_de(carimbo: object) -> datetime | None:
    """Epoch do Moodle vira data só quando é um epoch positivo de verdade.

    Ausente, None, 0 ou não-inteiro (ex.: string) são tratados como "sem
    data", nunca como epoch 0 — que seria 1970 e criaria uma entrega
    "atrasada há 56 anos" no topo da lista (T19).

    **Pública desde 14/09/2026, e pelo mesmo motivo de `texto.formatar_data`.**
    Ela nasceu privada aqui (`_quando_de`), `ja_entreguei` precisou da mesma
    regra e escreveu a segunda cópia, e `disciplinas` seria a terceira — que é
    exatamente como as duas semânticas de casamento por nome nasceram e
    custaram o T83. O campo muda de nome em cada função do Moodle (`timesort`,
    `duedate`, `enddate`), a regra não.
    """
    if isinstance(carimbo, bool):  # bool é subclasse de int; não é epoch.
        return None
    if not isinstance(carimbo, int) or carimbo <= 0:
        return None
    return datetime.fromtimestamp(carimbo, tz=FUSO_SAO_PAULO)


def _quando_de(timesort: object) -> datetime | None:
    """O nome antigo, mantido porque `projetar_eventos` e os testes de T19 o
    chamam — a regra é uma só, e mora em `data_de`."""
    return data_de(timesort)


def projetar_eventos(bruto: dict) -> Resultado:
    """Reduz a resposta crua de `core_calendar_get_action_events_by_timesort`
    à lista de vencimentos que responde "o que vence e quando"."""
    eventos = bruto.get("events", [])

    if not eventos:
        return Resultado(vencimentos=[], sem_data=0, vazio_por="sem_eventos_no_periodo")

    vencimentos: list[Vencimento] = []
    sem_data = 0
    for evento in eventos:
        quando = _quando_de(evento.get("timesort"))
        if quando is None:
            sem_data += 1
            continue
        vencimentos.append(
            Vencimento(
                nome=evento.get("activityname", ""),
                quando=quando,
                disciplina=evento.get("course", {}).get("shortname", ""),
                tipo=evento.get("modulename", ""),
                url=evento.get("url", ""),
            )
        )

    vencimentos.sort(key=lambda v: v.quando)

    return Resultado(vencimentos=vencimentos, sem_data=sem_data, vazio_por=None)
