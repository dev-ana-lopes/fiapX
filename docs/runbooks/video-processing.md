# Runbook — processamento de vídeos

## Vídeos acumulando na fila

Verifique `http://localhost:15672`, a profundidade de `video.processing`, consumidores ativos, CPU/memória e os logs de `video-worker`. No Windows, prefixe os comandos com `wsl -d Ubuntu-22.04 --`. Escale com `docker compose up -d --scale video-worker=3`.

## Vídeos falhando

Consulte `/api/v1/videos`, a fila `video.processing.dlq`, logs filtrados por `video_id` e erros do FFmpeg. Falhas permanentes resultam em `FAILED`; falhas transitórias usam a fila TTL de retry.

## Nenhum worker disponível

Verifique `docker compose ps`, `docker compose logs video-worker` e `/ready`. A mensagem permanece sem ACK durante a execução e pode ser redeliverada após o container cair.

## Redis indisponível

Redis mantém lease e progresso efêmero. Sem Redis, o worker não deve processar sem coordenação: corrija a dependência antes de escalar ou reprocessar.

## PostgreSQL indisponível

PostgreSQL é a fonte da verdade para status e outbox. O publisher pausa e retoma depois; não considere um upload enfileirado até o evento outbox estar publicado.

## SLO conceitual

- Disponibilidade alvo da API: 99,9%.
- P95 do upload (sem transferência): < 1 s.
- Nenhum job deve ser perdido silenciosamente.
- Falhas definitivas devem produzir estado `FAILED` e evento observável.

## Demonstração

1. `docker compose up -d --build` e migration; no Windows, execute ambos pelo WSL.
2. Escale três workers e envie cinco vídeos.
3. Pare um worker durante `PROCESSING`; suba outro e observe redelivery.
4. Envie um arquivo inválido e observe `FAILED`, a notificação, `video.processing.dlq` e Grafana. Durante `PROCESSING`, a API/UI exibem percentual e etapa corrente.
