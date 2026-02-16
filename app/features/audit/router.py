from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from app.config.database import get_db
from app.features.auth.router import get_current_user
from app.models.user import User
from app.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])

class AuditResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    details: str | None
    timestamp: datetime
    
    class Config:
        from_attributes = True

def log_action(db: Session, user_id: int, action: str, details: str = None):
    log = AuditLog(user_id=user_id, action=action, details=details)
    db.add(log)
    db.commit()

@router.get("/", response_model=List[AuditResponse])
def read_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Not authorized to view audit logs")
    
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
