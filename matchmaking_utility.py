import data_storage
import text_parser

import argparse
import pandas as pd

from matchday import DEFAULT_ELO
from matchmaking import MatchMaking

from typing import Dict, List


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


def main(filepath: str):
    players = text_parser.PlayersFile(filepath).players
    all_data = data_storage.GSheetStorage(
        'eternal-delight-433008-q1-1bb6245a61a9.json',
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
    for key, _ in teams:
        team = teams.get_group(key)
        players = team['player'].tolist()
        score = team['skill'].mean()
        team_str = key[0]
        players_str = ', '.join(players)
        print(f'Команда {team_str}: {players_str} - средний {score}')


if __name__ == '__main__':
    args = parse_argument()
    main(**vars(args))