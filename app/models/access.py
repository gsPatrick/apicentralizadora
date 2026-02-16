from sqlalchemy import Column, Integer, ForeignKey
from app.config.database import Base

class UserSystemAccess(Base):
    __tablename__ = "user_system_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=False)
