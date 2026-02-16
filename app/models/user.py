from sqlalchemy import Column, Integer, String, Boolean
from app.config.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_superadmin = Column(Boolean, default=False)
    role = Column(String, nullable=True) # e.g. 'manage_users', 'manage_systems', etc.
