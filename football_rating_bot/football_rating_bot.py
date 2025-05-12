from .bot_automat import BotAutomat, CommandState
from .football_database import FootballDatabase, RegisterType
from .inline_prompt import InlinePrompt
from football_rating.matchday import DEFAULT_ELO

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackContext, ContextTypes, filters
from telegram.ext import CallbackQueryHandler, ChosenInlineResultHandler, InlineQueryHandler, CommandHandler, MessageHandler
from typing import List

import logging
import telegram
import uuid

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger('football_rating_bot')
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

class FootballRatingBot:
    def __init__(self, token, db_path):
        self.token = token
        self.db = FootballDatabase(db_path)
        self.application = Application \
            .builder() \
            .token(self.token) \
            .build()
        # TODO: garbage collector
        self.automats = {}
        
    
    def run(self):
        self.application.add_handler(CommandHandler("start", self.start))

        allowed_updates=['message']
        self.application.run_polling(poll_interval=2, allowed_updates=allowed_updates)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        try:            
            automat = self.automats[user_id] = BotAutomat(self.db, user_id)
            await automat.prompt(update, context)
        except Exception as e:
            logger.debug(f'Ошибка: {str(e)}') 
