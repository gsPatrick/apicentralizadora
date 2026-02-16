from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.config.database import get_db
from app.features.auth.router import get_current_user
from app.models.user import User
from app.models.system import System
import secrets

router = APIRouter(prefix="/systems", tags=["Systems"])

class SystemCreate(BaseModel):
    name: str
    base_url: str

class SystemResponse(BaseModel):
    id: int
    name: str
    base_url: str
    # secret_key: str # Usually don't expose secret key in list

    class Config:
        from_attributes = True

def get_system_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin and current_user.role != 'manage_systems':
        raise HTTPException(status_code=403, detail="Not authorized to manage systems")
    return current_user

@router.post("/", response_model=SystemResponse)
def create_system(system: SystemCreate, db: Session = Depends(get_db), admin: User = Depends(get_system_admin)):
    db_system = db.query(System).filter(System.name == system.name).first()
    if db_system:
        raise HTTPException(status_code=400, detail="System already exists")
    
    new_system = System(
        name=system.name,
        base_url=system.base_url,
        secret_key=secrets.token_hex(32)
    )
    db.add(new_system)
    db.commit()
    db.refresh(new_system)
    return new_system

@router.get("/", response_model=List[SystemResponse])
def read_systems(db: Session = Depends(get_db), admin: User = Depends(get_system_admin)):
    return db.query(System).all()

@router.delete("/{system_id}")
def delete_system(system_id: int, db: Session = Depends(get_db), admin: User = Depends(get_system_admin)):
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    db.delete(system)
    db.commit()
    return {"detail": "System deleted"}
