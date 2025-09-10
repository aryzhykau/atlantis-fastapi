#!/usr/bin/env python3
"""
Script to create the first OWNER user in the database.
This should be run after the migration to add OWNER role.
"""

import asyncio
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models.user import User, UserRole
from app.auth.password import hash_password

def create_owner_user():
    """Create the first OWNER user"""
    db: Session = SessionLocal()
    
    try:
        # Check if an OWNER user already exists
        existing_owner = db.query(User).filter(User.role == UserRole.OWNER).first()
        
        if existing_owner:
            print(f"OWNER user already exists: {existing_owner.email}")
            return
        
        # Create owner user
        owner_email = input("Enter email for OWNER user: ").strip()
        owner_password = input("Enter password for OWNER user: ").strip()
        owner_first_name = input("Enter first name for OWNER user: ").strip()
        owner_last_name = input("Enter last name for OWNER user: ").strip()
        
        if not all([owner_email, owner_password, owner_first_name, owner_last_name]):
            print("All fields are required!")
            return
        
        # Check if user with this email already exists
        existing_user = db.query(User).filter(User.email == owner_email).first()
        if existing_user:
            print(f"User with email {owner_email} already exists!")
            return
        
        # Create the OWNER user
        hashed_password = hash_password(owner_password)
        
        owner_user = User(
            email=owner_email,
            hashed_password=hashed_password,
            first_name=owner_first_name,
            last_name=owner_last_name,
            role=UserRole.OWNER,
            is_active=True
        )
        
        db.add(owner_user)
        db.commit()
        db.refresh(owner_user)
        
        print(f"✅ OWNER user created successfully!")
        print(f"Email: {owner_user.email}")
        print(f"Role: {owner_user.role}")
        print(f"ID: {owner_user.id}")
        
    except Exception as e:
        print(f"❌ Error creating OWNER user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_owner_user()
