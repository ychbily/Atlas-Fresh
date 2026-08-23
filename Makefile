.PHONY: help install dev test docker docker-test clean clean-docker

# Default target
.DEFAULT_GOAL := help

PYTHON ?= python3
VENV := backend/venv
DOCKER_CMD := $(shell command -v docker 2> /dev/null)

help: ## Show this help message
	@echo "Atlas Fresh — Daily Apple Export Planner"
	@echo ""
	@echo "Prerequisites on a fresh machine:"
	@echo "  - Python 3.10+ (python3)"
	@echo "  - Node.js 18+ & npm"
	@echo "  - Docker & Docker Compose (optional)"
	@echo ""
	@echo "Quick Start Workflows:"
	@echo "  1. Standard Local Run (No Docker required):"
	@echo "     make install   -> Set up Python venv & npm packages"
	@echo "     make dev       -> Run FastAPI (:8000) & React Vite (:5173) locally"
	@echo "     make test      -> Execute backend pytest automated tests"
	@echo "     make clean     -> Clean temporary build files & test cache"
	@echo ""
	@echo "  2. Docker Containerized Run (Requires Docker daemon running):"
	@echo "     make docker        -> Build & start containers (auto-uses sudo if needed)"
	@echo "     make docker-test   -> Run pytest inside Docker backend container"
	@echo "     make clean-docker  -> Stop containers & clean Docker networks"
	@echo ""
	@echo "Available Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Set up Python venv and install dependencies for backend and frontend
	@echo "==> Setting up backend virtual environment..."
	@if [ ! -d "$(VENV)" ]; then \
		$(PYTHON) -m venv $(VENV); \
	fi
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r backend/requirements.txt
	@echo "==> Installing frontend dependencies..."
	cd frontend && npm install
	@echo "==> Installation complete! You can now run 'make dev' or 'make test'."

dev: ## Start backend (FastAPI :8000) and frontend (Vite :5173) locally
	@if [ ! -d "$(VENV)" ]; then \
		echo "==> Virtual environment not found. Running 'make install' first..."; \
		$(MAKE) install; \
	fi
	@echo "==> Starting backend on http://localhost:8000..."
	@echo "==> Starting frontend on http://localhost:5173..."
	@trap 'kill 0' EXIT; \
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend & \
	(cd frontend && npm run dev)

test: ## Run backend unit test suite using Python venv (auto-installs if missing)
	@if [ ! -d "$(VENV)" ]; then \
		echo "==> Virtual environment not found. Running 'make install' first..."; \
		$(MAKE) install; \
	fi
	@echo "==> Running backend automated unit tests..."
	cd backend && ./venv/bin/pytest tests/ -v

docker: ## Build and start both services using Docker Compose (auto-uses sudo if socket requires)
	@if [ -z "$(DOCKER_CMD)" ]; then \
		echo "ERROR: Docker executable not found in PATH."; \
		echo "Docker is not installed on this system. Please run the project locally using 'make dev' or install Docker."; \
		exit 1; \
	fi
	@DOCKER_EXEC="docker"; \
	if ! docker info >/dev/null 2>&1; then \
		if command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then \
			DOCKER_EXEC="sudo docker"; \
		elif command -v sudo >/dev/null 2>&1; then \
			echo "==> Requesting sudo access for Docker daemon..."; \
			DOCKER_EXEC="sudo docker"; \
		fi; \
	fi; \
	echo "==> Launching Docker containers..."; \
	$$DOCKER_EXEC compose up --build

docker-test: ## Run backend unit test suite inside Docker container (auto-rebuilds image)
	@if [ -z "$(DOCKER_CMD)" ]; then \
		echo "ERROR: Docker executable not found in PATH."; \
		echo "Docker is not installed on this system. Please run tests locally using 'make test' or install Docker."; \
		exit 1; \
	fi
	@DOCKER_EXEC="docker"; \
	if ! docker info >/dev/null 2>&1; then \
		if command -v sudo >/dev/null 2>&1; then \
			DOCKER_EXEC="sudo docker"; \
		fi; \
	fi; \
	echo "==> Running pytest inside Docker backend container..."; \
	$$DOCKER_EXEC compose run --build -e PYTHONPATH=/app --rm backend pytest tests/ -v



clean: ## Clean local temporary build files and test caches
	@echo "==> Cleaning local build artifacts and caches..."
	rm -rf backend/.pytest_cache
	rm -rf backend/app/__pycache__
	rm -rf backend/tests/__pycache__
	rm -rf frontend/dist
	rm -rf frontend/node_modules/.vite
	@echo "==> Local clean complete!"

clean-all: clean ## Full clean: remove local build caches, venv, and node_modules
	@echo "==> Completely removing virtual environment and node_modules..."
	rm -rf $(VENV)
	rm -rf frontend/node_modules
	@echo "==> Full local environment clean complete!"


clean-docker: ## Stop and remove all Docker containers, networks, and volumes
	@if [ -z "$(DOCKER_CMD)" ]; then \
		echo "ERROR: Docker executable not found in PATH."; \
		exit 1; \
	fi
	@DOCKER_EXEC="docker"; \
	if ! docker info >/dev/null 2>&1; then \
		if command -v sudo >/dev/null 2>&1; then \
			DOCKER_EXEC="sudo docker"; \
		fi; \
	fi; \
	echo "==> Stopping Docker containers..."; \
	$$DOCKER_EXEC compose down --volumes --remove-orphans
	@echo "==> Docker clean complete!"

clean-all-docker: ## Full Docker purge: remove containers, networks, volumes, and built images
	@if [ -z "$(DOCKER_CMD)" ]; then \
		echo "ERROR: Docker executable not found in PATH."; \
		exit 1; \
	fi
	@DOCKER_EXEC="docker"; \
	if ! docker info >/dev/null 2>&1; then \
		if command -v sudo >/dev/null 2>&1; then \
			DOCKER_EXEC="sudo docker"; \
		fi; \
	fi; \
	echo "==> Purging project Docker containers, volumes, and images..."; \
	$$DOCKER_EXEC compose down --volumes --remove-orphans --rmi all
	@echo "==> Full Docker purge complete!"
