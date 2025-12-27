.PHONY: start stop restart logs build clean reset install-agents help

# Default target
help:
	@echo "MCP-BTR: Budgeted Tool Router"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  start          Start all services"
	@echo "  stop           Stop all services"
	@echo "  restart        Restart all services"
	@echo "  logs           Follow logs from all services"
	@echo "  logs-gateway   Follow gateway logs only"
	@echo "  logs-ui        Follow UI logs only"
	@echo "  build          Build containers"
	@echo "  clean          Stop and remove containers, networks"
	@echo "  reset          Reset to default preset"
	@echo "  install-agents Install AI agents to ~/.claude/agents/"
	@echo "  status         Show service status"
	@echo ""

# Start services
start:
	docker compose up -d
	@echo "Services started. Gateway: http://localhost:8090 | UI: http://localhost:5010"

# Stop services
stop:
	docker compose down

# Restart services
restart: stop start

# View logs
logs:
	docker compose logs -f

logs-gateway:
	docker compose logs -f gateway

logs-ui:
	docker compose logs -f ui

# Build containers
build:
	docker compose build

# Clean up
clean:
	docker compose down -v --remove-orphans
	@echo "Cleaned up containers and volumes"

# Reset to default preset
reset:
	@echo "Resetting to default preset..."
	@curl -s -X POST http://localhost:5010/api/presets/load \
		-H 'Content-Type: application/json' \
		-d '{"name": "development"}' | jq .
	@echo "Reset complete"

# Install AI agents
install-agents:
	@bash agents/install.sh

# Show status
status:
	@docker compose ps
	@echo ""
	@echo "Gateway: http://localhost:8090/mcp"
	@echo "UI:      http://localhost:5010"
