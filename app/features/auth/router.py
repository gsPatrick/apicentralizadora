from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.features.auth.service import authenticate_user, create_user_token
from app.models.user import User
from app.models.system import System
from app.models.access import UserSystemAccess
from app.utils.security import create_transfer_token
from jose import jwt, JWTError
from app.config.settings import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

# OAuth2 scheme for Swagger UI
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    username = form_data.username.strip().lower() # Standardize
    print(f"DEBUG: Login attempt for {username}")
    user = authenticate_user(db, username, form_data.password)
    
    if not user:
        # One last try check if email exists with different case
        user = db.query(User).filter(User.email.ilike(username)).first()
        if user and authenticate_user(db, user.email, form_data.password):
             print(f"DEBUG: Login successful via ILIKE for {user.email}")
        else:
            print(f"DEBUG: Login failed for {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    print(f"DEBUG: Login successful for {user.email}")
    access_token = create_user_token(user)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/verify-session")
def verify_session(
    system_id: int,
    redirect_url: str,
    response: Response,
    token: str = Depends(oauth2_scheme), # Expecting token in Authorization header for API, or cookie for browser?
    # The prompt says "Check if the user has an active session cookie". 
    # For simplicity in this API-first design, we'll check the Authorization header primarily, 
    # but a real browser flow would use a cookie. 
    # Let's assume the frontend/browser sends the token or we rely on a cookie wrapper.
    # For this strict backend task, I will implement it looking for the Cookie if the Header is missing, or just standard Depends.
    # Let's add a cookie check for the browser flow.
    db: Session = Depends(get_db)
):
    # In a real browser flow, the user clicks "Verify" and the browser sends the request.
    # If using Swagger, we use the button. If using a browser, we need a cookie.
    # I will assume the user has a cookie named "access_token" for the browser flow.
    
    # Logic:
    # 1. Get User from Token (Header or Cookie)
    # 2. Check Access
    # 3. Redirect
    
    # We'll use the get_current_user dependency which works with the Bearer token. 
    # To support the browser flow effectively, we'd need a cookie-based dependency, 
    # but I'll stick to the requested "Route" logic using the standard dependency for now.
    pass

# Redefining verify_session to handle the browser flow better
from starlette.requests import Request
from starlette.responses import RedirectResponse

@router.get("/verify-session-browser")
async def verify_session_browser(
    request: Request,
    system_id: int,
    redirect_url: str,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    # custom logic to pull token from query param, cookie or header
    if not token:
        token = request.cookies.get("access_token") 
    
    if not token:
        # Not logged in -> Redirect to Central Login (Frontend URL)
        hub_login_url = "https://hub-sbacem.vercel.app/login"
        target = f"{hub_login_url}?system_id={system_id}&redirect_url={redirect_url}"
        return RedirectResponse(url=target)

    try:
        user = await get_current_user(token, db) # Re-using the logic manually
    except Exception:
        hub_login_url = "https://hub-sbacem.vercel.app/login"
        target = f"{hub_login_url}?system_id={system_id}&redirect_url={redirect_url}"
        return RedirectResponse(url=target)
    
    # Check Access
    access = db.query(UserSystemAccess).filter(
        UserSystemAccess.user_id == user.id,
        UserSystemAccess.system_id == system_id
    ).first()

    if not access:
        unauthorized_url = "https://hub-sbacem.vercel.app/unauthorized"
        return RedirectResponse(url=unauthorized_url)

    # Generate Transfer Token
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        unauthorized_url = "https://hub-sbacem.vercel.app/unauthorized?error=system_not_found"
        return RedirectResponse(url=unauthorized_url)

    transfer_data = {
        "sub": user.email,
        "type": "transfer", 
        "system_id": system_id
    }
    transfer_token = create_transfer_token(transfer_data)

    # Redirect
    # {satellite_base_url}/liberar?token={transfer_token}&next={redirect_url}
    target = f"{system.base_url}/liberar?token={transfer_token}&next={redirect_url}"
    return RedirectResponse(url=target)

@router.post("/validate-ticket")
def validate_ticket(ticket: dict, db: Session = Depends(get_db)):
    # Ticket comes in the body: {"token": "..."}
    token = ticket.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "transfer":
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Verify Access Again (Double check)
        system_id = payload.get("system_id")
        access = db.query(UserSystemAccess).filter(
            UserSystemAccess.user_id == user.id,
            UserSystemAccess.system_id == system_id
        ).first()
        
        if not access:
             raise HTTPException(status_code=403, detail="Access revoked")
             
        return {
            "email": user.email,
            "id": user.id,
            "is_admin": user.is_superadmin, # returning central admin status, or whatever satellite needs
            "status": "active"
        }
        
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
