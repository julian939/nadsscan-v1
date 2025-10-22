import uuid
from sqlalchemy import (
    Column,
    String,
    BigInteger,
    Numeric,
    Boolean,
    DateTime,
    func,
)
from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID


# --- Swap Basemodel ---
class Swap(Base):
    __tablename__ = "swaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tx_hash = Column(String, index=True, nullable=False)
    block_number = Column(BigInteger, nullable=False)
    block_hash = Column(String, nullable=False)
    pool = Column(String, nullable=True)

    token_in = Column(String, nullable=False)
    token_out = Column(String, nullable=False)

    amount_in_raw = Column(String, nullable=True)
    amount_out_raw = Column(String, nullable=True)
    amount_in = Column(Numeric, nullable=True)
    amount_out = Column(Numeric, nullable=True)

    mon_amount = Column(Numeric, nullable=False)
    is_sell = Column(Boolean, nullable=False, default=False)

    wallet = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())