# Doogie Chat Bot

A chat bot application with a Hybrid RAG (BM25 + FAISS) and GraphRAG system, using external LLM services.

## Features

- Hybrid RAG (BM25 + FAISS) for efficient document retrieval
- GraphRAG for relationship-aware retrieval
- Multi-user capabilities
- Admin dashboard
- Support for multiple LLM providers
- Document processing

## Requirements

- Python 3.12+
- Node.js 20.x
- pnpm

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/doogie-chat.git
   cd doogie-chat
   ```

2. Create a `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```

3. Update the `.env` file with your LLM API keys and other configuration.

4. Start the application with Docker:
   ```bash
   make docker-up
   ```

   Or for production mode:
   ```bash
   make docker-up-prod
   ```

5. Access the application at http://localhost:3000

## Development

### Directory Structure

- `backend/` - FastAPI backend
- `frontend/` - Next.js frontend
- `data/` - Persistent data storage
  - `data/db/` - SQLite database files
  - `data/indexes/` - RAG index files

### Common Commands

- `make all` - Install dependencies, run linters, and tests
- `make clean` - Clean up build artifacts, caches, and virtual environment
- `make install` - Install backend and frontend dependencies
- `make dev` - Start development environment with Docker
- `make docker-build` - Build Docker image
- `make test` - Run tests locally
- `make docker-test` - Run tests in Docker container
- `make lint` - Run linters locally
- `make docker-lint` - Run linters in Docker container
- `make docker-security` - Run security checks in Docker container
- `make generate-docs` - Generate project documentation

## Configuration

- Backend configuration is in `backend/app/core/config.py`
- Environment variables are defined in the `.env` file
- For LLM providers, set the API keys in the `.env` file or in the admin dashboard

## Security

Run `make docker-security` to perform security checks.

## License

See the [LICENSE](LICENSE) file for details.
