from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    func,
    Index,
)
from app.db.database import Base
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional


class Position(Base):
    __tablename__ = "positions"

    wallet = Column(String, primary_key=True, index=True)
    token = Column(String, primary_key=True, index=True)

    # Position size
    amount = Column(Numeric(precision=36, scale=18), nullable=False, default=0)

    # Entry price tracking (weighted average)
    average_entry_price_mon = Column(Numeric(precision=36, scale=18), nullable=False)
    total_cost_mon = Column(Numeric(precision=36, scale=18), nullable=False, default=0)

    # PnL tracking
    realized_pnl_mon = Column(Numeric(precision=36, scale=18), nullable=False, default=0)
    unrealized_pnl_mon = Column(Numeric(precision=36, scale=18), nullable=True, default=0)

    # Trade statistics
    total_bought = Column(Numeric(precision=36, scale=18), nullable=False, default=0)
    total_sold = Column(Numeric(precision=36, scale=18), nullable=False, default=0)
    trade_count = Column(Numeric, nullable=False, default=0)

    # Metadata
    first_trade_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        Index('ix_position_wallet_token', 'wallet', 'token'),
        Index('ix_position_amount', 'amount'),  # For filtering non-zero positions
    )

    @classmethod
    def exists(cls, db: Session, wallet: str, token: str) -> bool:
        """Check if position exists"""
        try:
            return db.query(cls).filter(cls.wallet == wallet, cls.token == token).first() is not None
        except Exception:
            return False

    @classmethod
    def get_position(cls, db: Session, wallet: str, token: str) -> Optional['Position']:
        """Get position by wallet and token"""
        try:
            return db.query(cls).filter(cls.wallet == wallet, cls.token == token).first()
        except Exception:
            return None

    @classmethod
    def create_position(
            cls,
            db: Session,
            wallet: str,
            token: str,
            initial_amount: Decimal,
            entry_price_mon: Decimal
    ) -> Optional['Position']:
        """
        Create new position from first buy

        Args:
            db: Database session
            wallet: Wallet address
            token: Token address
            initial_amount: Initial token amount bought
            entry_price_mon: Price per token in MON

        Returns:
            Position object if successful
        """
        try:
            if cls.exists(db, wallet, token):
                return cls.get_position(db, wallet, token)

            total_cost = initial_amount * entry_price_mon

            position = cls(
                wallet=wallet,
                token=token,
                amount=initial_amount,
                average_entry_price_mon=entry_price_mon,
                total_cost_mon=total_cost,
                total_bought=initial_amount,
                trade_count=1
            )
            db.add(position)
            db.commit()
            db.refresh(position)
            return position

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def update_on_buy(
            cls,
            db: Session,
            wallet: str,
            token: str,
            buy_amount: Decimal,
            buy_price_mon: Decimal
    ) -> Optional['Position']:
        """
        Update position when buying more tokens

        Recalculates weighted average entry price

        Args:
            db: Database session
            wallet: Wallet address
            token: Token address
            buy_amount: Amount of tokens bought
            buy_price_mon: Price per token in MON

        Returns:
            Updated Position object
        """
        try:
            position = cls.get_position(db, wallet, token)

            if not position:
                # Create new position if it doesn't exist
                return cls.create_position(db, wallet, token, buy_amount, buy_price_mon)

            # Calculate new weighted average entry price
            additional_cost = buy_amount * buy_price_mon
            new_total_cost = position.total_cost_mon + additional_cost
            new_amount = position.amount + buy_amount

            position.average_entry_price_mon = new_total_cost / new_amount if new_amount > 0 else Decimal(0)
            position.total_cost_mon = new_total_cost
            position.amount = new_amount
            position.total_bought += buy_amount
            position.trade_count += 1

            db.commit()
            db.refresh(position)
            return position

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def update_on_sell(
            cls,
            db: Session,
            wallet: str,
            token: str,
            sell_amount: Decimal,
            sell_price_mon: Decimal
    ) -> Optional['Position']:
        """
        Update position when selling tokens

        Calculates realized PnL based on average entry price

        Args:
            db: Database session
            wallet: Wallet address
            token: Token address
            sell_amount: Amount of tokens sold
            sell_price_mon: Price per token in MON received

        Returns:
            Updated Position object
        """
        try:
            position = cls.get_position(db, wallet, token)

            if not position:
                # No position exists - this shouldn't happen normally
                # Create position with negative amount (short position)
                position = cls.create_position(db, wallet, token, -sell_amount, sell_price_mon)
                position.realized_pnl_mon = Decimal(0)  # No PnL on first sell
                db.commit()
                db.refresh(position)
                return position

            # Calculate realized PnL
            # PnL = (sell_price - avg_entry_price) * sell_amount
            pnl = (sell_price_mon - position.average_entry_price_mon) * sell_amount
            position.realized_pnl_mon += pnl

            # Update position size
            new_amount = position.amount - sell_amount

            if new_amount > 0:
                # Partial sell - reduce cost basis proportionally
                cost_of_sold_portion = position.average_entry_price_mon * sell_amount
                position.total_cost_mon -= cost_of_sold_portion
                position.amount = new_amount
            elif new_amount == 0:
                # Complete close - position is flat
                position.amount = Decimal(0)
                position.total_cost_mon = Decimal(0)
                position.average_entry_price_mon = Decimal(0)
            else:
                # Oversell - went short or error
                position.amount = new_amount
                # Keep entry price for tracking, but cost basis is zero
                position.total_cost_mon = Decimal(0)

            position.total_sold += sell_amount
            position.trade_count += 1

            db.commit()
            db.refresh(position)
            return position

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def update_unrealized_pnl(
            cls,
            db: Session,
            wallet: str,
            token: str,
            current_price_mon: Decimal
    ) -> Optional['Position']:
        """
        Update unrealized PnL based on current market price

        Unrealized PnL = (current_price - avg_entry_price) * amount

        Args:
            db: Database session
            wallet: Wallet address
            token: Token address
            current_price_mon: Current price per token in MON

        Returns:
            Updated Position object
        """
        try:
            position = cls.get_position(db, wallet, token)

            if not position or position.amount <= 0:
                return position

            # Calculate unrealized PnL
            position.unrealized_pnl_mon = (
                    (current_price_mon - position.average_entry_price_mon) * position.amount
            )

            db.commit()
            db.refresh(position)
            return position

        except Exception as e:
            db.rollback()
            raise e

    @classmethod
    def get_total_pnl(cls, position: 'Position') -> Decimal:
        """
        Calculate total PnL (realized + unrealized)

        Args:
            position: Position object

        Returns:
            Total PnL in MON
        """
        realized = position.realized_pnl_mon or Decimal(0)
        unrealized = position.unrealized_pnl_mon or Decimal(0)
        return realized + unrealized

    @classmethod
    def get_wallet_positions(cls, db: Session, wallet: str) -> list:
        """Get all positions for a wallet"""
        try:
            return db.query(cls).filter(cls.wallet == wallet).all()
        except Exception:
            return []

    @classmethod
    def get_active_positions(cls, db: Session, wallet: str) -> list:
        """Get all non-zero positions for a wallet"""
        try:
            return db.query(cls).filter(
                cls.wallet == wallet,
                cls.amount > 0
            ).all()
        except Exception:
            return []

    @classmethod
    def remove_position(cls, db: Session, wallet: str, token: str) -> bool:
        """
        Remove position from database

        Returns:
            True if removed, False if not found
        """
        try:
            position = db.query(cls).filter_by(wallet=wallet, token=token).first()
            if position:
                db.delete(position)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            raise