from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.wallet import Wallet
from app.api.key_value_qn import add_wallet_key_value_list, remove_wallet_key_value_list


def resolve_wallet(wallets: list[str], db: Session = Depends(get_db())) -> str:
    """
    gets the wallet address which is also in the wallet table.
    """
    if wallets is None or len(wallets) == 0:
        return "Error"

    for wallet in wallets:
        result = db.query(Wallet).filter(Wallet.address == wallet.lower()).first()
        if result:
            return wallet.lower()

    return "Error"


def add_wallet(wallet: str,
               twitter_name: str,
               twitter_pfp: str,
               db: Session = Depends(get_db())):

    Wallet.add_wallet(db, wallet, twitter_name, twitter_pfp)
    add_wallet_key_value_list([wallet])


def remove_wallet(wallet: str, db: Session = Depends(get_db())):
    Wallet.remove_wallet(db, wallet)
    remove_wallet_key_value_list([wallet])
