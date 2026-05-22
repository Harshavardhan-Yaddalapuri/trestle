.PHONY: dev down setup clean

dev:
	docker compose up --build

down:
	docker compose down

setup:
	@echo "==> Copying .env.example to .env..."
	cp -n .env.example .env 2>/dev/null || echo ".env already exists — skipped"
	@echo "==> Edit .env with your API keys before running 'make dev'"
	@echo "    Required: SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY"
	@echo "    Optional: TAVILY_API_KEY, FIRECRAWL_API_KEY"

clean:
	docker compose down -v --rmi local
