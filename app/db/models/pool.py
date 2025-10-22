from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
)
from app.db.database import Base


# --- Pool Basemodel ---
class Pool(Base):
    __tablename__ = "pools"

    address = Column(String, primary_key=True, index=True)
    token0 = Column(String, nullable=False)
    token1 = Column(String, nullable=False)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )