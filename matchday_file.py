import matchday

from dataclasses import dataclass, field


@dataclass
class MatchDayFile:
    filepath: str
    results: matchday.MatchDay = matchday.MatchDay()

    def __post_init__(self):
        self.load(self.filepath)

    def load(self, filepath):
        with open(filepath, 'r') as file:
            lines = [line.rstrip() for line in file]
        index = lines.index('')
        team_lines = lines[:index]
        result_lines = lines[index + 1:]
        self.results.teams = [self.read_team(line) for line in team_lines]
        self.results.matches = [self.read_match(line) for line in result_lines]

    def read_team(self, team_line: str) -> matchday.Team:
        pass

    def read_match(self, match_line: str):
        pass