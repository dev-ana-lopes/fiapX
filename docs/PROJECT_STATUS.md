# FIAP X — Status Técnico do Projeto

## 1. Resumo executivo

O repositório contém uma implementação ampla do fluxo assíncrono: API FastAPI, autenticação JWT com Argon2, PostgreSQL/Alembic, MinIO, RabbitMQ com outbox, Redis para progresso/lease, video-worker, frontend Angular e infraestrutura de observabilidade. O frontend foi validado por compilação e dois smoke tests E2E.

Os gaps mais relevantes são: notificações não persistidas e exibidas com dados hardcoded; logout sem revogação no backend; refresh token armazenado em `localStorage`; ausência de endpoint `/videos/{id}/events`; métricas e dashboards referenciam séries que não são emitidas no código; ausência de testes backend de integração/autenticação/ownership/worker; e impossibilidade de validar runtime Docker, banco e pipeline remoto nesta máquina.

**Score geral estimado: 5,8/10.** A nota é ponderada pela existência de código executável, mas reduzida por fluxos não confirmados, testes insuficientes e gaps funcionais de notificação/segurança.

## 2. Nível de confiança da auditoria

**MÉDIO.** O código, configuração, migrations, workflows e testes foram inspecionados; lint, build frontend e E2E smoke foram executados. A confiança é limitada porque Docker não está disponível, não houve execução ponta a ponta com PostgreSQL/RabbitMQ/Redis/MinIO, a suíte pytest abortou com access violation do runtime Python, e GitHub Actions não foi consultado.

## 3. Estrutura atual do repositório

```text
.
├── backend/
│   ├── apps/api/src/fiapx_api/       # API, auth, DB, messaging, storage, progress
│   ├── apps/video_worker/src/        # consumo, FFmpeg, ZIP, resiliência
│   ├── apps/notification_worker/src/# consumo de eventos e log
│   ├── packages/shared/              # contratos Pydantic e status
│   ├── migrations/versions/          # 0001, 0002, 0003
│   └── tests/                        # 5 arquivos, unitários limitados
├── frontend/src/app/                 # Angular standalone, auth, dashboard, detalhes
├── frontend/e2e/                     # smoke Playwright
├── .github/workflows/                # CI backend/frontend, segurança, containers, release
├── infra/prometheus/                 # scrape configuration
├── monitoring/grafana/               # provisioning e dashboard versionado
├── docs/runbooks/                    # runbook operacional
├── docker-compose.yml
├── Makefile
├── README.md
├── SECURITY.md
└── .env.example
```

## 4. Stack realmente encontrada

| Área | Encontrado | Evidência/validação |
|---|---|---|
| Frontend | Angular 22, TypeScript 6, RxJS, Material e Tailwind nas dependências | `frontend/package.json`; build passou |
| Backend | Python >=3.14, FastAPI, Pydantic, SQLAlchemy, Alembic, uv | `backend/pyproject.toml`; import/runtime backend não validado |
| Dados | PostgreSQL e Redis no Compose; SQLAlchemy/Alembic e cliente Redis no código | `docker-compose.yml`, `db.py`, `models.py`, `progress.py` |
| Mensageria | RabbitMQ/aio-pika, exchange topic, filas duráveis, publisher confirms | `messaging.py`, `video_worker/main.py` |
| Storage/processamento | MinIO SDK e FFmpeg por subprocesso | `minio_storage.py`, `processor.py`, Dockerfile |
| Observabilidade | Prometheus client, Prometheus e Grafana declarados | `main.py`, `infra/prometheus`, `monitoring`; instrumentação limitada |

## 5. Arquitetura planejada vs implementação real

O fluxo planejado está representado no README. A implementação real contém API → PostgreSQL/MinIO/outbox → RabbitMQ → video-worker → FFmpeg/MinIO → atualização de status. O processamento pesado não está no handler HTTP: `create_video()` salva o arquivo e cria outbox; FFmpeg aparece em `video_worker/processor.py`.

Há divergências: o `notification-worker` não cria registros na tabela `notifications` nem chama provedor externo; não há Datadog, OpenTelemetry ou propagação de trace; e não há endpoint de eventos/SSE. A escala horizontal é declarada por documentação e Compose, mas não foi executada.

## 6. Status do Frontend

| Item | Status | Evidência |
|---|---|---|
| Angular 22 | ✅ Implementado | versões 22.0.0 em `frontend/package.json`; build passou |
| Standalone Components | ✅ Implementado | decorators nos componentes em `frontend/src/app` |
| Signals/computed/inject | ✅ Implementado | `auth.service.ts`, `dashboard.component.ts` |
| `@if`, `@for` | ✅ Implementado | templates de login, registro, dashboard e detalhes |
| `@defer` | ❌ Não implementado | busca no frontend não encontrou `@defer` |
| Lazy loading | ✅ Implementado | `app.routes.ts:6-10`, `loadComponent` |
| Material | ⚠️ Parcial | dependência existe, não foram encontrados componentes `mat-*` utilizados |
| Tailwind | ⚠️ Parcial | dependência/config existem; estilos entregues são majoritariamente CSS próprio |
| Tema dark/responsividade | ✅ Implementado | `styles.css` possui tema escuro e media queries; não foi validado em vários viewports |
| Login/cadastro/dashboard/detalhes | ✅ Implementado | componentes em `features`; smoke E2E confirma apenas carga/validação |
| Upload/listagem/status/progresso/download | ⚠️ Parcial | `VideoService` e dashboard chamam API; integração backend não foi executada |
| Loading/erro | ✅ Implementado | signals, skeletons e mensagens no dashboard/detalhes |
| Logout | ⚠️ Parcial | frontend limpa storage/navega; API `logout()` não revoga token |
| Guard/interceptor/401 | ✅ Implementado | `auth.guard.ts`, `auth.interceptor.ts` |
| Refresh token | ⚠️ Parcial | endpoint e retry existem; token fica em `localStorage`, sem rotação/revogação persistida |
| Backend real | ⚠️ Parcial | URLs HTTP e serviços existem; E2E só testa telas públicas |
| Testes unitários | ❌ Não implementado | `npm test` reportou 0 testes |
| E2E | ⚠️ Parcial | `smoke.spec.ts`: 2 testes passaram; não cobre autenticação real nem MVP |
| Notificações | ❌ Não implementado como integração | `notifications.component.ts:4` usa array local hardcoded |

## 7. Status do Backend

✅ A API possui rotas de registro, login, refresh, logout, `/auth/me`, upload, listagem, detalhe, download, delete, `/health`, `/ready` e `/metrics` em `backend/apps/api/src/fiapx_api/main.py`.

⚠️ A validação completa é incompleta: não há testes de rotas autenticadas, ownership, upload, download ou integração. O endpoint esperado `GET /videos/{id}/events` não foi encontrado. `logout()` em `main.py:169-171` retorna 204 sem operação.

✅ O upload lê em chunks, limita tamanho, sanitiza basename, valida extensão/MIME, grava no storage e persiste `Video`, `ProcessingJob` e `OutboxEvent` na mesma transação lógica (`main.py:185-257`).

⚠️ A ordem storage → banco cria uma janela em que falhas de limpeza podem deixar objeto órfão; o tratamento dessa compensação não foi validado em execução.

## 8. Status da Autenticação

✅ Senhas usam `argon2.PasswordHasher` em `auth.py:17,58-66`; JWT contém `sub`, `type` e `exp`; access token padrão expira em 15 minutos e refresh em 7 dias (`config.py:36-40`). Rotas de vídeo usam `get_current_user`.

✅ Ownership está presente nas consultas de listagem, detalhe, download e delete (`main.py:282`, `307`, `327`, `345`), sempre filtrando `Video.user_id == user.id`. Isso é evidência estática; não houve teste com dois usuários.

⚠️ Refresh apenas valida assinatura/tipo/expiração e não confirma que o usuário existe nem mantém sessão/revogação. Logout não invalida tokens. Frontend persiste access e refresh token em `localStorage` (`auth.service.ts:10,15-19`), expondo-os a scripts em caso de XSS.

❓ Não confirmado: política de enumeração de usuários, rate limiting, MFA e proteção contra brute force não aparecem no código/configuração inspecionados.

## 9. Status da Persistência

✅ Existem tabelas/modelos `users`, `videos`, `processing_jobs`, `notifications` e `outbox_events` em `models.py` e migrations `0001_initial.py`–`0003_outbox.py`. Há PKs, FK, unique em email/object key, índices de usuário/job e timestamps.

⚠️ `videos.user_id` é nullable no modelo e migration, apesar de uploads autenticados; não há CHECK constraint para enum/status, faixa de progresso ou tamanho. Não foi possível executar `alembic current` por `ModuleNotFoundError: fiapx_api`; `alembic heads` retornou `0003_outbox`.

❓ Estado real do banco, versão aplicada e divergência model/migration não foram confirmados por conexão.

## 10. Status do RabbitMQ

✅ `messaging.py` declara exchange `fiapx.events`, filas duráveis `video.processing`, `video.processing.retry` e `video.processing.dlq`, bindings, mensagens persistentes e publisher confirms. O upload publica indiretamente via outbox.

✅ O worker usa `no_ack=False`, `message.process(requeue=True)` e `prefetch_count` configurável, padrão 1 (`video_worker/main.py:140-145,214-219`). Há backoff/jitter em `resilience.py` e TTL por expiração da mensagem de retry.

⚠️ Não há execução do broker. A fila retry não tem consumidor próprio; depende de expiração da mensagem e dead-letter para `video.uploaded`. O outbox não usa claim/lock entre múltiplas instâncias, portanto duplicação de publicação é possível em escala horizontal. Não foi encontrada estratégia de deduplicação do consumidor por `event_id`.

## 11. Status do Processamento de Vídeos

✅ `video_worker/main.py:149-168` baixa o original, chama `VideoProcessor`, cria ZIP, envia `result/frames.zip`, verifica existência e atualiza COMPLETED. `processor.py:20-47` extrai um frame por segundo; `make_zip()` inclui apenas `frame_*.jpg`.

✅ O FFmpeg é executado por `create_subprocess_exec`, com argumentos separados e timeout de 3600s; timeout mata o processo e stderr/código de retorno são tratados (`processor.py:20-43`). Diretório temporário é isolado por job.

⚠️ Não há validação por conteúdo real além de extensão/MIME e do resultado do FFmpeg; não há limites explícitos de duração, CPU, memória ou disco. O fluxo completo com vídeo real não foi executado.

## 12. Status do MinIO

✅ `MinioStorage` encapsula upload/download/delete/exists/presigned URL em `minio_storage.py`; API usa chave por usuário/vídeo e download exige ownership + COMPLETED.

⚠️ Bucket é criado sob demanda e endpoints/credenciais de desenvolvimento estão no Compose e `.env.example`. Não houve execução MinIO nem confirmação de criação, upload, presigned URL ou cleanup.

## 13. Status do Redis

✅ Redis é usado para progresso em `progress.py` e lease distribuído em `video_worker/resilience.py`; lease usa `SET NX EX` e scripts Lua protegem renew/release por owner.

⚠️ Progresso é efêmero e não há fallback comprovado. Cada consulta de detalhe cria/fecha cliente Redis. Não há execução, métricas de Redis ou teste de reconexão/restart.

## 14. Status das Notificações

❌ Notificação funcional/persistente não está implementada. `notification_worker/main.py:15-25` valida evento e apenas escreve log; não usa o modelo `Notification`, não persiste status e não integra SMTP/webhook/push.

⚠️ Existe fila `video.notification` ligada a eventos completed/failed (`main.py:28-35`) e o frontend tem uma tela, mas `notifications.component.ts:4` contém dados fixos. Não há endpoint para consultar notificações nem ação funcional “marcar como lidas”.

## 15. Resiliência e Concorrência

✅ Há reconexão robusta do aio-pika, ACK manual, retry exponencial limitado com jitter, DLQ para falha definitiva, lease Redis e transição condicional `UPDATE ... WHERE status=QUEUED` (`video_worker/main.py:87-110`). Nome determinístico de resultado reduz colisões.

⚠️ Não foi validada escala com múltiplos workers. Se o worker cair após gravar ZIP/status e antes do ACK, a mensagem pode ser redeliverada; a transição condicional evita novo processamento quando já não está QUEUED, mas não há teste de consistência desse cenário. Se cair entre banco e publicação do evento de conclusão, o status pode estar atualizado sem notificação.

❓ RabbitMQ/Redis/PostgreSQL/MinIO indisponíveis, restart, ACK perdido, FFmpeg travado e dois workers concorrentes não foram executados; o comportamento é apenas inferido onde o código o torna explícito.

## 16. Consistência Distribuída

✅ Existe transactional outbox: vídeo, job e evento são gravados no mesmo commit (`main.py:234-250`; migration `0003_outbox.py`). Isso reduz a janela banco COMMIT + publicação perdida.

⚠️ O publisher marca `published_at` após publish, mas não há locking/claim; instâncias concorrentes podem publicar o mesmo evento. Não há inbox/idempotência persistida, e a gravação no MinIO não participa da transação PostgreSQL. Objeto órfão e duplicidade continuam cenários possíveis.

## 17. Segurança

| Severidade | Achado e evidência |
|---|---|
| HIGH | Segredo JWT default `change-me-in-production` em `config.py:36`, `.env.example:29-30` e default do Compose; não há fail-fast para ambiente produtivo. |
| HIGH | Credenciais default de PostgreSQL/RabbitMQ/MinIO expostas no Compose e exemplos; adequadas apenas para desenvolvimento, mas serviços são publicados em portas do host. |
| HIGH | Refresh/access tokens em `localStorage` (`auth.service.ts:10,16,19`). |
| MEDIUM | Logout não revoga token; refresh não tem rotação/revogação persistida. |
| MEDIUM | Upload valida extensão/MIME/tamanho, mas não valida magic bytes nem duração/recursos antes do FFmpeg. |
| LOW | CORS permite métodos/headers `*`, embora origins sejam configuráveis (`main.py:102-107`). |

Não foram encontrados `shell=True`, comando FFmpeg concatenado em shell ou path traversal no nome de upload. Gitleaks/CodeQL estão configurados, mas seus resultados remotos não foram confirmados.

## 18. Observabilidade

✅ `/metrics` é montado e `videos_received_total` é incrementado; logs do worker incluem `video_id`, `worker_id`, `attempt` e tipo de erro.

⚠️ Prometheus/Grafana estão configurados, mas o dashboard usa `http_requests_total`, `fiapx_video_processing_retries_total`, histogram de duração e métricas RabbitMQ que não foram encontradas emitidas pela aplicação/API. Não há OpenTelemetry, trace ID ou Datadog encontrado. O `X-Correlation-ID` é capturado no upload e transportado no contrato, mas não há tracing propagado.

## 19. Docker e Infraestrutura

✅ Compose declara PostgreSQL, Redis, RabbitMQ, MinIO, API, dois workers, frontend, Prometheus e Grafana; há volumes, healthchecks para dependências e `depends_on` condicionado em API/worker. Backend roda como usuário não-root (`backend/Dockerfile:15,23`) e instala FFmpeg.

⚠️ Docker não está instalado/disponível nesta máquina (`docker` não reconhecido); portanto `docker compose config`, build, startup, migration em container e `--scale` não foram validados. Não há resource limits, secrets nativos ou restart policies explícitas. A imagem MinIO usa `latest`.

## 20. CI/CD

✅ Existem workflows para backend, frontend, segurança, containers e release. Eles configuram lint/type-check/test/build, npm/uv lockfile, scans pip-audit/npm audit/Gitleaks/CodeQL, Trivy/SBOM e publicação GHCR em tags SemVer.

⚠️ Workflow configurado; execução no GitHub não confirmada. Não há deploy de ambiente, validação de Compose no workflow e não há evidência de proteção administrativa da branch. O release possui permissões de escrita e publica `latest`, risco operacional que exige revisão de governança.

## 21. Testes

| Tipo | Estado |
|---|---|
| Backend unitário | ⚠️ 5 arquivos; contratos, health, ZIP e retry cobertos superficialmente |
| Backend integração/API/auth/ownership | ❌ Não encontrado |
| Worker/RabbitMQ/PostgreSQL/Redis/MinIO | ❌ Não encontrado |
| Concorrência/resiliência E2E | ❌ Não encontrado |
| Frontend unitário | ❌ `npm test`: 0 testes |
| Playwright | ⚠️ 2 smoke passaram: login carrega e registro valida campos obrigatórios |

`uv run pytest` abortou com Windows fatal exception/access violation dentro de `pydantic_core` no Python 3.14.0a5. Não há contagem confiável de testes backend executados.

## 22. Qualidade de Código

✅ Ruff format check e Ruff lint passaram; TypeScript `npm run lint` passou; Angular production build passou. O projeto declara mypy strict.

⚠️ Mypy sofreu access violation no mesmo ambiente e não produziu resultado confiável. O frontend possui componentes e templates muito compactados em uma linha, o que reduz legibilidade/manutenibilidade. Não há cobertura de domínio suficiente para sustentar qualidade de produção.

## 23. Documentação

✅ README documenta arquitetura, execução, endpoints, testes, escala e runbook; existem `docs/runbooks/video-processing.md`, `docs/security.md`, `.env.example`, Makefile e política `SECURITY.md`.

⚠️ Comandos documentados não foram todos executados com infraestrutura real. O README descreve notificações como fluxo, mas também admite que a tela ainda usa dados locais; a documentação deve distinguir claramente implementação aparente de comportamento validado.

## 24. Débito Técnico

Foram encontrados usos legítimos de `mock` somente em teste de retry, e `placeholder` em dependência lockfile/HTML. Não foram encontrados TODO/FIXME/HACK/NotImplemented relevantes no código executável.

Débitos concretos: notification scaffold/log-only; dados hardcoded na tela de notificações; `logout` no-op; ausência de `/events`; métricas referenciadas mas não instrumentadas; testes de integração inexistentes; falta de locking do outbox; defaults inseguros; e comandos Alembic que não carregam o pacote sem configuração adicional de `PYTHONPATH`.

## 25. Validação do Fluxo MVP

| Etapa | Status | Evidência/validação |
|---|---|---|
| 1. Criar conta | ⚠️ Parcial | rota/código em `main.py:127`; sem teste backend/DB |
| 2. Login | ⚠️ Parcial | rota e Argon2 em `main.py:143`; sem execução contra DB |
| 3. Enviar vídeo | ⚠️ Parcial | `create_video()` e serviço frontend; sem backend/MinIO |
| 4. Persistir metadata | ✅ Implementado por código | `Video` + commit/outbox em `main.py:217-246` |
| 5. Armazenar vídeo | ✅ Implementado por código | `storage.upload()` em `main.py:214-216`; não executado |
| 6. Enviar job RabbitMQ | ⚠️ Parcial | outbox e publisher; broker não executado |
| 7. Worker consumir | ⚠️ Parcial | `queue.consume(handle)`; não executado |
| 8. Extrair frames | ✅ Implementado por código | `processor.py:17-47`; teste só cobre ZIP |
| 9. Criar ZIP | ✅ Implementado | `make_zip()` e `test_processor.py` |
| 10. Armazenar resultado | ⚠️ Parcial | upload + `exists`; MinIO não validado |
| 11. COMPLETED | ⚠️ Parcial | `finish()`; sem execução worker/DB |
| 12. Frontend exibir status | ⚠️ Parcial | polling/dashboard; sem API real |
| 13. Download ZIP | ⚠️ Parcial | presigned URL + UI; sem MinIO |
| 14. FAILED | ⚠️ Parcial | exceções/retry/DLQ em código; sem execução |
| 15. Notificação ao usuário | ❌ Não implementado | worker apenas loga; UI hardcoded |

**VALIDADO EM EXECUÇÃO: NÃO.** O fluxo MVP completo não foi executado.

## 26. Matriz dos Requisitos do Hackathon

| Requisito | Status | Evidência | Validação | Gap |
|---|---|---|---|---|
| Múltiplos vídeos simultaneamente | ❓ Não confirmado | prefetch/lease e worker existem | Código | escala não executada |
| Nenhuma requisição perdida em pico | ⚠️ Parcial | outbox durável | Código | sem teste de carga/limites |
| Autenticação | ⚠️ Parcial | JWT + Argon2 + rotas | Código | sem testes e revogação |
| Listagem de status | ⚠️ Parcial | `GET /videos`, polling | Código | integração não executada |
| Notificação em erro | ❌ Não implementado | consumer só loga | Código | sem persistência/provedor/UI real |
| Persistência | ✅ Implementado por código | modelos + migrations | Código | banco não conectado na auditoria |
| Escalabilidade | ❓ Não confirmado | Compose/workers | Documentação | `--scale` não executado |
| GitHub | ✅ Implementado por configuração | `.github/workflows` | Código | execução remota não confirmada |
| Testes | ⚠️ Parcial | pytest/Playwright | Teste | cobertura de integração ausente |
| CI/CD | ⚠️ Parcial | cinco workflows | Código | resultados/deploy não confirmados |
| Arquitetura documentada | ✅ Implementado | README/runbook | Documentação | divergências ainda existem |
| Script/migration de banco | ✅ Implementado por código | Alembic 0001–0003 | Código | `current` não executou |

## 27. Matriz Arquitetura Planejada vs Real

| Componente planejado | Encontrado | Utilizado | Validado | Evidência | Observação |
|---|---|---|---|---|---|
| Angular 22 | Sim | Sim | Sim, build/E2E smoke | `package.json` | fluxo real não validado |
| Tailwind | Sim | Não confirmado | Não | config/package | CSS próprio predominante |
| Angular Material | Sim | Não confirmado | Não | package | sem `mat-*` encontrado |
| FastAPI | Sim | Sim | Não | `main.py` | backend runtime indisponível |
| PostgreSQL | Compose/driver | Sim por código | Não | `db.py`, migrations | sem conexão |
| Redis | Compose/driver | Sim | Não | progress/lease | sem conexão |
| RabbitMQ | Compose/aio-pika | Sim por código | Não | messaging/worker | sem broker |
| MinIO | Compose/SDK | Sim por código | Não | `minio_storage.py` | sem storage |
| FFmpeg | Dockerfile | Sim no worker | Não | `processor.py` | sem vídeo real |
| video-worker | Sim | Sim por código | Não | `worker/main.py` | sem execução |
| notification-worker | Sim | Consome/loga | Não | `notification_worker/main.py` | notificação não persiste |
| OpenTelemetry | Não encontrado | Não | Não | busca no repositório | gap |
| Prometheus | Sim | API expõe uma métrica | Não | `main.py`, config | séries do dashboard faltam |
| Grafana | Sim | Configurado | Não | dashboard/provisioning | sem datasource em runtime |
| Datadog | Não encontrado | Não | Não | busca no repositório | opcional planejado |
| GitHub Actions | Sim | Configurado | Não | `.github/workflows` | execução remota desconhecida |
| pytest | Sim | Sim | Não | `backend/tests` | access violation |
| Playwright | Sim | Sim | Sim, 2/2 | `smoke.spec.ts` | somente smoke público |
| Testcontainers | Não encontrado | Não | Não | busca no repositório | gap de integração |

## 28. Score do Projeto

| Área | Nota | Motivo |
|---|---:|---|
| Arquitetura | 7,0 | separação API/worker/outbox clara; runtime não validado |
| Backend | 6,0 | rotas e fluxo principal existem; testes e tratamento operacional incompletos |
| Frontend | 7,0 | build, navegação e smoke passam; notificações fake |
| Mensageria | 6,5 | topology/ACK/retry/outbox; sem execução/idempotência de consumidor |
| Persistência | 6,5 | models/migrations/outbox; constraints e estado real não confirmados |
| Processamento | 7,0 | FFmpeg seguro, ZIP e timeout; sem vídeo real |
| Resiliência | 6,0 | retry/lease/ACK; cenários distribuídos não testados |
| Segurança | 4,5 | ownership e Argon2 bons; defaults, localStorage e revogação fracos |
| Observabilidade | 4,0 | endpoint/stack existem; instrumentação insuficiente |
| Testes | 3,5 | dois smoke E2E e poucos unitários; zero frontend unitários |
| CI/CD | 6,5 | workflows e scans configurados; execução não confirmada |
| Docker/Infra | 6,0 | Compose amplo e non-root; Docker indisponível, sem limits/restart |
| Documentação | 7,0 | README/runbooks completos; algumas afirmações excedem validação |
| UX | 7,0 | interface dark responsiva e fluxos visuais; dados de notificações fake |
| Prontidão para apresentação | 5,0 | demo visual provável; backend E2E e infraestrutura ainda não comprovados |

**SCORE GERAL / 10: 5,8.**

## 29. 🚨 Gaps críticos antes da entrega

1. **CRITICAL — Notificação não funcional.** Evidência: `notification_worker/main.py:15-25` só registra log e `notifications.component.ts:4` usa dados fixos. Impacto: requisito de notificar erro não é demonstrável. Identificado estaticamente.
2. **HIGH — Fluxo distribuído não validado.** Docker não está disponível; pytest backend abortou; não há execução API/DB/MQ/MinIO/worker. Impacto: login, upload, processamento e download podem falhar na apresentação. Limitação de validação, não prova de ausência.
3. **HIGH — Tokens não revogáveis e refresh em localStorage.** Evidência: `auth.py:46-55`, `main.py:169-171`, `auth.service.ts:10-19`. Impacto: logout não encerra sessão e XSS pode expor refresh token. Identificado estaticamente.
4. **HIGH — Métricas do dashboard não correspondem à instrumentação encontrada.** Evidência: dashboard Grafana referencia séries de HTTP/retry/duração/DLQ; código só declara `videos_received_total`. Impacto: observabilidade operacional enganosa. Identificado estaticamente.
5. **HIGH — Outbox sem claim/locking.** Evidência: `main.py:66-93` seleciona eventos pendentes sem lock. Impacto: múltiplas APIs podem publicar duplicatas em escala. Identificado estaticamente.
6. **MEDIUM — Ausência de testes de integração e concorrência.** Evidência: `backend/tests` e smoke E2E. Impacto: ownership, redelivery, DLQ e MVP não têm prova automatizada. Identificado por inventário.

## 30. Backlog priorizado

| Prioridade | Tarefa | Motivo | Evidência | Arquivos envolvidos | Esforço |
|---|---|---|---|---|---|
| P0 | Implementar persistência/consulta de notificações e conectar UI | requisito obrigatório ausente | worker log-only/UI hardcoded | notification worker, API, frontend, migration | L |
| P0 | Subir ambiente e executar E2E real com migration, vídeo e download | demo não validada | Docker indisponível | Compose, API, workers, Playwright | L |
| P0 | Remover defaults inseguros e definir política de segredo/revogação | risco de segurança | config/Compose/auth | config, Compose, auth/frontend | M |
| P1 | Adicionar testes API/auth/ownership/upload e worker com dependências | cobertura crítica ausente | `backend/tests` | backend/tests, CI | L |
| P1 | Corrigir claim/locking e deduplicação do outbox | duplicidade em escala | `main.py:66-93` | API/messaging/models | M |
| P1 | Instrumentar métricas usadas no Grafana e health/readiness operacionais | dashboard inconsistente | Grafana vs `main.py` | API, worker, dashboard | M |
| P1 | Validar escala, redelivery, retry, DLQ e falhas de dependências | resiliência não comprovada | sem testes/runtime | Compose, testes, runbook | L |
| P2 | Adicionar endpoint de eventos/status em tempo real, se requisito mantido | endpoint planejado ausente | busca de rotas | API/frontend | M |
| P2 | Avaliar cookies HttpOnly/SameSite ou estratégia equivalente | reduzir exposição de tokens | `auth.service.ts` | auth API/frontend | M |
| P3 | Adicionar Testcontainers, tracing e Datadog se exigidos | melhoria/arquitetura opcional | não encontrado | CI/infra | XL |

## 31. Roadmap recomendado

1. Disponibilizar Docker/ambiente de dependências e corrigir a execução de Alembic/Python.
2. Implementar e validar notificações persistentes, inclusive falha de processamento.
3. Executar o MVP completo com vídeo real e registrar evidências de cada etapa.
4. Criar testes de API, autenticação, ownership, integração e worker; depois testar concorrência/redelivery/DLQ.
5. Corrigir segredo padrão, logout/revogação e armazenamento de refresh token.
6. Corrigir outbox concorrente e validar duplicidade/idempotência.
7. Alinhar métricas emitidas ao dashboard e validar Prometheus/Grafana.
8. Executar checks completos em CI e preparar roteiro de apresentação baseado apenas no comportamento comprovado.

## 32. Comandos executados

| Comando | Objetivo | Resultado | Alterou estado? |
|---|---|---|---|
| `rg --files ...` | inventário do repositório | concluído | NÃO |
| `git status --short` | identificar alterações prévias | worktree já modificado | NÃO |
| `Get-Content`/`Select-String` | ler arquivos, estrutura e instruções | concluído | NÃO |
| `uv run pytest --cov=apps --cov=packages ...` | testes backend | access violation em pydantic_core/Python 3.14.0a5 | NÃO |
| `uv run ruff format --check .` | formato backend | 28 arquivos já formatados | NÃO |
| `uv run ruff check .` | lint backend | passou | NÃO |
| `uv run mypy apps packages` | type checking | access violation, sem resultado confiável | NÃO |
| `npm run lint` | TypeScript check | passou | NÃO |
| `npm test` | testes frontend | 0 testes, processo passou | NÃO |
| `npm run build` | build Angular | passou | NÃO |
| `npx playwright test` | smoke E2E | 2 passaram | NÃO |
| `docker compose config --quiet` | validar Compose | não executado: Docker não reconhecido | NÃO |
| `uv run alembic current` | versão DB | falhou: `ModuleNotFoundError: fiapx_api` | NÃO |
| `uv run alembic heads` | heads das migrations | `0003_outbox (head)` | NÃO |

## 33. Limitações da auditoria

- Docker/Compose não está disponível nesta máquina; não houve startup, build, scale, healthcheck ou fluxo com serviços reais.
- Banco, RabbitMQ, Redis e MinIO não foram conectados; estado aplicado de migrations não foi confirmado.
- Python usado é `3.14.0a5` e provocou access violation em `pydantic_core` durante pytest/mypy; não é possível classificar a suíte backend como passando/falhando por testes.
- GitHub Actions, registry, CodeQL, Gitleaks, Trivy, pip-audit e npm audit não foram executados remotamente nesta auditoria.
- Não foram fornecidos secrets de ambiente; configurações default foram analisadas estaticamente e não exibidas como segredos reais.
- O fluxo MVP completo e teste de carga/concorrência não foram executados.
- A presença de código, configuração ou documentação foi diferenciada de uso e comportamento validado.

## 34. Conclusão

### Atualização pós-auditoria — 2026-09-07

O diagnóstico acima é histórico e foi preservado. As correções posteriores foram registradas em `docs/METAS_CODEX.md` e validadas executando Docker pelo WSL Ubuntu-22.04. O Compose subiu com dois `video-worker`, as migrations avançaram até `0007_video_progress_stage`, e os fluxos de autenticação, upload, processamento FFmpeg, ZIP, download, falha, DLQ, notificação, ownership e progresso por percentual/etapa foram executados. A suíte backend passou em Python estável (`15 passed, 2 skipped`), o frontend passou lint, 3 testes Vitest, build e 4 E2E; `npm audit --audit-level=high` não reportou vulnerabilidades HIGH/CRITICAL.

> O parágrafo a seguir é a conclusão da auditoria inicial e não substitui a atualização pós-auditoria acima.

O projeto já possui uma base arquitetural coerente para processamento assíncrono e uma interface frontend compilável, com evidências estáticas fortes de separação entre API e worker, ownership, armazenamento de objetos, retry e outbox. Entretanto, ainda não há evidência suficiente para declarar o sistema pronto para produção ou para uma demonstração ponta a ponta: notificações são scaffold, segurança de sessão precisa ser endurecida, observabilidade está incompleta e os componentes distribuídos não foram executados juntos. A próxima prioridade objetiva é tornar notificações reais e validar o MVP completo em ambiente Docker, seguida de testes de integração e concorrência.
