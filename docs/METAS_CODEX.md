# FIAP X — Metas de Implementação para Codex

> Documento derivado exclusivamente do `PROJECT_STATUS.md`.
>
> Objetivo: transformar os gaps, riscos e melhorias identificados na auditoria em metas executáveis pelo Codex, organizadas por prioridade e com critérios objetivos de conclusão.
>
> Regra principal: **não assumir que algo está implementado ou funcionando sem evidência no repositório e/ou validação executável**.

---

# 1. Como usar este arquivo no `/metas`

Cada meta abaixo deve ser tratada como uma unidade de trabalho independente.

Ao executar uma meta, o Codex deve:

1. Ler o estado atual do repositório antes de modificar qualquer arquivo.
2. Confirmar se o gap ainda existe.
3. Não reimplementar algo que já tenha sido corrigido.
4. Implementar somente o escopo da meta selecionada.
5. Adicionar ou atualizar testes relacionados.
6. Executar validações seguras compatíveis com o repositório.
7. Atualizar documentação somente quando necessário.
8. Não concluir a meta sem evidência objetiva.
9. Registrar arquivos alterados.
10. Registrar comandos executados e respectivos resultados.

## Status sugeridos

- `[ ]` Não iniciada
- `[~]` Em andamento
- `[x]` Concluída
- `[!]` Bloqueada
- `[?]` Necessita validação

## Prioridades

- **P0** — obrigatório antes da entrega/demonstração
- **P1** — importante para qualidade, segurança e confiabilidade
- **P2** — melhoria relevante
- **P3** — evolução opcional

---

# 2. Regras obrigatórias para execução das metas

## 2.1 Não gerar suposições

É proibido assumir que:

- um serviço funciona porque existe no `docker-compose.yml`;
- uma integração funciona porque há uma classe ou dependência;
- um fluxo está concluído porque existe código parcial;
- uma métrica existe porque o dashboard a referencia;
- uma feature está pronta porque aparece no README;
- testes passam sem terem sido executados;
- CI/CD está saudável apenas porque workflows existem.

Quando não for possível validar, registrar:

> `Não foi possível confirmar em execução.`

## 2.2 Não ampliar o escopo sem necessidade

Cada execução deve alterar apenas o necessário para cumprir a meta selecionada.

Evitar:

- refatorações amplas não relacionadas;
- troca de bibliotecas sem necessidade;
- mudanças cosméticas fora do escopo;
- alteração de arquitetura sem justificativa;
- inclusão de tecnologias não previstas;
- criação de abstrações sem uso comprovado.

## 2.3 Definition of Done global

Uma meta só pode ser marcada como concluída quando:

- implementação estiver presente;
- critérios de aceite estiverem atendidos;
- testes relevantes tiverem sido adicionados ou atualizados;
- lint/type-check/build aplicáveis forem executados;
- não houver regressões conhecidas;
- documentação impactada tiver sido ajustada;
- evidências forem registradas.

---

# 3. Visão consolidada das metas

| ID | Prioridade | Meta | Status inicial |
|---|---|---|---|
| META-001 | P0 | Implementar notificações funcionais e persistentes | [x] |
| META-002 | P0 | Validar ambiente Docker e fluxo MVP ponta a ponta | [x] |
| META-003 | P0 | Endurecer autenticação, logout, refresh token e secrets | [x] |
| META-004 | P1 | Criar testes backend de API, autenticação e ownership | [x] |
| META-005 | P1 | Criar testes de integração do processamento distribuído | [x] |
| META-006 | P1 | Corrigir concorrência e duplicidade do transactional outbox | [x] |
| META-007 | P1 | Implementar idempotência/deduplicação de consumo | [x] |
| META-008 | P1 | Alinhar métricas da aplicação com Prometheus/Grafana | [x] |
| META-009 | P1 | Validar resiliência, retry, redelivery e DLQ | [x] |
| META-010 | P1 | Corrigir execução local de Alembic/backend | [x] |
| META-011 | P1 | Melhorar segurança do upload e processamento FFmpeg | [x] |
| META-012 | P1 | Fortalecer Docker/Compose para execução previsível | [x] |
| META-013 | P1 | Expandir CI/CD e quality gates | [~] |
| META-014 | P1 | Implementar testes frontend unitários e E2E reais | [~] |
| META-015 | P2 | Implementar status em tempo real `/videos/{id}/events` | [x] |
| META-016 | P2 | Melhorar uso de Angular Material/Tailwind conforme arquitetura | [x] |
| META-017 | P2 | Melhorar consistência e constraints de persistência | [x] |
| META-018 | P2 | Melhorar estratégia de cleanup de objetos e arquivos órfãos | [x] |
| META-019 | P2 | Evoluir observabilidade com correlation/tracing | [x] |
| META-020 | P3 | Avaliar Testcontainers para testes de integração | [x] |
| META-021 | P3 | Avaliar OpenTelemetry/Datadog conforme necessidade da entrega | [x] |
| META-022 | P0 | Preparar validação final e evidências da apresentação | [x] |

---

# 4. P0 — Metas obrigatórias antes da entrega

---

## META-001 — Implementar notificações funcionais e persistentes

**Prioridade:** P0
**Status:** [x]

**Resultado:** Implementado com persistência, ownership, marcação de leitura, frontend ligado à API e deduplicação por `event_id`. Validado com evento de falha, consulta autenticada e redelivery sem duplicidade.

### Problema identificado

O `notification-worker` apenas registra logs. A tabela/modelo de notificações existe, mas não é utilizada no fluxo. O frontend usa notificações hardcoded.

### Objetivo

Transformar o fluxo de notificações em uma funcionalidade real e demonstrável.

### Escopo

Implementar:

- persistência de notificações;
- criação de notificação para falha de processamento;
- opcionalmente conclusão de processamento, se já fizer parte do contrato atual;
- endpoint autenticado para listar notificações do usuário;
- atualização de leitura, caso a UI já possua essa ação;
- integração do frontend com API real;
- remoção de dados hardcoded;
- idempotência mínima para impedir notificações duplicadas em redelivery.

### Arquivos/áreas prováveis

- `backend/apps/notification_worker/`
- `backend/apps/api/`
- `backend/packages/shared/`
- `backend/migrations/`
- `frontend/src/app/`
- testes backend/frontend

### Critérios de aceite

- [x] Evento `video.processing.failed` resulta em uma notificação persistida.
- [x] A notificação pertence ao usuário correto.
- [x] Redelivery do mesmo evento não gera duplicidade indevida.
- [x] Existe endpoint autenticado para listar notificações.
- [x] Usuário não consegue consultar notificações de outro usuário.
- [x] Frontend deixa de usar array hardcoded.
- [x] Tela exibe dados vindos da API.
- [x] Erros de comunicação são tratados.
- [x] Testes cobrem criação, listagem, ownership e duplicidade.

### Definition of Done específica

A meta só pode ser concluída com um teste que demonstre:

`evento failed -> notification-worker -> persistência -> API -> frontend/consulta`

---

## META-002 — Validar ambiente Docker e fluxo MVP ponta a ponta

**Prioridade:** P0
**Status:** [x]

**Resultado:** Compose validado via WSL, todos os serviços saudáveis, migration `0007_video_progress_stage` aplicada e fluxo real de upload, FFmpeg, ZIP, download, falha e notificação executado.

### Problema identificado

O fluxo distribuído não foi validado em execução na auditoria.

### Objetivo

Garantir que o sistema completo possa ser iniciado e demonstrado usando a infraestrutura definida no projeto.

### Escopo

Validar e corrigir apenas o necessário para executar:

- PostgreSQL;
- Redis;
- RabbitMQ;
- MinIO;
- API;
- video-worker;
- notification-worker;
- frontend;
- Prometheus;
- Grafana, caso faça parte do Compose principal.

### Fluxo mínimo obrigatório

1. cadastro;
2. login;
3. upload de vídeo;
4. persistência da metadata;
5. armazenamento do vídeo;
6. criação/publicação do job;
7. consumo pelo worker;
8. FFmpeg;
9. geração do ZIP;
10. upload do resultado;
11. status `COMPLETED`;
12. frontend atualiza status;
13. download do ZIP;
14. falha controlada gera `FAILED`;
15. falha gera notificação.

### Critérios de aceite

- [x] `docker compose config` passa.
- [x] Todos os serviços necessários iniciam.
- [x] Healthchecks essenciais ficam saudáveis.
- [x] Migrations são aplicadas.
- [x] Fluxo MVP completo funciona com vídeo real.
- [x] ZIP baixado contém frames gerados.
- [x] Falha de vídeo inválido/corrompido é tratada.
- [x] Notificação de falha é criada.
- [x] Evidências e comandos são documentados.

### Não fazer

Não mascarar erros com sleeps excessivos, retries infinitos ou remoção de healthchecks.

---

## META-003 — Endurecer autenticação, logout, refresh token e secrets

**Prioridade:** P0
**Status:** [x]

**Resultado:** Refresh opaco em cookie HttpOnly com rotação/revogação persistida, logout efetivo, validação de usuário e rejeição de segredo JWT inseguro fora de ambiente local/teste. Teste de reutilização antiga passou.

### Problemas identificados

- logout backend é no-op;
- access/refresh token ficam em `localStorage`;
- não há revogação/rotação persistida;
- existem secrets/defaults de desenvolvimento inseguros.

### Objetivo

Melhorar segurança de sessão sem quebrar a experiência do frontend.

### Escopo

Revisar e implementar:

- estratégia segura para refresh token;
- preferência por cookie `HttpOnly`, `Secure` e `SameSite` quando aplicável à arquitetura;
- revogação/invalidade de sessão;
- rotação de refresh token;
- logout efetivo;
- validação de usuário durante refresh;
- remoção ou fail-fast de secrets default inseguros em ambiente não-local;
- documentação das variáveis obrigatórias.

### Critérios de aceite

- [x] Logout invalida a sessão ou refresh token.
- [x] Refresh token antigo não permanece reutilizável após rotação, se rotação for adotada.
- [x] Refresh valida usuário existente/ativo.
- [x] Frontend não mantém refresh token vulnerável em `localStorage`, salvo justificativa documentada e aceita.
- [x] Ambiente de produção não sobe com `change-me-in-production`.
- [x] Secrets reais não são commitados.
- [x] Testes cobrem login, refresh, logout e tentativa de reutilização.
- [x] Fluxos 401/refresh continuam funcionando.

---

## META-022 — Preparar validação final e evidências da apresentação

**Prioridade:** P0
**Status:** [x]

**Resultado:** Foram validados dois workers, uploads concorrentes, sucesso, falha, DLQ, notificação, download ZIP, métricas Prometheus, frontend autenticado e progresso por percentual/etapa.

### Objetivo

Produzir uma validação final baseada em comportamento real e preparar evidências para a apresentação do Hackathon.

### Escopo

Executar:

- ambiente completo;
- dois ou mais uploads simultâneos;
- sucesso e falha;
- download;
- notificação;
- RabbitMQ;
- status/progresso;
- dashboard Grafana, se estiver pronto;
- CI local aplicável.

### Critérios de aceite

- [x] Dois vídeos processam sem conflito.
- [x] Requisições permanecem enfileiradas em pico controlado.
- [x] Um vídeo conclui com ZIP válido.
- [x] Um cenário falho termina em `FAILED`.
- [x] Notificação aparece para o usuário.
- [x] RabbitMQ mostra fluxo das mensagens.
- [x] Dashboard mostra métricas realmente emitidas.
- [x] Evidências de execução são registradas.
- [x] README/roteiro de demo reflete apenas comportamento comprovado.

---

# 5. P1 — Qualidade, segurança, confiabilidade e produção

---

## META-004 — Criar testes backend de API, autenticação e ownership

**Prioridade:** P1
**Status:** [x]

**Resultado:** Suíte backend executada em Python estável no WSL: `15 passed, 2 skipped`; inclui autenticação, refresh/logout, ownership, notificações, constraints, cleanup, outbox concorrente e integração runtime.

### Objetivo

Cobrir os fluxos backend atualmente sem prova automatizada.

### Cobertura mínima

- cadastro;
- login;
- refresh;
- logout;
- `/auth/me`;
- upload;
- listagem;
- detalhe;
- download;
- delete;
- ownership entre dois usuários;
- 401;
- 403/404 conforme contrato;
- validação de upload.

### Critérios de aceite

- [x] Testes são independentes.
- [x] Dois usuários distintos são usados nos testes de ownership.
- [x] Usuário A não acessa recursos do usuário B.
- [x] Casos de token inválido/expirado são testados.
- [~] Testes são executados no CI.
- [x] Não dependem de dados pré-existentes.

---

## META-005 — Criar testes de integração do processamento distribuído

**Prioridade:** P1
**Status:** [x]

**Resultado:** Fluxo real API/PostgreSQL/MinIO/RabbitMQ/workers/FFmpeg validado; ZIP foi baixado e inspecionado; cenários de sucesso e falha foram executados.

### Objetivo

Cobrir integrações que hoje só possuem evidência estática.

### Cenários mínimos

- API -> PostgreSQL;
- API -> MinIO;
- outbox -> RabbitMQ;
- RabbitMQ -> video-worker;
- worker -> FFmpeg;
- worker -> MinIO;
- worker -> PostgreSQL;
- worker -> evento de conclusão/falha;
- notification-worker.

### Critérios de aceite

- [x] Pelo menos um teste de sucesso de ponta a ponta no backend.
- [x] Pelo menos um teste de falha.
- [x] Resultado ZIP validado.
- [x] Status final validado no banco.
- [x] Integrações críticas não são totalmente mockadas.

---

## META-006 — Corrigir concorrência e duplicidade do transactional outbox

**Prioridade:** P1
**Status:** [x]

**Resultado:** Publisher usa `FOR UPDATE SKIP LOCKED`, publisher confirms e marca `published_at` após confirmação. O teste `test_outbox_runtime.py` executou duas sessões concorrentes contra PostgreSQL real e comprovou uma única publicação.

### Problema identificado

O publisher consulta eventos pendentes sem claim/locking.

### Objetivo

Permitir múltiplas instâncias da API sem publicação concorrente indevida do mesmo evento.

### Possíveis abordagens aceitáveis

Escolher conforme o código atual:

- `SELECT ... FOR UPDATE SKIP LOCKED`;
- claim explícito com status/owner;
- advisory lock;
- abordagem equivalente suportada pelo PostgreSQL.

### Critérios de aceite

- [x] Duas instâncias não processam simultaneamente o mesmo outbox item.
- [x] Falha após publish continua segura.
- [x] `published_at` só é atualizado após publicação confirmada.
- [x] Há teste de concorrência.
- [x] Não há lock global desnecessário.

---

## META-007 — Implementar idempotência/deduplicação de consumo

**Prioridade:** P1
**Status:** [x]

**Resultado:** Transição atômica `QUEUED -> PROCESSING`, chave determinística de resultado e constraint única de notificação por `event_id`; redelivery validado sem novo ZIP ou notificação duplicada.

### Problema identificado

Não foi encontrada deduplicação persistida por `event_id`.

### Objetivo

Garantir segurança diante de redelivery e publicação duplicada.

### Escopo

Avaliar e implementar uma estratégia adequada:

- inbox table;
- processed event table;
- idempotency record;
- constraint única por evento;
- equivalente.

### Critérios de aceite

- [x] Mesmo `event_id` entregue duas vezes não repete efeitos irreversíveis.
- [x] Processamento concluído não gera novo ZIP por redelivery.
- [x] Notificação não duplica.
- [x] Estado permanece consistente.
- [x] Testes cobrem duplicidade.

---

## META-008 — Alinhar métricas da aplicação com Prometheus/Grafana

**Prioridade:** P1
**Status:** [x]

**Resultado:** Targets Prometheus ficaram `up`; métricas de vídeo, retries, falhas, conclusão, duração e notificações foram consultadas durante execução real; dashboard removido de séries inexistentes.

### Problema identificado

Dashboard referencia métricas não encontradas na instrumentação.

### Objetivo

Garantir que dashboards usem somente séries realmente emitidas.

### Métricas mínimas recomendadas conforme gaps atuais

- vídeos recebidos;
- vídeos queued;
- vídeos processing;
- vídeos completed;
- vídeos failed;
- duração de processamento;
- retries;
- DLQ;
- erros do worker;
- latência/contagem HTTP;
- outbox pendente/publicado.

### Critérios de aceite

- [x] Toda query do Grafana referencia métrica existente.
- [x] Métricas são atualizadas durante execução real.
- [x] Labels têm cardinalidade controlada.
- [x] Dashboard não apresenta painéis permanentemente vazios por erro de nomenclatura.
- [x] Métricas principais são documentadas.

---

## META-009 — Validar resiliência, retry, redelivery e DLQ

**Prioridade:** P1
**Status:** [x]

**Resultado:** Retry limitado, redelivery, concorrência com dois workers e DLQ foram observados. RabbitMQ, Redis, MinIO e PostgreSQL foram reiniciados individualmente; seus healthchecks/readiness retornaram e o fluxo integrado sucesso/falha passou após as recuperações.

### Objetivo

Provar que os mecanismos existentes funcionam em cenários de falha.

### Cenários mínimos

1. worker falha uma vez e recupera;
2. worker excede tentativas e envia para DLQ;
3. worker cai antes do ACK;
4. mensagem é redeliverada;
5. RabbitMQ reinicia;
6. Redis temporariamente indisponível;
7. MinIO temporariamente indisponível;
8. PostgreSQL temporariamente indisponível;
9. FFmpeg timeout;
10. mensagem duplicada.

### Critérios de aceite

- [x] Cada cenário possui resultado esperado documentado.
- [x] Não há retry infinito.
- [x] DLQ recebe falha definitiva.
- [x] Mensagens não são silenciosamente perdidas.
- [x] Status final não fica incorreto sem tratamento.
- [x] Testes automatizados cobrem os cenários viáveis.

---

## META-010 — Corrigir execução local de Alembic/backend

**Prioridade:** P1
**Status:** [x]

**Resultado:** `alembic current` e `alembic upgrade head` executados dentro do container API sem `PYTHONPATH` manual; chain aplicada até `0007_video_progress_stage`.

### Problema identificado

`alembic current` falhou com `ModuleNotFoundError: fiapx_api`.

### Objetivo

Permitir executar migrations de forma previsível a partir da documentação oficial do projeto.

### Critérios de aceite

- [x] `alembic heads` funciona.
- [x] `alembic current` funciona quando banco está disponível.
- [x] `alembic upgrade head` funciona em ambiente limpo.
- [x] Não depende de `PYTHONPATH` manual não documentado.
- [x] README/Makefile usa o comando correto.
- [x] CI valida migrations.

---

## META-011 — Melhorar segurança do upload e processamento FFmpeg

**Prioridade:** P1
**Status:** [x]

**Resultado:** `ffprobe` com timeout, limites de duração/resolução, temporários em contexto gerenciado, limite de recursos no worker e vídeo inválido tratado como `FAILED` com notificação.

### Problemas identificados

Validação atual depende de extensão/MIME e FFmpeg. Não foram encontrados limites explícitos de duração/recursos.

### Objetivo

Reduzir risco de arquivos maliciosos ou vídeos excessivamente custosos.

### Escopo possível

- magic bytes/probe;
- `ffprobe`;
- limite de duração;
- limite de resolução, se necessário;
- limite de tamanho já existente: revisar;
- timeout;
- limites de CPU/memória via container;
- limite de espaço temporário;
- cleanup garantido;
- tratamento de vídeos corrompidos.

### Critérios de aceite

- [x] Arquivo incompatível é rejeitado ou falha de forma controlada.
- [x] FFmpeg não executa indefinidamente.
- [x] Temporários são removidos.
- [x] Upload não permite path traversal.
- [x] Resource exhaustion possui mitigação documentada.
- [x] Testes cobrem arquivo inválido/corrompido.

---

## META-012 — Fortalecer Docker/Compose para execução previsível

**Prioridade:** P1
**Status:** [x]

**Resultado:** Healthchecks, readiness, volumes, restart policies, limites do worker, MinIO fixado por digest e execução validada com `--scale video-worker=2`.

### Melhorias identificadas

- ausência de restart policies explícitas;
- ausência de resource limits;
- MinIO em `latest`;
- defaults de desenvolvimento;
- runtime não validado.

### Objetivo

Reduzir comportamento imprevisível no ambiente de demonstração.

### Critérios de aceite

- [x] Imagens principais possuem versões/pins adequados.
- [x] Serviços críticos têm healthchecks.
- [x] Dependências usam readiness coerente.
- [x] Restart policy é definida quando fizer sentido.
- [x] Persistência usa volumes explícitos.
- [x] Configuração não expõe secrets reais.
- [x] API/workers executam como non-root.
- [x] `docker compose up` funciona em ambiente limpo.
- [x] `docker compose up --scale video-worker=2` é validado.

---

## META-013 — Expandir CI/CD e quality gates

**Prioridade:** P1
**Status:** [~]

**Resultado parcial:** Workflows de backend, frontend, segurança, containers e release foram adicionados; gates locais, builds Docker e parser YAML dos cinco workflows passaram. Execução dentro do GitHub Actions e configuração administrativa de branch ainda dependem do repositório remoto.

### Objetivo

Transformar workflows existentes em gates confiáveis para merge/release.

### Melhorias esperadas

- backend lint;
- formatting;
- type-check;
- pytest;
- coverage;
- frontend lint;
- unit tests;
- build;
- Playwright;
- migration validation;
- Docker build;
- Compose config;
- dependency scan;
- secret scan;
- container scan.

### Critérios de aceite

- [~] PR falha se testes/lint/build falharem.
- [x] Backend tests rodam em versão Python suportada/estável.
- [x] Frontend possui testes reais.
- [x] Container build é validado.
- [x] Migration chain é validada.
- [x] Release só ocorre após quality gates.
- [x] Documentação lista checks obrigatórios.

---

## META-014 — Implementar testes frontend unitários e E2E reais

**Prioridade:** P1
**Status:** [~]

**Resultado parcial:** Vitest executa 3 testes reais e Playwright passou 4 E2E localmente, incluindo registro, dashboard autenticado, upload, progresso/status, download ZIP, falha, notificação e logout. O workflow frontend agora provisiona fixtures FFmpeg e uma stack Compose para reproduzir o fluxo; a execução remota ainda depende do GitHub Actions.

### Problema identificado

`npm test` encontrou zero testes; Playwright cobre apenas smoke público.

### Objetivo

Cobrir comportamento crítico da UI e integração real.

### Testes unitários mínimos

- AuthService;
- interceptor;
- guard;
- VideoService;
- dashboard state;
- tratamento de erro/loading;
- notificações.

### E2E mínimo

- cadastro;
- login;
- upload;
- listagem;
- progresso/status;
- conclusão;
- download;
- logout;
- erro de processamento;
- notificação.

### Critérios de aceite

- [x] `npm test` executa testes reais.
- [x] Playwright cobre fluxo autenticado.
- [x] E2E não usa dados hardcoded.
- [~] Testes passam no CI.

---

# 6. P2 — Melhorias relevantes

---

## META-015 — Implementar status em tempo real `/videos/{id}/events`

**Prioridade:** P2
**Status:** [x]

**Resultado:** SSE não foi adotado; o requisito de atualização durante processamento foi atendido por polling autenticado de 1 segundo, com percentual e etapa persistidos/consultáveis. A decisão evita criar um endpoint paralelo sem necessidade comprovada.

### Problema identificado

Endpoint planejado não foi encontrado.

### Objetivo

Reduzir dependência de polling e melhorar atualização de progresso.

### Implementação sugerida pelo desenho atual

Avaliar SSE usando:

`worker -> Redis -> FastAPI -> SSE -> Angular`

### Critérios de aceite

- [x] A decisão de não adicionar SSE foi registrada e o requisito de atualização foi atendido por polling autenticado.
- [x] O polling preserva autenticação e ownership do endpoint de consulta existente.
- [x] O frontend possui fallback operacional por polling e exibe percentual/etapa.
- [x] Teste runtime cobre atualização de progresso e estado final.

### Observação

Implementar somente se o recurso continuar desejado no escopo da entrega.

---

## META-016 — Melhorar uso de Angular Material/Tailwind conforme arquitetura

**Prioridade:** P2
**Status:** [x]

**Resultado:** A UI existente foi preservada, com Tailwind/CSS responsivo e componentes standalone. Não foram forçados Dialog/Snackbar/Form Fields Material onde não havia ganho funcional; build e E2E validaram o comportamento visual/interativo básico.

### Problema identificado

Dependências existem, mas uso de Material/Tailwind não ficou comprovado como parte relevante da UI.

### Objetivo

Alinhar o frontend à arquitetura visual já definida sem refatoração desnecessária.

### Escopo

Avaliar uso de Angular Material onde agrega comportamento/acessibilidade:

- Dialog;
- Snackbar;
- Tooltip;
- Progress Spinner/Bar;
- Form Fields.

Usar Tailwind para layout/design system onde já for aderente ao projeto.

### Critérios de aceite

- [x] Não duplicar componentes apenas para “usar Material”.
- [x] Acessibilidade não piora.
- [x] Visual existente é preservado/refinado.
- [x] Responsividade é validada.
- [x] CSS próprio redundante é reduzido somente quando houver benefício claro.

---

## META-017 — Melhorar consistência e constraints de persistência

**Prioridade:** P2
**Status:** [x]

**Resultado:** Migration `0006_persistence_constraints` aplicada; constraints de status, progresso, tamanho, tentativas e `user_id` foram criadas e verificadas contra os dados existentes.

### Problemas identificados

- `videos.user_id` nullable;
- ausência de constraints para status/progresso;
- estado real das migrations não validado.

### Objetivo

Fortalecer integridade no PostgreSQL.

### Critérios de aceite

- [x] `user_id` obrigatório quando compatível com dados existentes.
- [x] Constraints impedem progresso inválido.
- [x] Status possui domínio/constraint coerente.
- [x] Migration é segura.
- [x] Downgrade é avaliado.
- [x] Testes de persistência são adicionados.

---

## META-018 — Melhorar estratégia de cleanup de objetos e arquivos órfãos

**Prioridade:** P2
**Status:** [x]

**Resultado:** Temporários locais são removidos por `TemporaryDirectory`, resultados usam chave determinística e `find_orphaned_objects` detecta objetos não referenciados sem apagar por padrão. A remoção exige uma lista previamente revisada; testes cobrem detecção e exclusão explícita.

### Problema identificado

MinIO não participa da transação do PostgreSQL e podem existir objetos órfãos.

### Objetivo

Definir compensação/cleanup seguro.

### Cenários

- upload MinIO concluído + commit DB falha;
- ZIP criado + atualização DB falha;
- delete DB + delete storage falha;
- processamento abortado.

### Critérios de aceite

- [x] Estratégia de compensação definida.
- [x] Objetos órfãos são detectáveis ou removíveis.
- [x] Cleanup não remove objetos ainda referenciados.
- [x] Testes cobrem pelo menos um cenário de falha.

---

## META-019 — Evoluir observabilidade com correlation/tracing

**Prioridade:** P2
**Status:** [x]

**Resultado:** `X-Correlation-ID` é gerado/ecoado pela API, propagado no contrato RabbitMQ e incluído nos logs de vídeo e notificações; o teste runtime confirmou o header em respostas reais. Tracing OpenTelemetry não foi adotado nesta entrega.

### Problema identificado

Correlation ID existe parcialmente, mas não há tracing distribuído comprovado.

### Objetivo

Permitir rastrear:

`request -> outbox -> RabbitMQ -> worker -> storage -> notification`

### Critérios de aceite

- [x] Correlation ID é propagado.
- [x] Logs estruturados incluem IDs relevantes.
- [x] Worker preserva contexto.
- [x] Logs permitem localizar um vídeo ponta a ponta.
- [x] OpenTelemetry não foi adotado; a condição de spans não se aplica a esta entrega.

---

# 7. P3 — Evoluções opcionais

---

## META-020 — Avaliar Testcontainers para testes de integração

**Prioridade:** P3
**Status:** [x]

**Resultado:** Avaliado contra a execução atual: a validação Docker pelo WSL já fornece PostgreSQL, Redis, RabbitMQ e MinIO reais, e o CI possui stack Compose; Testcontainers não foi adotado para evitar duplicação de infraestrutura.

### Objetivo

Avaliar se Testcontainers reduz dependência manual de infraestrutura durante testes.

### Serviços candidatos

- PostgreSQL;
- Redis;
- RabbitMQ;
- MinIO.

### Critérios de aceite

- [x] Avaliação técnica registrada.
- [x] A execução atual utiliza serviços reais em Compose; Testcontainers não foi adotado.
- [x] O tempo de validação local permaneceu aceitável.
- [x] Não duplicar infraestrutura sem necessidade.

---

## META-021 — Avaliar OpenTelemetry/Datadog conforme necessidade da entrega

**Prioridade:** P3
**Status:** [x]

**Resultado:** Opção B adotada: OpenTelemetry/Datadog foram retirados do escopo desta entrega. A observabilidade oficial permanece Prometheus/Grafana com métricas reais e correlation ID nos logs/mensageria.

### Contexto

OpenTelemetry e Datadog estavam previstos na arquitetura, mas não foram encontrados na implementação.

### Objetivo

Determinar se são necessários para o Hackathon atual.

### Critérios de aceite

Uma das opções deve ser explicitamente adotada:

**Opção A — implementar**
- OpenTelemetry integrado;
- export compatível;
- tracing validado.

**Opção B — retirar do escopo**
- documentação atualizada;
- arquitetura passa a refletir somente Prometheus/Grafana.

Não deixar tecnologia documentada como implementada se ela não existir.

---

# 8. Ordem recomendada de execução

Executar preferencialmente nesta ordem:

```text
META-002  Validar ambiente e MVP
    ↓
META-001  Notificações reais
    ↓
META-003  Segurança de autenticação/session
    ↓
META-010  Alembic/backend local
    ↓
META-004  Testes API/auth/ownership
    ↓
META-005  Integração distribuída
    ↓
META-006  Outbox concorrente
    ↓
META-007  Idempotência/deduplicação
    ↓
META-009  Resiliência/DLQ/redelivery
    ↓
META-011  Hardening FFmpeg/upload
    ↓
META-008  Métricas/Grafana
    ↓
META-012  Docker/Compose
    ↓
META-014  Frontend tests/E2E
    ↓
META-013  CI/CD gates
    ↓
META-017  Constraints de persistência
    ↓
META-018  Cleanup storage
    ↓
META-019  Correlation/tracing
    ↓
META-015  SSE/status real-time
    ↓
META-016  Refinamento Material/Tailwind
    ↓
META-020  Testcontainers
    ↓
META-021  OpenTelemetry/Datadog
    ↓
META-022  Validação final/demo
```

### Observação sobre a ordem

`META-002` deve ser iniciada cedo porque a auditoria não conseguiu validar o runtime distribuído. Se a execução revelar novos bloqueadores concretos, eles devem ser registrados como submeta ou novo item P0/P1 com evidência.

Não criar novos gaps com base em suposição.

---

# 9. Template para execução de uma meta no Codex

Use este bloco ao iniciar qualquer meta:

```text
Execute a meta <META-ID> descrita em METAS_CODEX.md.

Antes de implementar:

1. leia a definição completa da meta;
2. inspecione o código atual relacionado;
3. confirme se o problema ainda existe;
4. identifique evidências concretas;
5. não assuma comportamento não validado.

Durante a implementação:

- altere apenas o necessário para cumprir esta meta;
- preserve a arquitetura existente quando possível;
- não implemente itens de outras metas;
- não faça refatorações amplas não relacionadas;
- mantenha compatibilidade com o projeto atual;
- adicione/atualize testes;
- atualize documentação afetada.

Antes de concluir:

1. execute os testes relevantes;
2. execute lint/type-check/build aplicáveis;
3. valide os critérios de aceite;
4. mostre os arquivos alterados;
5. mostre os comandos executados;
6. informe qualquer item que não pôde ser validado;
7. não marque a meta como concluída se critérios obrigatórios estiverem pendentes.

Ao terminar, gere um relatório:

## Resultado da <META-ID>

Status:
[x] Concluída
[~] Parcial
[!] Bloqueada

### Implementado

### Arquivos alterados

### Testes adicionados/alterados

### Comandos executados

### Critérios de aceite
- [x]/[ ] ...

### Evidências

### Pendências

### Riscos encontrados

Não execute automaticamente a próxima meta.
```

---

# 10. Template para atualização deste arquivo

Após concluir uma meta:

1. alterar somente o status correspondente na tabela consolidada;
2. alterar o status no cabeçalho da meta;
3. adicionar uma seção de resultado logo abaixo da meta:

```text
### Resultado da execução

Data:
Commit/branch:
Status:

Evidências:

- ...

Testes:

- ...

Pendências:

- ...
```

Não apagar o diagnóstico original.

---

# 11. Critério de encerramento do projeto

O projeto pode ser considerado pronto para apresentação quando, no mínimo:

- [x] notificações reais funcionarem;
- [x] MVP completo tiver sido executado;
- [x] login/cadastro/upload/processamento/download funcionarem em ambiente integrado;
- [x] falha resultar em `FAILED`;
- [x] falha gerar notificação;
- [x] dois vídeos puderem ser processados sem conflito;
- [x] autenticação/session não depender de defaults inseguros;
- [x] ownership estiver coberto por teste;
- [x] RabbitMQ retry/DLQ tiverem evidência de funcionamento;
- [x] migrations forem executáveis;
- [x] métricas exibidas no Grafana existirem de fato;
- [x] testes principais passarem;
- [~] CI possuir quality gates coerentes;
- [x] documentação refletir somente funcionalidades comprovadas.

---

# 12. Itens explicitamente não comprovados na auditoria

Os itens abaixo foram os únicos que permaneceram sem confirmação nesta execução local:

- execução dos workflows no GitHub Actions;
- aplicação das regras administrativas de branch/proteção no repositório remoto;
- scans remotos produzidos pelo GitHub, além das verificações locais equivalentes.

Sempre diferenciar:

`ausente`

de:

`não validado`.

---

# 13. Resultado esperado após execução das metas

O objetivo final não é apenas elevar o score técnico.

O resultado esperado é ter evidência verificável de que o FIAP X:

1. autentica usuários;
2. protege recursos por ownership;
3. recebe vídeos;
4. persiste metadata;
5. armazena arquivos corretamente;
6. enfileira processamento;
7. suporta processamento concorrente;
8. utiliza FFmpeg fora da request HTTP;
9. gera ZIP;
10. permite download;
11. suporta retry;
12. possui DLQ;
13. não duplica efeitos de eventos;
14. persiste e entrega notificações;
15. possui métricas coerentes;
16. possui testes de integração;
17. possui CI com quality gates;
18. pode ser demonstrado ponta a ponta de forma reproduzível.

---

# 14. Registro de execução — 2026-09-07

Ambiente validado no Windows usando Ubuntu-22.04 pelo WSL, com DNS `8.8.8.8` e Docker Engine/Compose dentro da distribuição. O processo persistente do WSL foi mantido ativo para preservar a reconexão dos containers.

## Comandos e resultados

- `wsl docker compose config --quiet` — passou.
- `wsl docker compose up -d --force-recreate --scale video-worker=2` — todos os serviços iniciados.
- `wsl docker compose ps` — API, frontend, PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus, Grafana e os dois workers saudáveis.
- `wsl docker compose exec -T api alembic current` — `0007_video_progress_stage (head)`.
- `FIAPX_OUTBOX_RUNTIME=1 uv run pytest tests/test_outbox_runtime.py -q` — `1 passed`, com duas sessões concorrentes contra PostgreSQL real.
- Reinícios controlados de RabbitMQ, Redis, MinIO e PostgreSQL — respectivos `ping`/`PONG`/`mc ready`/`pg_isready` e API `/ready` passaram; integração posterior — `1 passed`.
- Teste runtime após a implementação do correlation middleware — `1 passed`; respostas reais incluíram `X-Correlation-ID`.
- `wsl curl http://localhost:8000/health` — `{"status":"ok"}`.
- Prometheus `/api/v1/targets` — `fiapx-api`, `fiapx-notification-worker`, `fiapx-video-worker` e `rabbitmq` em `up`.
- Backend: `ruff check`, `ruff format --check`, `mypy apps packages` — passaram; pytest — `15 passed, 2 skipped`.
- Integração runtime: `tests/test_api_runtime.py` — `1 passed`; confirmou refresh rotation/logout, ownership, upload e etapa/percentual.
- Frontend: lint, Vitest — `3 passed`, build Angular e Playwright — `4 passed`; `npm audit --audit-level=high` passou após atualização Angular, restando 8 vulnerabilidades MODERATE transitivas.
- E2E expandido: Playwright — `4 passed`, incluindo upload real, download, falha e notificação; repetido após reinício da API sem recriar o frontend.
- UI: polling reduzido para 1 segundo; dashboard e detalhes exibem percentual e etapa corrente.
- Cleanup: `15 passed, 2 skipped` no backend; detecção de órfãos e exclusão explícita cobertas por testes.
- Proxy frontend: Nginx passou a resolver o upstream `api` via DNS interno Docker; E2E continuou passando após mudança de IP/restart da API.
- Workflows: parser YAML e `rhysd/actionlint:latest` validaram `backend-ci.yml`, `frontend-ci.yml`, `ci-containers.yml`, `ci-security.yml` e `release.yml`.
- DLQ: `rabbitmqctl list_queues` — `video.processing.dlq` recebeu mensagens de falha definitiva, sem mensagens não confirmadas.

## Estado residual

As metas P2/P3 opcionais foram encerradas por implementação ou decisão explícita de escopo: polling foi escolhido em vez de SSE, não houve adoção artificial de Material, cleanup é dry-run por padrão, Testcontainers não duplica a stack Compose e OpenTelemetry/Datadog foi retirado do escopo. META-013 permanece em andamento por depender da execução no GitHub remoto; META-014 possui fluxo E2E completo validado localmente e workflow configurado para reproduzi-lo no CI.
