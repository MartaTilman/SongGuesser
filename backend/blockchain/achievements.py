"""
On-chain achievement badges for SongGuesserAchievements.sol.

After a game finishes, determine_achievements() looks at the game's own
local blockchain (the same proof-of-work chain already used for the audit
log / final proof) and works out which players earned which badges this
game. mint_achievements() then mints those badges as soulbound ERC-1155
tokens directly to each player's connected wallet address on Sepolia.

Mirrors the anchor.py pattern on purpose:
    - Missing env vars (ETH_RPC_URL / SUBMITTER_PRIVATE_KEY /
      ACHIEVEMENTS_CONTRACT_ADDRESS) => achievements are still recorded
      locally, minting is just skipped with a clear status.
    - A player with no connected wallet => same thing, skipped with
      status "no_wallet" (this is expected until MetaMask login lands on
      the frontend).
    - Minting failures never raise -- they're caught and reported per
      player so a bad transaction can't crash the game.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# Achievement token IDs -- must match the constants in
# contracts/SongGuesserAchievements.sol.
ACHIEVEMENT_IDS = {
    "WINNER": 1,
    "PERFECT_ROUND": 2,
    "STREAK": 3,
    "FASTEST_ANSWER": 4,
}

# How many fully-correct answers in a row (across the whole game, not just
# one round) counts as a "streak".
STREAK_THRESHOLD = 3

# ABI for SongGuesserAchievements.sol (only the function we call from here).
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "player", "type": "address"},
            {"internalType": "string", "name": "lobbyId", "type": "string"},
            {"internalType": "uint256", "name": "gameNumber", "type": "uint256"},
            {"internalType": "uint256[]", "name": "ids", "type": "uint256[]"},
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"},
        ],
        "name": "mintAchievements",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def determine_achievements(blockchain, leaderboard, game_number):
    """
    Pure function -- no side effects, no network calls. Reads the
    song_result blocks this Blockchain instance already recorded for
    `game_number` and figures out who earned what.

    Returns {player_name: [token_id, ...]} (only players who earned at
    least one achievement are included).
    """
    song_results = [
        block.data
        for block in blockchain.chain
        if block.data.get("type") == "song_result"
        and block.data.get("game_number") == game_number
    ]
    song_results.sort(key=lambda d: (d.get("round") or 0, d.get("song_number") or 0))

    achievements = {}

    def award(player_name, token_id):
        ids = achievements.setdefault(player_name, [])
        if token_id not in ids:
            ids.append(token_id)

    # --- WINNER: highest score on the final leaderboard (ties all win) ---
    if leaderboard:
        top_score = max(entry["score"] for entry in leaderboard)
        if top_score > 0:
            for entry in leaderboard:
                if entry["score"] == top_score:
                    award(entry["name"], ACHIEVEMENT_IDS["WINNER"])

    per_player_song_flags = {}   # name -> [fully_correct, ...] in play order
    rounds_all_correct = {}      # name -> {round_number: all_correct_so_far}
    best_song_score = {}         # name -> best single-song gained_points (only fully-correct songs count)

    for result in song_results:
        round_number = result.get("round")
        for entry in result.get("awarded_points", []):
            name = entry.get("name")
            if not name:
                continue

            fully_correct = bool(
                entry.get("title_correct")
                and entry.get("artist_correct")
                and entry.get("year_correct")
            )
            per_player_song_flags.setdefault(name, []).append(fully_correct)

            round_flags = rounds_all_correct.setdefault(name, {})
            round_flags[round_number] = round_flags.get(round_number, True) and fully_correct

            if fully_correct:
                gained = entry.get("gained_points", 0)
                if gained > best_song_score.get(name, -1):
                    best_song_score[name] = gained

    # --- PERFECT_ROUND: every song in at least one round fully correct ---
    for name, per_round in rounds_all_correct.items():
        if any(per_round.values()):
            award(name, ACHIEVEMENT_IDS["PERFECT_ROUND"])

    # --- STREAK: STREAK_THRESHOLD+ fully-correct answers in a row ---
    for name, flags in per_player_song_flags.items():
        streak = 0
        for flag in flags:
            streak = streak + 1 if flag else 0
            if streak >= STREAK_THRESHOLD:
                award(name, ACHIEVEMENT_IDS["STREAK"])
                break

    # --- FASTEST_ANSWER: single highest-scoring fully-correct answer in the game ---
    if best_song_score:
        fastest_name = max(best_song_score, key=best_song_score.get)
        award(fastest_name, ACHIEVEMENT_IDS["FASTEST_ANSWER"])

    return achievements


def _load_config():
    rpc_url = os.getenv("ETH_RPC_URL")
    contract_addr = os.getenv("ACHIEVEMENTS_CONTRACT_ADDRESS")
    private_key = os.getenv("SUBMITTER_PRIVATE_KEY")

    if not all([rpc_url, contract_addr, private_key]):
        missing = [k for k, v in {
            "ETH_RPC_URL": rpc_url,
            "ACHIEVEMENTS_CONTRACT_ADDRESS": contract_addr,
            "SUBMITTER_PRIVATE_KEY": private_key,
        }.items() if not v]
        logger.warning(
            "Achievement minting disabled — missing env vars: %s.",
            ", ".join(missing)
        )
        return None

    return rpc_url, contract_addr, private_key


async def _mint_one(config, wallet_address, lobby_id, game_number, ids):
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware

    rpc_url, contract_addr, private_key = config

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        return {"status": "error", "ids": ids, "error": "RPC unreachable"}

    account = w3.eth.account.from_key(private_key)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_addr),
        abi=CONTRACT_ABI
    )

    tx = contract.functions.mintAchievements(
        Web3.to_checksum_address(wallet_address),
        str(lobby_id),
        int(game_number),
        list(ids),
        [1] * len(ids),
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 250_000,
    })

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    receipt = await asyncio.to_thread(
        w3.eth.wait_for_transaction_receipt, tx_hash, 120
    )

    if receipt.status != 1:
        return {"status": "reverted", "ids": ids, "tx_hash": tx_hash.hex()}

    return {"status": "minted", "ids": ids, "tx_hash": tx_hash.hex()}


async def mint_achievements(lobby_id, game_number, achievements_by_player, wallet_addresses):
    """
    achievements_by_player: {player_name: [token_id, ...]} -- from
        determine_achievements().
    wallet_addresses: {player_name: "0x..."} -- only players who have
        connected a wallet appear here. Players without one are skipped
        with status "no_wallet" (the achievement is still on the local
        blockchain log either way).

    Returns {player_name: {"status": ..., "ids": [...], ...}} -- never
    raises, so a minting problem can never break the game itself.
    """
    config = _load_config()
    results = {}

    for player_name, ids in achievements_by_player.items():
        if not ids:
            continue

        wallet_address = wallet_addresses.get(player_name)

        if not wallet_address:
            results[player_name] = {"status": "no_wallet", "ids": ids}
            continue

        if config is None:
            results[player_name] = {"status": "not_configured", "ids": ids}
            continue

        try:
            results[player_name] = await _mint_one(
                config, wallet_address, lobby_id, game_number, ids
            )
        except Exception as exc:
            logger.exception("Achievement mint failed for %s: %s", player_name, exc)
            results[player_name] = {"status": "error", "ids": ids, "error": str(exc)}

    return results
