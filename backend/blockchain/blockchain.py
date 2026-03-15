from blockchain.block import Block


class Blockchain:

    def __init__(self):

        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):

        return Block(0, {"type": "genesis"}, "0")

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

        return new_block

    # zapis kad igrač uđe u lobby
    def add_player_join(self, player_name):

        self.add_block({
            "type": "player_join",
            "player": player_name
        })

    # zapis za autentifikaciju / join akciju
    def add_auth_event(self, player_name, action):

        self.add_block({
            "type": "auth_event",
            "player": player_name,
            "action": action
        })

    # zapis za rezultat jedne pjesme s kahoot bodovanjem
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

    # zapis za kraj cijele igre
    def add_game_finished(self, leaderboard):

        self.add_block({
            "type": "game_finished",
            "leaderboard": leaderboard
        })

    def is_valid(self):

        for i in range(1, len(self.chain)):

            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False

            if current.previous_hash != previous.hash:
                return False

        return True

    def to_list(self):

        return [block.to_dict() for block in self.chain]