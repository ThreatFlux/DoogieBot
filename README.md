# DoogieBot

This project is a chatbot application built with Next.js (frontend) and FastAPI (backend). It allows users to interact with documents and a Large Language Model (LLM). The project initially focused on addressing markdown formatting issues in chatbot responses but has evolved into a full-fledged application.

## Project Overview
This application provides a user interface for:
- Managing documents (uploading, processing, and retrieving)
- Configuring LLM settings
- Interacting with an LLM through a chat interface
- Managing user accounts

## Technology Stack

- **Frontend:** Next.js, React, Tailwind CSS
- **Backend:** FastAPI, Python
- **Database:** (Inferred from migrations - likely PostgreSQL or similar)
- **LLM Integration:** Supports multiple LLMs (OpenAI, Anthropic, Ollama, etc.)
- **Vector Database:** (Inferred from code - likely FAISS)
- **Deployment:** Docker, Docker Compose

## Production Setup (Docker Compose)

The production setup uses Docker Compose to run the application in a containerized environment.

**`docker-compose.prod.yml` Configuration:**

-   Defines a single service named `app`.
-   Builds the application from the root `Dockerfile`.
-   Exposes ports 3000 (frontend) and 8000 (backend).
-   Uses bind mounts for the application code:
    -   `./:/app`: Mounts the entire project directory.
    -   Excludes build artifacts and dependencies: `/app/frontend/.next`, `/app/frontend/node_modules`, `/app/backend/__pycache__`.
-   Sets environment variables:
    -   `NODE_ENV=production`
    -   `PYTHONPATH=/app`
    -   `FASTAPI_ENV=production`
    -   Database connection settings (if applicable)
    -   LLM service API keys (OpenAI, Anthropic, etc.)
    -   Secret key and other security-related settings.
-   Uses `/app/entrypoint.prod.sh` as the entrypoint.
-   Restarts the service unless stopped (`restart: unless-stopped`).

**`entrypoint.prod.sh` Script:**

-   Installs backend and frontend dependencies.
-   Runs database migrations using Alembic.
-   Builds the frontend for production (`npm run build`).
-   Starts the backend server using Uvicorn:
    -   `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 300`
-   Starts the frontend server using `npm run start`.
-   Handles shutdown signals (SIGTERM, SIGINT) to gracefully stop the services.

**Running in Production:**

1.  Set the necessary environment variables in a `.env` file or directly in your shell. You'll need to provide API keys for the LLM services you want to use and a strong `SECRET_KEY`.
2.  Run `docker compose -f docker-compose.prod.yml up --build` to build and start the application.

## Development Setup

1.  Clone the repository: `git clone <repository_url>`
2.  Navigate to the project directory: `cd doogie6`
3.  Install backend dependencies:
    ```bash
    cd backend
    pip install -r requirements.txt
    ```
4.  Install frontend dependencies:
    ```bash
    cd ../frontend
    npm install
    ```
5.  Run database migrations:
    ```bash
    cd ../backend
    python -m alembic upgrade head
    ```
6.  Start the development servers:
    - You can use the `docker-compose.yml` file for a combined development environment. This will automatically rebuild and reload on code changes.
    - Run `docker compose up --build`

## Memory Bank
This project utilizes a memory bank system to maintain context and documentation across sessions. The memory bank consists of Markdown files located in the `memory-bank/` directory. These files contain information about the project's goals, architecture, context, and progress. Key files include:

- `projectbrief.md`: Defines the core requirements and goals of the project.
- `productContext.md`: Explains the purpose and functionality of the application.
- `activeContext.md`: Tracks the current focus, recent changes, and next steps.
- `systemPatterns.md`: Describes the system architecture and design patterns.
- `techContext.md`: Lists the technologies used and development setup.
- `progress.md`: Summarizes the current status and known issues.
