"""Testes de integração da API usando o modelo real exportado pelo notebook."""
from fastapi.testclient import TestClient

from api.main import app

PACIENTE_ALTO_RISCO = {
    "Age": 58, "Sex": "M", "ChestPainType": "ASY", "RestingBP": 140, "Cholesterol": 0,
    "FastingBS": 1, "RestingECG": "Normal", "MaxHR": 110, "ExerciseAngina": "Y",
    "Oldpeak": 1.5, "ST_Slope": "Flat",
}
PACIENTE_BAIXO_RISCO = {
    "Age": 35, "Sex": "F", "ChestPainType": "ATA", "RestingBP": 110, "Cholesterol": 180,
    "FastingBS": 0, "RestingECG": "Normal", "MaxHR": 170, "ExerciseAngina": "N",
    "Oldpeak": 0.0, "ST_Slope": "Up",
}


def test_saude_retorna_ok():
    with TestClient(app) as cliente:
        assert cliente.get("/health").json() == {"status": "ok"}


def test_predicao_paciente_alto_risco():
    with TestClient(app) as cliente:
        resposta = cliente.post("/predict", json=PACIENTE_ALTO_RISCO)
    assert resposta.status_code == 200
    assert resposta.json()["doenca_cardiaca"] == 1


def test_predicao_paciente_baixo_risco():
    with TestClient(app) as cliente:
        resposta = cliente.post("/predict", json=PACIENTE_BAIXO_RISCO)
    assert resposta.status_code == 200
    assert resposta.json()["doenca_cardiaca"] == 0


def test_categoria_invalida_retorna_422():
    paciente_invalido = {**PACIENTE_ALTO_RISCO, "Sex": "X"}
    with TestClient(app) as cliente:
        assert cliente.post("/predict", json=paciente_invalido).status_code == 422
