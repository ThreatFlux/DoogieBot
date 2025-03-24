"""
Database indexes for improved query performance.
This file contains index creation statements for various tables in the application.
These indexes are particularly helpful for filtering, sorting, and searching operations.
"""

from sqlalchemy import Index, text
from app.models.tag import Tag, ChatTag

# Create indexes for tag filtering and searching
# These will improve performance for the tag search/filtering capabilities

# Index on tag name for fast searching by name
tag_name_idx = Index('ix_tags_name', Tag.name)

# Index on tag color for filtering by color
tag_color_idx = Index('ix_tags_color', Tag.color)

# Composite index on user_id + name for faster user-specific tag searches
tag_user_name_idx = Index('ix_tags_user_id_name', Tag.user_id, Tag.name)

# Index on chat_tags for efficient lookups of tags for a specific chat
chat_tag_chat_id_idx = Index('ix_chat_tags_chat_id', ChatTag.chat_id)

# Index on chat_tags for efficient lookups of chats for a specific tag
chat_tag_tag_id_idx = Index('ix_chat_tags_tag_id', ChatTag.tag_id)

# Function to create all indexes
def create_indexes(engine):
    """Create all custom indexes on the database."""
    tag_name_idx.create(engine)
    tag_color_idx.create(engine)
    tag_user_name_idx.create(engine)
    chat_tag_chat_id_idx.create(engine)
    chat_tag_tag_id_idx.create(engine)
    
    # Log index creation
    print("Created custom indexes for tag filtering and searching")
