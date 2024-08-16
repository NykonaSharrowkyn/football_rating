from dataclasses import dataclass, field
from typing import List, Dict


DEFAULT_ELO = 1000.


@dataclass
class Player:
    name: str
    elo: float = DEFAULT_ELO

    def update_elo(self):
        pass


@dataclass
class Team:
    name: str
    players: List[Player]
    elo: float = 0.

    def __post_init__(self):
        # calculate elo here
        pass

    def short_name(self):
        return self.name[0].lower()

    def update_elo(self, other_team: 'Team'):
        pass

    def set_elo(self, ratings: Dict[str, float]):
        pass


@dataclass
class Match:
    team1: Team
    team2: Team
    result: float | None = None

    def update_elo(self):
        pass


@dataclass
class MatchDay:
    matches: List[Match] = field(default_factory=List[Match])
    teams: List[Team] = field(default_factory=List[Team])

    def short_teams_names(self):
        return {team.short_name(): team for team in self.teams}

    def update_elo(self):
        for match in self.matches:
            match.update_elo()