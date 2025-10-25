import requests
from app.config.config import config

def update_wallet_key_value_list(add_items: list[str] = [], remove_items: list[str] = []):
    url = "https://api.quicknode.com/kv/rest/v1/lists/wallets"

    payload = {
        "addItems": add_items,
        "removeItems": remove_items
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": config.QUICKNODE_API_KEY
    }

    response = requests.patch(url, headers=headers, json=payload)

    print(response.text)

def create_wallet_key_value_list():
    url = "https://api.quicknode.com/kv/rest/v1/lists"

    payload = {
        "key": "wallets",
        "items": []
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": config.QUICKNODE_API_KEY
    }

    response = requests.post(url, headers=headers, json=payload)

    print(response.text)

def get_wallet_key_value_list():
    url = "https://api.quicknode.com/kv/rest/v1/lists/wallets"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": config.QUICKNODE_API_KEY
    }

    response = requests.get(url, headers=headers)

    print(response.text)

def delete_wallet_key_value_list():
    url = "https://api.quicknode.com/kv/rest/v1/lists/wallets"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": config.QUICKNODE_API_KEY
    }

    response = requests.delete(url, headers=headers)

    print(response.text)

def add_wallet_key_value_list(add_items: list[str]):
    update_wallet_key_value_list(add_items=add_items)

def remove_wallet_key_value_list(remove_items: list[str]):
    update_wallet_key_value_list(remove_items=remove_items)
