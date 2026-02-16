from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from app.config.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable if system action? Usually user driven.
    action = Column(String, nullable=False) # e.g., "CREATE_SYSTEM", "GRANT_ACCESS"
    details = Column(Text, nullable=True) # JSON or text details
    timestamp = Column(DateTime, default=datetime.utcnow)
