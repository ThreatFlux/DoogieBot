# Project Brief: Doogie Chat Bot

## Core Requirements

- Create a chat bot with a Hybrid RAG (BM25 + FAISS) and a graphRAG
- Always use an external service for LLM needs
- Multi-user system with two roles: user and admin
- User features: start chats, view/resume chat history, manage profile
- Admin features: user management, LLM configuration, RAG management, chat review

## Technical Stack

- Python 3.12+ and SQLite3
- FastAPI for backend
- Next.js/React for frontend
- Docker and Docker Compose for deployment
- Latest versions of dependencies

## Key Features

### User Features
- Chat initiation and history management
- Profile management (download/delete history, theme preferences)
- Feedback mechanism (thumbs up/down with explanation)
- Streaming results for immediate feedback

### Admin Features
1. **User Management**
   - Approve new user registrations
   - Assign user roles (user/admin)

2. **LLM Options**
   - Select LLM service (Ollama, LM Studio, OpenAI, Openrouter, Deepseek, Anthropic)
   - Configure chat and embedding models
   - Set default system prompts

3. **RAG Management**
   - Upload documents (PDF, Microsoft docs, MD, RST, TST, JSON, JSONL)
   - Rebuild RAG from documents
   - Regenerate graphRAG
   - Manual information addition

4. **Chat Review**
   - Review chats marked as incorrect
   - Mark chats as reviewed

## UI/UX Requirements
- Modern, dynamic interface suitable for a chat bot
- Dark mode by default with light mode option
- Proxy frontend requests to backend API
- Support for reasoning model output (<think></think> tags)
- Chat statistics display (tokens, token/s, etc.)

## Initial Setup
- Create default admin user on first launch
- Email addresses as usernames