# Active Context

## Current Work Focus

We have completed the initial setup phase (Phase 1) and the frontend development phase (Phase 3) of the Doogie chat bot project. We've also made significant progress on Phase 2 (Backend Development) and Phase 4 (Integration) by implementing chat functionality and connecting the frontend to the LLM service. The basic project structure has been created, including Docker configuration, backend and frontend frameworks, database models, and Git initialization. We have also implemented the frontend components, including the chat interface, user profile management, and admin dashboard.

## Recent Changes

- Updated API URL handling to support both regular and streaming requests
- Implemented dual authentication support for EventSource endpoints
- Fixed async streaming issues in chat endpoints
- Created the basic project structure for backend and frontend
- Set up Docker and Docker Compose configuration with a single container approach
- Initialized Git repository
- Created FastAPI application structure
- Implemented database models and Alembic for migrations
- Set up Next.js application with TypeScript and Tailwind CSS
- Implemented database migrations with Alembic
- Developed user authentication system with JWT tokens
- Created API endpoints for user management
- Implemented first admin user creation on startup
- Implemented frontend authentication flow
- Created chat interface with streaming support
- Developed user profile management
- Built admin dashboard
- Implemented dark/light mode theming
- Implemented LLM configuration system with support for multiple providers
- Added functionality to ensure only one LLM service is active at a time
- Implemented chat management functionality in the backend
- Created API endpoints for chat functionality including streaming responses
- Connected frontend to backend API for chat functionality
- Implemented streaming response handling for real-time chat interactions
- Added robust error handling for undefined values in the chat interface
- Implemented a consistent approach for API URL handling across the frontend

## Next Steps

1. **Backend Development**
   - ✅ Implement chat management
   - ✅ Develop API endpoints for chat functionality
   - Implement document processing
   - Develop RAG components (BM25, FAISS, GraphRAG)
   - ✅ Create LLM service integrations

2. **Integration**
   - ✅ Connect frontend to backend API for chat functionality
   - ✅ Implement streaming response handling
   - Set up document processing pipeline
   - Create feedback mechanism

3. **Testing**
   - Develop unit tests for backend components
   - Create integration tests for API endpoints
   - Implement frontend component tests
   - Perform end-to-end testing

## Active Decisions and Considerations

1. **Docker Configuration**
   - Single container approach as specified in .clinerules
   - Auto-reload configured for both frontend and backend
   - Bind mount to local filesystem instead of using Docker volumes

2. **Database Schema Design**
   - Models created for users, chats, messages, documents, and RAG components
   - Relationships established between entities
   - SQLite chosen for simplicity and portability
   - Added LLMConfig model to store LLM configuration

3. **LLM Integration**
   - Implemented factory pattern for creating LLM clients
   - Support for multiple LLM providers (OpenAI, Ollama, etc.)
   - Database-backed configuration system
   - Only one LLM service active at a time
   - Admin interface for managing LLM configurations

4. **RAG Implementation**
   - Planning hybrid approach with BM25 and FAISS
   - GraphRAG structure designed with nodes and edges
   - Document processing pipeline to be implemented

5. **UI/UX Design**
   - Modern chat interface with Tailwind CSS implemented
   - Dark mode set as default with light mode option
   - Component-based architecture for reusability
   - Responsive design for different screen sizes

6. **Security Considerations**
   - JWT-based authentication implemented
   - Role-based authorization (user/admin) implemented
   - Secure storage of API keys for external LLM services

7. **API URL Handling**
    - Implemented a consistent approach for all API URL handling
    - Created utility functions in api.ts for different types of API requests
    - Support dual authentication methods:
      - Regular API calls use Authorization header with JWT
      - Streaming endpoints accept token via query parameters
    - Next.js proxy configuration handles both request types:
      - /api/* for regular API requests
      - /v1/* for streaming endpoints
    - Consistent error handling across all request types

## Current Challenges

1. **Single Container Architecture**
   - Balancing resources between frontend and backend
   - Ensuring efficient development workflow with auto-reload

2. **External LLM Integration**
   - Managing multiple LLM service providers
   - Creating a consistent interface across different APIs

3. **Document Processing**
   - Supporting multiple document formats
   - Implementing efficient chunking and indexing strategies

4. **Backend-Frontend Integration**
   - Ensuring proper API communication
   - Handling streaming responses efficiently

## Recent Fixes

1. **User Management**
   - Fixed issue with users not being listed in the admin interface
   - Corrected pagination in the backend API responses
   - Aligned frontend and backend user models for proper data exchange
   - Improved error handling for pending user accounts
   - Enhanced user registration flow with better feedback messages
   - Fixed authentication flow to properly handle admin access
   - Implemented specific error message for pending users during login
   - Fixed API error handling to properly extract FastAPI error details

2. **Frontend-Backend Communication**
   - Fixed error handling in API service to properly extract error details from FastAPI responses
   - Improved error message display for better user experience
   - Enhanced authentication flow with more specific error messages
   - Fixed API routing issues by updating URL prefixes in Next.js configuration
   - Updated frontend API service to use the correct API URL prefix

3. **Chat Functionality**
    - Fixed "Cannot read properties of undefined (reading 'map')" errors by adding null checks
    - Added defensive coding to handle undefined values throughout the chat page
    - Updated the chat loading logic to properly initialize empty arrays
    - Fixed the chat creation process to handle undefined state
    - Implemented proper error handling for streaming responses
    - Added null checks for messages array in all places where it's used
    - Fixed SQLite IntegrityError with updated_at field by explicitly setting the timestamp
    - Fixed API routing by setting the correct baseURL in the API service
    - Fixed EventSource streaming issues:
      - Added support for token-based authentication via query parameters
      - Fixed async generator handling in stream endpoints
      - Implemented proper error handling for stream authentication
      - Configured Next.js proxy to handle both regular and streaming routes
    - Added flexible auth dependency for stream endpoints to support both header and query auth
    - Fixed coroutine handling in chat streaming to properly await responses
    - Fixed chat interface scrolling issues:
      - Improved container layout for proper scrollbar display
      - Added flex constraints for better content flow
      - Enhanced scroll behavior during message streaming
      - Fixed sidebar shrinking issues
    
    4. **API URL Handling**
   - Implemented a unified approach for API URL handling in frontend/services/api.ts
   - Added getApiUrl utility function to handle different URL requirements
   - Updated chat.ts to use the new approach for EventSource URLs
   - Updated .clinerules with clear guidelines for API URL handling