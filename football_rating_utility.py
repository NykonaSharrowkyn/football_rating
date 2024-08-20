import matchday
import text_parser
import data_storage

import argparse

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


def main(filepath: str):
    # storage = data_storage.CsvTextFileStorage('ratings.csv')
    storage = data_storage.GSheetStorage('eternal-delight-433008-q1-1bb6245a61a9.json')
    players_data = storage.data
    results = text_parser.MatchDayFile(filepath).results
    teams = results.teams
    players = [player.name for player in player_generator(teams)]
    stored_players = players_data.get_players_data(players)
    text_parser.check_new_players(players, list(stored_players.keys()))
    for player in player_generator(teams):
        try:
            elo, matches = stored_players[player.name]
            player.elo = elo
            player.matches = matches
        except KeyError:
            pass
    results.update_players()
    new_player_data = {
        player.name: (player.elo, player.matches) for player in player_generator(teams)
    }
    players_data.set_players_data(new_player_data)
    storage.write()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    args = parse_argument()
    main(**vars(args))
