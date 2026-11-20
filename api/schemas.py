"""Contratos de entrada e saída da API de predição de doença cardíaca."""
from typing import Literal

from pydantic import BaseModel, Field


class DadosPaciente(BaseModel):
    """Os 11 atributos clínicos originais do dataset, validados por faixa e categoria."""

    Age: int = Field(..., ge=1, le=120, description="Idade em anos")
    Sex: Literal["M", "F"] = Field(..., description="Sexo: M (masculino) ou F (feminino)")
    ChestPainType: Literal["TA", "ATA", "NAP", "ASY"] = Field(
        ..., description="Tipo de dor no peito: TA, ATA, NAP ou ASY (assintomático)"
    )
    RestingBP: int = Field(..., ge=0, le=300, description="Pressão arterial em repouso (mm Hg)")
    Cholesterol: int = Field(..., ge=0, le=700, description="Colesterol sérico (mg/dl); 0 = não medido")
    FastingBS: Literal[0, 1] = Field(..., description="Glicemia em jejum > 120 mg/dl: 1 = sim, 0 = não")
    RestingECG: Literal["Normal", "ST", "LVH"] = Field(..., description="Eletrocardiograma em repouso")
    MaxHR: int = Field(..., ge=40, le=250, description="Frequência cardíaca máxima atingida")
    ExerciseAngina: Literal["Y", "N"] = Field(..., description="Angina induzida por exercício")
    Oldpeak: float = Field(..., ge=-3, le=10, description="Depressão do segmento ST induzida por exercício")
    ST_Slope: Literal["Up", "Flat", "Down"] = Field(..., description="Inclinação do segmento ST")

    model_config = {
        "json_schema_extra": {
            "example": {
                "Age": 58, "Sex": "M", "ChestPainType": "ASY", "RestingBP": 140,
                "Cholesterol": 0, "FastingBS": 1, "RestingECG": "Normal", "MaxHR": 110,
                "ExerciseAngina": "Y", "Oldpeak": 1.5, "ST_Slope": "Flat",
            }
        }
    }


class ResultadoPredicao(BaseModel):
    """Resposta da predição: classe prevista e a probabilidade associada."""

    doenca_cardiaca: Literal[0, 1] = Field(..., description="1 = doença cardíaca prevista, 0 = saudável")
    probabilidade_doenca: float = Field(..., description="Probabilidade (0 a 1) de doença cardíaca")
    diagnostico: str = Field(..., description="Texto legível do resultado")
