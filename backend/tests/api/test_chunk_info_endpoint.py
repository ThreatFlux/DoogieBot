import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime

from app.main import app
from app.models.document import DocumentChunk, Document
from app.utils.deps import get_db, get_current_user
from app.models.user import User

# Create test client
client = TestClient(app)

# Mock user for authentication
mock_user = User(
    id="test_user_id",
    email="test@example.com",
    role="user",
    status="active"
)

# Override authentication dependency
@pytest.fixture(autouse=True)
def override_get_current_user():
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides = {}

# Mock database dependency
@pytest.fixture
def mock_db():
    """Create a mock database session"""
    mock_session = MagicMock(spec=Session)
    
    # Create a document
    test_document = Document(
        id="test_doc_id",
        title="Test Document",
        type="text",
        filename="test_file.txt",
        uploaded_by="test_user_id",
        created_at=datetime.utcnow()
    )
    
    # Create a chunk
    test_chunk = DocumentChunk(
        id="test_chunk_id",
        document_id="test_doc_id",
        content="Test chunk content",
        chunk_index=1,
        created_at=datetime.utcnow()
    )
    
    # Configure mock query responses
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    
    # Configure the mock to handle both DocumentChunk and Document queries
    def mock_filter_call(*args, **kwargs):
        filter_args = args[0]
        if isinstance(filter_args.left, DocumentChunk.__table__.columns.values()):
            mock_query.first.return_value = test_chunk
        elif isinstance(filter_args.left, Document.__table__.columns.values()):
            mock_query.first.return_value = test_document
        return mock_query
    
    mock_query.filter.side_effect = mock_filter_call
    
    # Override the get_db dependency
    app.dependency_overrides[get_db] = lambda: mock_session
    yield mock_session
    app.dependency_overrides = {}


def test_get_chunk_info_success(mock_db):
    """Test successful retrieval of chunk information"""
    response = client.get("/api/v1/rag/chunks/test_chunk_id")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that the response contains all expected fields
    assert data["chunk_id"] == "test_chunk_id"
    assert data["chunk_index"] == 1
    assert data["document_id"] == "test_doc_id"
    assert data["document_title"] == "Test Document"
    assert data["document_type"] == "text"
    assert data["document_filename"] == "test_file.txt"
    assert "created_at" in data


def test_get_chunk_info_not_found(mock_db):
    """Test retrieval of a non-existent chunk"""
    # Override the mock to return None for chunks
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/rag/chunks/nonexistent_chunk_id")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_chunk_info_document_not_found(mock_db):
    """Test when chunk exists but document doesn't"""
    # Mock queries to return a chunk but no document
    mock_query = mock_db.query.return_value
    mock_chunk = DocumentChunk(
        id="test_chunk_id",
        document_id="missing_doc_id",
        content="Test chunk content",
        chunk_index=1,
        created_at=datetime.utcnow()
    )
    
    # Configure mock to return chunk but not document
    def mock_filter_call(*args, **kwargs):
        filter_args = args[0]
        if DocumentChunk.id.key in str(filter_args):
            mock_query.first.return_value = mock_chunk
        elif Document.id.key in str(filter_args):
            mock_query.first.return_value = None
        return mock_query
    
    mock_query.filter.side_effect = mock_filter_call
    
    response = client.get("/api/v1/rag/chunks/test_chunk_id")
    
    assert response.status_code == 404
    assert "Document with id" in response.json()["detail"]
