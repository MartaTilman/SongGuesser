class Player:

    def __init__(self, name, websocket, avatar):

        self.name = name
        self.websocket = websocket
        self.avatar = avatar

        self.score = 0
        self.answers = {}