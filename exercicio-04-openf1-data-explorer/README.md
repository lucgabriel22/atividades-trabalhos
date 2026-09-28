# Exercício 04 — OpenF1 Explorer

Painel Streamlit para navegar pelas sessões salvas pelo exercício 01 e comparar
o desempenho dos pilotos volta a volta.

## Como executar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

## Funcionalidades

- filtro por temporada e sessão;
- resumo do país, circuito e horário da sessão;
- seleção de vários pilotos;
- gráfico de duração por volta;
- tabela com a melhor volta de cada piloto;
- dados completos em uma área expansível;
- cache de consultas por 60 segundos.
