import hashlib
import json
import time


class Block:

    def __init__(self, index, data, previous_hash, timestamp=None, block_hash=None):
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.hash = block_hash or self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True)

        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, block_data):
        return cls(
            index=block_data["index"],
            data=block_data["data"],
            previous_hash=block_data["previous_hash"],
            timestamp=block_data["timestamp"],
            block_hash=block_data["hash"]
        )
