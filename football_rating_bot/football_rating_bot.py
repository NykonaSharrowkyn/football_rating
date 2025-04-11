from .football_database import FootballDatabase
from .inline_prompt import InlinePrompt
from football_rating.matchday import DEFAULT_ELO

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackContext, ContextTypes
from telegram.ext import CallbackQueryHandler, ChosenInlineResultHandler, InlineQueryHandler, MessageHandler, filters
from typing import List

import json
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
        
    async def action_button(self, data: dict, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass
        
    async def chosen_inline_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chosen_result = update.chosen_inline_result
        result_id = chosen_result.result_id
        user_id = chosen_result.from_user.id
        message_id = chosen_result.inline_message_id
        event_name = context.user_data.get('event_name')
        logger.debug(f'chosen_inline_result: result_id={result_id}, user_id={user_id}, message={message_id}')
        event_id = uuid.uuid4()
        self.db.add_event(
            event_id=event_id,
            owner_id=user_id,
            event_title=event_name
        )
        self.db.add_event_message(
            inline_id=uuid.UUID(result_id),
            message_id=message_id,
            event_id=event_id
        )        
        
    async def event_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = json.loads(query.data)
        buttons = [
            self.participate_button,
            self.action_button
        ]
        try:
            await buttons[data['id']](data, update, context)
        except IndexError as e:
            logger.debug(f'Некорректная data в кнопке: {data}')

    async def inline_query(self, update: Update, context: CallbackContext):
        query = update.inline_query.query
        prompt = InlinePrompt(query)

        id = str(uuid.uuid4())
        logger.debug(f'Получен inline-запрос: {query} от {update.inline_query.from_user.id}, id={id}')
        markup = None
        if prompt.check_data():
            markup = self._create_markup(id)
            context.user_data['event_name'] = prompt.input['name']

        results = [
            InlineQueryResultArticle(
                id=id,
                title=prompt.prompt(),
                description=prompt.description(),
                input_message_content=InputTextMessageContent(f'<i>{prompt.answer()}:</i>', parse_mode='HTML'),
                reply_markup=markup,
            )
        ]

        await update.inline_query.answer(results, cache_time=0)

    async def participate_button(self, data: dict, update: Update, context: ContextTypes.DEFAULT_TYPE):        
        query = update.callback_query
        username = query.from_user.username
        user_id = query.from_user.id
        try:
            inline_id = uuid.UUID(data['inline_id'])
            event_id = self.db.get_event_id(inline_id)
            event = self.db.get_event(event_id)
            player_id = self.db.get_player_id(user_id)
            # TODO: set elo for player
            if not player_id:
                player_id = self.db.add_player(username, user_id, DEFAULT_ELO)
            # TODO: check max number
            if self.db.is_player_registered(player_id, event_id):
                self.db.unregister_player(player_id, event_id)
            else:
                self.db.register_player(player_id, event_id)
                
            players = self.db.registered_players(event_id)
            message = self._create_text(event, players)
            message_ids = self.db.get_messages(event_id)
            for id in message_ids:
                try:
                    await context.bot.edit_message_text(
                        inline_message_id=id,
                        text=message,
                        reply_markup=self._create_markup(str(inline_id)),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.debug(f'Не удалось отредактировать сообщение: {id}')                
        except KeyError as e:
            logger.debug(f'Некорректная data в кнопке: {data}')
        except Exception as e:
            logger.debug(f'Ошибка: {str(e)}')
    
    def run(self):
        self.application.add_handler(InlineQueryHandler(self.inline_query))
        self.application.add_handler(ChosenInlineResultHandler(self.chosen_inline_result))
        self.application.add_handler(CallbackQueryHandler(self.event_button))

        allowed_updates=['message', 'inline_query', 'chosen_inline_result', 'callback_query']
        self.application.run_polling(poll_interval=2, allowed_updates=allowed_updates)

    def _create_markup(self, id: str) -> InlineKeyboardMarkup:
        button_data = {
            'join': {'caption': 'Участвовать / Отмена'},
            'actions': {'caption': 'Действия'}
        }
        for i, button in enumerate(button_data):
            button_data[button]['data'] = json.dumps({'id': i, 'inline_id': id})

        keyboard = [
            [InlineKeyboardButton(button_data[key]['caption'], callback_data=button_data[key]['data'])]
            for key in button_data.keys()
        ]
        return InlineKeyboardMarkup(keyboard)

    
    def _create_text(self, event: dict, players: List[dict] | None) -> str:
        title = f"<i>{event['event_title']}:</i>"
        if not players:
            return title
        message = f'{title}\n'
        names = [player['player_name'] for player in players]
        message += '\n'.join(names)
        return message
