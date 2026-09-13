"""
Deploy SongGuesserAchievements.sol to Sepolia (or any EVM chain).

Usage:
    cd backend
    python ../scripts/deploy_achievements.py

Requires these environment variables (in backend/.env, same place as the
ones for anchor.py):

    ETH_RPC_URL           - Sepolia RPC endpoint (e.g. from Alchemy/Infura)
    SUBMITTER_PRIVATE_KEY - hex private key of the wallet that will own the
                             contract and pay gas for every deployment and
                             every future mint. Needs a small amount of
                             Sepolia test ETH (get some from a Sepolia
                             faucet).

On success, prints the deployed contract address. Put that address in
backend/.env as:

    ACHIEVEMENTS_CONTRACT_ADDRESS=0x...
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "backend" / ".env")

ABI_PATH = ROOT / "contracts" / "build" / "SongGuesserAchievements.abi.json"
BYTECODE_PATH = ROOT / "contracts" / "build" / "SongGuesserAchievements.bytecode.txt"

# Metadata URI template for token IDs. {id} is replaced by wallets/explorers
# with the hex token id. Point this at wherever you decide to host the
# achievement metadata JSON (can be a simple static file on your backend,
# e.g. https://songguesser.onrender.com/achievements/metadata/{id}.json).
METADATA_URI = "https://songguesser.onrender.com/achievements/metadata/{id}.json"


def main():
    rpc_url = os.getenv("ETH_RPC_URL")
    private_key = os.getenv("SUBMITTER_PRIVATE_KEY")

    if not rpc_url or not private_key:
        print("Missing ETH_RPC_URL or SUBMITTER_PRIVATE_KEY in backend/.env")
        sys.exit(1)

    abi = json.loads(ABI_PATH.read_text())
    bytecode = BYTECODE_PATH.read_text().strip()

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"Cannot connect to RPC: {rpc_url}")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    print(f"Deploying from address: {account.address}")

    balance = w3.eth.get_balance(account.address)
    print(f"Balance: {w3.from_wei(balance, 'ether')} ETH")
    if balance == 0:
        print("Warning: this wallet has 0 balance on this network. "
              "Get Sepolia test ETH from a faucet before continuing.")
        sys.exit(1)

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx = Contract.constructor(METADATA_URI, account.address).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
    })

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Deployment tx sent: {tx_hash.hex()}")
    print("Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt.status != 1:
        print("Deployment transaction reverted.")
        sys.exit(1)

    print()
    print("Deployed successfully!")
    print(f"Contract address: {receipt.contractAddress}")
    print()
    print("Add this to backend/.env:")
    print(f"ACHIEVEMENTS_CONTRACT_ADDRESS={receipt.contractAddress}")


if __name__ == "__main__":
    main()
