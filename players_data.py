from typing import Dict, List


class PlayersData:
    def __init__(self):
        self.data = {}

    def clear(self):
        self.data = {}

    def get_players_data(self, players: List[str]) -> Dict[str, List[int]]:
        return {player: self.data[player] for player in players if player in self.data}

    def set_players_data(self, players: Dict[str, List[int]]):
        for player in players:
            self.data[player] = players[player]

    def __iter__(self):
        return iter(self.data.items())
