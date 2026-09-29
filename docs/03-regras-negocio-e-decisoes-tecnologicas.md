# FIAP X — Regras de negócio e decisões tecnológicas

> Documento **as built**: catálogo das regras observadas em código, migrations, configurações e pipeline em 28/09/2026. “Regra de negócio” descreve comportamento que protege a jornada ou o domínio; “restrição técnica” detalha como ele é garantido.

## 1. Regras de negócio

### 1.1 Conta, identidade e sessão

| ID | Regra | Justificativa de negócio | Garantia atual |
|---|---|---|---|
| RN-01 | Cada conta possui e-mail único. | Evita identidades ambíguas e permite login unívoco. | Índice/constraint única e validação antes de criar; conflito `409`. |
| RN-02 | Nome, e-mail e senha são necessários para cadastro; nome ausente no contrato de API recebe a parte anterior ao `@` do e-mail. | Todo vídeo e notificação precisa de dono identificável, mantendo compatibilidade com clientes de API. | Formulário exige nome; API aceita nome opcional e define fallback. |
| RN-03 | A senha de cadastro deve ter no mínimo 8 caracteres na experiência web. | Define patamar mínimo de qualidade da credencial. | Validador Angular; a API atualmente não repete essa regra, ponto a ser alinhado se houver clientes externos. |
| RN-04 | Senhas nunca são persistidas em texto puro. | Protege credenciais se a base for exposta. | Argon2 armazena `password_hash`. |
| RN-05 | Recursos privados exigem usuário autenticado com access token do tipo `access`. | Impede acesso anônimo ou uso indevido de token de renovação. | Bearer JWT HS256, validação de expiração/tipo e carregamento do usuário. |
| RN-06 | Uma sessão pode ser renovada somente com refresh ativo, não expirado e não revogado; cada renovação invalida o refresh anterior. | Diminui janela de roubo de sessão e evita reuso do token. | Refresh opaco hasheado, bloqueio da linha, rotação e `revoked_at`. |
| RN-07 | Logout invalida a sessão de refresh identificada e remove cookie. | Encerra a continuidade da sessão no servidor e no navegador. | Revogação persistida e `delete_cookie`. |

### 1.2 Propriedade e privacidade

| ID | Regra | Justificativa de negócio | Garantia atual |
|---|---|---|---|
| RN-08 | Todo vídeo pertence obrigatoriamente a um usuário. | A biblioteca e os resultados são privados por padrão. | `videos.user_id` não nulo desde migration 0006. |
| RN-09 | Só o proprietário pode listar, ver detalhes, prévia, miniatura, baixar ou excluir vídeo. | Evita vazamento de mídia e resultados. | Todo endpoint filtra por `video_id` e `user_id`; não encontrado e sem posse retornam `404`. |
| RN-10 | Só o destinatário pode ler ou alterar suas notificações. | Notificações podem revelar título e falha de processamento. | Filtros por `notification.user_id`; `404` em acesso indevido. |
| RN-11 | Original e resultado são armazenados em prefixos de usuário e vídeo. | Reduz colisão de nomes e facilita isolamento/auditoria. | Chaves incluem UUID de usuário e UUID de vídeo. |

### 1.3 Aceite de upload

| ID | Regra | Justificativa de negócio | Garantia atual |
|---|---|---|---|
| RN-12 | Aceita somente `.mp4`, `.mov`, `.avi`, `.mkv` e `.webm`. | Delimita codecs/containers suportados pelo pipeline. | Validação no Angular e no backend com `ALLOWED_VIDEO_EXTENSIONS`. |
| RN-13 | Um arquivo não pode ultrapassar 500 MiB por padrão. | Protege capacidade de transferência, armazenamento e processamento. | Validação inicial no frontend, leitura limitada no backend, `client_max_body_size 500m` no Nginx e `MAX_UPLOAD_SIZE_BYTES` configurável. |
| RN-14 | O arquivo precisa ter nome, conteúdo não vazio e MIME compatível com vídeo (ou octet-stream). | Evita objetos inúteis e reduz conteúdo disfarçado. | Nome é saneado; extensão, MIME e tamanho são validados. |
| RN-15 | O nome recebido não determina a chave interna. | Evita traversal, colisões e caracteres de controle. | API usa apenas basename saneado e UUID na chave de MinIO. |
| RN-16 | Um upload só é aceito como enfileirado depois de original, vídeo, trabalho e evento pendente estarem consistentes. | O usuário não deve ter um vídeo “aceito” sem processamento recuperável. | Original no MinIO; transaction cria `Video`, `ProcessingJob` e `OutboxEvent`; rollback remove o original. |
| RN-17 | O aceite é assíncrono e retorna `202`/`QUEUED`, não o resultado. | Conversão pode ser longa e não deve prender a interação do usuário. | API devolve cedo; outbox inicia o pipeline. |

### 1.4 Processamento e resultado

| ID | Regra | Justificativa de negócio | Garantia atual |
|---|---|---|---|
| RN-18 | Um vídeo aceito percorre `QUEUED → PROCESSING → COMPLETED` ou `FAILED`; falha transitória pode voltar a `QUEUED`. | Cria ciclo de vida compreensível, auditável e exibível na UI. | Enum, check constraints e transições no worker. |
| RN-19 | Apenas um worker pode iniciar efetivamente um vídeo em fila. | Impede duplicação de custo e resultados concorrentes. | Lease Redis e `UPDATE ... WHERE status = QUEUED`. |
| RN-20 | O vídeo precisa conter stream de vídeo, não exceder 3.600 s, 3.840 px de largura ou 2.160 px de altura por padrão. | Limita insumos inválidos e custo operacional. | `ffprobe` antes da extração; limites configuráveis. |
| RN-21 | A extração gera uma imagem JPEG a cada 1 segundo por padrão. | É a transformação entregue pelo produto. | Filtro FFmpeg `fps=1/video_frame_interval_seconds`. |
| RN-22 | O resultado é um único `frames.zip` com frames ordenados `frame_000001.jpg` etc. | Simplifica download e preserva ordem temporal. | Diretório temporário exclusivo e ZIP DEFLATED ordenado. |
| RN-23 | Um resultado só é disponibilizado se o ZIP foi gravado e confirmado no armazenamento. | Não oferecer download de objeto inexistente/corrompido. | Worker chama `storage.exists` antes de concluir; `download_available` exige `COMPLETED` + `result_object_key`. |
| RN-24 | Falha de entrada é definitiva; falha inesperada/dependência é repetida até o limite. | Evita desperdiçar tentativas em arquivo inválido e tolera indisponibilidades temporárias. | `ValueError`/`PermanentError` falham; demais exceções usam retry. |
| RN-25 | Há no máximo 3 tentativas no valor padrão e atraso exponencial com jitter. | Reduz tempestade de retries, mantendo recuperação automática. | `attempt < VIDEO_PROCESSING_MAX_RETRIES`, fila retry com TTL. |
| RN-26 | Percentual e etapa são atualizados durante o processamento. | Dá transparência ao usuário para um fluxo naturalmente demorado. | Redis para leitura rápida e PostgreSQL como cópia persistente. |
| RN-27 | A mensagem de erro persistida é limitada a 500 caracteres. | Dá diagnóstico sem gravar payloads enormes/sensíveis no domínio. | Truncamento no worker e coluna limitada onde aplicável. |

### 1.5 Biblioteca, download e notificações

| ID | Regra | Justificativa de negócio | Garantia atual |
|---|---|---|---|
| RN-28 | A lista de vídeos retorna primeiro os mais recentes e pagina entre 1 e 100 itens por página. | Mantém navegação estável e protege a API de consultas excessivas. | Ordenação decrescente, normalização de `page` e clamp de `page_size`. |
| RN-29 | Só vídeos concluídos aparecem em “Meus vídeos”; ativos e falhos aparecem no Dashboard. | Separa biblioteca de resultados disponíveis do acompanhamento operacional. | Filtros da UI; API conserva todos no endpoint de lista. |
| RN-30 | Prévia entrega o original; miniatura é o primeiro JPEG do ZIP. | Oferece confirmação visual com baixo esforço no fluxo existente. | Endpoints autenticados `preview` e `thumbnail`; miniatura requer conclusão. |
| RN-31 | Download só é autorizado para vídeo concluído com resultado. | Impede expectativa de conteúdo ainda inexistente. | Endpoints retornam `404` quando a condição não é satisfeita. |
| RN-32 | Cada término de processamento deve produzir uma notificação de sucesso ou falha, no máximo uma vez por evento. | Fecha a jornada sem exigir que usuário fique acompanhando a tela. | Worker de notificação e `event_id` único com insert idempotente. |
| RN-33 | Notificações começam `PENDING` e podem ser lidas individualmente ou em massa. | Permite identificar novidades e limpar a central. | `status`, `read_at`, PATCH individual e POST coletivo. |
| RN-34 | A consulta de notificações retorna no máximo 100 itens recentes e contagem de pendentes. | Controla volume e mantém o indicador correto. | `ORDER BY created_at DESC LIMIT 100` e contagem separada. |

## 2. Invariantes e validações de persistência

| Invariante | Como é aplicado |
|---|---|
| `videos.file_size >= 0` | Check constraint no PostgreSQL. |
| `videos.progress` entre 0 e 100 | Check constraint no PostgreSQL. |
| Status de vídeo/trabalho pertencem ao conjunto conhecido | Check constraints com `UPLOADING`, `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`. |
| Tentativa de trabalho não é negativa | Check constraint no PostgreSQL. |
| Chave de objeto e e-mail não colidem | Constraints únicas. |
| Um evento não cria duas notificações | `notifications.event_id` único. |

## 3. Decisões tecnológicas e justificativas

| Escolha | Justificativa | Consequências/limites assumidos |
|---|---|---|
| Angular 22 + TypeScript | SPA tipada, componentes standalone, router, forms e Signals adequados à experiência reativa de dashboard. | Access token fica no `localStorage`; há mitigação por refresh HttpOnly, mas proteção contra XSS continua essencial. |
| Angular Material + Tailwind | Material atende componentes/semântica; Tailwind permite acabamento visual rápido e consistente. | Duas abordagens de estilo exigem disciplina para não duplicar padrões. |
| Nginx | Serve build estático com baixo custo e fornece proxy same-origin para a API. | Não substitui um gateway/WAF de produção. |
| FastAPI + Pydantic 2 | APIs assíncronas, validação declarativa e OpenAPI automático; bom encaixe com I/O de banco, broker e storage. | Regras de domínio precisam ser mantidas também em testes/migrations para não ficarem apenas em handlers. |
| Python 3.14 + `uv` | Linguagem adequada ao ecossistema FFmpeg/automação; `uv.lock` dá instalação reprodutível e rápida. | Requer runtime recente e imagem compatível. |
| SQLAlchemy async + Alembic | ORM tipado e migrations versionadas preservam evolução do modelo relacional. | Operações de domínio críticas ainda precisam de SQL condicional explícito, como já ocorre no claim do job. |
| PostgreSQL 16 | ACID, constraints, locks e consultas relacionais sustentam a fonte da verdade e a outbox. | É dependência central: indisponibilidade pausa publicação e atualização confiável. |
| MinIO/S3 | Armazena arquivos grandes fora do banco e permite migração natural a provedores S3. | API ainda faz proxy do preview e ZIP; para escala externa podem ser necessários URLs pré-assinados ou CDN. |
| RabbitMQ topic + AMQP | Separa serviços, permite filas duráveis, DLQ, TTL e scale-out de workers. | Entrega é ao menos uma vez; consumidores precisam ser idempotentes. |
| Transactional outbox | Garante que evento de upload sobreviva à falha entre commit SQL e publish AMQP. | Há latência de polling de até ~1 s ocioso e necessidade de monitorar eventos não publicados. |
| Redis | É muito eficiente para lease com TTL, renovação atômica e progresso de leitura rápida. | Não pode ser fonte de verdade; indisponibilidade bloqueia coordenação segura do worker. |
| FFprobe/FFmpeg em subprocesso sem shell | Solução madura para inspecionar e extrair mídia; argumentos separados evitam injeção por shell. | Operação é CPU/memória intensiva e demanda timeout, limites e isolamento. |
| Diretório temporário por vídeo + chave de resultado determinística | Evita mistura entre jobs e torna repetição idempotente sobre o mesmo resultado lógico. | É necessário dimensionar disco temporário e políticas de retenção do storage. |
| Workers independentes | Processamento e notificação escalam/falham isoladamente da API. | A consistência é eventual: notificação pode aparecer após a tela já mostrar conclusão. |
| `prefetch_count=1` | Um worker trata somente um vídeo de cada vez, equilibrando jobs longos e protegendo memória. | Para throughput maior, escalam-se réplicas em vez de concorrência interna. |
| Prometheus + Grafana | Padrão aberto para métricas e dashboards; expõe contadores, histogramas e saúde operacional. | Não substitui logs centralizados, tracing distribuído ou alertas configurados. |
| Docker Compose | Reproduz stack completa localmente e facilita demonstração/E2E. | Não é orquestrador de produção; HA, autoscaling e secret management exigem plataforma adicional. |
| GitHub Actions + CodeQL + auditorias + Trivy/SBOM | Automatiza qualidade, vulnerabilidades, segredos, imagens e rastreabilidade de supply chain. | Alguns checks estão configurados como advisory/`continue-on-error`; a proteção real depende de branch rules e política do repositório. |

## 4. Segurança por decisão

| Vetor | Controle implementado | Motivo |
|---|---|---|
| Roubo de senha | Argon2 | Resistente a ataques offline comparado a hashes rápidos. |
| Roubo/reuso de refresh | Token opaco, hash no banco, cookie HttpOnly/SameSite, rotação e revogação | Não expõe refresh ao JavaScript e limita reuso. |
| Acesso horizontal indevido | Filtro por proprietário e resposta `404` | Protege mídia/notificações e reduz enumeração. |
| Upload malicioso | Extensão, MIME, limite, basename saneado, `ffprobe`, timeout e limites de resolução/duração | Reduz tipos impróprios, traversal e consumo excessivo. |
| Execução de comando | `create_subprocess_exec` com argumentos separados | Não há interpolação de nome de arquivo em shell. |
| Exaustão do worker | CPU, memória e PIDs limitados no Compose; `prefetch=1` | Contém impacto de mídia hostil ou pesada. |
| Segredo padrão em produção | Validação de configuração fora de `local`/`test` | Impede inicializar produção com credenciais de exemplo. |
| CORS com credenciais | Origens configuráveis e específicas | Evita combinação insegura de credenciais com origem curinga. |

## 5. Decisões e lacunas a acompanhar

Estas não invalidam o comportamento atual, mas devem ser tratadas como backlog técnico/produto antes de expansão:

- A API não aplica explicitamente a política mínima de 8 caracteres nem normaliza e-mail; a regra hoje está concentrada no formulário web.
- Não há rate limiting, recuperação de senha, MFA, verificação de e-mail, antivírus de upload ou política de retenção/exclusão automática.
- Não há endpoint/UI de reprocessamento, cancelamento ou exclusão visível, embora `DELETE /videos/{id}` exista.
- A paginação do frontend busca todas as páginas de vídeos antes de paginar em memória; para volumes altos, convém passar paginação e filtros ao backend/UX.
- A DLQ preserva trabalhos que precisam de intervenção, mas não há console administrativo nem runbook de replay automatizado.
- O acesso a preview e download passa pela API; para alto volume, avaliar URLs pré-assinadas de curta duração e CDN sem abrir mão da autorização.
- A observabilidade cobre métricas e logs correlacionáveis; tracing distribuído, alertas e retenção de logs ainda não fazem parte do código.
