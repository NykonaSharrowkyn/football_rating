from dataclasses import dataclass, field
from typing import List, Dict


DEFAULT_ELO = 1000.


@dataclass
class Player:
    name: str
    elo: float = DEFAULT_ELO
    matches: int = 0

    def update_elo(self):
        pass


@dataclass
class Team:
    name: str
    players: List[Player]

    def __post_init__(self):
        # calculate elo here
        pass

    def expected_score(self, other_team: 'Team'):
        impact = 800
        elos = [player.elo for player in other_team.players]
        ep_individual = [
            [1/(1 + pow(10, (elo - player.elo) / impact)) for player in self.players]
            for elo in elos
        ]
        ep_player_team = [sum(ep)/len(ep) for ep in ep_individual]
        ep_team = sum(ep_player_team)/len(ep_player_team)
        return ep_team

    def short_name(self):
        return self.name[0].lower()


def elo_update(player: Player, actual: float, expected: float):
    player.elo = player.elo + 32 * (actual - expected)


@dataclass
class Match:
    team1: Team
    team2: Team
    goals1: int | None = None
    goals2: int | None = None
    result: float | None = None
    updated: bool = False

    def __post_init__(self):
        if self.goals1 is not None and self.goals2 is not None:
            if self.goals1 < self.goals2:
                self.result = 0.
            elif self.goals1 == self.goals2:
                self.result = .5
            else:
                self.result = 1.

    def update_elo(self):
        if self.updated:
            return
        ep1 = self.team1.expected_score(self.team2)
        ep2 = self.team2.expected_score(self.team1)
        for player in self.team1.players:
            elo_update(player, self.result, ep1)
        for player in self.team2.players:
            elo_update(player, 1 - self.result, ep2)


class MatchDay:
    def __init__(self, matches: List[Match] = None, teams: List[Team] = None):
        self.matches = matches or []
        self.teams = teams or []

    def short_teams_names(self):
        return {team.short_name(): team for team in self.teams}

    def update(self):
        self.update_elo()
        self.update_matches()

    def update_elo(self):
        for match in self.matches:
            match.update_elo()

    def update_matches(self):
        pass