from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    func,
)
from app.db.database import Base


# --- Position Basemodel ---
class Position(Base):
    __tablename__ = "position"

    wallet = Column(String, primary_key=True, index=True)
    token = Column(String, primary_key=True)
    amount = Column(Numeric, nullable=False)
    realised_pnl = Column(Numeric, nullable=True, default=0)
    average_entry_price_mon = Column(Numeric, nullable=False)
    unrealised_pnl = Column(Numeric, nullable=True, default=0)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )