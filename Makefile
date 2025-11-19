.PHONY: help build up down restart logs logs-follow clean clean-all status shell-firewall shell-backend shell-frontend install-dev test health check-ports stop-all

# Variables
COMPOSE=docker-compose
PROJECT_NAME=semantic-firewall

# Colors for output
GREEN=\033[0;32m
YELLOW=\033[1;33m
RED=\033[0;31m
NC=\033[0m # No Color

##@ Help

help: ## Show this help
	@echo '$(GREEN)Semantic Firewall - Available Commands$(NC)'
	@echo ''
	@awk 'BEGIN {FS = ":.*##"; printf "\nUso:\n  make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Building and Initialization

build: ## Build all Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	$(COMPOSE) build --no-cache

build-fast: ## Build Docker images using cache
	@echo "$(GREEN)Building Docker images (using cache)...$(NC)"
	$(COMPOSE) build

up: ## Start all services
	@echo "$(GREEN)Starting services...$(NC)"
	$(COMPOSE) up -d
	@echo "$(GREEN)Services started successfully!$(NC)"
	@echo "$(YELLOW)Frontend:$(NC) http://localhost:5173"
	@echo "$(YELLOW)Firewall:$(NC) http://localhost:8080"
	@echo "$(YELLOW)Backend:$(NC) http://localhost:8000"
	@echo "$(YELLOW)OPA:$(NC) http://localhost:8181"

up-build: ## Build and start all services
	@echo "$(GREEN)Building and starting services...$(NC)"
	$(COMPOSE) up -d --build
	@$(MAKE) status

dev: up-build ## Alias for fast development (build + start)

start: up ## Alias for starting services

##@ Service Management

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(COMPOSE) down

stop: down ## Alias for stopping services

restart: ## Restart all services
	@echo "$(YELLOW)Restarting services...$(NC)"
	$(COMPOSE) restart
	@$(MAKE) status

restart-firewall: ## Restart only the firewall service
	@echo "$(YELLOW)Restarting firewall...$(NC)"
	$(COMPOSE) restart firewall

restart-backend: ## Restart only the backend service
	@echo "$(YELLOW)Restarting backend...$(NC)"
	$(COMPOSE) restart backend

restart-frontend: ## Restart only the frontend service
	@echo "$(YELLOW)Restarting frontend...$(NC)"
	$(COMPOSE) restart frontend

##@ Logs and Monitoring

logs: ## Show logs of all services
	$(COMPOSE) logs --tail=100

logs-follow: ## Follow logs in real time
	$(COMPOSE) logs -f

logs-firewall: ## Show logs of the firewall
	$(COMPOSE) logs --tail=100 firewall

logs-backend: ## Show logs of the backend
	$(COMPOSE) logs --tail=100 backend

logs-frontend: ## Show logs of the frontend
	$(COMPOSE) logs --tail=100 frontend

logs-opa: ## Show logs of OPA
	$(COMPOSE) logs --tail=100 opa

status: ## Show the status of the services
	@echo "$(GREEN)Status of the services:$(NC)"
	@$(COMPOSE) ps

health: ## Check the health of the services
	@echo "$(GREEN)Checking the health of the services...$(NC)"
	@echo "$(YELLOW)Frontend (5173):$(NC)"
	@curl -f http://localhost:5173 > /dev/null 2>&1 && echo "  ✓ OK" || echo "  ✗ No disponible"
	@echo "$(YELLOW)Firewall (8080):$(NC)"
	@curl -f http://localhost:8080/health > /dev/null 2>&1 && echo "  ✓ OK" || echo "  ✗ Not available"
	@echo "$(YELLOW)Backend (8000):$(NC)"
	@curl -f http://localhost:8000/health > /dev/null 2>&1 && echo "  ✓ OK" || echo "  ✗ Not available"
	@echo "$(YELLOW)OPA (8181):$(NC)"
	@curl -f http://localhost:8181/health > /dev/null 2>&1 && echo "  ✓ OK" || echo "  ✗ Not available"

check-ports: ## Check which ports are in use
	@echo "$(GREEN)Checking which ports are in use...$(NC)"
	@echo "$(YELLOW)Port 5173 (Frontend):$(NC)"
	@lsof -i :5173 || echo "  Free"
	@echo "$(YELLOW)Port 8080 (Firewall):$(NC)"
	@lsof -i :8080 || echo "  Free"
	@echo "$(YELLOW)Port 8000 (Backend):$(NC)"
	@lsof -i :8000 || echo "  Free"
	@echo "$(YELLOW)Port 8181 (OPA):$(NC)"
	@lsof -i :8181 || echo "  Free"

##@ Development

shell-firewall: ## Open a shell in the firewall container
	$(COMPOSE) exec firewall /bin/bash

shell-backend: ## Open a shell in the backend container
	$(COMPOSE) exec backend /bin/bash

shell-frontend: ## Open a shell in the frontend container
	$(COMPOSE) exec frontend /bin/sh

shell-opa: ## Open a shell in the OPA container
	$(COMPOSE) exec opa /bin/sh

install-dev: ## Install development dependencies (Python)
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	cd firewall && pip install -r requirements.txt
	cd backend && pip install -r requirements.txt


##@ Cleanup

clean: ## Stop and remove containers and networks
	@echo "$(YELLOW)Stopping and removing containers and networks...$(NC)"
	$(COMPOSE) down --remove-orphans

clean-volumes: ## Remove also volumes
	@echo "$(RED)Stopping and removing containers, networks and volumes...$(NC)"
	$(COMPOSE) down -v --remove-orphans

clean-all: ## Complete cleanup (containers, volumes and images)
	@echo "$(RED)Complete cleanup...$(NC)"
	$(COMPOSE) down -v --rmi all --remove-orphans

clean-images: ## Remove the Docker images of the project
	@echo "$(RED)Removing Docker images...$(NC)"
	docker images | grep semantic-firewall | awk '{print $$3}' | xargs -r docker rmi -f || true

prune: ## Clean up unused Docker resources of the system
	@echo "$(YELLOW)Cleaning up unused Docker resources...$(NC)"
	docker system prune -f

prune-all: ## Deep cleanup of the Docker system
	@echo "$(RED)Deep cleanup of the Docker system...$(NC)"
	docker system prune -af --volumes

##@ Utilities

ps: ## List the containers of the project
	$(COMPOSE) ps -a

top: ## Show the processes of the containers
	$(COMPOSE) top

stats: ## Show the statistics of the resources of the containers
	docker stats --no-stream $$(docker ps --filter "name=$(PROJECT_NAME)" --format "{{.Names}}")

pull: ## Download the latest base images
	@echo "$(GREEN)Downloading base images...$(NC)"
	docker pull python:3.11-slim
	docker pull node:20-alpine
	docker pull openpolicyagent/opa:latest

config: ## Validate and show the configuration of docker-compose
	$(COMPOSE) config

##@ Quick shortcuts

all: clean build up ## Clean, build and start everything from scratch

rebuild: down build up ## Rebuild and start the services

refresh: down up-build ## Quick restart with reconstruction

stop-all: ## Stop all the Docker containers of the system
	@echo "$(RED)Stopping all the Docker containers...$(NC)"
	docker stop $$(docker ps -aq) 2>/dev/null || true

