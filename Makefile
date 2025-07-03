.PHONY: install build build-all run clean help lint check logs test test-unit test-integration test-security test-performance test-fast test-slow test-coverage test-docker test-watch web web-prod web-alt kill-flask-port

# Flask port configuration
FLASK_PORT ?= 5000

# Default target
help:
	@echo "Dev-Container Launcher - Available commands:"
	@echo "  make install         - Install Python dependencies"
	@echo "  make build           - Build the base devbox image"
	@echo "  make build-all       - Build all language-specific images"
	@echo "  make run             - Launch the Textual UI"
	@echo "  make web             - Launch the Flask web interface"
	@echo "  make web-prod        - Launch Flask in production mode"
	@echo "  make clean           - Remove all dev containers"
	@echo "  make lint            - Run code linting"
	@echo "  make check           - Run security and type checks"
	@echo "  make logs            - View application logs"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-security   - Run security tests only"
	@echo "  make test-performance - Run performance tests only"
	@echo "  make test-fast       - Run fast tests only (skip slow tests)"
	@echo "  make test-slow       - Run slow tests only"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo "  make test-docker     - Run Docker integration tests only"
	@echo "  make test-watch      - Run tests in watch mode"
	@echo ""
	@echo "  make help            - Show this help message"

install:
	pip install -r requirements.txt

build:
	python scripts/devctl.py build

build-all: build
	@echo "Building Python 3.12 image..."
	docker build -f docker/images/python-3.12.Dockerfile -t python-3.12 .
	@echo "Building Node.js 20 image..."
	docker build -f docker/images/node-20.Dockerfile -t node-20 .
	@echo "Building Go 1.22 image..."
	docker build -f docker/images/go-1.22.Dockerfile -t go-1.22 .
	@echo "All images built successfully!"

run:
	python app.py

# Kill any process using Flask port
kill-flask-port:
	@echo "Killing any process using port $(FLASK_PORT)..."
	@lsof -ti:$(FLASK_PORT) | xargs kill -9 2>/dev/null || true

# Run the Flask web application
web: kill-flask-port
	FLASK_PORT=$(FLASK_PORT) python web_app.py

# Run Flask in production mode with gunicorn
web-prod: kill-flask-port
	gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$(FLASK_PORT) web_app:app

# Run Flask on alternative port
web-alt:
	FLASK_PORT=5001 python web_app.py

clean:
	@echo "Stopping and removing all dev containers..."
	@docker stop $$(docker ps -q --filter "label=devcontainer=true") 2>/dev/null || true
	@docker rm $$(docker ps -aq --filter "label=devcontainer=true") 2>/dev/null || true
	@echo "Cleanup complete!"

# Development targets
dev-setup: install build
	@echo "Development environment ready!"
	@echo "Don't forget to add your SSH key to authorized_keys"

test:
	@echo "Running all tests..."
	python -m pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	python -m pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	python -m pytest tests/integration/ -v

test-security:
	@echo "Running security tests..."
	python -m pytest tests/ -v -m security

test-performance:
	@echo "Running performance tests..."
	python -m pytest tests/performance/ -v

test-fast:
	@echo "Running fast tests only..."
	python -m pytest tests/ -v -m "not slow"

test-slow:
	@echo "Running slow tests only..."
	python -m pytest tests/ -v -m slow

test-coverage:
	@echo "Running tests with coverage..."
	python -m pytest tests/ -v --cov=scripts --cov=utils --cov=config --cov=app --cov-report=html --cov-report=term-missing

test-docker:
	@echo "Running Docker integration tests..."
	python -m pytest tests/integration/test_docker_operations.py -v

test-watch:
	@echo "Running tests in watch mode..."
	python -m pytest tests/ -v --looponfail

lint:
	@echo "Running linting checks..."
	@python -m ruff check . 2>/dev/null || python -m flake8 . 2>/dev/null || echo "No linter installed"

check: lint
	@echo "Running type checks..."
	@python -m mypy . 2>/dev/null || echo "mypy not installed"
	@echo "Running security checks..."
	@python -m bandit -r . -x /venv 2>/dev/null || echo "bandit not installed"

logs:
	@echo "Showing application logs..."
	@tail -f ~/.devcontainer/devcontainer.log 2>/dev/null || echo "No logs found"
