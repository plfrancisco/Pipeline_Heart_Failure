# Pipeline de Ciência de Dados — Heart Failure Prediction

Projeto final: pipeline automatizado de análise de dados para prever doença cardíaca
(dataset *Heart Failure Prediction*, 918 pacientes, 11 atributos clínicos).

**Integrantes:** Pedro Lucas Francisco, Nathalia Rodrigues, Pedro Henrique Cavalcante

> Projeto acadêmico, sem validade para uso clínico.

## Estrutura
| Pasta | Conteúdo |
|---|---|
| `data/` | dataset `heart.csv` |
| `notebooks/` | `pipeline.ipynb`: pré-processamento, atributos novos, Rank/PCA, modelos, otimização e exportação |
| `src/` | `features.py`: limpeza e engenharia de atributos, compartilhada entre treino e API |
| `models/` | modelo exportado (`modelo.joblib`) e tabelas de métricas e hiperparâmetros |
| `api/` | API FastAPI pública, sem autenticação |
| `relatorio/` | figuras do notebook, relatório em PDF e em Word (ABNT) e os scripts que os geram |
| `tests/` | testes da API |

## Resultados resumidos
Modelo escolhido: **Regressão Logística** (maior F1 em validação cruzada), otimizada com `GridSearchCV`.
Detalhes e hiperparâmetros em `models/relatorio_hiperparametros.json`.

## Como reproduzir o treino
```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Linux/Mac: .venv/bin/pip
.venv/Scripts/jupyter nbconvert --to notebook --execute --inplace notebooks/pipeline.ipynb
```

## Relatório
`relatorio/relatorio_final.pdf` (ABNT, 12 páginas com a capa) e `relatorio/relatorio_final.docx` são gerados por
`relatorio/gerar_relatorio.py` e `relatorio/gerar_docx.py`. Antes de gerar de novo, preencha os dados da capa
(instituição, disciplina, professor e cidade) no topo de `gerar_relatorio.py`. O PDF usa o Microsoft Edge.

## API
Execução local com Docker:
```bash
docker build -t heart-api .
docker run -p 8000:8000 heart-api
```
Testes automáticos: `pytest` (rodam onde o `pydantic` instala normalmente, ou dentro do container).

Documentação interativa (Swagger): http://localhost:8000/docs

Exemplo de predição:
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"Age":58,"Sex":"M","ChestPainType":"ASY","RestingBP":140,"Cholesterol":0,"FastingBS":1,"RestingECG":"Normal","MaxHR":110,"ExerciseAngina":"Y","Oldpeak":1.5,"ST_Slope":"Flat"}'
```
Resposta: `{"doenca_cardiaca":1,"probabilidade_doenca":0.9769,"diagnostico":"Alto risco de doença cardíaca"}`

## Deploy (Render)
1. Em render.com, criar um **Web Service** conectado a este repositório do GitHub.
2. Ambiente: **Docker** (o `Dockerfile` da raiz é detectado automaticamente).
3. Plano gratuito, sem variáveis de ambiente (a porta vem da variável `PORT`).
4. A API fica pública em `https://<nome>.onrender.com`, com `/docs` e `/predict`.
