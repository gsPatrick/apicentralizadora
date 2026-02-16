from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.config.database import get_db
from app.features.auth.router import get_current_user
from app.models.user import User
from app.models.access import UserSystemAccess

router = APIRouter(prefix="/access", tags=["Access"])

class AccessRequest(BaseModel):
    user_id: int
    system_id: int

def get_access_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin and current_user.role != 'manage_users': # managing access is usually user management
        raise HTTPException(status_code=403, detail="Not authorized to manage access")
    return current_user

from app.features.audit.router import log_action

@router.post("/grant")
def grant_access(req: AccessRequest, db: Session = Depends(get_db), admin: User = Depends(get_access_admin)):
    exists = db.query(UserSystemAccess).filter(
        UserSystemAccess.user_id == req.user_id,
        UserSystemAccess.system_id == req.system_id
    ).first()
    
    if exists:
        return {"detail": "Access already granted"}
    
    new_access = UserSystemAccess(user_id=req.user_id, system_id=req.system_id)
    db.add(new_access)
    db.commit()
    
    log_action(db, user_id=admin.id, action="GRANT_ACCESS", details=f"Granted access to System ID {req.system_id} for User ID {req.user_id}")
    return {"detail": "Access granted"}

@router.post("/revoke")
def revoke_access(req: AccessRequest, db: Session = Depends(get_db), admin: User = Depends(get_access_admin)):
    access = db.query(UserSystemAccess).filter(
        UserSystemAccess.user_id == req.user_id,
        UserSystemAccess.system_id == req.system_id
    ).first()
    
    if not access:
        raise HTTPException(status_code=404, detail="Access not found")
        
    db.delete(access)
    db.commit()
    
    log_action(db, user_id=admin.id, action="REVOKE_ACCESS", details=f"Revoked access to System ID {req.system_id} for User ID {req.user_id}")
    return {"detail": "Access revoked"}
