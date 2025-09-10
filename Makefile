.PHONY: up down build test lint report
up: ; docker compose up -d --build
down: ; docker compose down -v
build: ; docker compose build
lint: ; ruff check . && black --check . || true
report: ; python scripts/make_report.py
