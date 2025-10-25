import uuid
from sqlalchemy import (
    Column,
    String,
    BigInteger,
    Numeric,
    Boolean,
    DateTime,
    func,
    Index,
)
from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional


class Swap(Base):
    __tablename__ = "swaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tx_hash = Column(String, index=True, nullable=False, unique=True)
    block_number = Column(BigInteger, nullable=False, index=True)
    block_hash = Column(String, nullable=False)
    pool = Column(String, nullable=True, index=True)

    token_in = Column(String, nullable=False, index=True)
    token_out = Column(String, nullable=False, index=True)

    amount_in_raw = Column(String, nullable=True)
    amount_out_raw = Column(String, nullable=True)
    amount_in = Column(Numeric, nullable=True)
    amount_out = Column(Numeric, nullable=True)

    mon_amount = Column(Numeric, nullable=False)
    is_sell = Column(Boolean, nullable=False, default=False)

    wallet = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_swap_wallet_timestamp', 'wallet', 'timestamp'),
        Index('ix_swap_block', 'block_number', 'block_hash'),
    )

    @classmethod
    def exists(cls, db: Session, tx_hash: str) -> bool:
        """Check if swap exists in database"""
        try:
            return db.query(cls).filter(cls.tx_hash == tx_hash).first() is not None
        except Exception:
            return False

    @classmethod
    def get_swap(cls, db: Session, tx_hash: str) -> Optional['Swap']:
        """Get swap by transaction hash"""
        try:
            return db.query(cls).filter(cls.tx_hash == tx_hash).first()
        except Exception:
            return None

    @classmethod
    def add_swap(cls, db: Session,
                 tx_hash: str,
                 block_number: int,
                 block_hash: str,
                 pool: str,
                 token_in: str,
                 token_out: str,
                 amount_in_raw: str,
                 amount_out_raw: str,
                 amount_in: Decimal,
                 amount_out: Decimal,
                 mon_amount: Decimal,
                 is_sell: bool,
                 wallet: str) -> Optional['Swap']:
        """
        Add new swap to database

        Returns:
            Swap object if successful, existing Swap if already exists
        """
        try:
            if cls.exists(db, tx_hash):
                return cls.get_swap(db, tx_hash)

            swap = cls(
                tx_hash=tx_hash,
                block_number=block_number,
                block_hash=block_hash,
                pool=pool,
                token_in=token_in,
                token_out=token_out,
                amount_in_raw=amount_in_raw,
                amount_out_raw=amount_out_raw,
                amount_in=amount_in,
                amount_out=amount_out,
                mon_amount=mon_amount,
                is_sell=is_sell,
                wallet=wallet
            )
            db.add(swap)
            db.commit()
            db.refresh(swap)
            return swap

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_swap(cls, db: Session, tx_hash: str) -> bool:
        """
        Remove swap from database

        Returns:
            True if removed, False if not found
        """
        try:
            swap = db.query(cls).filter_by(tx_hash=tx_hash).first()
            if swap:
                db.delete(swap)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            raise