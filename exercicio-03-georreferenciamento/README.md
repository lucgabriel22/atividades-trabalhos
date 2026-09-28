# Exercício 03 — Georreferenciamento com GeoJSON

Baixa um CSV, valida latitude e longitude, cria pontos GeoJSON e mantém a
coleção do MongoDB sincronizada com a fonte. Um índice `2dsphere` é criado no
campo `location` para consultas geoespaciais.

## Como executar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python geodata_importer.py
```

Configure `DATA_URL` e, se os nomes forem diferentes, ajuste
`LATITUDE_COLUMN` e `LONGITUDE_COLUMN`.

## Estrutura do documento

```json
{
  "_id": "hash estável da linha",
  "properties": { "nome": "UBS Exemplo" },
  "location": { "type": "Point", "coordinates": [-46.63, -23.55] },
  "snapshot_id": "identificador da carga",
  "imported_at": "data UTC"
}
```

Linhas com coordenadas vazias, não numéricas ou fora dos limites geográficos
são registradas no log e ignoradas. A coleção anterior só é limpa depois que a
nova carga foi validada e gravada.
