# NexoFrota - Desafio MongoDB Aula 4

Aplicação Streamlit de monitoramento geoespacial e persistência poliglota. A
marca do estudo de caso foi alterada para **NexoFrota**, mantendo os requisitos
técnicos da atividade: SQLite para dados cadastrais, MongoDB para telemetria,
consultas geoespaciais, junção em memória e dashboard interativo.

## Entregáveis

- `app.py`: aplicação completa em um único arquivo Python;
- `relatorio_tecnico_nexofrota.pdf`: relatório de arquitetura em 3 páginas;
- `requirements.txt`: dependências da aplicação;
- `.env.example`: configuração opcional do ambiente.

## Aderência ao estudo de caso

| Requisito | Implementação |
| --- | --- |
| Persistência poliglota | SQLite (`nexofrota.db`) e MongoDB (`nexofrota_db`) |
| Cadastro relacional | Tabelas `motoristas` e `veiculos` |
| Telemetria flexível | Coleção `telemetria` com histórico GeoJSON |
| Índice geoespacial | Índices `2dsphere` criados na inicialização |
| Busca por raio | Agregação `$geoNear` com raio em quilômetros |
| Junção em memória | Cadastro SQLite combinado à última posição MongoDB |
| Visualização | Streamlit, Folium e Plotly |
| Bônus | Botão **Simular Movimentação** com atualização imediata |

A coleção auxiliar `posicoes_atuais` mantém somente a última leitura de cada
veículo. Ela evita que uma leitura histórica antiga apareça no mapa depois de
uma simulação, sem alterar a coleção `telemetria` exigida no enunciado.

## Como executar

1. Inicie o MongoDB localmente na porta padrão `27017`.
2. Crie o ambiente e instale as dependências:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Opcionalmente, copie `.env.example` para `.env` e ajuste os valores.
4. Inicie a interface:

```powershell
streamlit run app.py
```

O banco SQLite, as tabelas, os índices MongoDB e a massa inicial são criados de
forma idempotente no primeiro acesso. O seed representa três veículos na região
de João Pessoa, com os motoristas Carlos Andrade, Mariana Silva e Roberto Souza.

## Estrutura final

```text
desafio mongodb aula4/
|-- app.py
|-- relatorio_tecnico_nexofrota.pdf
|-- requirements.txt
|-- .env.example
`-- README.md
```
