from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.config.database import get_db
from app.features.auth.router import get_current_user
from app.models.user import User
from app.utils.security import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_superadmin: bool = False
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_superadmin: bool
    role: Optional[str]
    
    class Config:
        from_attributes = True

# Dependency to check admin permissions
def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin and current_user.role != 'manage_users':
        raise HTTPException(status_code=403, detail="Not authorized to manage users")
    return current_user

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        is_superadmin=user.is_superadmin,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
         raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}
