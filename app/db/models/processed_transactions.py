from sqlalchemy import (
    Column,
    String,
    BigInteger,
    DateTime,
    func,
    Index,
)
from app.db.database import Base
from sqlalchemy.orm import Session
from typing import Optional


class ProcessedTransaction(Base):
    __tablename__ = "processed_transactions"

    tx_hash = Column(String, primary_key=True, index=True)
    block_number = Column(BigInteger, nullable=False, index=True)  # Index added for reorg queries
    block_hash = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Composite index for block queries
    __table_args__ = (
        Index('ix_block_number_hash', 'block_number', 'block_hash'),
    )

    @classmethod
    def is_processed(cls, db: Session, tx_hash: str) -> bool:
        """Check if transaction has been processed"""
        try:
            return db.query(cls).filter(cls.tx_hash == tx_hash).first() is not None
        except Exception:
            return False

    @classmethod
    def get_processed(cls, db: Session, tx_hash: str) -> Optional['ProcessedTransaction']:
        """Get processed transaction by hash"""
        try:
            return db.query(cls).filter(cls.tx_hash == tx_hash).first()
        except Exception:
            return None

    @classmethod
    def add_processed(cls, db: Session, tx_hash: str, block_number: int, block_hash: str) -> Optional[
        'ProcessedTransaction']:
        """
        Mark transaction as processed

        Args:
            db: Database session
            tx_hash: Transaction hash
            block_number: Block number
            block_hash: Block hash

        Returns:
            ProcessedTransaction object if successful, None if already exists
        """
        try:
            if cls.is_processed(db, tx_hash):
                return cls.get_processed(db, tx_hash)

            tx = cls(
                tx_hash=tx_hash,
                block_number=block_number,
                block_hash=block_hash
            )
            db.add(tx)
            db.commit()
            db.refresh(tx)
            return tx

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_processed(cls, db: Session, tx_hash: str) -> bool:
        """
        Remove processed transaction

        Returns:
            True if removed, False if not found
        """
        try:
            tx = db.query(cls).filter_by(tx_hash=tx_hash).first()
            if tx:
                db.delete(tx)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            raise

    @classmethod
    def get_by_block(cls, db: Session, block_number: int) -> Optional['ProcessedTransaction']:
        """Get any processed transaction from a specific block"""
        try:
            return db.query(cls).filter(cls.block_number == block_number).first()
        except Exception:
            return None