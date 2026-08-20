.DEFAULT_GOAL := help

.PHONY: help up down api-test dependency-check db-upgrade

help:
	@echo "up       Start the local stack"
	@echo "down     Stop the local stack"
	@echo "api-test Run API and OpenAPI contract tests in a container"
	@echo "db-upgrade Apply the current PostgreSQL schema migration"
	@echo "dependency-check Verify every direct dependency has an approval record"

up:
	docker compose up --build

down:
	docker compose down

api-test:
	docker build --target test -t ballot-api-test ./apps/api
	docker run --rm --mount type=bind,source="$(CURDIR)/data",target=/app/data,readonly ballot-api-test

db-upgrade:
	docker compose run --rm migrate

dependency-check:
	python scripts/check_direct_dependency_approvals.py
