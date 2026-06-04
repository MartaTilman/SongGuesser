import hashlib
import json
import time


class Block:

    def __init__(
        self,
        index,
        data,
        previous_hash,
        timestamp=None,
        block_hash=None,
        nonce=None,
        difficulty=0,
        schema_version=2
    ):
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce if nonce is not None else 0
        self.difficulty = difficulty
        self.schema_version = schema_version
        self.hash = block_hash or self.calculate_hash()

    def calculate_hash(self):
        block_payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }

        if self.schema_version >= 2:
            block_payload.update({
                "nonce": self.nonce,
                "difficulty": self.difficulty,
                "schema_version": self.schema_version
            })

        block_string = json.dumps(block_payload, sort_keys=True)

        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine(self):
        prefix = "0" * self.difficulty

        while not self.hash.startswith(prefix):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "schema_version": self.schema_version,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, block_data):
        schema_version = block_data.get("schema_version")
        if schema_version is None:
            schema_version = 2 if "nonce" in block_data else 1

        return cls(
            index=block_data["index"],
            data=block_data["data"],
            previous_hash=block_data["previous_hash"],
            timestamp=block_data["timestamp"],
            block_hash=block_data["hash"],
            nonce=block_data.get("nonce"),
            difficulty=block_data.get("difficulty", 0),
            schema_version=schema_version
        )
