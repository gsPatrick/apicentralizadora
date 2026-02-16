from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import verify_password, create_access_token, create_transfer_token
from app.config.settings import settings

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_user_token(user: User):
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "id": user.id, "is_superadmin": user.is_superadmin},
        expires_delta=access_token_expires
    )
    return access_token
