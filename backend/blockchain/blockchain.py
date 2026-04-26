import json
from pathlib import Path

from blockchain.block import Block


DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent / "blockchain_storage"


class Blockchain:

    def __init__(self, lobby_id, storage_dir=None, autoload=True):
        self.lobby_id = str(lobby_id).upper()
        self.storage_dir = Path(storage_dir or DEFAULT_STORAGE_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / f"{self.lobby_id}.json"

        if autoload and self.file_path.exists():
            self.chain = self._load_chain_from_disk()
        else:
            self.chain = [self.create_genesis_block()]
            self.save()

    def create_genesis_block(self):
        return Block(
            0,
            {
                "type": "genesis",
                "lobby_id": self.lobby_id
            },
            "0"
        )

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        previous_block = self.get_latest_block()

        new_block = Block(
            index=len(self.chain),
            data=data,
            previous_hash=previous_block.hash
        )

        self.chain.append(new_block)
        self.save()

        return new_block

    def add_lobby_created(self):
        self.add_block({
            "type": "lobby_created",
            "lobby_id": self.lobby_id
        })

    def add_player_join(self, player_name):
        self.add_block({
            "type": "player_join",
            "player": player_name
        })

    def add_auth_event(self, player_name, action):
        self.add_block({
            "type": "auth_event",
            "player": player_name,
            "action": action
        })

    def add_host_changed(self, previous_host, new_host):
        self.add_block({
            "type": "host_changed",
            "previous_host": previous_host,
            "new_host": new_host
        })

    def add_round_started(
        self,
        round_number,
        song_number,
        song_title,
        artist,
        year,
        decade
    ):
        self.add_block({
            "type": "round_started",
            "round": round_number,
            "song_number": song_number,
            "song_title": song_title,
            "artist": artist,
            "year": year,
            "decade": decade
        })

    def add_song_result(
        self,
        song_title,
        artist,
        year,
        decade,
        round_number,
        song_number,
        awarded_points
    ):
        self.add_block({
            "type": "song_result",
            "song_title": song_title,
            "artist": artist,
            "year": year,
            "decade": decade,
            "round": round_number,
            "song_number": song_number,
            "awarded_points": awarded_points
        })

    def add_game_finished(self, leaderboard):
        self.add_block({
            "type": "game_finished",
            "leaderboard": leaderboard
        })

    def save(self):
        payload = {
            "lobby_id": self.lobby_id,
            "block_count": len(self.chain),
            "valid": self.is_valid(),
            "chain": self.to_list()
        }

        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def _load_chain_from_disk(self):
        with self.file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        chain_data = payload.get("chain", [])
        if not chain_data:
            return [self.create_genesis_block()]

        return [Block.from_dict(block_data) for block_data in chain_data]

    def is_valid(self):
        if not self.chain:
            return False

        genesis = self.chain[0]
        if genesis.index != 0:
            return False

        if genesis.previous_hash != "0":
            return False

        if genesis.data.get("type") != "genesis":
            return False

        if genesis.data.get("lobby_id") != self.lobby_id:
            return False

        if genesis.hash != genesis.calculate_hash():
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

        return True

    def to_list(self):
        return [block.to_dict() for block in self.chain]


def list_saved_blockchains(storage_dir=None):
    target_dir = Path(storage_dir or DEFAULT_STORAGE_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    saved = []

    for file_path in sorted(target_dir.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)

            chain = payload.get("chain", [])
            first_timestamp = chain[0]["timestamp"] if chain else None
            last_timestamp = chain[-1]["timestamp"] if chain else None

            saved.append({
                "lobby_id": payload.get("lobby_id") or file_path.stem.upper(),
                "block_count": payload.get("block_count", len(chain)),
                "valid": payload.get("valid"),
                "created_at": first_timestamp,
                "updated_at": last_timestamp
            })
        except Exception:
            saved.append({
                "lobby_id": file_path.stem.upper(),
                "block_count": 0,
                "valid": False,
                "created_at": None,
                "updated_at": None
            })

    return saved


def load_saved_blockchain(lobby_id, storage_dir=None):
    normalized_lobby_id = str(lobby_id).upper()
    file_path = Path(storage_dir or DEFAULT_STORAGE_DIR) / f"{normalized_lobby_id}.json"

    if not file_path.exists():
        return None

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)
