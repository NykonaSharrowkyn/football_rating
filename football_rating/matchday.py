import datetime
import math
import numpy as np
from collections import Counter
from dataclasses import dataclass
from typing import List

DEFAULT_ELO = 1250


@dataclass
class Player:
    name: str
    elo: int = DEFAULT_ELO
    matches: int = 0


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


def elo_update(player: Player, actual: float, expected: float, point_factor: float= 1.):
    player.elo = round(player.elo + (50/(1 + player.matches/300)) * point_factor * (actual - expected))


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
        if self.result == 0.5:
            p = 1.
        else:
            p = 1 + (math.log10(abs(self.goals1 - self.goals2))**3)
        for player in self.team1.players:
            elo_update(player, self.result, ep1, p)
        for player in self.team2.players:
            elo_update(player, 1 - self.result, ep2, p)


class MatchDay:
    def __init__(
            self,
            matches: List[Match] = None,
            teams: List[Team] = None,
            date: datetime.date = datetime.date.today()
    ):
        self.matches = matches or []
        self.teams = teams or []
        self.date = date

    def matches_per_player(self) -> dict:
        players = [player.name for match in self.matches for player in match.team1.players + match.team2.players]
        return dict(Counter(players))

    def short_teams_names(self):
        return {team.short_name(): team for team in self.teams}

    def update_players(self):
        self.update_elo()
        self.update_matches()

    def update_elo(self):
        for match in self.matches:
            match.update_elo()

    def update_matches(self):
        for match in self.matches:
            for player in match.team1.players + match.team2.players:
                player.matches += 1
    
    def get_scores(self) -> dict:
        scores = {team.name: np.zeros((3,), dtype=int) for team in self.teams}
        for match in self.matches:            
            update1 = np.zeros((3,), dtype=int)
            update2 = np.zeros((3,), dtype=int)
            if match.result == 0.:
                update2[0] += 3
            elif match.result == 1.:
                update1[0] += 3
            else:
                update1[0] += 1
                update2[0] += 1
            update1 += [0, match.goals1, -match.goals2]
            update2 += [0, match.goals2, -match.goals1]
            scores[match.team1.name] += update1
            scores[match.team2.name] += update2
        return scores
            
            