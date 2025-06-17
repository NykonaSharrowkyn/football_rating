import pandas as pd
import pygsheets
import pygsheets.client

from players_data import PlayersStorageData

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Tuple


@dataclass
class Storage(ABC):
    data: PlayersStorageData = PlayersStorageData()

    def __post_init__(self):
        self.open()
        self.read()

    @abstractmethod
    def open(self):
        pass

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
    sheet_name: str = 'rating'
    file_name: str | None = None
    url: str | None = None
    gc: pygsheets.client.Client | None = None
    wb: pygsheets.Spreadsheet | None = None
    wks: pygsheets.Worksheet | None= None

    def __post_init__(self):
        self.gc = pygsheets.authorize(service_file=self.service_file)
        return super().__post_init__()

    def check_sheet(self, name: str):
        try:
            wks = self.wb.worksheet_by_title(name)
        except pygsheets.exceptions.WorksheetNotFound:
            wks = self.wb.add_worksheet(name)
        return wks
    
    def open(self):
        if self.url:
            self.wb = self.gc.open_by_url(self.url)
        elif self.file_name:
            try:
                self.wb = self.gc.open(self.file_name)
            except pygsheets.SpreadsheetNotFound:
                self.wb = self.gc.create(self.file_name)
                self.wks = self.wb.add_worksheet(self.sheet_name)
                self.wks.update_value('A1', 'Name')
                self.wks.update_value('B1', 'Rating')
                self.wks.update_value('C1', 'Matches')
                self.wks.update_value('D1', 'Prev rating')
                self.wks.update_value('E1', 'Change')
                self._update_color(self.wks, ('A1', 'E1'), (0.0, 0.8, 0.0))
                self.url = self.wb.url
        else:
            raise ValueError('No url or name provided')
        self.wks = self.wb.worksheet_by_title(self.sheet_name)


    def read(self):
        self.wb = self.gc.open(self.file_name)
        self.wks = self.wb.worksheet_by_title('rating')
        df: pd.DataFrame = self.wks.get_as_df()
        df.set_index('Name', inplace=True)
        self.data.df = df
        self.data.sort()

    def read_sheet(self, sheet_name) -> pd.DataFrame:
        wks = self.check_sheet(sheet_name)
        return wks.get_as_df()

    def write(self):
        df = self.data.df.copy()
        self.wks.clear()
        self.wks.set_dataframe(df.reset_index(), (1, 1))
        self._update_color(self.wks, ("A1", "E1"), (0.0, 0.8, 0.0))

    def write_sheet(self, sheet_name, df: pd.DataFrame):
        wks: pygsheets.Worksheet = self.wb.worksheet_by_title(sheet_name)
        wks.set_dataframe(df, (1, 1))
        end = chr(ord('A') + df.shape[1] - 1) + '1'
        self._update_color(wks, ("A1", end), (0.8, 0.8, 0.8))

    def update_time_stats(self, dt: datetime):
        year = dt.strftime("%Y")
        wks = self.check_sheet(year)
        old_df = wks.get_as_df(numerize=False)
        new_df = self.data.get_players_rating().reset_index()
        column_format = "%m.%Y"
        column_name = dt.strftime(column_format)
        new_df.columns = ['Name', column_name]
        if not old_df.empty:
            old_df.set_index('Name', inplace=True)
            old_df = old_df.astype(int)
            last_month = datetime.strptime(str(old_df.columns[-1]), column_format).date()
            current_month = dt.replace(day=1).date()
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