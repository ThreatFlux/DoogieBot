from app.db.base import Base, engine
from app.models.tag import Tag, ChatTag

def create_tag_tables():
    # Create tables that don't exist
    Base.metadata.create_all(bind=engine)
    print("Tag tables created successfully")

if __name__ == "__main__":
    create_tag_tables()
