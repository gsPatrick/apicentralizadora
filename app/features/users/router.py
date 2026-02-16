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
from app.features.audit.router import log_action

# ... (Previous imports)

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_superadmin: bool = False
    is_active: bool = True
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_superadmin: bool
    is_active: bool
    role: Optional[str]
    
    class Config:
        from_attributes = True

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
        is_active=user.is_active,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_action(db, user_id=admin.id, action="CREATE_USER", details=f"Created user: {new_user.email}")
    return new_user

@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.patch("/{user_id}/activate")
def activate_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    db.commit()
    
    log_action(db, user_id=admin.id, action="ACTIVATE_USER", details=f"Activated user: {user.email}")
    return {"detail": "User activated"}

@router.patch("/{user_id}/deactivate")
def deactivate_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    db.commit()
    
    log_action(db, user_id=admin.id, action="DEACTIVATE_USER", details=f"Deactivated user: {user.email}")
    return {"detail": "User deactivated"}

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
         raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user_email = user.email
    db.delete(user)
    db.commit()
    
    log_action(db, user_id=admin.id, action="DELETE_USER", details=f"Deleted user: {user_email} (ID: {user_id})")
    return {"detail": "User deleted"}

from app.models.system import System
from app.models.access import UserSystemAccess

@router.get("/me/systems")
def get_my_systems(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns systems the current user has access to."""
    systems = db.query(System).join(UserSystemAccess).filter(
        UserSystemAccess.user_id == current_user.id
    ).all()
    
    return [
        {"id": s.id, "name": s.name, "base_url": s.base_url}
        for s in systems
    ]

@router.get("/{user_id}/systems")
def get_user_systems(user_id: int, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Returns systems a specific user has access to (Admin only)."""
    systems = db.query(System).join(UserSystemAccess).filter(
        UserSystemAccess.user_id == user_id
    ).all()
    
    return [
        {"id": s.id, "name": s.name, "base_url": s.base_url}
        for s in systems
    ]
