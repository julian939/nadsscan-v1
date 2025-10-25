from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
)
from app.db.database import Base
from sqlalchemy.orm import Session
from typing import Optional


class Wallet(Base):
    __tablename__ = "wallets"

    address = Column(String, primary_key=True, index=True)
    twitter_name = Column(String, nullable=True)
    twitter_pfp = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    def exists(cls, db: Session, address: str) -> bool:
        """Check if wallet exists in database"""
        try:
            return db.query(cls).filter(cls.address == address).first() is not None
        except Exception:
            return False

    @classmethod
    def get_wallet(cls, db: Session, address: str) -> Optional['Wallet']:
        """Get wallet by address"""
        try:
            return db.query(cls).filter(cls.address == address).first()
        except Exception:
            return None

    @classmethod
    def add_wallet(cls, db: Session, address: str, twitter_name: Optional[str] = None,
                   twitter_pfp: Optional[str] = None) -> Optional['Wallet']:
        """
        Add new wallet to database

        Args:
            db: Database session
            address: Wallet address
            twitter_name: Twitter username (optional)
            twitter_pfp: Twitter profile picture URL (optional)

        Returns:
            Wallet object if successful, None if already exists
        """
        try:
            if cls.exists(db, address):
                return cls.get_wallet(db, address)

            wallet = cls(
                address=address,
                twitter_name=twitter_name,
                twitter_pfp=twitter_pfp
            )
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
            return wallet

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_wallet(cls, db: Session, address: str) -> bool:
        """
        Remove wallet from database

        Returns:
            True if removed, False if not found
        """
        try:
            wallet = db.query(cls).filter_by(address=address).first()
            if wallet:
                db.delete(wallet)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            raise