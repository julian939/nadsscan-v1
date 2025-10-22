from sqlalchemy import (
    Column,
    String,
    BigInteger,
    DateTime,
    func,
)
from app.db.database import Base


# --- Processed Transaction Basemodel ---
class ProcessedTransaction(Base):
    __tablename__ = "processed_transactions"

    tx_hash = Column(String, primary_key=True, index=True)
    block_number = Column(BigInteger, nullable=False)
    block_hash = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())