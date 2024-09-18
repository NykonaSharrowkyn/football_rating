import datetime

import pandas as pd

import matchday
import players_data
import text_parser
import data_storage

import argparse
import sys

from typing import List


def parse_argument() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='football_rating_utility',
        description='File based football elo rating program'
    )
    parser.add_argument('filepath', help='text file with match results')
    return parser.parse_args()


def player_generator(teams: List[matchday.Team]):
    for team in teams:
        for player in team.players:
            yield player


def save_match_played(
        storage: data_storage.GSheetStorage,
        match_day: matchday.MatchDay
):
    matches = match_day.matches_per_player()
    new_df = storage.data.df.reset_index()[["Name"]].set_index('Name')
    column_name = match_day.date.strftime('%Y-%m-%d')
    new_df[column_name] = matches
    new_df.fillna(0, inplace=True)
    new_df = new_df.astype(int)
    sheet_name = f'{match_day.date.year}-matches'
    old_df = storage.read_sheet(sheet_name)
    if old_df.empty:
        df = new_df
    else:
        old_df.set_index('Name', inplace=True)
        df = pd.concat([old_df, new_df], axis=1)
        df.fillna(0, inplace=True)
        df = df.astype(int)
    storage.write_sheet(sheet_name, df.reset_index())


def main(filepath: str):
    # storage = data_storage.CsvTextFileStorage('ratings.csv')
    storage_name = 'football-rating-test-2'
    storage = data_storage.GSheetStorage(
        service_file='eternal-delight-433008-q1-1bb6245a61a9.json',
        file_name=storage_name
    )
    if storage_name == 'football-rating':
        key = input('Update main storage? [y]:')
        if key.lower() != 'y':
            print('Main storage guard abort')
            sys.exit(1)
    storage.update_time_stats()
    stored_data = storage.data
    results = text_parser.MatchDayFile(filepath).results
    teams = results.teams
    players = [player.name for player in player_generator(teams)]
    stored_players = stored_data.get_players_match_data_dict(players)
    text_parser.check_new_players(players, list(stored_players.keys()))
    for player in player_generator(teams):
        try:
            elo, matches = stored_players[player.name]
            player.elo = elo
            player.matches = matches
        except KeyError:
            pass
    for team in teams:
        players_elo = [player.elo for player in team.players]
        team_elo = sum(players_elo) / len(players_elo)
        print(f'Команда {team.name} - средний {team_elo}')
    results.update_players()
    new_player_data = {
        player.name: (player.elo, player.matches) for player in player_generator(teams)
    }
    stored_data.set_players_match_data(new_player_data)
    storage.write()
    save_match_played(storage, results)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    args = parse_argument()
    main(**vars(args))
