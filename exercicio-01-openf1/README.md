# Exercício 01 — OpenF1 + MongoDB

Coleta uma sessão da API OpenF1 e armazena sessões, pilotos e voltas no
MongoDB. A importação é idempotente: executá-la novamente atualiza os registros
existentes em vez de criar duplicatas.

## Como executar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python openf1_collector.py
```

Edite `.env` antes da execução. `OPENF1_MEETING_KEY` é opcional; remova a linha
para filtrar a sessão apenas por `OPENF1_SESSION_KEY`.

## Coleções e chaves únicas

- `sessions`: `session_key`;
- `drivers`: `session_key` + `driver_number`;
- `laps`: `session_key` + `driver_number` + `lap_number`.
