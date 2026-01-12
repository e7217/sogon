.PHONY: help install start stop restart status logs clean test dev

# Configuration
SHELL := /bin/bash
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
API_PORT = 8000
FRONTEND_PORT = 3000
API_LOG = /tmp/sogon_server.log
FRONTEND_LOG = /tmp/frontend_server.log

help: ## Show available commands
	@echo "SOGON Project Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Dependencies installed"

start: ## Start backend + frontend servers
	@echo "🚀 Starting servers..."
	@$(MAKE) stop > /dev/null 2>&1 || true
	@source $(VENV)/bin/activate && \
		nohup $(PYTHON) api_server.py > $(API_LOG) 2>&1 & \
		echo $$! > /tmp/sogon_api.pid
	@cd frontend && \
		nohup npx http-server -p $(FRONTEND_PORT) -c-1 --cors > $(FRONTEND_LOG) 2>&1 & \
		echo $$! > /tmp/sogon_frontend.pid
	@sleep 2
	@$(MAKE) status

stop: ## Stop all servers
	@echo "🛑 Stopping servers..."
	@if [ -f /tmp/sogon_api.pid ]; then \
		kill -9 $$(cat /tmp/sogon_api.pid) 2>/dev/null || true; \
		rm -f /tmp/sogon_api.pid; \
	fi
	@if [ -f /tmp/sogon_frontend.pid ]; then \
		kill -9 $$(cat /tmp/sogon_frontend.pid) 2>/dev/null || true; \
		rm -f /tmp/sogon_frontend.pid; \
	fi
	@lsof -ti:$(API_PORT) | xargs -r kill -9 2>/dev/null || true
	@lsof -ti:$(FRONTEND_PORT) | xargs -r kill -9 2>/dev/null || true
	@echo "✅ Servers stopped"

restart: ## Restart servers
	@$(MAKE) stop
	@sleep 1
	@$(MAKE) start

status: ## Check server status
	@echo "📊 Server Status:"
	@echo ""
	@echo "Backend API (port $(API_PORT)):"
	@if curl -s http://localhost:$(API_PORT)/health > /dev/null 2>&1; then \
		echo "  ✅ Running"; \
		curl -s http://localhost:$(API_PORT)/health | jq -r '"  Status: \(.status) | Worker: \(.config.worker_status.running) | Jobs: \(.config.repository_stats.total_jobs)"'; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo ""
	@echo "Frontend (port $(FRONTEND_PORT)):"
	@if curl -s -o /dev/null -w "%{http_code}" http://localhost:$(FRONTEND_PORT) | grep -q 200; then \
		echo "  ✅ Running"; \
	else \
		echo "  ❌ Not running"; \
	fi

logs: ## View logs (Ctrl+C to exit)
	@echo "📋 Monitoring logs (Ctrl+C to exit)..."
	@tail -f $(API_LOG) $(FRONTEND_LOG)

logs-api: ## View API logs only
	@tail -f $(API_LOG)

logs-frontend: ## View frontend logs only
	@tail -f $(FRONTEND_LOG)

clean: ## Clean temporary files and cache
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -f $(API_LOG) $(FRONTEND_LOG)
	rm -f /tmp/sogon_*.pid
	@echo "✅ Cleanup complete"

test: ## Run tests
	@echo "🧪 Running tests..."
	source $(VENV)/bin/activate && pytest -v

dev: ## Development mode (auto-reload)
	@echo "🔧 Starting in dev mode..."
	source $(VENV)/bin/activate && uvicorn api_server:app --reload --host 0.0.0.0 --port $(API_PORT)

health: ## Health check
	@curl -s http://localhost:$(API_PORT)/health | jq

jobs: ## List all jobs
	@curl -s http://localhost:$(API_PORT)/api/v1/jobs | jq

open: ## Open frontend in browser
	@xdg-open http://localhost:$(FRONTEND_PORT) 2>/dev/null || open http://localhost:$(FRONTEND_PORT) 2>/dev/null || echo "Please open manually: http://localhost:$(FRONTEND_PORT)"
