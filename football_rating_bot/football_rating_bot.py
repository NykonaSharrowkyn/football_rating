from .football_database import FootballDatabase
from .inline_prompt import InlinePrompt

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackContext, ContextTypes
from telegram.ext import CallbackQueryHandler, ChosenInlineResultHandler, InlineQueryHandler

import logging
import telegram
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
        self.application = Application \
            .builder() \
            .token(self.token) \
            .read_timeout(30) \
            .write_timeout(30) \
            .build()
        
    async def event_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        username = query.from_user.username
        logger.debug(f'event_button: data={query.data}, username={username}')
        if not username:
            return
        data = query.data
        try:
            if data != 'event_button_0':
                return
            new_text = query.message + '\nТесто'
            await query.edit_message_text(new_text)
        except telegram.error.BadRequest as e:
            logger.debug(f'Bad request: {str(e)}')
        except KeyError as e:
            logger.debug('No "id" in callback data')
        
    async def chosen_inline_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chosen_result = update.chosen_inline_result
        result_id = chosen_result.result_id
        user_id = chosen_result.from_user.id
        message_id = chosen_result.inline_message_id
        event_name = context.user_data.get('event_name')
        logger.debug(f'chosen_inline_result: result_id={result_id}, user_id={user_id}, message={message_id}')
        self.db.add_event(
            event_id=uuid.UUID(result_id),
            owner_id=user_id,
            message_id=message_id,
            event_name=event_name
        )        

    async def inline_query(self, update: Update, context: CallbackContext):
        query = update.inline_query.query
        prompt = InlinePrompt(query)

        id = str(uuid.uuid4())
        logger.debug(f'Получен inline-запрос: {query} от {update.inline_query.from_user.id}, id={id}')
        markup = None
        if prompt.check_data():
            button_data = {
                'join': {'name': 'event_button_0', 'caption': 'Участвовать / Отмена'},
                'actions': {'name' : 'event_button_1', 'caption': 'Действия'}
            }
            keyboard = [
                [InlineKeyboardButton(button_data[key]['caption'], callback_data=button_data[key]['name'])]
                for key in button_data.keys()
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

    def run(self):
        self.application.add_handler(InlineQueryHandler(self.inline_query))
        self.application.add_handler(ChosenInlineResultHandler(self.chosen_inline_result))
        self.application.add_handler(CallbackQueryHandler(self.event_button))

        allowed_updates=['message', 'inline_query', 'chosen_inline_result', 'callback_query']
        self.application.run_polling(poll_interval=2, allowed_updates=allowed_updates)
