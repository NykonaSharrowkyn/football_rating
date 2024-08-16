from dataclasses import dataclass
from typing import Dict, List, Tuple


# TODO: abstract class later
@dataclass
class Storage:
    filepath: str
    ratings = Dict[str, float]

    def __post_init__(self):
        self.ratings = {}
        try:
            with open(self.filepath, 'r', encoding='utf-8') as file:
                for line in file:
                    parts = line.rstrip().split(':')
                    parts = [part.rstrip().lstrip() for part in parts]
                    name = parts[0]
                    elo = int(parts[1])
                    matches = int(parts[2])
                    self.ratings[name] = (elo, matches)
        except FileNotFoundError:
            pass

    def get_players_data(self, players: List[str]) -> Dict[str, float]:
        return {player: self.ratings[player] for player in players if player in self.ratings}

    def set_players_data(self, players: Dict[str, Tuple[int, float]]):
        pass

    def save(self):
        pass
