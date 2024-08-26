import pandas as pd

from typing import Dict, List


class PlayersStorageData:
    def __init__(self):
        self.df = pd.DataFrame()

    def clear(self):
        self.df = pd.DataFrame()

    def get_players_data(self, players: List[str]) -> pd.Series:
        return self.df[self.df.index.isin(players)]

    def get_players_match_data(self, players: List[str]) -> Dict[str, List[int]]:
        series = self.get_players_data(players)
        return series[['Rating', 'Matches']].T.to_dict('list')

    def set_players_match_data(self, players: Dict[str, List[int]]):
        df = pd.DataFrame.from_dict(players, orient='index')
        df.index.name = 'Name'
        df.columns = ['Rating', 'Matches']
        prev_rating = self.df['Rating'][self.df.index.isin(df.index)]
        diff = (df['Rating'] - self.df['Rating'])
        df['Prev rating'] = prev_rating
        df['Change'] = diff
        self.df['Change'] = 0
        self.df.update(df)
        self.sort()

    def sort(self):
        self.df.sort_values('Rating', ascending=False, inplace=True)

    def __iter__(self):
        for index, row in self.df.iterrows():
            yield row.tolist()
