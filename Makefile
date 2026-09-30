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

.PHONY: help setup report lint format test test-cov run monitor \
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

report: ## Generate the lab report PDF from docs/lab-report.md
	pandoc docs/lab-report.md \
		--from markdown \
		--pdf-engine=xelatex \
		--toc --toc-depth=3 \
		--number-sections \
		-V geometry:margin=2.5cm \
		-V fontsize=11pt \
		-V colorlinks=true \
		-V linkcolor=blue \
		-V urlcolor=blue \
		-o docs/lab-report.pdf

all: lint test ## Run lint and tests

docker-ps: ## Show running containers with their IP addresses
	$(COMPOSE) -f $(COMPOSE_FILE) ps

docker-shell: ## Open an interactive shell in the monitor container
	$(COMPOSE) -f $(COMPOSE_FILE) exec monitor bash

docker-monitor: ## Run the monitoring script inside the monitor container
	$(COMPOSE) -f $(COMPOSE_FILE) exec monitor \
		uv run python -m scripts.network_monitor --config scripts/config.yaml

docker-targets: ## Inspect tc netem rules on each target
	@echo "--- target-alpha ---"
	$(COMPOSE) -f $(COMPOSE_FILE) exec target-alpha tc qdisc show dev eth0
	@echo "--- target-beta ---"
	$(COMPOSE) -f $(COMPOSE_FILE) exec target-beta tc qdisc show dev eth0

docker-clean-reports: ## Fix ownership of reports written by the container
	sudo chown -R $$(id -u):$$(id -g) reports/
