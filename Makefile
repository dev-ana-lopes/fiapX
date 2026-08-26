up:
	docker compose up -d
down:
	docker compose down
logs:
	docker compose logs -f
worker-logs:
	docker compose logs -f video-worker notification-worker
test:
	cd backend && uv run pytest
test-backend:
	cd backend && uv run pytest
test-frontend:
	cd frontend && npm test
lint:
	cd backend && uv run ruff check . && uv run mypy apps packages
	cd frontend && npm run build
migrate:
	docker compose run --rm api alembic upgrade head
migration:
	cd backend && uv run alembic revision --autogenerate -m "change"

