"""Gera o relatório em PDF seguindo a ABNT (NBR 14724, 6024, 6027, 6028, 10520, 6023).

Uso: python relatorio/gerar_relatorio.py <pasta_temporaria> relatorio/relatorio_final.pdf
Antes, preencha os dados da capa (INSTITUICAO, DISCIPLINA, PROFESSOR, CIDADE) abaixo.
A capa é um PDF à parte (não é contada nem numerada); o corpo é renderizado duas vezes para
obter as páginas do sumário.
"""
import re
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

PASTA_TRABALHO = Path(sys.argv[1])
CAMINHO_SAIDA = Path(sys.argv[2])
NAVEGADOR = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PASTA_FIGURAS = Path(__file__).resolve().parent / "figuras"

# Dados da capa e da folha de rosto: preencher os colchetes com os dados reais do grupo.
INSTITUICAO = "[NOME DA INSTITUIÇÃO]"
CURSO = "Curso de TSI"
DISCIPLINA = "[DISCIPLINA]"
PROFESSOR = "[NOME DO PROFESSOR]"
CIDADE = "[CIDADE]"
ANO = "2026"
AUTORES = ["Pedro Lucas Francisco", "Nathalia Rodrigues", "Pedro Henrique Cavalcante"]
TITULO = "Pipeline de ciência de dados para predição de doença cardíaca"
SUBTITULO = "Projeto final: pipeline automatizado de análise de dados"

CSS = """
@page { size: A4; margin: 3cm 2cm 2cm 3cm; }
@page capa { margin: 3cm 2cm 2cm 3cm; }
@page pre { margin: 3cm 2cm 2cm 3cm; }
@page tex { margin: 3cm 2cm 2cm 3cm;
  @top-right { content: counter(page); font-family: 'Times New Roman', serif; font-size: 12pt;
               vertical-align: top; padding-top: 1.1cm; } }
html { font-family: 'Times New Roman', Times, serif; font-size: 12pt; color: #000; }
body { margin: 0; line-height: 1.5; text-align: justify; }
.capa { page: capa; } .pre { page: pre; } .tex { page: tex; }
.quebra { break-before: page; }
p { margin: 0; }
p.texto { text-indent: 1.25cm; }
.centro { text-align: center; }
.capa-bloco { display: flex; flex-direction: column; justify-content: space-between; height: 24.6cm; }
.capa-topo, .capa-meio, .capa-base { text-align: center; line-height: 1.5; }
.capa-meio { margin-top: 0; }
.natureza { margin-left: 8cm; text-align: justify; line-height: 1.0; font-size: 12pt; }
h1.sec { font-size: 12pt; font-weight: bold; text-transform: uppercase; margin: 18pt 0 18pt 0;
         text-align: left; break-after: avoid; }
h2.sub { font-size: 12pt; font-weight: bold; margin: 18pt 0 18pt 0; text-align: left; break-after: avoid; }
h1.sem-numero { font-size: 12pt; font-weight: bold; text-transform: uppercase; text-align: center;
                margin: 0 0 18pt 0; break-after: avoid; }
.resumo { line-height: 1.0; text-align: justify; }
.palavras { line-height: 1.0; margin-top: 12pt; text-align: justify; }
ol.alineas { list-style: none; counter-reset: alinea; margin: 0 0 0 1.25cm; padding: 0; }
ol.alineas li { counter-increment: alinea; padding-left: 0.75cm; text-indent: -0.75cm; }
ol.alineas li::before { content: counter(alinea, lower-alpha) ") "; display: inline-block; width: 0.75cm; text-indent: 0; }
.legenda { font-size: 10pt; line-height: 1.15; text-align: left; margin: 12pt 0 4pt 0; break-after: avoid; }
.fonte { font-size: 10pt; line-height: 1.15; text-align: left; margin: 4pt 0 12pt 0; }
table.tab { border-collapse: collapse; width: 100%; font-size: 10pt; line-height: 1.15; break-inside: avoid;
            border-top: 1.2pt solid #000; border-bottom: 1.2pt solid #000; }
table.tab th { border-bottom: 0.7pt solid #000; text-align: left; padding: 2pt 4pt; font-weight: bold; }
table.tab td { padding: 2pt 4pt; text-align: left; }
.fig { text-align: center; break-inside: avoid; }
.fig img { max-width: 15.5cm; max-height: 7.5cm; }
.sumario-linha { display: flex; align-items: baseline; line-height: 1.5; text-align: left; }
.sumario-linha .rotulo { flex: 0 1 auto; }
.sumario-linha .pontos { flex: 1 1 auto; border-bottom: 1.3pt dotted #000; margin: 0 4pt; transform: translateY(-3pt); }
.sumario-linha .num { flex: 0 0 auto; }
.nivel1 { font-weight: bold; text-transform: uppercase; }
.nivel2 { padding-left: 0.6cm; }
.refs p { text-align: left; line-height: 1.0; margin-bottom: 12pt; }
i.est { font-style: italic; }
"""


def ident(texto):
    """Identificadores de código e estrangeirismos vão em itálico (ABNT)."""
    return f'<i class="est">{texto}</i>'


def tabela(cabecalho, linhas):
    html = '<table class="tab"><thead><tr>' + "".join(f"<th>{c}</th>" for c in cabecalho) + "</tr></thead><tbody>"
    for linha in linhas:
        html += "<tr>" + "".join(f"<td>{valor}</td>" for valor in linha) + "</tr>"
    return html + "</tbody></table>"


def legenda(texto):
    return f'<p class="legenda"><b>{texto}</b></p>'


def fonte(texto="Fonte: elaborado pelos autores (2026)."):
    return f'<p class="fonte">{texto}</p>'


def figura(arquivo, alternativo):
    return f'<div class="fig"><img src="{Path(arquivo).as_uri()}" alt="{alternativo}"></div>'


def paragrafo(texto):
    return f'<p class="texto">{texto}</p>'


def secao(numero, titulo):
    return f'<h1 class="sec">{numero} {titulo}</h1>'


def subsecao(numero, titulo):
    return f'<h2 class="sub">{numero} {titulo}</h2>'


METRICAS = ["Acurácia", "Precisão", "Recall", "F1", "AUC"]

# Títulos que entram no sumário: (nível, rótulo)
TITULOS = [
    (1, "1 INTRODUÇÃO"), (1, "2 OBJETIVO"), (1, "3 MATERIAL E MÉTODOS"),
    (2, "3.1 Dados e pré-processamento"), (2, "3.2 Engenharia de atributos"),
    (2, "3.3 Redução de dimensionalidade"), (2, "3.4 Modelos e hiperparâmetros padrão"),
    (2, "3.5 Avaliação e otimização"), (2, "3.6 Disponibilização"),
    (1, "4 RESULTADOS E DISCUSSÃO"), (2, "4.1 Comparação dos modelos"),
    (2, "4.2 Otimização de hiperparâmetros"), (2, "4.3 Atributos mais importantes"),
    (1, "5 CONSIDERAÇÕES FINAIS"), (1, "REFERÊNCIAS"),
]


def pagina_capa():
    autores = "<br>".join(a.upper() for a in AUTORES)
    return f"""
<div class="capa"><div class="capa-bloco">
  <div class="capa-topo"><b>{INSTITUICAO.upper() if not INSTITUICAO.startswith('[') else INSTITUICAO}</b><br>{CURSO.upper()}</div>
  <div class="capa-meio"><b>{autores}</b></div>
  <div class="capa-meio"><b>{TITULO.upper()}</b><br>{SUBTITULO}</div>
  <div class="capa-base">{CIDADE}<br>{ANO}</div>
</div></div>"""


def folha_de_rosto():
    autores = "<br>".join(a.upper() for a in AUTORES)
    return f"""
<div class="pre"><div class="capa-bloco">
  <div class="capa-meio"><b>{autores}</b></div>
  <div class="capa-meio"><b>{TITULO.upper()}</b><br>{SUBTITULO}</div>
  <div class="natureza">Relatório do projeto final apresentado à disciplina {DISCIPLINA} do {CURSO}, como requisito parcial de avaliação.<br><br>Professor: {PROFESSOR}</div>
  <div class="capa-base">{CIDADE}<br>{ANO}</div>
</div></div>"""


RESUMO = ("Este trabalho apresenta um pipeline automatizado de ciência de dados para prever a presença de doença "
          "cardíaca a partir de 11 atributos clínicos de 918 pacientes. Foram realizados o pré-processamento dos dados, "
          "a criação de três atributos, a redução de dimensionalidade por Rank e PCA, a comparação de Regressão "
          "Logística, Random Forest e KNN, a otimização de hiperparâmetros com " + ident("GridSearchCV") +
          " e a exportação do modelo em uma API REST. A avaliação combinou validação cruzada de cinco partições e um "
          "conjunto de teste com 184 pacientes. A Regressão Logística apresentou o melhor desempenho no teste, com "
          "89,67% de acurácia, 92,16% de recall e 90,82% de F1 após a otimização, ganho pequeno em relação ao modelo "
          "com hiperparâmetros padrão (F1 de 90,73%). Os atributos mais relevantes foram a inclinação do segmento ST, "
          "o tipo de dor no peito e a angina induzida por exercício. O modelo tem finalidade exclusivamente "
          "acadêmica e não possui validade clínica.")
ABSTRACT = ("This paper presents an automated data science pipeline to predict the presence of heart disease from "
            "11 clinical attributes of 918 patients. The steps were data preprocessing, creation of three new "
            "features, dimensionality reduction with Rank and PCA, comparison of Logistic Regression, Random Forest "
            "and KNN, hyperparameter tuning with " + ident("GridSearchCV") + " and export of the model as a REST API. "
            "Evaluation combined five-fold cross-validation and a test set of 184 patients. Logistic Regression "
            "achieved the best performance on the test set, with 89.67% accuracy, 92.16% recall and 90.82% F1-score "
            "after tuning, a small gain over the default model (F1-score of 90.73%). The most relevant attributes "
            "were the ST segment slope, the chest pain type and exercise-induced angina. The model is for academic "
            "purposes only and has no clinical validity.")


def pre_textuais(numeros_paginas):
    resumo = f"""
<div class="pre quebra"><h1 class="sem-numero">Resumo</h1>
<p class="resumo">{RESUMO}</p>
<p class="palavras"><b>Palavras-chave:</b> aprendizado de máquina. Doença cardíaca. Regressão logística. Seleção de atributos. API.</p></div>
<div class="pre quebra"><h1 class="sem-numero">Abstract</h1>
<p class="resumo">{ABSTRACT}</p>
<p class="palavras"><b>Keywords:</b> machine learning. Heart disease. Logistic regression. Feature selection. API.</p></div>"""
    linhas = ""
    for nivel, rotulo in TITULOS:
        pagina = numeros_paginas.get(rotulo, "")
        linhas += (f'<div class="sumario-linha nivel{nivel}"><span class="rotulo">{rotulo}</span>'
                   f'<span class="pontos"></span><span class="num">{pagina}</span></div>')
    sumario = f'<div class="pre quebra"><h1 class="sem-numero">Sumário</h1>{linhas}</div>'
    return resumo + sumario


def parte_textual():
    p = []
    p.append('<div class="tex quebra">')
    p.append(secao("1", "Introdução"))
    p.append(paragrafo("As doenças cardiovasculares são a principal causa de morte no mundo, com cerca de 17,9 milhões "
                       "de óbitos em 2019 (ORGANIZAÇÃO MUNDIAL DA SAÚDE, 2021). A detecção precoce reduz esse risco, e por "
                       "isso modelos de aprendizado de máquina que estimam a presença de doença cardíaca a partir de dados "
                       "clínicos de rotina têm despertado interesse como apoio à triagem."))
    p.append(paragrafo("Este trabalho aplica um pipeline automatizado de ciência de dados ao conjunto " +
                       ident("Heart Failure Prediction") + ", que reúne 918 pacientes de cinco bases clínicas públicas "
                       "(DETRANO et al., 1989; FEDESORIANO, 2021). Cada paciente é descrito por 11 atributos, como idade, "
                       "tipo de dor no peito, pressão arterial, colesterol e frequência cardíaca máxima, e pela variável-alvo " +
                       ident("HeartDisease") + " (1 para doença cardíaca e 0 para saudável). O problema é, portanto, de "
                       "classificação binária."))

    p.append(secao("2", "Objetivo"))
    p.append(paragrafo("O objetivo geral é construir um pipeline automatizado que preveja a presença de doença cardíaca "
                       "e entregue o melhor modelo em uma API pública. Os objetivos específicos são:"))
    p.append('<ol class="alineas"><li>preparar os dados e criar ao menos dois atributos novos;</li>'
             "<li>reduzir a dimensionalidade com Rank e PCA e selecionar os atributos mais importantes;</li>"
             "<li>treinar e comparar três algoritmos de classificação;</li>"
             "<li>otimizar os hiperparâmetros do melhor modelo e compará-lo ao modelo padrão;</li>"
             "<li>exportar o modelo otimizado como API REST sem autenticação.</li></ol>")

    p.append(secao("3", "Material e métodos"))
    p.append(paragrafo("O pipeline foi desenvolvido em Python 3.12 com as bibliotecas da Tabela 1, em um notebook Jupyter. "
                       "Todas as etapas usam semente aleatória fixa (42), o que torna os resultados reproduzíveis."))
    p.append(legenda("Tabela 1 – Bibliotecas e versões"))
    p.append(tabela(["Biblioteca", "Versão", "Uso"], [
        ["pandas / numpy", "3.1.1 / 2.5.5", "leitura e manipulação dos dados"],
        ["scikit-learn", "1.9.1", "pré-processamento, Rank, PCA, modelos, validação cruzada e " + ident("GridSearchCV")],
        ["matplotlib / seaborn", "3.11.2 / 0.13.2", "gráficos"],
        ["joblib", "1.6.0", "exportação do modelo"],
        ["FastAPI / Uvicorn / Pydantic", "0.165.0 / 0.54.0 / 2.14.4", "API REST e validação das entradas"],
    ]))
    p.append(fonte())

    p.append(subsecao("3.1", "Dados e pré-processamento"))
    p.append(paragrafo("O conjunto tem 918 registros, 11 atributos e nenhum registro duplicado; 55,3% dos pacientes têm "
                       "doença cardíaca, então as classes estão razoavelmente balanceadas. Colesterol igual a 0 (172 "
                       "registros) e pressão arterial igual a 0 (1 registro) são valores impossíveis e foram tratados como "
                       "ausentes. Os dados foram divididos em 80% para treino (734 pacientes) e 20% para teste (184), de "
                       "forma estratificada pelo alvo."))
    p.append(paragrafo("A imputação pela mediana, a padronização das variáveis numéricas (" + ident("StandardScaler") +
                       ") e a codificação " + ident("one-hot") + " das categóricas ficam dentro de um " + ident("Pipeline") +
                       " do scikit-learn, ajustado apenas com os dados de treino, para evitar vazamento de informação do "
                       "teste. Após a codificação, o conjunto passa a ter 26 atributos."))

    p.append(subsecao("3.2", "Engenharia de atributos"))
    p.append(paragrafo("Foram criados três atributos: " + ident("FaixaEtaria") + " (até 40, 41 a 50, 51 a 60 e acima de 60 "
                       "anos); " + ident("MaxHR_pct") + ", a frequência cardíaca máxima dividida pela máxima teórica "
                       "(220 menos a idade); e " + ident("ColesterolAlto") + ", igual a 1 quando o colesterol é de pelo "
                       "menos 240 mg/dl."))

    p.append(subsecao("3.3", "Redução de dimensionalidade"))
    p.append(paragrafo("Foram aplicadas duas técnicas. No Rank, cada atributo foi ordenado pela informação mútua com o alvo (" +
                       ident("SelectKBest") + " com " + ident("mutual_info_classif") + "), com a importância de atributos de "
                       "uma Random Forest como verificação complementar. O número de atributos mantidos (k) foi escolhido "
                       "por validação cruzada. O PCA foi usado como comparação, para medir quantos componentes explicam 90% "
                       "da variância. O Rank integra o modelo final porque preserva os atributos originais e mantém o "
                       "resultado interpretável."))

    p.append(subsecao("3.4", "Modelos e hiperparâmetros padrão"))
    p.append(paragrafo("Foram comparados três algoritmos de classificação: Regressão Logística (HOSMER; LEMESHOW, 2000), "
                       "Random Forest (BREIMAN, 2001) e KNN (COVER; HART, 1967), com os hiperparâmetros padrão da Tabela 2."))
    p.append(legenda("Tabela 2 – Hiperparâmetros padrão dos modelos"))
    p.append(tabela(["Modelo", "Hiperparâmetros"], [
        ["Regressão Logística", f"{ident('C')} = 1,0; penalidade L2; solver lbfgs; {ident('max_iter')} = 1000"],
        ["Random Forest", f"{ident('n_estimators')} = 100; {ident('max_depth')} = sem limite; "
                          f"{ident('min_samples_split')} = 2; {ident('min_samples_leaf')} = 1"],
        ["KNN", f"{ident('n_neighbors')} = 5; {ident('weights')} = uniform; {ident('p')} = 2 (distância euclidiana)"],
    ]))
    p.append(fonte("Fonte: elaborado pelos autores (2026), com base em Pedregosa et al. (2011)."))

    p.append(subsecao("3.5", "Avaliação e otimização"))
    p.append(paragrafo("Os modelos foram avaliados por validação cruzada estratificada de 5 partições no treino e, depois, no "
                       "conjunto de teste, com cinco métricas: acurácia, precisão, recall, F1 e área sob a curva ROC (AUC). "
                       "O F1 foi o critério de escolha, e o recall recebeu atenção especial, porque no contexto médico deixar "
                       "de detectar um paciente doente é o erro mais grave."))
    p.append(paragrafo("O melhor modelo foi otimizado com " + ident("GridSearchCV") + " (PEDREGOSA et al., 2011), uma busca "
                       "exaustiva em grade, com a mesma validação cruzada de 5 partições e o F1 como métrica. A busca usou "
                       "apenas os dados de treino; o teste só serviu para a comparação final."))

    p.append(subsecao("3.6", "Disponibilização"))
    p.append(paragrafo("O pipeline completo (limpeza, atributos novos, pré-processamento, Rank e modelo) foi exportado com " +
                       ident("joblib") + " e é servido por uma API REST em FastAPI, sem autenticação, empacotada em Docker. "
                       "A rota " + ident("POST /predict") + " recebe os 11 atributos originais do paciente e devolve a "
                       "classe prevista e a probabilidade de doença."))

    p.append(secao("4", "Resultados e discussão"))
    p.append(paragrafo("A Regressão Logística foi o melhor modelo, com 89,67% de acurácia e F1 de 90,73% no teste, e a "
                       "otimização de hiperparâmetros trouxe ganho praticamente nulo. As subseções abaixo detalham as "
                       "métricas, a otimização e os atributos mais relevantes."))
    p.append(subsecao("4.1", "Comparação dos modelos"))
    p.append(paragrafo("Na validação cruzada (Tabela 3), a Regressão Logística e a Random Forest ficaram próximas, com F1 de "
                       "86,74% e 86,42%, e o KNN ficou atrás, com 85,59%. A Regressão Logística foi escolhida por ter o "
                       "maior F1."))
    p.append(legenda("Tabela 3 – Métricas na validação cruzada (5 partições, treino, média, hiperparâmetros padrão)"))
    p.append(tabela(["Modelo"] + METRICAS, [
        ["Regressão Logística", "85,15%", "86,20%", "87,45%", "86,74%", "92,01%"],
        ["Random Forest", "84,88%", "86,13%", "86,96%", "86,42%", "92,29%"],
        ["KNN", "83,92%", "85,09%", "86,22%", "85,59%", "89,34%"],
    ]))
    p.append(fonte())
    p.append(paragrafo("No conjunto de teste (Tabela 4 e Figura 1), a vantagem da Regressão Logística ficou maior: 89,67% de "
                       "acurácia, contra 85,33% da Random Forest e 83,70% do KNN. A diferença entre a validação cruzada "
                       "(cerca de 85%) e o teste (cerca de 90%) é esperada com apenas 184 pacientes no teste: cada paciente "
                       "vale 0,54 ponto percentual."))
    p.append(legenda("Tabela 4 – Métricas no conjunto de teste (184 pacientes, hiperparâmetros padrão)"))
    p.append(tabela(["Modelo"] + METRICAS, [
        ["Regressão Logística", "89,67%", "90,29%", "91,18%", "90,73%", "93,65%"],
        ["Random Forest", "85,33%", "86,41%", "87,25%", "86,83%", "91,98%"],
        ["KNN", "83,70%", "83,96%", "87,25%", "85,58%", "90,14%"],
    ]))
    p.append(fonte())
    p.append(legenda("Figura 1 – Comparação dos três modelos: validação cruzada e curvas ROC no teste"))
    p.append(figura(str(PASTA_FIGURAS / "06_comparacao_modelos.png"), "Comparação dos modelos"))
    p.append(fonte())

    p.append(subsecao("4.2", "Otimização de hiperparâmetros"))
    p.append(paragrafo("A busca em grade testou 20 combinações, o que equivale a 100 ajustes com a validação cruzada de 5 "
                       "partições (Tabela 5). O melhor F1 na validação cruzada foi 86,85%, contra 86,74% do modelo padrão."))
    p.append(legenda("Tabela 5 – Hiperparâmetros otimizados da Regressão Logística (" + "GridSearchCV, F1)"))
    p.append(tabela(["Hiperparâmetro", "Espaço testado", "Padrão", "Escolhido"], [
        [f"{ident('C')} (inverso da regularização)", "0,01; 0,1; 1; 10; 100", "1,0", "0,1"],
        [ident("class_weight"), "nenhum; balanced", "nenhum", "nenhum"],
        ["k do Rank (atributos mantidos)", "15; todos", "15", "todos (26)"],
    ]))
    p.append(fonte())
    p.append(paragrafo("No teste (Tabela 6 e Figura 2), o modelo otimizado manteve a acurácia de 89,67% e subiu o recall de "
                       "91,18% para 92,16%, com queda na precisão (90,29% para 89,52%) e na AUC (93,65% para 93,38%). Na "
                       "prática, o modelo otimizado detectou um paciente doente a mais (94 de 102, contra 93), ao custo de "
                       "um falso positivo a mais (11 contra 10). Como isso envolve um único paciente, a diferença está "
                       "dentro da variação esperada, e não se pode afirmar que a otimização melhorou o modelo. Ainda assim, "
                       "o modelo otimizado foi o exportado, por ter o maior recall, que é a métrica prioritária no contexto "
                       "médico."))
    p.append(legenda("Tabela 6 – Modelo padrão e otimizado no conjunto de teste"))
    p.append(tabela(["Modelo"] + METRICAS, [
        ["Regressão Logística padrão", "89,67%", "90,29%", "91,18%", "90,73%", "93,65%"],
        ["Regressão Logística otimizada", "89,67%", "89,52%", "92,16%", "90,82%", "93,38%"],
    ]))
    p.append(fonte())
    p.append(legenda("Figura 2 – Modelo padrão e otimizado: métricas e matrizes de confusão no teste"))
    p.append(figura(str(PASTA_FIGURAS / "07_padrao_vs_otimizado.png"), "Comparação entre modelo padrão e otimizado"))
    p.append(fonte())

    p.append(subsecao("4.3", "Atributos mais importantes"))
    p.append(paragrafo("Pelo Rank de informação mútua, os atributos mais associados à doença foram a inclinação do segmento "
                       "ST (" + ident("ST_Slope") + "), o tipo de dor no peito assintomática (" + ident("ChestPainType_ASY") +
                       "), a angina induzida por exercício (" + ident("ExerciseAngina") + ") e a depressão do segmento ST (" +
                       ident("Oldpeak") + "). Entre os atributos criados, " + ident("MaxHR_pct") + " ficou em terceiro lugar na "
                       "importância da Random Forest (7,9%), à frente da frequência cardíaca máxima original, o que mostra "
                       "que normalizar pela idade acrescentou informação. O PCA precisou de 12 dos 26 componentes para "
                       "explicar 90% da variância, ou seja, os atributos têm pouca redundância e a redução por PCA seria "
                       "pouco vantajosa aqui."))

    p.append(secao("5", "Considerações finais"))
    p.append(paragrafo("O pipeline atingiu o objetivo: a Regressão Logística otimizada acerta 89,67% dos pacientes do teste, "
                       "detecta 92,16% dos doentes (recall) e está disponível em uma API REST pública, sem autenticação. A "
                       "otimização de hiperparâmetros não trouxe ganho relevante sobre o modelo padrão, e o resultado mais "
                       "sólido do trabalho é a comparação entre algoritmos e a identificação dos atributos mais importantes."))
    p.append(paragrafo("Há limitações a considerar: o conjunto é pequeno (918 pacientes), o teste tem apenas 184 casos, a "
                       "avaliação usou uma única divisão entre treino e teste e não houve validação externa com dados de "
                       "outra população. Por isso, o modelo é um exercício acadêmico e não deve ser usado para decisões "
                       "clínicas."))
    p.append(paragrafo("Como trabalhos futuros, sugerem-se: repetir a validação cruzada com várias divisões para medir a "
                       "variabilidade; ajustar o limiar de decisão para priorizar o recall; testar outros algoritmos, como " +
                       ident("gradient boosting") + "; explicar as previsões individuais; e validar o modelo em dados externos. "
                       "O código-fonte, os modelos e a API estão disponíveis em https://github.com/plfrancisco/Pipeline_Heart_Failure."))

    p.append('<h1 class="sem-numero" style="margin-top:18pt">Referências</h1><div class="refs">')
    p.append("<p>BREIMAN, L. Random forests. <b>Machine Learning</b>, [s. l.], v. 45, n. 1, p. 5-32, 2001.</p>")
    p.append("<p>COVER, T.; HART, P. Nearest neighbor pattern classification. <b>IEEE Transactions on Information "
             "Theory</b>, [s. l.], v. 13, n. 1, p. 21-27, 1967.</p>")
    p.append("<p>DETRANO, R. <i>et al</i>. International application of a new probability algorithm for the diagnosis of "
             "coronary artery disease. <b>The American Journal of Cardiology</b>, [s. l.], v. 64, n. 5, p. 304-310, 1989.</p>")
    p.append("<p>FEDESORIANO. <b>Heart Failure Prediction Dataset</b>. [<i>S. l.</i>]: Kaggle, 2021. Disponível em: "
             "https://www.kaggle.com/datasets/fedesoriano/heart-failure-prediction. Acesso em: 19 nov. 2026.</p>")
    p.append("<p>HOSMER, D. W.; LEMESHOW, S. <b>Applied logistic regression</b>. 2. ed. New York: Wiley, 2000.</p>")
    p.append("<p>ORGANIZAÇÃO MUNDIAL DA SAÚDE. <b>Cardiovascular diseases (CVDs)</b>. Genebra: OMS, 2021. Disponível em: "
             "https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds). Acesso em: 19 nov. 2026.</p>")
    p.append("<p>PEDREGOSA, F. <i>et al</i>. Scikit-learn: machine learning in Python. <b>Journal of Machine Learning "
             "Research</b>, [s. l.], v. 12, p. 2825-2830, 2011.</p>")
    p.append("</div></div>")
    return "\n".join(p)


def documento(corpo_html):
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f"<body>{corpo_html}</body></html>")


def renderizar(html, nome_pdf):
    caminho_html = PASTA_TRABALHO / (nome_pdf + ".html")
    caminho_pdf = PASTA_TRABALHO / (nome_pdf + ".pdf")
    caminho_html.write_text(html, encoding="utf-8")
    subprocess.run([NAVEGADOR, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={PASTA_TRABALHO / 'perfil'}", f"--print-to-pdf={caminho_pdf}",
                    caminho_html.as_uri()], check=True, capture_output=True, timeout=180)
    return caminho_pdf


def descobrir_paginas(caminho_pdf):
    """Acha em que página (contando a folha de rosto como 1) começa cada título do sumário."""
    leitor = PdfReader(str(caminho_pdf))
    textos = [re.sub(r"\s+", "", pagina.extract_text() or "") for pagina in leitor.pages]
    pagina_sumario = next(i for i, t in enumerate(textos) if t.startswith("Sumário") or "SUMÁRIO" in t[:20].upper())
    resultado = {}
    for _, rotulo in TITULOS:
        alvo = re.sub(r"\s+", "", rotulo)
        for indice in range(pagina_sumario + 1, len(textos)):
            if alvo in textos[indice]:
                resultado[rotulo] = indice + 1
                break
    return resultado, len(leitor.pages)


def main():
    capa_pdf = renderizar(documento(pagina_capa()), "capa")
    corpo_sem_numeros = documento(folha_de_rosto() + pre_textuais({}) + parte_textual())
    primeiro = renderizar(corpo_sem_numeros, "corpo_pass1")
    numeros, total = descobrir_paginas(primeiro)
    corpo_final = documento(folha_de_rosto() + pre_textuais(numeros) + parte_textual())
    segundo = renderizar(corpo_final, "corpo")
    numeros2, total2 = descobrir_paginas(segundo)
    assert numeros == numeros2, f"paginação mudou entre as passagens: {numeros} x {numeros2}"
    escritor = PdfWriter()
    for caminho in (capa_pdf, segundo):
        for pagina in PdfReader(str(caminho)).pages:
            escritor.add_page(pagina)
    escritor.write(str(CAMINHO_SAIDA))
    print("páginas do corpo (da folha de rosto em diante):", total2, "| total com capa:", total2 + 1)
    print(numeros)


main()
