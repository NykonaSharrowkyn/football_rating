import pandas as pd
import pygsheets

from players_data import PlayersStorageData

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Storage(ABC):
    data = PlayersStorageData()

    def __post_init__(self):
        self.read()

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass


# noinspection PyAbstractClass
@dataclass
class FileStorage(Storage):
    filepath: str


@dataclass
class PlainTextFileStorage(FileStorage):
    def read(self):
        raise NotImplementedError('Not tested after pandas rework')
        # self.data.clear()
        # try:
        #     with open(self.filepath, 'r', encoding='utf-8') as file:
        #         for line in file[1:]:
        #             parts = line.rstrip().split(',')
        #             parts = [part.rstrip().lstrip() for part in parts]
        #             name = parts[0]
        #             elo = int(parts[1])
        #             matches = int(parts[2])
        #             self.data.data[name] = (elo, matches)
        # except FileNotFoundError:
        #     pass

    def write(self):
        raise NotImplementedError('Not tested after pandas rework')
        # with open(self.filepath, 'w', encoding='utf-8') as file:
        #     for item in self.data:
        #         file.write(",".join(item))


@dataclass
class CsvTextFileStorage(FileStorage):
    def read(self):
        raise NotImplementedError('Not tested after pandas rework')
        # try:
        #     df = pd.read_csv(self.filepath)
        #     df.set_index('Name', inplace=True)
        #     self.data.data = df.T.to_dict('list')
        # except FileNotFoundError:
        #     pass

    def write(self):
        raise NotImplementedError('Not tested after pandas rework')
        # df = pd.DataFrame.from_dict(self.data.data, orient='index')
        # df.index.name = 'Name'
        # df.columns = ['Rating', 'Matches']
        # df.to_csv(self.filepath)


@dataclass
class GSheetStorage(Storage):
    service_file: str
    file_name: str = 'football-rating'
    sheet_name: str = 'rating'
    gc: Any = None
    wb: Any = None
    wks: Any = None

    def read(self):
        self.gc = pygsheets.authorize(service_file=self.service_file)
        self.wb = self.gc.open(self.file_name)
        self.wks = self.wb.worksheet_by_title('rating')
        df = self.wks.get_as_df()
        df.set_index('Name', inplace=True)
        self.data.df = df
        self.data.sort()

    def write(self):
        df = self.data.df.copy()
        self.wks.clear()
        self.wks.set_dataframe(df.reset_index(), (1, 1))
        requests = [
            {
                "repeatCell": {
                    "range": self.wks.get_gridrange("A1", "E1"),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.0, "green": 0.8, "blue": 0.0}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
        self.gc.sheet.batch_update(self.wb.id, requests)
