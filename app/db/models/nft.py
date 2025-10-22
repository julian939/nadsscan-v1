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



# --- NFT Basemodel ---
class NFTTrade(Base):
    __tablename__ = "nft_trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tx_hash = Column(String, index=True, nullable=False)
    block_number = Column(BigInteger, nullable=False)
    block_hash = Column(String, nullable=False)

    contract = Column(String, nullable=False)
    token_id = Column(String, nullable=False)
    value_mon = Column(Numeric, nullable=False)

    is_sell = Column(Boolean, nullable=False, default=False)
    is_buy = Column(Boolean, nullable=False, default=False)

    wallet = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())