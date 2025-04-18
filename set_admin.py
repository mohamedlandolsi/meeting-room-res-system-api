#!/usr/bin/env python3
"""
Script to set a user as an admin by email address
"""
import sys
import os
import argparse
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the current directory to the path so we can import from user-service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'user-service'))

def set_admin(email):
    """Set a user as admin by email"""
    # Load environment variables from user-service
    load_dotenv(os.path.join(os.path.dirname(__file__), 'user-service', '.env'))
    
    # Import User model 
    from user_service.models import User

    # Connect to database
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/user_db')
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Find user by email
    user = session.query(User).filter_by(email=email).first()
    
    if not user:
        print(f"❌ User with email {email} not found")
        return False
    
    # Update role to Admin
    if user.role == 'Admin':
        print(f"ℹ️ User {user.name} ({user.email}) is already an Admin")
        return True
        
    user.role = 'Admin'
    session.commit()
    print(f"✅ User {user.name} ({user.email}) has been set as Admin")
    return True

def main():
    """Main function to set admin role"""
    parser = argparse.ArgumentParser(description='Set a user as admin by email')
    parser.add_argument('email', help='Email address of the user to make admin')
    
    args = parser.parse_args()
    set_admin(args.email)

if __name__ == "__main__":
    main()
