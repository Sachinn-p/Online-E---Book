from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import hashlib

from database import get_db
from models import User
from init_db import init_db
from auth import verify_password, get_password_hash, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES

# Initialize database on startup
init_db()

app = FastAPI(title="User Service", description="Microservice for user management and authentication", version="1.0.0")

# Security scheme for JWT
security = HTTPBearer()

# Pydantic models for request/response
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

def hash_password(password: str) -> str:
    """Simple password hashing function - replaced by bcrypt in auth.py"""
    return get_password_hash(password)

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user with username and password"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user

@app.get("/")
def read_root():
    return {"message": "User Service is running!", "service": "user_service"}

@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    # Validate input data
    if len(user.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user.username.strip()).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    try:
        # Create new user
        hashed_password = hash_password(user.password)
        db_user = User(
            username=user.username.strip(),
            email=user.email,
            password_hash=hashed_password,
            full_name=user.full_name.strip() if user.full_name else None
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating user")

@app.post("/login", response_model=Token)
def login_for_access_token(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    # Validate input
    if len(user_credentials.username.strip()) == 0:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if len(user_credentials.password) == 0:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    
    user = authenticate_user(db, user_credentials.username.strip(), user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user

@app.get("/verify-token")
def verify_user_token(current_user: User = Depends(get_current_user)):
    """Verify JWT token - used by other services"""
    return {
        "valid": True, 
        "user_id": current_user.id, 
        "username": current_user.username,
        "email": current_user.email
    }

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch user by ID - requires authentication"""
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/users", response_model=list[UserResponse])
def get_all_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all users - requires authentication"""
    users = db.query(User).all()
    return users

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update user - requires authentication"""
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    
    # Validate update data
    if 'username' in update_data:
        if len(update_data['username'].strip()) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
        # Check if new username already exists
        existing_user = db.query(User).filter(User.username == update_data['username'].strip(), User.id != user_id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    if 'email' in update_data:
        # Check if new email already exists
        existing_user = db.query(User).filter(User.email == update_data['email'], User.id != user_id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already taken")
    
    try:
        for field, value in update_data.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating user")

@app.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete user - requires authentication"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
