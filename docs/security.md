# Segurança e supply chain

## Controles

- Autenticação usa tokens Bearer e autorização verifica o proprietário do vídeo.
- O access token é usado pelo frontend, enquanto o refresh token é opaco, persistido somente como cookie `HttpOnly`/`SameSite=Lax`, rotacionado e revogado no logout.
- Origens CORS são configuradas por `CORS_ORIGINS`; não usar `*` com credenciais.
- Uploads são validados no backend por extensão, MIME, tamanho e `ffprobe`; nomes são reduzidos ao basename.
- FFmpeg/ffprobe são executados com argumentos separados, sem shell, em diretório temporário isolado e com timeout, duração e resolução limitadas.
- O worker possui limites de CPU, memória e processos no Compose; o resultado usa chave determinística para reduzir efeitos duplicados.
- Segredos pertencem ao ambiente de runtime. `.env` é ignorado e `.env.example` contém somente valores fictícios para desenvolvimento.

## Gates automatizados

`ci-security.yml` executa CodeQL para Python/TypeScript, `pip-audit`, `npm audit --audit-level=high` e Gitleaks. O workflow de containers executa Trivy para vulnerabilidades HIGH/CRITICAL corrigíveis e gera SBOM CycloneDX. Falhas críticas bloqueiam a pipeline; médios e baixos devem ser avaliados como débito/advisory.

As dependências são atualizadas via PR e `backend/uv.lock` e `frontend/package-lock.json` são obrigatórios. Dependabot verifica npm, pip, Docker e GitHub Actions semanalmente.

## Supply chain e release

Uma release `vMAJOR.MINOR.PATCH` só publica imagens depois dos gates. As imagens recebem tag imutável baseada no SHA, a tag semver e `latest` apenas em releases. Buildx habilita provenance e SBOM para as imagens publicadas no GHCR.

## Tratamento de incidentes

Não abra uma vulnerabilidade crítica em issue pública. Use o mecanismo privado de Security Advisories do GitHub ou peça aos mantenedores um canal privado pelo repositório. Revogue e substitua imediatamente qualquer credencial exposta.
