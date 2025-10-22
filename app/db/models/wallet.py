from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
)
from app.db.database import Base


# --- Wallet Basemodel ---
class Wallet(Base):
    __tablename__ = "wallets"

    address = Column(String, primary_key=True, index=True)
    twitter_name = Column(String, nullable=True)
    twitter_pfp = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())