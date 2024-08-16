from dataclasses import dataclass
from typing import Dict, List


# TODO: abstract class later
@dataclass
class Storage:
    filepath: str
    ratings = Dict[str, float]

    def __post_init__(self):
        pass

    def get_elo(self, player: str) -> float:
        pass

    def get_elos(self, players: List[str]) -> Dict[str, float]:
        pass

    def update_elo(self, player: str, new_elo: float):
        pass

    def update_elos(self, new_elos: Dict[str, float]):
        pass
