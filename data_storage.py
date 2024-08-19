from dataclasses import dataclass
from typing import Dict, List, Tuple


# TODO: base class later
@dataclass
class Storage:
    filepath: str
    data = Dict[str, Tuple[int, int]]

    def __post_init__(self):
        self.data = {}
        try:
            with open(self.filepath, 'r', encoding='utf-8') as file:
                for line in file:
                    parts = line.rstrip().split(':')
                    parts = [part.rstrip().lstrip() for part in parts]
                    name = parts[0]
                    elo = int(parts[1])
                    matches = int(parts[2])
                    self.data[name] = (elo, matches)
        except FileNotFoundError:
            pass

    def get_players_data(self, players: List[str]) -> Dict[str, Tuple[int, int]]:
        return {player: self.data[player] for player in players if player in self.data}

    def set_players_data(self, players: Dict[str, Tuple[int, int]]):
        for player in players:
            self.data[player] = players[player]

    def save(self):
        with open(self.filepath, 'w', encoding='utf-8') as file:
            for name, (matches, elo) in self.data.items():
                file.write(f'{name}:{matches}:{elo}\n')
