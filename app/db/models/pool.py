from sqlite3 import IntegrityError

from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
)
from app.db.database import Base


# --- Pool Basemodel ---
class Pool(Base):
    __tablename__ = "pools"

    address = Column(String, primary_key=True, index=True)
    token0 = Column(String, nullable=False)
    token1 = Column(String, nullable=False)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    @classmethod
    def exists(cls, db, address: str) -> bool:
        return db.query(cls).filter(cls.address == address).first() is not None

    @classmethod
    def get_pool(cls, db, address: str):
        return db.query(cls).filter(cls.address == address).first()

    @classmethod
    def add_pool(cls, db, address: str, token0: str, token1: str):
        try:
            if not cls.exists(db, address):
                pool = cls(
                    address=address,
                    token0=token0,
                    token1=token1
                )
                db.add(pool)
        except IntegrityError:
            db.rollback()
            return None
        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def remove_pool(cls, db, address: str):
        try:
            pool = db.query(cls).filter_by(address=address).first()
            if pool:
                db.delete(pool)
                db.commit()
        except Exception:
            db.rollback()
            raise