# NexoFrota

## Plataforma de telemetria logística com persistência poliglota

**Responsável:** Lucas Gabriel<br>
**Versão:** 1.0<br>
**Data:** setembro de 2026

## 1. Resumo executivo

A NexoFrota é uma aplicação para acompanhamento operacional de veículos de
carga. O sistema registra dados cadastrais, recebe telemetria, mantém a última
posição conhecida, executa consultas geoespaciais e apresenta informações em um
dashboard web. O projeto demonstra persistência poliglota ao usar PostgreSQL
para informações relacionais e MongoDB para eventos de telemetria em GeoJSON.

A solução inclui ambiente Docker, carga de demonstração, simulação de
movimentação, mapa interativo, indicadores, gráficos históricos, testes
automatizados e documentação operacional.

## 2. Objetivos

- representar corretamente dados relacionais e documentos geoespaciais;
- preservar o histórico de leituras sem perder a posição atual;
- localizar veículos dentro de um raio e ordenar os mais próximos;
- combinar dados de fontes diferentes sem acoplamento entre os bancos;
- sinalizar condições operacionais relevantes;
- oferecer execução reproduzível para avaliação e desenvolvimento.

## 3. Requisitos funcionais

| Código | Requisito | Implementação |
| --- | --- | --- |
| RF-01 | Manter motoristas e veículos | PostgreSQL com chaves e restrições |
| RF-02 | Registrar telemetria | Coleção MongoDB `telemetry` |
| RF-03 | Consultar posição atual | Coleção `current_positions` |
| RF-04 | Buscar por raio | Pipeline `$geoNear` e índice `2dsphere` |
| RF-05 | Unificar dados | `FleetService` associa por `vehicle_id` |
| RF-06 | Exibir mapa | Folium integrado ao Streamlit |
| RF-07 | Exibir indicadores | Métricas e gráficos Plotly |
| RF-08 | Simular movimento | `MovementSimulator` gera novas leituras |
| RF-09 | Consultar histórico | Filtro por veículo e período |

## 4. Arquitetura da solução

A interface Streamlit acessa somente a camada de serviços. O `FleetService`
orquestra repositórios especializados, evitando consultas de infraestrutura na
camada visual. O PostgreSQL é a fonte de verdade dos cadastros; o MongoDB é a
fonte de verdade da telemetria.

```text
Usuário
  |
  v
Streamlit + Folium + Plotly
  |
  v
FleetService ---- MovementSimulator
  |                         |
  +-----------+-------------+
              |
      +-------+--------+
      |                |
PostgreSQL          MongoDB
drivers             telemetry
vehicles            current_positions
```

### 4.1 Fluxo de leitura

1. A aplicação obtém veículos e motoristas do PostgreSQL.
2. Obtém a posição atual de cada veículo no MongoDB.
3. Associa os resultados em memória pelo identificador do veículo.
4. Calcula alertas e prepara tabelas, mapas e gráficos.

### 4.2 Fluxo de escrita

1. Uma leitura é validada pelo modelo de domínio.
2. O documento é inserido no histórico `telemetry`.
3. A posição do mesmo veículo é substituída em `current_positions`.
4. A próxima consulta da interface reflete imediatamente o novo estado.

## 5. Modelo relacional

### 5.1 Tabela `drivers`

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | chave primária |
| `name` | varchar(120) | obrigatório |
| `license_number` | varchar(20) | único e obrigatório |
| `status` | varchar(20) | active, inactive ou leave |

### 5.2 Tabela `vehicles`

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | chave primária |
| `plate` | varchar(10) | único e obrigatório |
| `model` | varchar(100) | obrigatório |
| `driver_id` | inteiro | FK única para `drivers` |
| `active` | booleano | padrão verdadeiro |

A chave estrangeira impede veículos associados a motoristas inexistentes. A
unicidade de `driver_id` modela a atribuição de um motorista por veículo neste
escopo acadêmico.

## 6. Modelo de documentos

Um evento de telemetria possui o seguinte formato:

```json
{
  "vehicle_id": 101,
  "location": {
    "type": "Point",
    "coordinates": [-46.6333, -23.5505]
  },
  "speed_kmh": 56.0,
  "cargo_temperature_c": 4.0,
  "recorded_at": "2026-09-27T12:00:00Z"
}
```

GeoJSON exige a ordem longitude, latitude. Datas são persistidas como BSON Date
em UTC, permitindo ordenação cronológica correta.

### 6.1 Índices

- `telemetry.location`: `2dsphere`;
- `telemetry.vehicle_id + recorded_at`: índice composto;
- `current_positions.location`: `2dsphere`;
- `current_positions.recorded_at`: índice decrescente.

## 7. Consultas geoespaciais

A busca recebe um ponto central e um raio em quilômetros. O repositório converte
o raio para metros e utiliza `$geoNear` sobre `current_positions`. O pipeline
retorna a distância calculada pelo MongoDB e os resultados já ordenados do mais
próximo para o mais distante.

A separação da posição atual evita um erro comum: considerar um veículo dentro
da área porque uma leitura histórica esteve próxima, mesmo que sua localização
mais recente esteja fora do raio.

## 8. Regras operacionais

O dashboard classifica automaticamente:

- excesso de velocidade: acima de 80 km/h;
- veículo parado: abaixo de 1 km/h;
- temperatura crítica: abaixo de -20 °C ou acima de 8 °C;
- sem telemetria: veículo cadastrado sem posição atual.

Esses limites são demonstrativos. Em produção, devem ser configuráveis por tipo
de carga, veículo, rota e contrato de nível de serviço.

## 9. Interface analítica

A aplicação possui quatro áreas:

1. **Mapa:** veículos dentro do raio, círculo da consulta e lista dos mais próximos.
2. **Visão geral:** cadastro, última leitura, coordenadas e alertas.
3. **Dashboard:** KPIs, velocidade atual e temperatura da carga.
4. **Histórico:** séries temporais filtradas por veículo e período.

O botão de simulação cria uma leitura por veículo usando deslocamento máximo
configurável. O movimento respeita limites de latitude e longitude, e a fonte de
aleatoriedade pode ser injetada para testes determinísticos.

## 10. Implantação

O Docker Compose inicia PostgreSQL, MongoDB e aplicação. Verificações de saúde
evitam que o Streamlit seja iniciado antes dos bancos. Volumes nomeados preservam
os dados entre reinicializações.

```text
docker compose up -d --build
docker compose exec app python -m nexofrota.seed --if-empty
```

A aplicação fica disponível na porta 8501, PostgreSQL na 5433 do host e MongoDB
na 27018 do host.

## 11. Segurança e confiabilidade

- segredos são lidos do ambiente e o `.env` não é versionado;
- o container da aplicação executa como usuário sem privilégios;
- validações rejeitam coordenadas e velocidades inválidas;
- consultas SQL usam parâmetros;
- o HTML exibido em pop-ups é escapado;
- o seed destrutivo exige a opção explícita `--reset`;
- índices e esquema são criados de forma idempotente;
- as conexões possuem timeout e verificação de disponibilidade.

As senhas do exemplo são exclusivas para desenvolvimento e devem ser
substituídas em qualquer ambiente compartilhado.

## 12. Estratégia de testes

Os testes unitários verificam:

- conversão entre modelo e documento GeoJSON;
- rejeição de coordenadas inválidas;
- classificação de alertas;
- limite geográfico da simulação;
- preservação do número de veículos em uma rodada;
- quantidade, identidade e estado final do seed.

Testes de integração podem ser executados contra os containers para validar
restrições SQL, índices MongoDB e pipelines geoespaciais.

## 13. Limitações e evolução

O projeto é adequado a demonstração e avaliação acadêmica. Para produção,
recomenda-se adicionar autenticação, autorização, ingestão assíncrona por fila,
observabilidade, retenção de histórico, replicação, backups e testes de carga.

Uma evolução natural é transformar `current_positions` em uma projeção mantida
por change streams ou processamento de eventos. Outra é parametrizar limites de
alerta e rotas autorizadas por cliente.

## 14. Conclusão

A NexoFrota demonstra como escolher bancos por característica do dado, sem
tratar persistência poliglota como simples duplicação. O PostgreSQL protege
relações cadastrais; o MongoDB atende o histórico de eventos e as consultas
geoespaciais; a camada de serviços une os contextos e mantém a interface
independente da infraestrutura.

O resultado é uma base organizada, testável e reproduzível para telemetria
logística, com separação clara de responsabilidades e caminho de evolução para
cenários reais.
