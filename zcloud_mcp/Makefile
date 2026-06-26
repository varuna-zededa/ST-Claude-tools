# Makefile for Zededa MCP Server

.PHONY: test test-verbose test-coverage test-watch test-quick install-deps clean lint help

# Default target
help:
	@echo "Available targets:"
	@echo "  test         - Run all MCP unit tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-watch   - Run tests in watch mode"
	@echo "  test-quick   - Run tests with minimal output"
	@echo "  install-deps - Install test dependencies"
	@echo "  clean        - Clean up test artifacts"
	@echo "  lint         - Run code linting"
	@echo "  help         - Show this help message"

# Install test dependencies
install-deps:
	python3 -m pip install -e ".[test]"

# Run tests
test:
	python3 -m pytest test_*.py --tb=short

# Run tests with verbose output
test-verbose:
	python3 -m pytest test_*.py -v

# Run tests with coverage
test-coverage:
	python3 -m pytest test_*.py --cov=. --cov-report=html --cov-report=term-missing

# Run tests in watch mode (requires pytest-watch)
test-watch:
	python3 -m ptw test_*.py

# Run tests with minimal output (quick feedback)
test-quick:
	python3 -m pytest test_*.py -q

# Clean up test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf __pycache__
	rm -rf */__pycache__
	rm -f .coverage

# Run linting (if you have flake8 or similar installed)
lint:
	python3 -m flake8 *.py test_*.py --max-line-length=100 --exclude=__pycache__

# Install package in development mode
install:
	python3 -m pip install -e .

# Run the MCP server
run:
	python3 mcpserver.py
