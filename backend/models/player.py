class Player:

    def __init__(self, name, websocket, avatar, public_key=None, join_signature=None, wallet_address=None):
        self.name = name
        self.websocket = websocket
        self.avatar = avatar
        self.public_key = public_key
        self.join_signature = join_signature
        # Real Ethereum address (e.g. from MetaMask), used only to mint
        # on-chain achievement badges. Separate from `public_key`, which is
        # the browser-generated RSA key used for signing in-game actions.
        self.wallet_address = wallet_address
        self.connected = True

        self.score = 0
        self.answers = {}

    def to_dict(self):
        return {
            "name": self.name,
            "avatar": self.avatar,
            "score": self.score,
            "connected": self.connected,
            "has_wallet": bool(self.public_key),
            "has_eth_wallet": bool(self.wallet_address)
        }
