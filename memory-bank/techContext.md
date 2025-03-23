# Technical Context

## Technologies Used

### Backend
- **Python 3.12+**: Core programming language
- **FastAPI**: High-performance web framework for building APIs
- **SQLite3**: Lightweight, file-based relational database
- **Pydantic**: Data validation and settings management
- **FAISS**: Efficient similarity search and clustering of dense vectors
- **Rank-BM25**: Implementation of the BM25 ranking function
- **NetworkX**: Creation and analysis of graph structures for GraphRAG
- **GraphRAG**: Specialized graph library optimized for RAG operations (alternative to NetworkX)
- **PyPDF2/PDFMiner**: PDF parsing
- **python-docx**: Microsoft Word document parsing
- **Markdown**: Markdown parsing
- **JSON/JSONL**: JSON/JSONL parsing
- **SQLAlchemy**: SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Uvicorn**: ASGI server
- **Starlette**: ASGI framework (used by FastAPI)
- **JWT**: Authentication mechanism

### Frontend
- **Next.js**: React framework for production
- **React**: JavaScript library for building user interfaces
- **TypeScript**: Typed superset of JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: Promise-based HTTP client
- **React Query**: Data fetching and state management
- **React Hook Form**: Form validation and handling
- **Zod**: TypeScript-first schema validation
- **SSE (Server-Sent Events)**: For streaming responses

### DevOps
- **Docker**: Containerization platform
- **Docker Compose**: Multi-container Docker applications
- **Git**: Version control
- **ESLint/Prettier**: Code linting and formatting
- **PyTest**: Testing framework for Python
- **Jest/React Testing Library**: Testing for React components

## Development Setup

### Docker Configuration

The entire application runs in a single Docker container with bind mounts to the local filesystem for development:

```yaml
# docker-compose.yml example structure
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"  # Frontend
      - "8000:8000"  # Backend API
    volumes:
      - ./:/app  # Bind mount for development
    environment:
      - NODE_ENV=development
      - PYTHONPATH=/app
      - FASTAPI_ENV=development
```

### Auto-Reload Configuration

- **Backend**: Uses Uvicorn with `--reload` flag
- **Frontend**: Uses Next.js development server with hot reloading

### Project Structure

```
doogie6/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── rag/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   └── main.py
├── frontend/
│   ├── components/
│   ├── contexts/
│   ├── hooks/
│   ├── pages/
│   ├── public/
│   ├── services/
│   ├── styles/
│   ├── types/
│   └── utils/
├── docs/
├── memory-bank/
├── uploads/
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## Technical Constraints

1. **External LLM Dependency**
   - System relies on external LLM services
   - Must handle potential service outages or API changes
   - Need to manage API keys securely

2. **Single Container Deployment**
   - All components must run in a single Docker container
   - Resource allocation must be balanced between frontend and backend
   - Potential scaling limitations

3. **SQLite Limitations**
   - Limited concurrent write operations
   - Not suitable for distributed deployments
   - File-based storage requires backup strategy

4. **Document Processing**
   - Various document formats require different parsing strategies
   - Large documents may impact processing time and resource usage
   - Need to handle malformed or corrupt documents gracefully

5. **Browser Compatibility**
   - Frontend must work across modern browsers
   - SSE for streaming must have fallback mechanisms

## Dependencies

### Core Dependencies

#### Backend
```
fastapi>=0.104.0
uvicorn>=0.23.2
sqlalchemy>=2.0.0
alembic>=1.12.0
pydantic>=2.4.2
python-jose>=3.3.0
passlib>=1.7.4
bcrypt>=4.0.1
python-multipart>=0.0.6
faiss-cpu>=1.7.4
rank-bm25>=0.2.2
networkx>=3.1
graphrag>=1.0.0  # Specialized graph library for RAG operations
pypdf2>=3.0.0
python-docx>=1.0.0
markdown>=3.5
```

#### Frontend
```
next>=14.0.0
react>=18.2.0
react-dom>=18.2.0
typescript>=5.2.2
tailwindcss>=3.3.0
axios>=1.6.0
@tanstack/react-query>=5.0.0
react-hook-form>=7.47.0
zod>=3.22.0
```

### Development Dependencies

#### Backend
```
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.9.0
isort>=5.12.0
mypy>=1.6.0
```

#### Frontend
```
eslint>=8.52.0
prettier>=3.0.0
jest>=29.7.0
@testing-library/react>=14.0.0
```

## Environment Variables

```
# Backend
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
FIRST_ADMIN_EMAIL=admin@example.com
FIRST_ADMIN_PASSWORD=initial-secure-password

# LLM Services
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
OPENROUTER_API_KEY=your-openrouter-key
DEEPSEEK_API_KEY=your-deepseek-key
OLLAMA_BASE_URL=http://your-ollama-server:11434
LM_STUDIO_BASE_URL=http://your-lmstudio-server:8000

# Frontend
NEXT_PUBLIC_API_URL=/api