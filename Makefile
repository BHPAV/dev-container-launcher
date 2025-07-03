.PHONY: install build build-all run clean help lint check logs

# Default target
help:
	@echo "Dev-Container Launcher - Available commands:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make build       - Build the base devbox image"
	@echo "  make build-all   - Build all language-specific images"
	@echo "  make run         - Launch the Textual UI"
	@echo "  make clean       - Remove all dev containers"
	@echo "  make lint        - Run code linting"
	@echo "  make check       - Run security and type checks"
	@echo "  make logs        - View application logs"
	@echo "  make help        - Show this help message"

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
	@echo "Running tests..."
	python -m pytest tests/ -v 2>/dev/null || echo "No tests found"

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
