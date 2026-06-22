"""
Ethereum anchor for SongGuesserAnchor.sol.

Submits the final game proof to the on-chain contract so the result is
permanently verifiable. Requires three environment variables:

    ETH_RPC_URL          - HTTP(S) RPC endpoint (Infura, Alchemy, local node)
    CONTRACT_ADDRESS     - Deployed SongGuesserAnchor contract address
    SUBMITTER_PRIVATE_KEY - Hex private key of the wallet paying gas

If any variable is missing the module logs a warning and skips submission
gracefully -- the game still works, proofs just aren't anchored.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# ABI for SongGuesserAnchor.sol (only the functions we call)
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string",  "name": "lobbyId",               "type": "string"},
            {"internalType": "bytes32", "name": "chainHash",             "type": "bytes32"},
            {"internalType": "bytes32", "name": "merkleRoot",            "type": "bytes32"},
            {"internalType": "bytes32", "name": "leaderboardHash",       "type": "bytes32"},
            {"internalType": "uint256", "name": "blockCountBeforeFinal", "type": "uint256"},
        ],
        "name": "submitGameProof",
        "outputs": [{"internalType": "bytes32", "name": "proofId", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "bytes32", "name": "proofId",               "type": "bytes32"},
            {"indexed": False, "internalType": "string",  "name": "lobbyId",               "type": "string"},
            {"indexed": False, "internalType": "bytes32", "name": "chainHash",             "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "merkleRoot",            "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "leaderboardHash",       "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "blockCountBeforeFinal", "type": "uint256"},
            {"indexed": True,  "internalType": "address", "name": "submitter",             "type": "address"},
        ],
        "name": "GameProofSubmitted",
        "type": "event",
    },
]


def _load_config():
    rpc_url     = os.getenv("ETH_RPC_URL")
    contract_addr = os.getenv("CONTRACT_ADDRESS")
    private_key = os.getenv("SUBMITTER_PRIVATE_KEY")

    if not all([rpc_url, contract_addr, private_key]):
        missing = [k for k, v in {
            "ETH_RPC_URL": rpc_url,
            "CONTRACT_ADDRESS": contract_addr,
            "SUBMITTER_PRIVATE_KEY": private_key,
        }.items() if not v]
        logger.warning(
            "Ethereum anchor disabled — missing env vars: %s. "
            "Set ETH_RPC_URL, CONTRACT_ADDRESS, and SUBMITTER_PRIVATE_KEY to enable.",
            ", ".join(missing)
        )
        return None

    return rpc_url, contract_addr, private_key


def _hex_to_bytes32(hex_str: str) -> bytes:
    """Convert a 64-char hex string to a 32-byte value for Solidity bytes32."""
    return bytes.fromhex(hex_str.lstrip("0x").zfill(64))


async def submit_anchor(final_proof: dict) -> dict:
    """
    Submit *final_proof* to the on-chain SongGuesserAnchor contract.

    Returns the proof dict with anchor_status and (on success) tx_hash / proof_id.
    Never raises — failures are logged and returned as anchor_status = "error".
    """
    config = _load_config()
    if config is None:
        return {**final_proof, "anchor_status": "not_configured"}

    rpc_url, contract_addr, private_key = config

    try:
        from web3 import Web3
        from web3.middleware import ExtraDataToPOAMiddleware

        w3 = Web3(Web3.HTTPProvider(rpc_url))

        # POA chains (e.g. Polygon, BSC, testnets) need this middleware
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not w3.is_connected():
            logger.error("Ethereum anchor: cannot connect to RPC %s", rpc_url)
            return {**final_proof, "anchor_status": "error", "anchor_error": "RPC unreachable"}

        account = w3.eth.account.from_key(private_key)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_addr),
            abi=CONTRACT_ABI
        )

        chain_hash       = _hex_to_bytes32(final_proof["chain_hash"])
        merkle_root      = _hex_to_bytes32(final_proof["merkle_root"])
        leaderboard_hash = _hex_to_bytes32(final_proof["leaderboard_hash"])
        block_count      = int(final_proof["block_count_before_final"])
        lobby_id         = str(final_proof["lobby_id"])

        tx = contract.functions.submitGameProof(
            lobby_id,
            chain_hash,
            merkle_root,
            leaderboard_hash,
            block_count,
        ).build_transaction({
            "from":  account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas":   200_000,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

        # wait_for_transaction_receipt is synchronous and can block for up to
        # `timeout` seconds. Run it in a thread so the asyncio event loop
        # stays responsive while we wait for on-chain confirmation.
        receipt = await asyncio.to_thread(
            w3.eth.wait_for_transaction_receipt, tx_hash, 120
        )

        if receipt.status != 1:
            logger.error("Anchor tx reverted: %s", tx_hash.hex())
            return {
                **final_proof,
                "anchor_status": "reverted",
                "tx_hash": tx_hash.hex(),
            }

        # Pull proof_id from the emitted event
        proof_id = None
        logs = contract.events.GameProofSubmitted().process_receipt(receipt)
        if logs:
            proof_id = "0x" + logs[0]["args"]["proofId"].hex()

        logger.info(
            "Anchor submitted for lobby %s — tx=%s proof_id=%s",
            lobby_id, tx_hash.hex(), proof_id
        )

        return {
            **final_proof,
            "anchor_status": "submitted",
            "tx_hash":       tx_hash.hex(),
            "proof_id":      proof_id,
            "contract":      contract_addr,
        }

    except ImportError:
        logger.error(
            "web3 package not installed. Run: pip install web3"
        )
        return {**final_proof, "anchor_status": "error", "anchor_error": "web3 not installed"}

    except Exception as exc:
        logger.exception("Anchor submission failed: %s", exc)
        return {**final_proof, "anchor_status": "error", "anchor_error": str(exc)}
