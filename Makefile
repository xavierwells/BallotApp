.DEFAULT_GOAL := help

.PHONY: help up down api-test dependency-check

help:
	@echo "up       Start the local stack"
	@echo "down     Stop the local stack"
	@echo "api-test Run API and OpenAPI contract tests in a container"
	@echo "dependency-check Verify every direct dependency has an approval record"

up:
	docker compose up --build

down:
	docker compose down

api-test:
	docker build --target test -t ballot-api-test ./apps/api
	docker run --rm ballot-api-test

dependency-check:
	python scripts/check_direct_dependency_approvals.py
