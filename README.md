# Exercícios de MongoDB e Redis

Soluções autorais para uma sequência de exercícios práticos de persistência,
integração com APIs e visualização de dados.

## Conteúdo

| Pasta | Tema |
| --- | --- |
| `exercicio-01-openf1` | Coleta da API OpenF1 e persistência idempotente no MongoDB |
| `exercicio-02-cartola-fc` | Importação do mercado do Cartola FC |
| `exercicio-03-georreferenciamento` | Conversão de CSV para GeoJSON e índice `2dsphere` |
| `exercicio-04-openf1-data-explorer` | Painel Streamlit para explorar sessões e voltas |
| `lista-01-redis` | Resolução comentada de 20 exercícios de Redis |

Cada pasta possui instruções próprias de instalação e execução. As aplicações
leem credenciais por variáveis de ambiente; nenhum segredo deve ser versionado.

## Qualidade

- configuração separada da regra de negócio;
- funções pequenas, tipadas e com responsabilidade única;
- gravações idempotentes sempre que a origem fornece chaves estáveis;
- validação de respostas externas antes da persistência;
- logs e códigos de saída adequados para automação;
- dependências fixadas em faixas de versões compatíveis.

## Referência dos enunciados

Os temas e objetivos foram baseados nos enunciados públicos do repositório
As implementações deste repositório foram escritas do zero.
