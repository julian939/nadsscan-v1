from sqlite3 import IntegrityError

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


    # --- Class Methods ---

    @classmethod
    def is_processed(cls, db, tx_hash: str) -> bool:
        return db.query(cls).filter(cls.tx_hash == tx_hash).first() is not None

    @classmethod
    def get_processed(cls, db, tx_hash: str):
        return db.query(cls).filter(cls.tx_hash == tx_hash).first()

    @classmethod
    def add_processed(cls, db, tx_hash: str, block_number: int, block_hash: str):
        try:
            if not cls.is_processed(db, tx_hash):
                tx = cls(
                    tx_hash=tx_hash,
                    block_number=block_number,
                    block_hash=block_hash
                )
                db.add(tx)
                db.commit()
                db.refresh(tx)
                return tx
        except IntegrityError:
            db.rollback()
            return None
        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_processed(cls, db, tx_hash: str):
        try:
            tx = db.query(cls).filter_by(tx_hash=tx_hash).first()
            if tx:
                db.delete(tx)
                db.commit()
        except Exception:
            db.rollback()
            raise
