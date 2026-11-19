"""Limpeza e engenharia de atributos do dataset Heart Failure Prediction.

Fica em um módulo próprio para ser usado tanto no notebook (treino) quanto na API
(predição), garantindo exatamente a mesma transformação nos dois lugares.
"""
import numpy as np
import pandas as pd

COLUNAS_ENTRADA = [
    "Age", "Sex", "ChestPainType", "RestingBP", "Cholesterol", "FastingBS",
    "RestingECG", "MaxHR", "ExerciseAngina", "Oldpeak", "ST_Slope",
]

NUMERICAS = ["Age", "RestingBP", "Cholesterol", "MaxHR", "Oldpeak",
             "FastingBS", "MaxHR_pct", "ColesterolAlto"]
CATEGORICAS = ["Sex", "ChestPainType", "RestingECG", "ExerciseAngina",
               "ST_Slope", "FaixaEtaria"]


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Trata zeros inválidos e cria 3 atributos novos.

    Novos atributos:
      - FaixaEtaria: faixa etária (categórica).
      - MaxHR_pct: MaxHR como fração da FC máxima teórica (220 - idade).
      - ColesterolAlto: 1 se colesterol >= 240 mg/dl, 0 caso contrário/ausente.
    """
    df = df[COLUNAS_ENTRADA].copy()
    # Colesterol e pressão iguais a 0 são impossíveis: viram valores ausentes
    # (a imputação é feita depois, dentro do Pipeline, só com dados de treino).
    df["Cholesterol"] = df["Cholesterol"].replace(0, np.nan)
    df["RestingBP"] = df["RestingBP"].replace(0, np.nan)

    df["FaixaEtaria"] = pd.cut(
        df["Age"], bins=[0, 40, 50, 60, 200],
        labels=["ate_40", "41_50", "51_60", "acima_60"],
    ).astype(str)
    df["MaxHR_pct"] = df["MaxHR"] / (220 - df["Age"])
    df["ColesterolAlto"] = (df["Cholesterol"] >= 240).astype(int)
    return df
