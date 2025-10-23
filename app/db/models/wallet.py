from sqlite3 import IntegrityError
from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
)
from app.db.database import Base


# --- Wallet Basemodel ---
class Wallet(Base):
    __tablename__ = "wallets"

    address = Column(String, primary_key=True, index=True)
    twitter_name = Column(String, nullable=True)
    twitter_pfp = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


    @classmethod
    def exists(cls, db, address: str) -> bool:
        return db.query(cls).filter(cls.address == address).first() is not None

    @classmethod
    def get_wallet(cls, db, address: str):
        return db.query(cls).filter(cls.address == address).first()

    @classmethod
    def add_wallet(cls, db, address: str, twitter_name: str, twitter_pfp: str):
        try:
            if not cls.exists(db, address):
                wallet = cls(
                    address=address,
                    twitter_name=twitter_name,
                    twitter_pfp=twitter_pfp
                )
                db.add(wallet)
                db.commit()
                db.refresh(wallet)
                return wallet
        except IntegrityError:
            db.rollback()
            return None
        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_wallet(cls, db, address: str):
        try:
            wallet = db.query(cls).filter_by(address=address).first()
            if wallet:
                db.delete(wallet)
                db.commit()
        except Exception:
            db.rollback()
            raise