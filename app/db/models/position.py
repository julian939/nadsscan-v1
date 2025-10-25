from sqlite3 import IntegrityError

from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    func,
)
from app.db.database import Base


# --- Position Basemodel ---
class Position(Base):
    __tablename__ = "position"

    wallet = Column(String, primary_key=True, index=True)
    token = Column(String, primary_key=True)
    amount = Column(Numeric, nullable=False)
    realised_pnl = Column(Numeric, nullable=True, default=0)
    average_entry_price_mon = Column(Numeric, nullable=False)
    unrealised_pnl = Column(Numeric, nullable=True, default=0)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    @classmethod
    def exists(cls, db, wallet: str, token: str) -> bool:
        return db.query(cls).filter(cls.wallet == wallet, cls.token == token).first() is not None

    @classmethod
    def get_position(cls, db, wallet: str, token: str):
        return db.query(cls).filter(cls.wallet == wallet, cls.token == token).first()

    @classmethod
    def add_position(cls, db, wallet: str, token: str, amount: float, average_entry_price_mon: float):
        try:
            if not cls.exists(db, wallet, token):
                position = cls(
                    wallet=wallet,
                    token=token,
                    amount=amount,
                    average_entry_price_mon=average_entry_price_mon
                )
        except IntegrityError:
            db.rollback()
            return None
        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_position(cls, db, wallet: str, token: str):
        try:
            position = db.query(cls).filter_by(wallet=wallet, token=token).first()
            if position:
                db.delete(position)
                db.commit()
        except Exception:
            db.rollback()
            raise
