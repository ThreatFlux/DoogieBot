.PHONY: all clean install dev lint docker-lint format docker-format test docker-test security-check docker-security-check docker-build docker-up docker-down docker-up-prod help migrate frontend-build frontend-dev backend-dev generate-docs sync lock fix-permissions fix-docker fix-all

# Default target
all: install lint test

# Python settings
UV = uv
PYTHON_VERSION = 3.13
VENV = .venv
UV_RUN = $(UV) run

# Local command settings
BACKEND_LINT = $(UV_RUN) pylint
BACKEND_FORMAT = $(UV_RUN) black
BACKEND_ISORT = $(UV_RUN) isort
BACKEND_TEST = $(UV_RUN) pytest
BACKEND_SECURITY_CHECK = $(UV_RUN) bandit

# Docker settings
IMAGE_NAME = ghcr.io/toosmooth/doogiebot
CONTAINER_NAME = doogie-chat-container
DOCKER_COMPOSE = docker compose
BUILD_ENV =

# Version management
VERSION = $(shell grep -m 1 version backend/pyproject.toml | cut -d'"' -f2)

# System detection
OS = $(shell uname -s)

# Colors for terminal output
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Fix permissions for Docker volumes
fix-permissions:
	@echo "${YELLOW}Fixing permissions for Docker volumes...${NC}"
	@chmod +x ./scripts/fix-permissions.sh
	@./scripts/fix-permissions.sh

# Fix Docker Compose formatting issues
fix-docker:
	@echo "${YELLOW}Fixing Docker Compose file formatting...${NC}"
	@chmod +x ./scripts/fix-docker-compose.sh
	@./scripts/fix-docker-compose.sh

# Fix all Docker environment issues
fix-all:
	@echo "${YELLOW}Fixing all Docker environment issues...${NC}"
	@chmod +x ./scripts/fix-all.sh
	@./scripts/fix-all.sh

# Help target
help:
	@echo "${GREEN}Security Onion Chatbot Makefile${NC}"
	@echo ""
	@echo "${YELLOW}Available targets:${NC}"
	@echo " ${GREEN}all${NC}             : Install dependencies, run linters, and tests"
	@echo " ${GREEN}clean${NC}           : Clean up build artifacts, caches, and virtual environment"
	@echo " ${GREEN}fix-permissions${NC} : Fix permissions for Docker volumes"
	@echo " ${GREEN}fix-docker${NC}      : Fix Docker Compose file formatting issues"
	@echo " ${GREEN}fix-all${NC}         : Fix all Docker environment issues"
	@echo " ${GREEN}install${NC}         : Install backend and frontend dependencies"
	@echo " ${GREEN}lock${NC}            : Generate lock file for reproducible builds"
	@echo " ${GREEN}sync${NC}            : Sync dependencies from lock file"
	@echo " ${GREEN}dev${NC}             : Start development environment with Docker"
	@echo " ${GREEN}lint${NC}            : Run linters locally using virtual environment"
	@echo " ${GREEN}docker-lint${NC}     : Run linters in Docker container"
	@echo " ${GREEN}format${NC}          : Format code locally using virtual environment"
	@echo " ${GREEN}docker-format${NC}   : Format code in Docker container"
	@echo " ${GREEN}test${NC}            : Run tests locally using virtual environment"
	@echo " ${GREEN}docker-test${NC}     : Run tests in Docker container"
	@echo " ${GREEN}security-check${NC}  : Run security checks locally using virtual environment"
	@echo " ${GREEN}docker-security${NC} : Run security checks in Docker container"
	@echo " ${GREEN}docker-build${NC}    : Build a fresh Docker image with no-cache and tag it as ${IMAGE_NAME}:latest"
	@echo " ${GREEN}docker-up${NC}       : Start Docker container in development mode"
	@echo " ${GREEN}docker-up-prod${NC}  : Start Docker container in production mode"
	@echo " ${GREEN}docker-down${NC}     : Stop Docker container"
	@echo " ${GREEN}migrate${NC}         : Run database migrations"
	@echo " ${GREEN}frontend-build${NC}  : Build frontend for production"
	@echo " ${GREEN}frontend-dev${NC}    : Start frontend development server"
	@echo " ${GREEN}backend-dev${NC}     : Start backend development server"
	@echo " ${GREEN}sync${NC}            : Sync codebase to a remote machine"

# Clean up
clean:
	@echo "${YELLOW}Cleaning up...${NC}"
	rm -rf $(VENV) *.egg-info dist build __pycache__ .pytest_cache .coverage
	rm -rf frontend/.next frontend/node_modules
	rm -rf backend/__pycache__ backend/**/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "${GREEN}Cleanup complete.${NC}"

# Generate lockfile
lock:
	@echo "${YELLOW}Generating lock file...${NC}"
	cd backend && $(UV) lock
	@echo "${GREEN}Lock file generated.${NC}"

# Sync dependencies
sync:
	@echo "${YELLOW}Syncing dependencies from lock file...${NC}"
	cd backend && $(UV) sync
	@echo "${GREEN}Dependencies synced.${NC}"

# Installation (used for local dev without Docker)
install:
	@echo "${YELLOW}Setting up virtual environment...${NC}"
	$(UV) venv --python $(PYTHON_VERSION)

	@echo "${YELLOW}Installing backend dependencies...${NC}"
	cd backend && $(UV) pip install -e .
	cd backend && $(UV) pip install -e ".[dev]"


	@echo "${YELLOW}Installing frontend dependencies...${NC}"
	cd frontend && pnpm install

	@echo "${GREEN}Installation complete.${NC}"

# Docker builds - builds the image locally with no-cache and tags it
docker-build:
	@echo "${YELLOW}Building fresh ${IMAGE_NAME} image with no cache...${NC}"
	docker build --no-cache -t ${IMAGE_NAME}:latest -f Dockerfile .
	@echo "${GREEN}Docker image built and tagged as ${IMAGE_NAME}:latest.${NC}"

# Start development environment
dev: clean docker-up

# Start Docker in development mode
docker-up:
	@echo "${YELLOW}Starting Docker container in development mode...${NC}"
	$(DOCKER_COMPOSE) up $(BUILD_ENV)

# Start Docker in production mode
docker-up-prod:
	@echo "${YELLOW}Starting Docker container in production mode...${NC}"
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml up $(BUILD_ENV)

# Stop Docker
docker-down:
	@echo "${YELLOW}Stopping Docker container...${NC}"
	$(DOCKER_COMPOSE) down
	@echo "${GREEN}Docker container stopped.${NC}"

# Primary commands use the local environment by default

# Linting (Local as primary command)
lint:
	@echo "${YELLOW}Running backend linters locally...${NC}"
	cd backend && $(BACKEND_LINT) app --disable=C0111
	@echo "${YELLOW}Running frontend linters locally...${NC}"
	cd frontend && npm run lint
	@echo "${GREEN}Linting complete.${NC}"

# Linting (Docker)
docker-lint:
	@echo "${YELLOW}Running backend linters in Docker...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend && uv run pylint app --disable=C0111,R0801"
	@echo "${YELLOW}Running frontend linters in Docker...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/frontend && npm run lint"
	@echo "${GREEN}Linting complete.${NC}"

# Formatting (Local as primary command)
format:
	@echo "${YELLOW}Formatting backend code locally...${NC}"
	cd backend && $(BACKEND_FORMAT) app
	cd backend && $(BACKEND_ISORT) app
	@if [ -d "backend/tests" ]; then \
		cd backend && $(BACKEND_FORMAT) tests; \
		cd backend && $(BACKEND_ISORT) tests; \
	fi
	@echo "${YELLOW}Formatting frontend code locally...${NC}"
	cd frontend && npm run format
	@echo "${GREEN}Formatting complete.${NC}"

# Formatting (Docker)
docker-format:
	@echo "${YELLOW}Formatting backend code in Docker...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend && uv run black app && uv run isort app && if [ -d 'tests' ]; then uv run black tests && uv run isort tests; fi"
	@echo "${YELLOW}Formatting frontend code in Docker...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/frontend && npm run format"
	@echo "${GREEN}Formatting complete.${NC}"

# Testing (Local as primary command)
test:
	@echo "${YELLOW}Running tests locally...${NC}"
	cd backend && $(BACKEND_TEST) tests
	cd frontend && npm test
	@echo "${GREEN}Tests complete.${NC}"

# Testing (Docker)
docker-test:
	@echo "${YELLOW}Running tests in Docker...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend && source /app/.venv/bin/activate && uv pip install -e . && uv pip install pytest pytest-cov && python -m pytest"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/frontend && npm test"
	@echo "${GREEN}Tests complete.${NC}"

# Security checks (Local as primary command)
security-check:
	@echo "${YELLOW}Running security checks locally...${NC}"
	cd backend && $(BACKEND_SECURITY_CHECK) -r app -c bandit.yaml
	cd frontend && npm audit
	@echo "${GREEN}Security checks complete.${NC}"

# Security checks (Docker)
docker-security:
	@echo "${YELLOW}Running security checks in Docker...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend && uv run bandit -r app -c bandit.yaml"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/frontend && npm audit"
	@echo "${GREEN}Security checks complete.${NC}"

# Run database migrations
migrate:
	@echo "${YELLOW}Running database migrations...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend && uv run alembic upgrade head"
	@echo "${GREEN}Migrations complete.${NC}"

# Build frontend for production
frontend-build:
	@echo "${YELLOW}Building frontend for production...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/frontend && npm run build"
	@echo "${GREEN}Frontend build complete.${NC}"

# Start frontend dev server
frontend-dev:
	@echo "${YELLOW}Starting frontend development server...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/frontend && npm run dev"

# Start backend dev server
backend-dev:
	@echo "${YELLOW}Starting backend development server...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

# Generate documentation
generate-docs:
	@echo "${YELLOW}Generating documentation...${NC}"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend && sphinx-apidoc -o docs/source app"
	$(DOCKER_COMPOSE) exec app bash -c "cd /app/backend/docs && make html"
	@echo "${GREEN}Documentation generated.${NC}"

# Sync code to remote server
sync:
	@echo "${YELLOW}Syncing codebase to remote machine...${NC}"
	@read -p "Enter destination (e.g., user@server:/path/to/project): " destination; \
	./sync-doogie.sh $$destination
	@echo "${GREEN}Sync complete.${NC}"

# Debug target to build, wait, check logs, and run fetch test with local server
debug:
	@echo "${YELLOW}Starting debug sequence...${NC}"
	@echo "${YELLOW}Starting local HTTP server on port 8888...${NC}"
	@python3 -m http.server 8888 & export HTTP_PID=$$!; \
	trap 'echo "${YELLOW}Stopping local HTTP server (PID: $$HTTP_PID)...${NC}"; kill $$HTTP_PID || true' EXIT; \
	echo "Local HTTP server started with PID: $$HTTP_PID"
	@echo "${YELLOW}Starting Docker container with local image...${NC}"
	$(DOCKER_COMPOSE) up -d
	@echo "${YELLOW}Waiting 60 seconds for services to initialize...${NC}"
	@sleep 60
	@echo "${YELLOW}Checking logs for server readiness...${NC}"
	@if $(DOCKER_COMPOSE) logs app | grep -q "Uvicorn running"; then \
		echo "${GREEN}Server seems ready. Running fetch tool test against local server...${NC}"; \
		TEST_URL="http://host.docker.internal:8888/test.txt" ./backend/tests/test_fetch_tool.sh; \
	else \
		echo "${RED}Server did not start correctly. Displaying logs:${NC}"; \
		$(DOCKER_COMPOSE) logs app; \
		kill $$HTTP_PID || true; \
		exit 1; \
	fi
	@echo "${YELLOW}Stopping local HTTP server (PID: $$HTTP_PID)...${NC}"
	@kill $$HTTP_PID || true
	@echo "${YELLOW}Displaying recent logs...${NC}"
	@$(DOCKER_COMPOSE) logs app --since 5m || true
	@echo "${GREEN}Debug sequence complete.${NC}"