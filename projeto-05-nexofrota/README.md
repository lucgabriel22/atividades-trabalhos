# NexoFrota

Plataforma de telemetria logística com persistência poliglota. Cadastros de
motoristas e veículos ficam no PostgreSQL; o histórico de telemetria e a
posição atual ficam no MongoDB. A aplicação Streamlit combina as duas fontes em
uma visão operacional com mapa, indicadores, alertas e simulação de movimento.

## Arquitetura

```text
                         +----------------------+
                         |  Streamlit / Folium  |
                         |  Plotly / Pandas     |
                         +----------+-----------+
                                    |
                            FleetService
                           /            \
                cadastro /              \ telemetria
                        v                v
              +----------------+   +----------------+
              |   PostgreSQL   |   |    MongoDB     |
              | drivers        |   | telemetry      |
              | vehicles       |   | current_positions |
              +----------------+   +----------------+
```

O histórico é imutável em `telemetry`. A coleção `current_positions` funciona
como uma projeção da última leitura de cada veículo, permitindo consultas
geoespaciais corretas e eficientes sem confundir posições antigas com a posição
atual.

## Funcionalidades

- cadastro relacional de motoristas e veículos;
- telemetria com coordenadas GeoJSON, velocidade, temperatura e instante UTC;
- índices `2dsphere` e composto por veículo/data;
- busca da posição atual por raio e lista dos veículos mais próximos;
- mapa interativo com marcadores e área de busca;
- visão unificada por meio de junção em memória;
- alertas de excesso de velocidade, veículo parado e temperatura crítica;
- histórico de velocidade e temperatura;
- simulação de novas leituras sem reiniciar a aplicação;
- ambiente completo com Docker Compose;
- seed idempotente e testes unitários.

## Execução com Docker

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose exec app python -m nexofrota.seed --if-empty
```

Acesse `http://localhost:8501`.

Para acompanhar os logs:

```powershell
docker compose logs -f app
```

Para encerrar sem apagar os volumes:

```powershell
docker compose down
```

## Execução local

Suba apenas os bancos e execute a aplicação no ambiente virtual:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres mongo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
python -m nexofrota.seed --if-empty
streamlit run src/app.py
```

## Comandos úteis

```powershell
# Recriar somente os dados de demonstração
python -m nexofrota.seed --reset

# Executar testes
pytest -q

# Validar estilo
ruff check .
ruff format --check .
```

`--reset` é destrutivo e deve ser usado apenas no ambiente de desenvolvimento.

## Documentação

- [`docs/RELATORIO_TECNICO.md`](docs/RELATORIO_TECNICO.md): relatório técnico editável;
- `output/pdf/relatorio_tecnico_nexofrota.pdf`: versão diagramada para entrega;
- [`docs/DECISOES_ARQUITETURA.md`](docs/DECISOES_ARQUITETURA.md): decisões e trade-offs.

## Segurança

O `.env` não deve ser versionado. Os valores de exemplo servem apenas para
desenvolvimento local; use senhas fortes e um gerenciador de segredos fora desse
ambiente.
