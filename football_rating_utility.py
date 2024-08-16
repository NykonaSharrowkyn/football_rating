import argparse
import storage
import matchday_file


def parse_argument() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='football_rating_utility',
        description='File based football elo rating program'
    )
    parser.add_argument('filepath', help='text file with match results')
    return parser.parse_args()


def main(filepath: str):
    ratings_storage = storage.Storage('ratings.txt')
    matchday = matchday_file.MatchDayFile(filepath).results
    teams = matchday.teams
    players = [player.name for team in teams for player in team.players]
    ratings = ratings_storage.get_elos(players)
    for team in teams:
        team.set_elo(ratings)
    matchday.update_elo()
    new_ratings = {
        player.name: player.elo for team in teams for player in team.players
    }
    ratings_storage.update_elos(new_ratings)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    args = parse_argument()
    main(**vars(args))
