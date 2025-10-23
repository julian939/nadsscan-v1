import uuid
from sqlite3 import IntegrityError

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


    @classmethod
    def exists(cls, db, tx_hash: str) -> bool:
        return db.query(cls).filter(cls.tx_hash == tx_hash).first() is not None

    @classmethod
    def get_swap(cls, db, tx_hash: str):
        return db.query(cls).filter(cls.tx_hash == tx_hash).first()

    @classmethod
    def add_swap(cls, db,
                 tx_hash: str,
                 block_number: int,
                 block_hash: str,
                 pool: str,
                 token_in: str,
                 token_out: str,
                 amount_in_raw: str,
                 amount_out_raw: str,
                 amount_in: float,
                 amount_out: float,
                 mon_amount: float,
                 is_sell: bool,
                 wallet: str):
        try:
            if not cls.exists(db, tx_hash):
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
        except IntegrityError:
            db.rollback()
            return None
        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_swap(cls, db, tx_hash: str):
        try:
            swap = db.query(cls).filter_by(tx_hash=tx_hash).first()
            if swap:
                db.delete(swap)
                db.commit()
        except Exception:
            db.rollback()
            raise