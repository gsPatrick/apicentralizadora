from sqlalchemy import Column, Integer, String
from app.config.database import Base

class System(Base):
    __tablename__ = "systems"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    base_url = Column(String, nullable=False)
    secret_key = Column(String, nullable=False) # Used for signature verification if needed
