import pandas as pd
import pygsheets

from players_data import PlayersStorageData

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Tuple


@dataclass
class Storage(ABC):
    data: PlayersStorageData = PlayersStorageData()
    dt: date = date.today()

    def __post_init__(self):
        self.read()

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass

    def update_time_stats(self):
        pass

    # def set_date(self, dt: datetime):
    #     self.dt = dt


# noinspection PyAbstractClass
@dataclass
class FileStorage(Storage):
    filepath: str | None = None


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
    service_file: str | None = None
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
        self._update_color(self.wks, ("A1", "E1"), (0.0, 0.8, 0.0))

    def update_time_stats(self):
        year = self.dt.strftime("%Y")
        try:
            wks = self.wb.worksheet_by_title(year)
        except pygsheets.exceptions.WorksheetNotFound:
            wks = self.wb.add_worksheet(year)
        old_df = wks.get_as_df(numerize=False)
        new_df = self.data.get_players_rating().reset_index()
        column_format = "%m.%Y"
        column_name = self.dt.strftime(column_format)
        new_df.columns = ['Name', column_name]
        if not old_df.empty:
            old_df.set_index('Name', inplace=True)
            old_df = old_df.astype(int)
            last_month = datetime.strptime(str(old_df.columns[-1]), column_format).date()
            current_month = self.dt.replace(day=1)
            if not current_month > last_month:
                return
            new_df.set_index('Name', inplace=True)
            new_df = pd.concat([old_df, new_df], axis=1)
            new_df = new_df.fillna(value=0).astype(int)
            new_df.sort_values(column_name, ascending=False, inplace=True)
            new_df.reset_index(inplace=True)

        wks.set_dataframe(new_df, (1, 1))
        end = chr(ord('A') + new_df.shape[1] - 1) + '1'
        self._update_color(wks, ("A1", end), (0.8, 0.8, 0.8))

    def _update_color(self, wks, grid_range: Tuple[str, ...], rgb: Tuple[float, ...]):
        red, green, blue = rgb
        requests = [
            {
                "repeatCell": {
                    "range": wks.get_gridrange(*grid_range),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": red, "green": green, "blue": blue}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
        self.gc.sheet.batch_update(self.wb.id, requests)