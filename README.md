# Doogie Chat Bot

Doogie Chat Bot is a hybrid RAG-based chatbot application with multi-user capabilities.

## Fixed Issues

### MCP Server Configuration

The MCP server configuration model had a mismatch with the service layer. The model doesn't contain fields for `command`, `args`, and `enabled` that the service was trying to use directly. Instead, these fields are now stored in the `config` JSON field of the model.

The service has been updated to handle this by:
1. Creating configurations with fields in the `config` JSON
2. Accessing these fields via `config.config.get("field_name")` instead of `config.field_name`
3. Using proper defaults where needed

## Database Schema

### MCPServerConfig
- id: String (UUID, primary key)
- name: String (required)
- description: String (optional)
- server_type: String (default="custom")
- base_url: String (optional)
- api_key: String (optional)
- models: JSON (optional)
- status: String (default="stopped")
- port: Integer (optional)
- container_id: String (optional)
- user_id: String (Foreign Key to users.id, required)
- created_at: DateTime
- updated_at: DateTime
- is_active: Boolean (default=true)
- config: JSON (stores command, args, env, enabled fields)

## Installation

1. Clone the repository
2. Run `make install` to install dependencies
3. Run `make dev` to start the development server

## Development

Run the following commands for development:

- `make docker-build` - Build Docker image
- `make docker-up` - Start Docker container in development mode
- `make docker-down` - Stop Docker container
- `make docker-up-prod` - Start Docker container in production mode
- `make docker-test` - Run tests in Docker container
- `make docker-lint` - Run linters in Docker container
- `make docker-format` - Format code in Docker container
- `make docker-security` - Run security checks in Docker container

## Admin Setup

Default admin credentials:
- Email: admin@example.com
- Password: change-this-password

Remember to change the default admin password after first login.
