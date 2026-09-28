# Decisões de arquitetura

## ADR-001 — Separação entre cadastros e eventos

**Decisão:** manter motoristas e veículos no PostgreSQL e leituras de telemetria
no MongoDB.

**Motivo:** os cadastros exigem unicidade, integridade referencial e relações
estáveis. A telemetria cresce como uma sequência de eventos independentes, com
estrutura orientada a documentos e consultas geoespaciais.

**Consequência:** não há `JOIN` entre bancos. A aplicação consulta cada fonte e
faz a associação por `vehicle_id` no serviço de frota.

## ADR-002 — Projeção da posição atual

**Decisão:** usar `telemetry` como histórico imutável e `current_positions` como
projeção atualizada por veículo.

**Motivo:** consultar diretamente todos os eventos próximos de um ponto pode
encontrar uma posição antiga, embora a posição atual do veículo esteja fora do
raio. A projeção garante que `$geoNear` opere apenas sobre o estado atual.

**Consequência:** cada gravação atualiza duas coleções. O histórico permanece a
fonte de auditoria e a projeção pode ser reconstruída se necessário.

## ADR-003 — Simulação como serviço de domínio

**Decisão:** isolar a geração de movimento da interface e da persistência.

**Motivo:** permite testes determinísticos por injeção de um gerador aleatório,
impõe limites geográficos e evita que regras de negócio fiquem presas ao
Streamlit.
## ADR-004 — Aplicação sem estado local

**Decisão:** todo estado persistente fica nos bancos. O cache do Streamlit guarda
apenas clientes e serviços.

**Motivo:** recarregar ou escalar a interface não pode apagar telemetria nem
divergir do estado compartilhado.

## ADR-005 — Containers reproduzíveis

**Decisão:** fornecer Dockerfile e Docker Compose com verificações de saúde.

**Motivo:** reduz diferenças de ambiente, documenta as portas e impede que a
aplicação seja iniciada antes de os bancos aceitarem conexões.
