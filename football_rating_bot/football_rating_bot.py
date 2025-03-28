from .football_database import FootballDatabase
from .inline_prompt import InlinePrompt

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackContext, ContextTypes
from telegram.ext import ChosenInlineResultHandler, InlineQueryHandler

import logging
import uuid

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

class FootballRatingBot:
    def __init__(self, token, db_path):
        self.token = token
        self.db = FootballDatabase(db_path)
        self.appliction = Application \
            .builder() \
            .token(self.token) \
            .read_timeout(30) \
            .write_timeout(30) \
            .build()

    async def inline_query(self, update: Update, context: CallbackContext):
        query = update.inline_query.query
        prompt = InlinePrompt(query)

        id = str(uuid.uuid4())
        logger.debug(f'Получен inline-запрос: {query} от {update.inline_query.from_user.id}, id={id}')
        markup = None
        if prompt.check_data():
            keyboard = [
                [InlineKeyboardButton('Участвовать / Отмена', callback_data='0|' + id)],                
                [InlineKeyboardButton('Действия', callback_data='1|' + id)],
            ]
            markup = InlineKeyboardMarkup(keyboard)
            context.user_data['event_name'] = prompt.input['name']

        results = [
            InlineQueryResultArticle(
                id=id,
                title=prompt.prompt(),
                description=prompt.description(),
                input_message_content=InputTextMessageContent(prompt.answer()),
                reply_markup=markup
            )
        ]

        await update.inline_query.answer(results, cache_time=0)

    async def chosen_inline_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chosen_result = update.chosen_inline_result
        result_id = chosen_result.result_id
        user_id = chosen_result.from_user.id
        message_id = chosen_result.inline_message_id
        event_name = context.user_data.get('event_name')
        logger.debug(f'Сработал chosen_inline_result: result_id={result_id}, user_id={user_id}, message={message_id}')
        self.db.add_event(
            event_id=uuid.UUID(result_id),
            owner_id=user_id,
            message_id=message_id,
            event_name=event_name
        )

    def run(self):
        self.appliction.add_handler(InlineQueryHandler(self.inline_query))
        self.appliction.add_handler(ChosenInlineResultHandler(self.chosen_inline_result))

        allowed_updates=['message', 'inline_query', 'chosen_inline_result']
        self.appliction.run_polling(poll_interval=2, allowed_updates=allowed_updates)
