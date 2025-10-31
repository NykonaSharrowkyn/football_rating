from .football_database import FootballDatabase, RecordNotFound
from football_rating.data_storage import GSheetStorage, StorageError
from football_rating.matchmaking import MatchMaking
from football_rating.text_parser import MatchDayParser, PlayersText, PlayersFormatError, TeamNotFound
from football_rating.football_rating_utility import player_generator
from football_rating.matchmaking_utility import get_teams

import json
import logging
import os
import pandas as pd
import re

from datetime import datetime
from dotenv import load_dotenv
from enum import IntEnum, unique
from functools import wraps
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from typing import Dict, Tuple

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger('football_rating_bot')
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

load_dotenv()

class ArgumentLengthException(Exception):
    pass

class PlayersNotFound(Exception):
    pass

class AdminRequired(PermissionError):
    pass

class PlayersNotDivisable(ValueError):
    pass

@unique
class BotInteraction(IntEnum):
    NONE=0,
    GMAIL=1,
    TEAMS=2,
    PLAYERS=3,
    ADMIN=4,
    START=5,
    URL=6,
    RESULTS=7

# только для синхронного кода без async
def bot_command(fn):
    @wraps(fn)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        answer = self.INTERNAL_ERROR
        try:
            self._clear_context(context)
            answer = fn(self, update, context)
        except Exception as e:
            self._clear_context(context)
            logger.debug(str(e))
        await update.message.reply_text(answer, parse_mode='HTML')
    return wrapper

class FootballRatingBot:
    INTERNAL_ERROR = 'Произошла внутренняя ошибка'
    MESSAGE_ERROR = 'Сообщение не распознано (посмотрите /help)'
    NO_USER_ERROR = 'Пользователь не найден, попросите его присоединиться.'
    WRONG_ARGUMENT = 'Неверный аргумент'    
    INTERACTION_KEY = 'user_input'
    GMAIL_KEY = 'user_gmail'    
    USER_KEY = 'user_name'
    TEAMS_KEY = 'team_size'
    MAX_LEN = 64
    MAX_TABLES = 50
    GMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'


    def __init__(self, db_url):
        self.token = os.getenv("BOT_TOKEN")
        self.gcp_key = os.getenv("GCP_KEY")
        self.folder_id = os.getenv("BOT_FOLDER_ID")
        self.admin_gmail = os.getenv("ADMIN_GMAIL")
        self.db = FootballDatabase(db_url)
        self.application = Application \
            .builder() \
            .token(self.token) \
            .build()
        # TODO: garbage collector
        
    @bot_command
    def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        try:
            current_user = self.db.get_user(user.id)
            if self.db.is_admin(user.id, current_user.url):
                answer = (
                    'Введите пользователя:\n'
                    '@username\n'
                    'user@gmail.com\n (опционально, дать права редактирования)' 
                )
                context.user_data[self.INTERACTION_KEY] = BotInteraction.ADMIN
            else:
                answer = 'У вас нет прав администратора'
        except LookupError:
            answer = self.NO_USER_ERROR # такого быть не должно
        return answer

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:            
            query = update.callback_query
            await query.answer()
            data = update.callback_query.data.lower()
            if context.user_data[self.INTERACTION_KEY] == BotInteraction.ADMIN:
                username = context.user_data[self.USER_KEY]
                gmail = context.user_data[self.GMAIL_KEY]
                self._set_admin(username, gmail, data == 'on')
                await query.message.reply_text('Права доступа успешно обновлены')
            elif context.user_data[self.INTERACTION_KEY] == BotInteraction.START:
                callbacks = {
                    'new' : self._start_new,
                    'join' : self._join
                }
                await callbacks[data](update, context)
        except Exception as e:
            logger.debug(str(e))
            await query.message.reply_text(self.INTERNAL_ERROR)

    @bot_command
    def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text: str = (
            '<b>Список команд:</b>\n'
            '/admin - дать права редактирования\n'
            '/help - список команд и формат\n'
            '/results - загрузить результаты\n'
            '/split - разбить на команды\n'
            '/start - запуск или переключение между группами таблицами\n'
        )

        text += (
            '\n<b>Пример результатов:\n</b>'
            '(сопоставление команд по первой букве)\n'
            'Синие: Пирло, Буффон, Тотти\n'
            'Красные: Роналдо Зуб, Рональдиньо, Цезар\n'
            'Желтые: Зидан, Бартез, Анри П\n\n'
            'С 0:0 К\n'
            'К 2:0 Ж\n'
            'С 2:0 Ж\n'
        )

        text += (
            '\n<b>Пример списка:</b>\n'
            'Турнир имени Кожаного Мяча:\n'
            '(* - разбить по разным командам)\n'
            '1. Пирло\n'
            '2. Рональдиньо\n'
            '*3. Буффон\n'
            '...'
        )
        return text


    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            callbacks = {
                BotInteraction.GMAIL : self._message_gmail,
                BotInteraction.ADMIN : self._message_admin,
                BotInteraction.TEAMS : self._message_teams,
                BotInteraction.PLAYERS: self._message_players,
                BotInteraction.RESULTS: self._message_results,
                BotInteraction.URL: self._message_url
            }
            await callbacks[context.user_data[self.INTERACTION_KEY]](update, context)
        except Exception as e:
            logger.debug(str(e))
            await update.message.reply_text(self.MESSAGE_ERROR)

    @bot_command
    def results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.INTERACTION_KEY] = BotInteraction.RESULTS
        return 'Введите результаты по шаблону'
    
    def run(self):
        self.application.add_handler(CommandHandler("admin", self.admin))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("results", self.results))
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("split", self.split))
        self.application.add_handler(CallbackQueryHandler(self.button))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, self.message))


        allowed_updates=['message', 'callback_query']
        self.application.run_polling(poll_interval=2, allowed_updates=allowed_updates)

    @bot_command
    def split(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.INTERACTION_KEY] = BotInteraction.TEAMS
        return 'Количество команд?'
    
    # без декоратора - надо вернуть кнопки
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            self._clear_context(context)
            context.user_data[self.INTERACTION_KEY] = BotInteraction.START
            buttons = [
                ('Создать', 'new'),
                ('Присоединиться', 'join')
            ]
            await update.message.reply_text(
                text= 'Вы хотите создать свою таблицу или присоединиться к другой?',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(button, callback_data=data) for button, data in buttons]
                ])
            )
        except Exception as e:
            logger.debug(str(e))
            await update.message.reply_text(self.INTERNAL_ERROR)   

    def _check_players(self, players, stored_players):
        diff = set(players) - set(stored_players)
        if diff:
            raise PlayersNotFound('<b>Не найдены игроки</b>:\n' + '\n'.join(diff))
        return
    
    def _clear_context(self, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.INTERACTION_KEY] = BotInteraction.NONE
        context.user_data[self.USER_KEY] = ''
        context.user_data[self.GMAIL_KEY] = ''

    def _get_tables_count(self):
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        credentials = Credentials.from_service_account_info(
            json.loads(self.gcp_key),
            scopes=SCOPES
        )
        drive_service = build('drive', 'v3', credentials=credentials)

        query = "name contains 'football-rating' and mimeType='application/vnd.google-apps.spreadsheet'"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        # contains сравнивает не совсем точно, не учитывая _ - нужно дополнительно отфильтровать        
        filtered_files = [f for f in files if f['name'].startswith('football-rating_')]
        return len(filtered_files)
    
    # def _get_argument(self, text: str, max_len: int | None = None):
    #     index = text.find(' ')
    #     if index == -1:
    #         return ''
    #     arg = text[index + 1:]
    #     if max_len and len(arg) > max_len:
    #         raise ArgumentLengthException()
    #     return arg

    def _get_players_dict(self, df: pd.DataFrame) -> Dict[str, Tuple[int, int]]:
        return {
            row["name"]: (row["elo"], row["matches"])
            for _, row in df.iterrows()
        }
    
    async def _message_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            lines = update.message.text.split('\n')
            username = lines[0]
            if not username.startswith('@'):
                raise ValueError()
            username = username[1:]            
            try:
                gmail = lines[1]            
                context.user_data[self.GMAIL_KEY] = gmail
                if not re.fullmatch(self.GMAIL_REGEX, gmail):
                    raise ValueError()
            except IndexError:
                context.user_data[self.GMAIL_KEY] = ''
            context.user_data[self.USER_KEY] = username
            self.db.get_user_by_name(username)
            buttons = [('Админ', 'on'), ('Пользователь', 'off')]
            await update.message.reply_text(
                text= 'Какие права дать пользователю?',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(caption, callback_data=data) for caption, data in buttons]
                ])
            )
        except (ValueError, IndexError):
            await update.message.reply_text('Неверный формат')
        except RecordNotFound:
            await update.message.reply_text(self.NO_USER_ERROR)
    
    async def _message_gmail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        answer = self.INTERNAL_ERROR
        gmail = update.message.text
        try:
            self._clear_context(context)
            count = self._get_tables_count()
            if count >= self.MAX_TABLES:
                raise ValueError(f'Достигнут лимит таблиц.')
            if not re.fullmatch(self.GMAIL_REGEX, gmail):
                raise ValueError(f'Неверный формат почты {gmail}')
            user = update.effective_user
            storage = GSheetStorage(
                service_json=self.gcp_key,
                file_name=f'football-rating_{user.id}',
                parent_id=self.folder_id
            )
            url = storage.url
            storage.wb.share(self.admin_gmail, role='writer', type='user')
            storage.wb.share(gmail, role='writer', type='user')
            self.db.update_owner(user.id, url)
            self.db.update_admin(user.id, url, True)
            self.db.update_user(user.id, user.username, url)
            answer = f'Рейтинговая таблица успешно создана: {url}'
        except Exception as e:
            answer = str(e)
        await update.message.reply_text(answer)
    
    async def _message_teams(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data[self.TEAMS_KEY] = int(update.message.text)
            context.user_data[self.INTERACTION_KEY] = BotInteraction.PLAYERS
            answer = 'Введите участников по формату'
        except ValueError:
            answer = 'Неверный формат: введите число команд'
        await update.message.reply_text(answer)
        
    async def _message_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        answer = self.INTERNAL_ERROR
        user = update.effective_user
        try:
            count = context.user_data[self.TEAMS_KEY]
            self._clear_context(context)
            parser = PlayersText(text=update.message.text)
            players = parser.players
            split_players = parser.to_split
            if len(players) % count != 0:
                raise PlayersNotDivisable
            team_size = len(players) // count
            db_user = self.db.get_user(user.id)
            storage = GSheetStorage(
                service_json=self.gcp_key,
                url=db_user.url
            )
            all_data = storage.data
            storage = None
            players_data = all_data.get_players_match_data_dict(players)
            stored_players = list(players_data.keys())
            self._check_players(players, stored_players)
            df = pd.DataFrame.from_dict(players_data, orient='index').reset_index()
            df.columns = ['player', 'skill', 'matches']
            matchmaker = MatchMaking(df, team_size, split=split_players)
            df = matchmaker.optimize()
            teams = df.groupby(['team'])[['player', 'skill']]
            team_list = []
            players_list = []
            for key, _ in teams:
                team = teams.get_group(key)
                players = team['player'].tolist()
                players_list.append(players)
                score = team['skill'].mean()
                # team_str = key[0]
                players_str = ', '.join(players)
                team_list.append(f'{players_str} - средний {score:.2f}')
            answer = '\n'.join(get_teams(team_list, html=True))
        except PlayersNotDivisable:
            answer = 'Количество участников должно делиться на число команд'
        except (RecordNotFound, PlayersNotFound, PlayersFormatError) as e:
            answer = str(e)            
        except (ValueError, AssertionError):
            answer = 'Не удалось получить число команд'
        await update.message.reply_text(answer, parse_mode='HTML')        

    async def _message_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        try:            
            self._clear_context(context)
            user = self.db.get_user(user.id)
            if not self.db.is_admin(user.id, user.url):
                raise AdminRequired('Необходимы права администратора')
            storage = GSheetStorage(
                service_json=self.gcp_key,
                url=user.url
            )
            storage.update_time_stats(datetime.today())
            stored_data = storage.data            
            results = MatchDayParser(text=update.message.text).results
            teams = results.teams
            players = [player.name for player in player_generator(teams)]
            stored_players = stored_data.get_players_match_data_dict(players)
            self._check_players(players, stored_players)
            for player in player_generator(results.teams):
                elo, matches = stored_players[player.name]
                player.elo = elo
                player.matches = matches
            scores = list(results.get_scores().items())
            scores.sort(key=lambda x: x[1][0], reverse=True)
            answer = ''
            for name, (points, scored, conceded) in scores:
                answer += f'<b>{name}</b>:\nОчки - {points}\nЗабито - {scored}\nПропущено - {-conceded}\n'

            results.update_players()

            new_player_data = {
                player.name: (player.elo, player.matches) for player in player_generator(teams)
            }            
            stored_data.set_players_match_data(new_player_data)
            storage.write()
        except (AdminRequired, RecordNotFound, TeamNotFound, PlayersNotFound, StorageError) as e:
            answer = str(e)            
        await update.message.reply_text(answer, parse_mode='HTML')

    async def _message_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user        
        MAX_SIZE = 1024
        self._clear_context(context)
        self.db.update_user(user.id, user.username, update.message.text[:MAX_SIZE])
        await update.message.reply_text("Вы успешно переключились на таблицу")

    def _set_admin(self, username: str, gmail: str, state: bool):
        user = self.db.get_user_by_name(username)
        self.db.update_admin(user.id, user.url, state)
        if gmail:
            user = self.db.get_user(user.id)
            storage = GSheetStorage(
                service_json=self.gcp_key,
                url=user.url
            )
            role = 'writer' if state else 'reader'
            storage.wb.share(gmail, role=role, type='user')       

    async def _start_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.INTERACTION_KEY] = BotInteraction.GMAIL
        await update.callback_query.message.reply_text(
            'Введите вашу gmail почту, чтобы дать права '
            'на редактирование (она нигде не сохраняется)'
        )

    async def _join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[self.INTERACTION_KEY] = BotInteraction.URL
        await update.callback_query.message.reply_text('Введите ссылку на таблицу')
        
        
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