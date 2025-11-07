SHELL := /bin/bash
COMPOSE := docker compose -f infra/compose/docker-compose.yml

.PHONY: dev-up dev-down build services ps logs update-openapi

dev-up:
	$(COMPOSE) up -d --build

dev-down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

services:
	@echo "Services: ingest:7001, embed:7002, retriever:7003, exam-engine:7004"

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=100

update-openapi:
	@echo "Updating OpenAPI specs from running services..."
	@python3 scripts/update-openapi-specs.py
