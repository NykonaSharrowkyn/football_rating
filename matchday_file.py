import re

from matchday import Match, MatchDay, Player, Team

from dataclasses import dataclass
from typing import List


def read_match(match_line: str, teams: List[Team]) -> Match:
    team_dict = {team.short_name(): team for team in teams}
    m = re.match(r"\s*([А-Яа-я]+)\s*(\d+)\s*:\s*(\d+)\s*([А-Яа-я]+)\s*", match_line)
    team1 = team_dict[m.group(1).lower()]
    goals1 = int(m.group(2))
    goals2 = int(m.group(3))
    team2 = team_dict[m.group(4).lower()]
    return Match(team1, team2, goals1, goals2)


def read_team(team_line: str) -> Team:
    colon = team_line.index(':')
    team_name = team_line[:colon].rstrip().lstrip()
    names = [name.lstrip().rstrip() for name in team_line[colon + 1:].split(',')]
    players = [Player(name) for name in names]
    return Team(team_name, players)


@dataclass
class MatchDayFile:
    filepath: str
    results: MatchDay = MatchDay([], [])

    def __post_init__(self):
        self.load(self.filepath)

    def load(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = [line.rstrip() for line in file]
        index = lines.index('')
        team_lines = lines[:index]
        result_lines = lines[index + 1:]
        self.results.teams = [read_team(line) for line in team_lines]
        self.results.matches = [
            read_match(line, self.results.teams) for line in result_lines
        ]
