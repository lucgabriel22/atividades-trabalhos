# Respostas — fundamentos de Redis

## 1. String simples

Cria a chave e confirma o valor armazenado.

```redis
SET sistema:nome "DataPlatform"
GET sistema:nome
```

## 2. Várias strings

`MSET` grava o conjunto em uma única operação; `MGET` preserva a ordem das
chaves solicitadas.

```redis
MSET env:db "postgres" env:cache "redis" env:queue "rabbitmq"
MGET env:db env:cache
```

## 3. Sessão com expiração

A opção `EX` define a expiração em segundos no próprio `SET`. O `TTL` deve
retornar um número entre 0 e 30 logo após a criação.

```redis
SET sessao:usuario:101 "xyz123" EX 30
TTL sessao:usuario:101
```

## 4. Contador de acessos

Partindo de uma chave inexistente, o resultado final será `4`.

```redis
INCR pageviews:home
INCRBY pageviews:home 5
DECRBY pageviews:home 2
GET pageviews:home
```

## 5. Perfil em hash

```redis
HSET usuario:201 nome "Carlos" email "carlos@email.com" nivel "admin"
```

## 6. Leitura de hash

```redis
HGET usuario:201 email
HGETALL usuario:201
```

## 7. Contador dentro do hash

Se o campo ainda não existir, `HINCRBY` o inicializa com zero antes de somar.

```redis
HINCRBY usuario:201 tentativas_login 1
HKEYS usuario:201
```

## 8. Fila com lista

`RPUSH` insere no final e mantém a ordem apresentada.

```redis
RPUSH fila:email "email_1" "email_2" "email_3"
```

## 9. Consumo da fila

```redis
LPOP fila:email
```

O valor removido deve ser `email_1`.

## 10. Consulta da fila

O intervalo `0 -1` representa a lista completa.

```redis
LRANGE fila:email 0 -1
```

## 11. Conjunto de tags

Sets eliminam duplicatas; por isso, a cardinalidade esperada é `3`.

```redis
SADD tags:post:1 "dados" "redis" "nosql" "redis"
SCARD tags:post:1
```

## 12. Interseção de conjuntos

```redis
SADD tags:post:2 "redis" "python" "backend"
SINTER tags:post:1 tags:post:2
```

A interseção contém apenas `redis`.

## 13. Teste de pertinência

```redis
SISMEMBER tags:post:1 "python"
```

O retorno esperado é `0`, pois a tag não pertence ao primeiro conjunto.

## 14. Ranking com sorted set

```redis
ZADD placar:game 1500 "alice" 2200 "bob" 1800 "carol"
```

## 15. Ranking decrescente

```redis
ZREVRANGE placar:game 0 -1 WITHSCORES
```

## 16. Atualização do ranking

Após o incremento, Alice terá 2300 pontos e ocupará a posição `0` (os índices
do Redis começam em zero).

```redis
ZINCRBY placar:game 800 "alice"
ZREVRANK placar:game "alice"
```

## 17. Pub/Sub

No primeiro terminal:

```redis
SUBSCRIBE notificacoes
```

Em outro terminal:

```redis
PUBLISH notificacoes "Novo relatorio disponivel"
```

O assinante permanece bloqueado aguardando novas mensagens até ser encerrado.

## 18. Transação

Primeiro, prepare saldos para testar sem produzir valores inesperados:

```redis
MSET conta:A 200 conta:B 100
```

Depois, enfileire e execute a transferência de forma atômica:

```redis
MULTI
DECRBY conta:A 50
INCRBY conta:B 50
EXEC
MGET conta:A conta:B
```

`MULTI/EXEC` garante a execução sem intercalação, mas não valida saldo. Uma
regra de negócio que impeça saldo negativo deve usar Lua ou `WATCH`.

## 19. Gerenciamento de chaves

```redis
EXISTS sistema:nome
RENAME sistema:nome sistema:app
DEL sistema:app
```

`RENAME` falha caso a chave de origem já tenha sido removida ou expirado.

## 20. Inspeção e limpeza

```redis
INFO memory
FLUSHDB
```

`INFO memory` mostra métricas do processo. `FLUSHDB` remove **todas** as chaves
do banco atual; não execute esse último comando em um ambiente compartilhado ou
de produção.
