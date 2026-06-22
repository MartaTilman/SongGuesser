import json
import os
from pathlib import Path

from blockchain.block import Block
from blockchain.crypto_utils import canonical_json, generate_salt, sha256_hex


DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent / "blockchain_storage"
DEFAULT_DIFFICULTY = 3


def get_blockchain_difficulty():
    raw_difficulty = os.getenv("BLOCKCHAIN_DIFFICULTY")
    if raw_difficulty:
        try:
            return max(1, int(raw_difficulty))
        except ValueError:
            print("Invalid BLOCKCHAIN_DIFFICULTY value. Using default=%d" % DEFAULT_DIFFICULTY)
    return DEFAULT_DIFFICULTY


class Blockchain:

    def __init__(self, lobby_id, storage_dir=None, autoload=True):
        self.lobby_id = str(lobby_id).upper()
        self.storage_dir = Path(storage_dir or DEFAULT_STORAGE_DIR)
        self.difficulty = get_blockchain_difficulty()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / f"{self.lobby_id}.json"
        if autoload and self.file_path.exists():
            self.chain = self._load_chain_from_disk()
        else:
            self.chain = [self.create_genesis_block()]
            self.save()

    def create_genesis_block(self):
        genesis = Block(0, {"type": "genesis", "lobby_id": self.lobby_id}, "0", difficulty=self.difficulty)
        genesis.mine()
        return genesis

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        previous_block = self.get_latest_block()
        new_block = Block(index=len(self.chain), data=data, previous_hash=previous_block.hash, difficulty=self.difficulty)
        new_block.mine()
        self.chain.append(new_block)
        self.save()
        return new_block

    def add_lobby_created(self):
        self.add_block({"type": "lobby_created", "lobby_id": self.lobby_id})

    def add_player_join(self, player_name):
        self.add_block({"type": "player_join", "player": player_name})

    def add_player_identity(self, player_name, public_key_jwk, join_signature_valid):
        self.add_block({"type": "player_identity", "player": player_name, "public_key": public_key_jwk, "join_signature_valid": bool(join_signature_valid)})

    def add_auth_event(self, player_name, action):
        self.add_block({"type": "auth_event", "player": player_name, "action": action})

    def add_signed_action(self, player_name, action, payload_hash, signature_valid):
        self.add_block({"type": "signed_action", "player": player_name, "action": action, "payload_hash": payload_hash, "signature_valid": bool(signature_valid)})

    def add_game_started(self, game_number):
        self.add_block({"type": "game_started", "game_number": game_number})

    def add_host_changed(self, previous_host, new_host):
        self.add_block({"type": "host_changed", "previous_host": previous_host, "new_host": new_host})

    def add_round_started(self, game_number, round_number, song_number, decade, song_commitment):
        self.add_block({"type": "round_started", "game_number": game_number, "round": round_number, "song_number": song_number, "decade": decade, "song_commitment": song_commitment})

    def add_song_result(self, game_number, song_title, artist, year, decade, round_number, song_number, awarded_points, youtube_id=None, song_commitment=None, song_salt=None):
        data = {"type": "song_result", "game_number": game_number, "song_title": song_title, "artist": artist, "youtube_id": youtube_id, "year": year, "decade": decade, "round": round_number, "song_number": song_number, "awarded_points": awarded_points}
        if song_commitment:
            data["song_commitment"] = song_commitment
        if song_salt:
            data["song_reveal"] = {"salt": song_salt}
        self.add_block(data)

    def add_game_finished(self, game_number, leaderboard):
        final_proof = self.build_final_proof(game_number, leaderboard)
        self.add_block({"type": "game_finished", "game_number": game_number, "leaderboard": leaderboard, "final_proof": final_proof})
        return final_proof

    def save(self):
        payload = {"lobby_id": self.lobby_id, "block_count": len(self.chain), "valid": self.is_valid(), "consensus": "proof_of_work", "difficulty": self.difficulty, "chain": self.to_list()}
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _load_chain_from_disk(self):
        with self.file_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        chain_data = payload.get("chain", [])
        if not chain_data:
            return [self.create_genesis_block()]
        return [Block.from_dict(b) for b in chain_data]

    def is_valid(self):
        if not self.chain:
            return False
        genesis = self.chain[0]
        if genesis.index != 0 or genesis.previous_hash != "0":
            return False
        if genesis.data.get("type") != "genesis" or genesis.data.get("lobby_id") != self.lobby_id:
            return False
        if genesis.hash != genesis.calculate_hash():
            return False
        if genesis.schema_version >= 2:
            if genesis.difficulty < 1 or not genesis.hash.startswith("0" * genesis.difficulty):
                return False
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.index != i:
                return False
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
            if current.schema_version >= 2:
                if current.difficulty < 1 or not current.hash.startswith("0" * current.difficulty):
                    return False
        return self.has_valid_song_reveals()

    def has_valid_song_reveals(self):
        # Legacy (schema v1) chains were recorded before the reveal feature existed.
        # Only enforce strict commitment->reveal pairing on schema v2+ chains.
        is_legacy = self.chain[0].schema_version < 2 if self.chain else True

        commitments = {}
        for block in self.chain:
            data = block.data
            if data.get("type") == "round_started" and data.get("song_commitment"):
                key = (data.get("game_number"), data.get("round"), data.get("song_number"))
                commitments[key] = data.get("song_commitment")

        revealed = set()
        for block in self.chain:
            data = block.data
            if data.get("type") != "song_result":
                continue
            key = (data.get("game_number"), data.get("round"), data.get("song_number"))
            reveal = data.get("song_reveal")
            # On v2+ chains every commitment must have a reveal
            if not is_legacy and key in commitments and not reveal:
                return False
            if not reveal:
                continue
            expected_commitment = commitments.get(key)
            if not expected_commitment:
                return False
            calculated_commitment = create_song_commitment(
                self.lobby_id, data.get("game_number"), data.get("round"), data.get("song_number"),
                {"youtube_id": data.get("youtube_id"), "artist": data.get("artist"), "title": data.get("song_title"), "year": data.get("year")},
                reveal.get("salt")
            )
            if calculated_commitment != expected_commitment:
                return False
            revealed.add(key)

        # On v2+ chains every commitment must have been revealed
        if not is_legacy and set(commitments.keys()) - revealed:
            return False
        return True

    def to_list(self):
        return [block.to_dict() for block in self.chain]

    def build_final_proof(self, game_number, leaderboard):
        block_hashes = [block.hash for block in self.chain]
        return {
            "game_number": game_number,
            "lobby_id": self.lobby_id,
            "chain_hash": calculate_chain_hash(self.to_list()),
            "merkle_root": calculate_merkle_root(block_hashes),
            "block_count_before_final": len(self.chain),
            "leaderboard_hash": sha256_hex(canonical_json(leaderboard)),
            "anchor_status": "not_submitted"
        }


def create_song_commitment(lobby_id, game_number, round_number, song_number, song, salt=None):
    if salt is None:
        salt = generate_salt()
    payload = {"lobby_id": str(lobby_id).upper(), "game_number": game_number, "round": round_number, "song_number": song_number, "youtube_id": song.get("youtube_id"), "artist": song.get("artist"), "title": song.get("title"), "year": song.get("year"), "salt": salt}
    return sha256_hex(canonical_json(payload))


def calculate_chain_hash(chain):
    return sha256_hex(canonical_json(chain))


def calculate_merkle_root(hashes):
    if not hashes:
        return sha256_hex("")
    level = list(hashes)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(sha256_hex(left + right))
        level = next_level
    return level[0]


def list_saved_blockchains(storage_dir=None):
    target_dir = Path(storage_dir or DEFAULT_STORAGE_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for file_path in sorted(target_dir.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            chain = payload.get("chain", [])
            saved.append({
                "lobby_id": payload.get("lobby_id") or file_path.stem.upper(),
                "block_count": payload.get("block_count", len(chain)),
                "valid": Blockchain(file_path.stem, storage_dir=target_dir).is_valid(),
                "created_at": chain[0]["timestamp"] if chain else None,
                "updated_at": chain[-1]["timestamp"] if chain else None
            })
        except Exception:
            saved.append({"lobby_id": file_path.stem.upper(), "block_count": 0, "valid": False, "created_at": None, "updated_at": None})
    return saved


def load_saved_blockchain(lobby_id, storage_dir=None):
    normalized_lobby_id = str(lobby_id).upper()
    target_dir = Path(storage_dir or DEFAULT_STORAGE_DIR)
    file_path = target_dir / f"{normalized_lobby_id}.json"
    if not file_path.exists():
        return None
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["valid"] = Blockchain(normalized_lobby_id, storage_dir=target_dir).is_valid()
    return payload
