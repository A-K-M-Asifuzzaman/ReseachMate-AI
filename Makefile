.PHONY: help infra infra-down backend frontend install test fmt

help:
	@echo "ResearchMate AI — common tasks"
	@echo "  make infra        # start postgres + qdrant + neo4j (docker compose)"
	@echo "  make infra-down   # stop infra"
	@echo "  make install      # install backend + frontend deps"
	@echo "  make backend      # run FastAPI (reload) on :8000"
	@echo "  make frontend     # run Next.js dev on :3000"
	@echo "  make test         # run backend tests"

infra:
	docker compose up -d

infra-down:
	docker compose down

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest -q
