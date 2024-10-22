import data_storage
import text_parser

import argparse
import numpy as np
import pandas as pd
import os
import sys

from matchday import DEFAULT_ELO, Team, Player
from matchmaking import MatchMaking

from typing import Dict, List, Tuple


def parse_argument() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='matchmaking_utility',
        description='File based football matchmaker'
    )
    parser.add_argument('filepath', help='text file with player names')
    return parser.parse_args()


def get_df(players_data: Dict[str, List[int]]) -> pd.DataFrame:
    df = pd.DataFrame.from_dict(players_data, orient='index').reset_index()
    df.columns = ['player', 'skill', 'matches']
    return df


def get_teams(teams: List[str]) -> List[str]:
    players_dict = {
        'Макс И': 'Красные',
        'Вова К': 'Синие',
        'Коля М': 'Желтые'
    }

    team_dict = {}
    for i, team in enumerate(teams):
        for key_name in players_dict:
            if key_name in team:
                team_dict[i] = players_dict[key_name]
                break

    unused_idx = set(range(len(teams))) - set(team_dict.keys())
    unused_names = set(players_dict.values()) - set(team_dict.values())
    if len(unused_idx) > len(unused_names):      # something gone wrong
        return [f'Команда {i}: {team}' for i, team in enumerate(teams)]

    team_dict.update({i: name for i, name in zip(unused_idx, unused_names)})
    return [f'{team_dict[i]}: {team}' for i, team in enumerate(teams)]

def test_expected(players_list: list, players_data: dict):
    teams = []
    for i, players in enumerate(players_list):
        teams.append(
            Team(
                f'team {i}',
                [Player(p, players_data[p][0]) for p in players]
            )
        )
    expected = np.array([[team1.expected_score(team2) for team2 in teams] for team1 in teams])
    print(expected)


def main(filepath: str):
    os.chdir(sys.path[0])
    players = text_parser.PlayersFile(filepath).players
    all_data = data_storage.GSheetStorage(
        service_file='eternal-delight-433008-q1-1bb6245a61a9.json',
        file_name='football-rating-test'
    ).data
    players_data = all_data.get_players_match_data_dict(players)
    stored_players = list(players_data.keys())
    text_parser.check_new_players(players, stored_players)
    new_players = set(players) - set(stored_players)
    new_players_data = {name: [0, DEFAULT_ELO] for name in new_players}
    players_data |= new_players_data
    df = get_df(players_data)
    matchmaker = MatchMaking(df, 5)
    df = matchmaker.optimize()
    teams = df.groupby(['team'])[['player', 'skill']]
    team_list = []
    players_list = []
    for key, _ in teams:
        team = teams.get_group(key)
        players = team['player'].tolist()
        players_list.append(players)
        score = team['skill'].mean()
        # team_str = key[0]
        players_str = ', '.join(players)
        team_list.append(f'{players_str} - средний {score}')

    for team in get_teams(team_list):
        print(team)

    test_expected(players_list, players_data)


if __name__ == '__main__':
    args = parse_argument()
    main(**vars(args))