.PHONY: run install help

# Default target: run the app
run:
	@chmod +x run.sh
	@./run.sh

# Install/Setup only
install:
	@chmod +x run.sh
	@./run.sh --setup

help:
	@echo "PyTask: Linux Task Manager"
	@echo "Usage:"
	@echo "  make        - Setup (if needed) and run the app"
	@echo "  make run    - Same as above"
	@echo "  make install - Only handle the virtual environment setup"
