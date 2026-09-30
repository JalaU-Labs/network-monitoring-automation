# ==============================================================================
# network-monitoring-automation - Makefile
# Week 05 Lab - Jala University
# ==============================================================================

SHELL := /bin/sh

UV          := uv
RUFF        := $(UV) run ruff
PYTEST      := $(UV) run pytest
PYTHON      := $(UV) run python
COMPOSE     := docker compose
COMPOSE_FILE:= docker-compose.yml

.PHONY: help setup lint format test test-cov run monitor \
        docker-build docker-up docker-down docker-logs \
        docker-clean clean all

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv and install all dependencies
	$(UV) sync

lint: ## Run ruff check (no changes)
	$(RUFF) check .

format: ## Run ruff format + auto-fix imports
	$(RUFF) check --fix .
	$(RUFF) format .

test: ## Run pytest
	$(PYTEST)

test-cov: ## Run pytest with coverage report
	$(PYTEST) --cov=scripts --cov-report=term-missing --cov-report=html

run: ## Run the monitoring script locally (uses scripts/config.yaml)
	$(PYTHON) -m scripts.network_monitor

monitor: run ## Alias for `run`

docker-build: ## Build all Docker images
	$(COMPOSE) -f $(COMPOSE_FILE) build

docker-up: ## Start the Docker network and all containers
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

docker-down: ## Stop containers and remove network created by compose
	$(COMPOSE) -f $(COMPOSE_FILE) down --remove-orphans

docker-logs: ## Tail logs from all containers
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f

docker-clean: docker-down ## Remove containers, images, volumes, networks and build cache
	$(COMPOSE) -f $(COMPOSE_FILE) down --rmi all --volumes --remove-orphans
	docker network prune -f
	docker builder prune -f

clean: ## Remove local caches and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache"  -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage reports/*.json reports/*.log reports/*.md 2>/dev/null || true

all: lint test ## Run lint and tests
