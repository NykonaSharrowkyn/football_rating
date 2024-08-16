import argparse
import data_storage
import matchday_file


def parse_argument() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='football_rating_utility',
        description='File based football elo rating program'
    )
    parser.add_argument('filepath', help='text file with match results')
    return parser.parse_args()


def main(filepath: str):
    storage = data_storage.Storage('ratings.txt')
    matchday = matchday_file.MatchDayFile(filepath).results
    teams = matchday.teams
    players = [player.name for team in teams for player in team.players]
    player_data = storage.get_players_data(players)
    for team in teams:
        for player in team.players:
            if player.name in player_data:
                elo, matches = player_data[player.name]
                player.elo = elo
                player.matches = matches
    matchday.update()
    new_player_data = {
        player.name: (player.elo, player.matches) for team in teams for player in team.players
    }
    storage.set_players_data(new_player_data)
    storage.save()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    args = parse_argument()
    main(**vars(args))
