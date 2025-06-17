from .football_database import FootballDatabase, UserRole, AdminRequired, RecordNotFound
from football_rating.data_storage import GSheetStorage
from football_rating.matchday import DEFAULT_ELO
from football_rating.text_parser import MatchDayParser
from football_rating.football_rating_utility import player_generator

from googleapiclient.discovery import build
import pygsheets

from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from typing import Dict, Tuple

import io
import logging
import pandas as pd
import re

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger('football_rating_bot')
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

class ArgumentLengthException(Exception):
    pass

class PlayerNotFound(Exception):
    pass

class FootballRatingBot:
    admin_error_text = 'Необходимы права администратора.'
    internal_error_text = 'Произошла внутренняя ошибка.'
    no_user_error_text = 'Пользователь не найден. Попросите его присоединиться.'
    wrong_argument_text = 'Неверный аргумент.'    
    gmail_key = 'wait_for_gmail'
    max_len = 64
    max_elo = 3000
    max_tables = 50


    def __init__(self, token, db_path):
        self.token = token
        self.service_file = '../football_rating/eternal-delight-433008-q1-1bb6245a61a9.json'
        self.db = FootballDatabase(db_path)
        self.application = Application \
            .builder() \
            .token(self.token) \
            .build()
        # TODO: garbage collector
        
    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE)            :
        context.user_data[self.gmail_key] = False
        user = update.effective_user
        try:
            args = self._get_argument(update.message.text).split(' ')
            state = args[0].lower()
            if state != 'on' or state != 'off':
                raise ValueError()
            state = state == 'on'
            name = args[1]
            if not name.startswith('@'):
                raise ValueError()
            name = name[1:]
            owner = self.db.get_owner(user.id)
            admin = self.db.get_user_by_name(name)
            self.db.update_admin(admin.id, owner.url, state)
        except (ValueError, IndexError):
            await update.message.reply_text(self.wrong_argument_text)
        except LookupError as e:
            await update.message.reply_text(e)
        except Exception as e:
            await update.message.reply_text(self.internal_error_text)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.gmail_key] = False
        text: str = (
            '<b>Список команд:</b>\n'
            '/admin [on|off] [@user] - дать @user права редактирования своей таблицы\n'
            '/help - список команд\n'
            '/results [Результаты] - загрузить результаты\n'
            '/split [Количество команд] [Список участников] - разбить на команды\n'
            '/start [Ссылка] - запуск или переключение между группами участников\n'
        )
        await update.message.reply_text(text)

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):        
        if not context.user_data[self.gmail_key]:
            return
        try:
            mail = update.message.text
            if not re.fullmatch(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', mail):
                raise ValueError(f'Не валидная почта {mail}')
            user = update.effective_user
            storage = GSheetStorage(
                self.service_file,
                file_name=f'football-rating_{user.id}'
            )
            url = storage.url
            storage.wb.share(mail)
            self.db.add_owner(user.id, url)
            self.db.update_admin(user.id, url, True)
            self.db.update_user(user.id, user.username, url)
            context.user_data[self.gmail_key] = False
            answer = f'Рейтинговая таблица успешно создана: {url}'
        except ValueError as e:
            answer = str(e)
        except Exception as e:
            answer = self.internal_error_text
        await update.message.reply_text(answer)

    async def results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.gmail_key] = False
        answer = 'Результаты успешно обновлены'
        user = update.effective_user
        try:            
            user = self.db.get_user(user.id)
            storage = GSheetStorage(
                self.service_file,
                url=user.url
            )
            storage.update_time_stats(datetime.today())
            stored_data = storage.data            
            results = MatchDayParser(text=update.message.text).results
            teams = results.teams
            players = [player.name for player in player_generator(teams)]
            stored_players = stored_data.get_players_match_data_dict(players)
            diff = set(players) - set(stored_players.keys())
            if diff:
                raise PlayerNotFound('\n'.join(diff))
            for player in player_generator(results.teams):
                elo, matches = stored_players[player.name]
                player.elo = elo
                player.matches = matches
            scores = list(results.get_scores().items())
            scores.sort(key=lambda x: x[1][0], reverse=True)
            text = ''
            for name, (points, scored, conceded) in scores:
                text += f'**{name}**:\nОчки - {points}\nЗабито - {scored}\nПропущено - {conceded}\n'
            await update.message.reply_text(text)

            admin = self.db.get_admin(user.id, user.url)
            if not admin:
                raise AdminRequired
            results.update_players()            

            new_player_data = {
                player.name: (player.elo, player.matches) for player in player_generator(teams)
            }            
            stored_data.set_players_match_data(new_player_data)
            storage.write()
        except AdminRequired as e:
            answer = self.admin_error_text
        except PlayerNotFound as e:
            answer = f'Добавьте игроков:\n{str(e)}'
        except RecordNotFound as e:
            answer = str(e)
        except Exception as e:
            answer = self.internal_error_text
        await update.message.reply_text(answer)
    
    def run(self):
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, self.message))


        allowed_updates=['message']
        self.application.run_polling(poll_interval=2, allowed_updates=allowed_updates)

    async def split(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.gmail_key] = False
        user = update.effective_user
        try:
            url = self._get_argument(update.message.text)
            if not url:      
                owner = self.db.get_owner(user.id)          
                self.db.update_user(user.id, user.name, owner.url)
            else:
                self.db.update_user(user.id, user.username, url)
            await update.message.reply_text('Вы успешно присоединились к таблице.')
        except RecordNotFound:
            count = self._get_tables_count()
            if count >= self.max_tables:
                await update.message.reply_text('Превышено количество таблиц. Обратитесь к разработчику.')
                return
            context.user_data[self.gmail_key] = True
            await update.message.reply_text('Введите вашу gmail почту, чтобы дать права на редактирование')
        except Exception:
            await update.message.reply_text(self.internal_error_text)

    def _get_tables_count(self):
        gc = pygsheets.authorize(service_account_file='service_account.json')
        drive_service = build('drive', 'v3', credentials=gc.auth)

        query = "name contains 'football-rating_' and mimeType='application/vnd.google-apps.spreadsheet'"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        return len(files)
    
    def _get_argument(self, text: str, max_len: int | None = None):
        index = text.find(' ')
        if index == -1:
            return ''
        arg = text[index + 1:]
        if max_len and len(arg) > max_len:
            raise ArgumentLengthException()
        return arg

    def _get_players_dict(self, df: pd.DataFrame) -> Dict[str, Tuple[int, int]]:
        return {
            row["name"]: (row["elo"], row["matches"])
            for _, row in df.iterrows()
        }
        
# import pygsheets
# from googleapiclient.discovery import build

# # Авторизация
# gc = pygsheets.authorize(service_account_file='service_account.json')
# drive_service = build('drive', 'v3', credentials=gc.auth)

# # Поиск таблиц по шаблону имени
# query = "name contains 'filename_' and mimeType='application/vnd.google-apps.spreadsheet'"
# results = drive_service.files().list(q=query, fields="files(id, name)").execute()
# files = results.get('files', [])

# print(f"Найдено таблиц: {len(files)}")
# for file in files:
#     print(f"ID: {file['id']}, Название: {file['name']}")

# import pygsheets

# gc = pygsheets.authorize(service_account_file='service_account.json')

# # Получить ВСЕ таблицы и отфильтровать локально
# all_sheets = gc.spreadsheets()
# filtered_sheets = [sh for sh in all_sheets if sh.title.startswith('filename_')]

# print(f"Найдено таблиц: {len(filtered_sheets)}")
# for sh in filtered_sheets:
#     print(f"ID: {sh.id}, Название: {sh.title}")