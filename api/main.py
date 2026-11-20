"""API REST pública (sem autenticação) que serve o modelo de predição de doença cardíaca."""
import json
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import DadosPaciente, ResultadoPredicao

# O pipeline salvo referencia src.features.preparar, por isso o pacote src precisa estar importável.
PASTA_MODELOS = Path(__file__).resolve().parent.parent / "models"
CAMINHO_MODELO = PASTA_MODELOS / "modelo.joblib"
CAMINHO_METADADOS = PASTA_MODELOS / "metadata.json"

recursos = {}


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Carrega o modelo uma única vez na inicialização, e não a cada requisição."""
    recursos["modelo"] = joblib.load(CAMINHO_MODELO)
    recursos["metadados"] = json.loads(CAMINHO_METADADOS.read_text(encoding="utf-8"))
    yield
    recursos.clear()


app = FastAPI(
    title="API de Predição de Doença Cardíaca",
    description="Projeto acadêmico (TSI). Não possui validade clínica.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

# API pública e sem autenticação: aceita chamadas de qualquer origem.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", summary="Informações gerais da API")
def raiz():
    return {"servico": app.title, "documentacao": "/docs", "modelo": recursos["metadados"]["modelo"]}


@app.get("/health", summary="Verificação de saúde do serviço")
def verificar_saude():
    return {"status": "ok"}


@app.post("/predict", response_model=ResultadoPredicao, summary="Prevê doença cardíaca de um paciente")
def prever(paciente: DadosPaciente):
    tabela_paciente = pd.DataFrame([paciente.model_dump()])
    try:
        probabilidade = float(recursos["modelo"].predict_proba(tabela_paciente)[0, 1])
    except Exception as erro:  # falha inesperada do modelo vira erro 500 explícito
        raise HTTPException(status_code=500, detail=f"Falha ao executar o modelo: {erro}") from erro

    possui_doenca = int(probabilidade >= 0.5)
    return ResultadoPredicao(
        doenca_cardiaca=possui_doenca,
        probabilidade_doenca=round(probabilidade, 4),
        diagnostico="Alto risco de doença cardíaca" if possui_doenca else "Baixo risco de doença cardíaca",
    )
