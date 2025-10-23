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


    @classmethod
    def exists(cls, db, tx_hash: str) -> bool:
        return db.query(cls).filter(cls.tx_hash == tx_hash).first() is not None

    @classmethod
    def get_nft_trade(cls, db, tx_hash: str):
        return db.query(cls).filter(cls.tx_hash == tx_hash).first()

    @classmethod
    def add_nft_trade(cls, db,
                      tx_hash: str,
                      block_number: int,
                      block_hash: str,
                      contract: str,
                      token_id: str,
                      value_mon: float,
                      is_sell: bool,
                      is_buy: bool,
                      wallet: str):
        try:
            if not cls.exists(db, tx_hash):
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
        except IntegrityError:
            db.rollback()
            return None
        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_nft_trade(cls, db, tx_hash: str):
        try:
            trade = db.query(cls).filter_by(tx_hash=tx_hash).first()
            if trade:
                db.delete(trade)
                db.commit()
        except Exception:
            db.rollback()
            raise