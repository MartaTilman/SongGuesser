class Game:

    def __init__(self, lobby_id, host):

        self.lobby_id = lobby_id
        self.host = host

        self.players = []
        self.current_song = None
        self.answers = []