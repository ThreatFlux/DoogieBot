#!/usr/bin/env python3
"""
Script to clear all users from the database.
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User, UserRole, UserStatus
from app.services.user import UserService
from app.core.config import settings
from app.schemas.user import UserCreate

# Use the specific database path
DB_PATH = "/app/backend/doogie.db"
DB_URL = f"sqlite:///{DB_PATH}"

# Create SQLite engine with the specific database path
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_admin_credentials():
    """Get admin credentials from user input."""
    while True:
        email = input("Enter admin email: ").strip()
        if "@" in email and "." in email:
            break
        print("Please enter a valid email address.")
    
    while True:
        password = input("Enter admin password: ").strip()
        if len(password) >= 8:
            break
        print("Password must be at least 8 characters long.")
    
    return email, password

def clear_users(recreate_admin: bool = False):
    """
    Clear all users from the database.
    
    Args:
        recreate_admin: Whether to recreate the first admin user after clearing.
                        Default is False to allow the application to create the first user on connect.
    """
    db = SessionLocal()
    try:
        # Get the count of users before deletion
        user_count = db.query(User).count()
        print(f"Found {user_count} users in the database.")
        
        # Delete all users
        db.query(User).delete()
        db.commit()
        print("All users have been deleted from the database.")
        
        # Optionally recreate the first admin user
        if recreate_admin:
            print("\nCreating admin user...")
            email, password = get_admin_credentials()
            admin = UserService.create_first_admin(db, email, password)
            print(f"\nCreated admin user with email: {admin.email}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear all users from the database.")
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Recreate the admin user after clearing (default: False)."
    )
    
    args = parser.parse_args()
    
    # Confirm with the user before proceeding
    confirm = input("This will delete ALL users from the database. Are you sure? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    clear_users(recreate_admin=args.create_admin)