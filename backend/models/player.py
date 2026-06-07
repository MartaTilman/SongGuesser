class Player:

    def __init__(self, name, websocket, avatar, public_key=None, join_signature=None):
        self.name = name
        self.websocket = websocket
        self.avatar = avatar
        self.public_key = public_key
        self.join_signature = join_signature
        self.connected = True

        self.score = 0
        self.answers = {}

    def to_dict(self):
        return {
            "name": self.name,
            "avatar": self.avatar,
            "score": self.score,
            "connected": self.connected,
            "has_wallet": bool(self.public_key)
        }
