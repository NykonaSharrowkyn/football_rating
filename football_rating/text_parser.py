import datetime
import re
import sys

from matchday import Match, MatchDay, Player, Team

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def read_match(match_line: str, teams: List[Team]) -> Match | None:
    team_dict = {team.short_name(): team for team in teams}
    m = re.match(r"\s*([А-Яа-я]+)\s*(\d+)\s*:\s*(\d+)\s*([А-Яа-я]+)\s*", match_line)
    if m is None:
        return None
    team1 = team_dict[m.group(1).lower()]
    goals1 = int(m.group(2))
    goals2 = int(m.group(3))
    team2 = team_dict[m.group(4).lower()]
    return Match(team1, team2, goals1, goals2)


def read_team(team_line: str) -> Team:
    colon = team_line.index(':')
    dash = team_line.find('-')
    if dash != -1:
        team_line = team_line[:dash]
    team_name = team_line[:colon].rstrip().lstrip()
    names = [name.lstrip().rstrip() for name in team_line[colon + 1:].split(',')]
    players = [Player(name) for name in names]
    return Team(team_name, players)


def read_lines(filepath: str) -> List[str]:
    with open(filepath, 'r', encoding='utf-8') as file:
        lines = [line.rstrip() for line in file]
    return lines


def check_new_players(players: List[str], stored: List[str]):
    # return True
    diff = set(players) - set(stored)
    if diff:
        print('New players:')
        for name in diff:
            print(name)
        print('Add new players rating to storage')
        sys.exit(1)


@dataclass
class MatchDayFile:
    filepath: str
    results: MatchDay = MatchDay([], [])

    def __post_init__(self):
        self.read(self.filepath)

    def read(self, filepath):
        lines = read_lines(filepath)
        index = lines.index('')
        team_lines = lines[:index]
        result_lines = lines[index + 1:]
        self.results.teams = [read_team(line) for line in team_lines]
        self.results.matches = [
            read_match(line, self.results.teams) for line in result_lines
        ]
        self.results.matches = [match for match in self.results.matches if match is not None]
        basename = Path(self.filepath).stem
        underscore = basename.find('_')
        if underscore != -1:
            basename = basename[:underscore]
        self.results.date = datetime.datetime.strptime(basename, "%Y-%m-%d").date()


@dataclass
class PlayersFile:
    filepath: str
    players: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.read(self.filepath)

    def read(self, filepath: str):
        lines = read_lines(filepath)
        lines.remove('')
        if not re.match(r'\s*\d', lines[0]):
            lines.pop(0)
        split_words = [
            ' вместо',
            ' без абика',
            ' абик',
            ' б/а',
            ' ба',
            ' аб'
        ]
        reg = re.compile(r'\d+\s*\.\s*([а-яё]+(\s+[а-яё]+\.?)?)\s*')
        for i, line in enumerate(lines):
            for word in split_words:
                if line.lower().endswith(word):
                    line = line[:-len(word)]
                    break
                word += ' '
                try:
                    index = line.lower().index(word)
                    line = line[:index]
                    break
                except ValueError:
                    pass
            m = re.fullmatch(reg, line.lower())
            if not m:
                raise ValueError(f'Line {i} is not match to regular expression.')
            name = line[m.start(1):m.end(1)]
            if name.endswith('.'):
                name = name[:-1]
            self.players.append(name)
