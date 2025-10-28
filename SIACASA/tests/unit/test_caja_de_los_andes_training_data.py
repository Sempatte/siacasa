import csv
from pathlib import Path
from typing import List

import pytest


def _load_training_csv() -> List[dict]:
    data_path = (
        Path(__file__)
        .resolve()
        .parents[2]
        / "admin_panel"
        / "training"
        / "demo_data"
        / "caja_de_los_andes_faq.csv"
    )
    with data_path.open() as handler:
        return list(csv.DictReader(handler))


@pytest.fixture(scope="module")
def caja_andes_rows() -> List[dict]:
    return _load_training_csv()


MANUAL_CASES = [
    ("CP001", ["horario", "atención"], ["lunes a viernes", "sábados"]),
    ("CP002", ["horario", "feriado"], ["feriados nacionales", "0800-52777"]),
    ("CP003", ["agencia", "x"], ["jr. principal 123", "mapa"]),
    ("CP004", ["rc-12345"], ["en proceso", "48 horas"]),
    ("CP005", ["rc-12345", "resol"], ["resolvió", "15/05/2024"]),
    ("CP006", ["bloquear", "noche"], ["24/7", "0800-52777"]),
    ("CP007", ["bloquear", "oficina"], ["agente humano", "derivo"]),
    ("CP008", ["blabla"], ["no entendí", "reformularla"]),
    ("CP009", ["xyz", "abc"], ["no entendí", "agencias"]),
    ("CP009A", ["explícame"], ["ejemplos", "horarios"]),
    ("CP010", ["opciones", "crédito"], ["créditos personales", "microcréditos"]),
    ("CP011", ["saldo"], ["app", "*777#"]),
    ("CP012", ["transferencia", "nacional"], ["transferencias nacionales", "token"]),
    ("CP013", ["transferencia", "internacional"], ["swift", "iban"]),
    ("CP014", ["preguntas", "frecuentes"], ["preguntas frecuentes", "enlace"]),
    ("CP015", ["hablar", "agente"], ["ticket", "agente humano"]),
    ("CP016", ["consulta", "no resolviste"], ["guías", "preguntas frecuentes"]),
    ("CP017", ["requisitos", "préstamo", "personal"], ["dni", "ingresos"]),
    ("CP018", ["número", "atención"], ["0800-52777", "whatsapp"]),
    ("CP019", ["canales", "digitales"], ["banca web", "whatsapp"]),
    ("CP020", ["fraudes", "digitales"], ["doble autenticación", "0800-52777"]),
    ("CP021", ["encuesta", "satisfacción"], ["encuesta", "1 al 5"]),
    ("CP022", ["pagar", "préstamo"], ["cronograma", "sms"]),
    ("CP023", ["promociones"], ["tasas", "10%"]),
    ("CP024", ["tarjeta", "débito"], ["dni", "s/ 20"]),
    ("CP025", ["perdí", "tarjeta"], ["0800-52777", "reposición"]),
    ("CP026", ["estado de cuenta"], ["pdf", "banca digital"]),
    ("CP027", ["presento", "reclamo"], ["libro de reclamaciones", "código"]),
    ("CP028", ["actualizo", "datos"], ["dni", "24 horas"]),
    ("CP029", ["cuesta", "cuenta"], ["s/ 3", "s/ 500"]),
    ("CP030", ["plazo fijo"], ["6.5%", "penalidad"]),
    ("CP031", ["feriado", "atienden"], ["cajeros automáticos", "app"]),
    ("CP032", ["activo", "banca digital"], ["código sms", "5 minutos"]),
    ("CP041", ["cuenta", "ahorros"], ["dni", "depósito mínimo"]),
]


@pytest.mark.parametrize(
    "case_id, query_keywords, response_keywords",
    MANUAL_CASES,
)
def test_manual_case_present_in_training_csv(caja_andes_rows, case_id, query_keywords, response_keywords):
    """
    Verifica que cada caso de prueba manual tenga soporte en los archivos de entrenamiento
    que se cargan desde el panel de administración para Caja de los Andes.
    """
    matches = []
    for row in caja_andes_rows:
        query = row["pregunta"].lower()
        response = row["respuesta"].lower()

        if all(keyword in query for keyword in query_keywords) and all(
            keyword in response for keyword in response_keywords
        ):
            matches.append(row)

    assert matches, f"No se encontró cobertura en los datos de entrenamiento para {case_id}"
