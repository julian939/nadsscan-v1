from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
    Index,
)
from app.db.database import Base
from sqlalchemy.orm import Session
from typing import Optional


class Pool(Base):
    __tablename__ = "pools"

    address = Column(String, primary_key=True, index=True)
    token0 = Column(String, nullable=False, index=True)
    token1 = Column(String, nullable=False, index=True)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Composite index for token lookups
    __table_args__ = (
        Index('ix_pool_tokens', 'token0', 'token1'),
    )

    @classmethod
    def exists(cls, db: Session, address: str) -> bool:
        """Check if pool exists in database"""
        try:
            return db.query(cls).filter(cls.address == address).first() is not None
        except Exception:
            return False

    @classmethod
    def get_pool(cls, db: Session, address: str) -> Optional['Pool']:
        """Get pool by address"""
        try:
            return db.query(cls).filter(cls.address == address).first()
        except Exception:
            return None

    @classmethod
    def add_pool(cls, db: Session, address: str, token0: str, token1: str) -> Optional['Pool']:
        """
        Add new pool to database

        Args:
            db: Database session
            address: Pool address
            token0: First token address
            token1: Second token address

        Returns:
            Pool object if successful, None otherwise
        """
        try:
            if cls.exists(db, address):
                return cls.get_pool(db, address)

            pool = cls(
                address=address,
                token0=token0,
                token1=token1
            )
            db.add(pool)
            db.commit()
            db.refresh(pool)
            return pool

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_pool(cls, db: Session, address: str) -> bool:
        """
        Remove pool from database

        Returns:
            True if removed, False if not found
        """
        try:
            pool = db.query(cls).filter_by(address=address).first()
            if pool:
                db.delete(pool)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            raise