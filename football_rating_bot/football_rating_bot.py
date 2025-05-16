from .football_database import FootballDatabase, RecordNotFound, AdminRequired
from football_rating.matchday import DEFAULT_ELO

from telegram import Update, InputFile
from telegram.ext import Application, ContextTypes
from typing import List

import io
import logging
import pandas as pd

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

class FootballRatingBot:
    admin_error_text = 'Необходимы права администратора.'
    too_long_error_text = 'Слишком длинное названия/имя (максимум 64 символа).'
    internal_error_text = 'Произошла внутренняя ошибка.'
    wrong_argument_text = 'Неверный аргумент.'    
    max_len = 64
    max_elo = 3000

    def __init__(self, token, db_path):
        self.token = token
        self.db = FootballDatabase(db_path)
        self.application = Application \
            .builder() \
            .token(self.token) \
            .build()
        # TODO: garbage collector

    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            args = update.message.text.split(' ')[1:]
            name = ' '.join(args[:-1])
            if len(name) > self.max_len:
                raise ArgumentLengthException
            elo = int(args[-1])
            self.db.add_player(update.effective_user.id, name, elo)
        except ArgumentLengthException:
            await update.message.reply_text(self.too_long_error_text)                        
        except AdminRequired:
            await update.message.reply_text(self.admin_error_text)            
        except ValueError:
            await update.message.reply_text(self.wrong_argument_text)
        except Exception as e:
            await update.message.reply_text(self.internal_error_text)
        
    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE)            :
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
            self.db.add_admin(update.effective_user.id, name, state)
        except (ValueError, IndexError):
            await update.message.reply_text(self.wrong_argument_text)
        except RecordNotFound:
            await update.message.reply_text('Пользователь не найден. Попросите его присоединиться.')
        except Exception as e:
            await update.message.reply_text(self.internal_error_text)

    async def export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            ratings = self.db.get_ratings(update.effective_user.id)
            df = pd.DataFrame(ratings)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            update.message.reply_document(
                document=InputFile(csv_buffer, filename='players_elo.csv'),
                caption='Рейтинг игроков'
            )
        except Exception as e:
            await update.message.reply_text(self.internal_error_text)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text: str = (
            '<b>Список команд:</b>\n'
            '/add [Имя] - добавить участника\n'
            '/admin [on|off] [@user] - дать @user права редактирования своих таблиц\n'
            '/export - выгрузить таблицу в csv'
            '/groups - список групп\n'
            '/help - список команд\n'
            '/join [on|off] [@user] - присоединиться к таблицам @user\n'
            '/rename [Имя] - [Имя] - переименовать участника\n'
            '/results [Результаты] - загрузить результаты\n'
            '/split [Количество команд] [Список участников] - разбить на команды\n'
            '/start [Имя группы] - запуск или переключение между группами участников\n'
        )
        await update.message.reply_text(text)
    
    def run(self):
        self.application.add_handler(CommandHandler("add", self.add))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("start", self.start))

        allowed_updates=['message']
        self.application.run_polling(poll_interval=2, allowed_updates=allowed_updates)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        try:
            self.db.add_user(user.id, user.username)
            group = self._get_argument(update.message.text, self.max_len)
            if not group:
                group = 'Default'
            self.db.select_group(user.id, group)                
            await update.message.reply_text(f'Успешно переключились на группу: {group}')
        except ArgumentLengthException:
            await update.message.reply_text(self.too_long_error_text)            
        except AdminRequired:
            await update.message.reply_text(self.admin_error_text)
        except Exception:
            await update.message.reply_text(self.internal_error_text)

    def _get_argument(self, text: str, max_len: int | None = None):
        index = text.find(' ')
        if index == -1:
            return ''
        arg = text[index + 1:]
        if max_len and len(arg) > max_len:
            raise ArgumentLengthException()
        return arg

        
