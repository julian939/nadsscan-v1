from app.db.models.position import Position


def update_position_amount(wallet: str, token: str, amount: float, entry_price, db) -> float:
    if Position.exists(db, wallet, token):
        curr_position = Position.get_position(db, wallet, token)
        if curr_position.amount + amount >= 0:
            curr_position.amount += amount
            db.save(curr_position)
            db.refresh(curr_position)
            return curr_position.amount
        else:
            curr_position.amount = 0
            db.save(curr_position)
            db.refresh(curr_position)
            return curr_position.amount
    else:
        Position.add_position(db, wallet, token, amount, entry_price)
        return Position.get_position(db, wallet, token).amount
