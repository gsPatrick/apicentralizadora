from app.config.database import SessionLocal, Base, engine
from app.models.user import User
from app.utils.security import get_password_hash

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    email = "admin@admin.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"Creating superuser: {email}")
        new_user = User(
            email=email,
            hashed_password=get_password_hash("admin123"),
            is_superadmin=True,
            role="superadmin"
        )
        db.add(new_user)
        db.commit()
    else:
        print("Superuser already exists")
    db.close()

if __name__ == "__main__":
    seed()
