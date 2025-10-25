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


class NFTTrade(Base):
    __tablename__ = "nft_trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tx_hash = Column(String, index=True, nullable=False, unique=True)
    block_number = Column(BigInteger, nullable=False, index=True)
    block_hash = Column(String, nullable=False)

    contract = Column(String, nullable=False, index=True)
    token_id = Column(String, nullable=False)
    #amount = Column(Numeric, nullable=False) - add?
    value_mon = Column(Numeric, nullable=False)

    is_sell = Column(Boolean, nullable=False, default=False)

    wallet = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_nft_wallet_timestamp', 'wallet', 'timestamp'),
        Index('ix_nft_contract_token', 'contract', 'token_id'),
        Index('ix_nft_block', 'block_number', 'block_hash'),
    )

    @classmethod
    def exists(cls, db: Session, tx_hash: str) -> bool:
        """Check if NFT trade exists in database"""
        try:
            return db.query(cls).filter(cls.tx_hash == tx_hash).first() is not None
        except Exception:
            return False

    @classmethod
    def get_nft_trade(cls, db: Session, tx_hash: str) -> Optional['NFTTrade']:
        """Get NFT trade by transaction hash"""
        try:
            return db.query(cls).filter(cls.tx_hash == tx_hash).first()
        except Exception:
            return None

    @classmethod
    def add_nft_trade(cls, db: Session,
                      tx_hash: str,
                      block_number: int,
                      block_hash: str,
                      contract: str,
                      token_id: str,
                      value_mon: Decimal,
                      is_sell: bool,
                      is_buy: bool,
                      wallet: str) -> Optional['NFTTrade']:
        """
        Add new NFT trade to database

        Returns:
            NFTTrade object if successful, existing trade if already exists
        """
        try:
            if cls.exists(db, tx_hash):
                return cls.get_nft_trade(db, tx_hash)

            trade = cls(
                tx_hash=tx_hash,
                block_number=block_number,
                block_hash=block_hash,
                contract=contract,
                token_id=token_id,
                value_mon=value_mon,
                is_sell=is_sell,
                is_buy=is_buy,
                wallet=wallet
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            return trade

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_nft_trade(cls, db: Session, tx_hash: str) -> bool:
        """
        Remove NFT trade from database

        Returns:
            True if removed, False if not found
        """
        try:
            trade = db.query(cls).filter_by(tx_hash=tx_hash).first()
            if trade:
                db.delete(trade)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            raise