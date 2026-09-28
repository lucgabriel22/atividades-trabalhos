# Exercício 02 — Mercado do Cartola FC

Importa clubes, atletas e metadados do mercado atual do Cartola FC. Cada
execução recebe um identificador de snapshot; registros antigos só são
removidos depois que a nova carga termina com sucesso.

## Como executar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python cartola_collector.py
```

## Coleções

- `clubes_rodada_atual`: um documento por clube;
- `atletas_rodada_atual`: um documento por atleta;
- `mercado_rodada_atual`: metadados da carga e catálogo de status.

O campo `collected_at` é salvo como data UTC nativa do MongoDB, e não como
texto, para permitir filtros e ordenações cronológicas.
