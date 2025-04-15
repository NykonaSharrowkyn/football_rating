from .bot_automat import BotAutomat, InitialState
from .bot_button import BotButton
from .football_database import FootballDatabase
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
        # TODO: garbage collector
        self.automats = {}
        
    async def chat_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        try:
            automat = self.automats[user_id]
        except KeyError as e:
            await context.bot.send_message(chat_id=user_id, text='Что-то пошло не так. Запускаю заново.')            
            automat = self.automats[user_id] = BotAutomat(db=self.db, user_id=user_id)
            automat.prompt(update, context)

        try:
            await automat.process(update, context)
        except Exception as e:
            automat = self.automats[user_id] = BotAutomat(db=self.db, user_id=user_id)
            await automat.prompt(update, context)
            logger.debug(f'Ошибка: {str(e)}')
        
    async def chosen_inline_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # TODO: ограничения на активные события ?
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

    async def inline_query(self, update: Update, context: CallbackContext):
        query = update.inline_query.query
        prompt = InlinePrompt(query)

        id = str(uuid.uuid4())
        logger.debug(f'Получен inline-запрос: {query} от {update.inline_query.from_user.id}, id={id}')
        markup = None
        if prompt.check_data():
            markup = self._create_inline_markup(id)
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

    async def register_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):        
        query = update.callback_query
        # username = query.from_user.username
        user_id = query.from_user.id
        user_name = query.from_user.full_name
        try:
            inline_id = uuid.UUID(query.data.split(':')[1])            
            event_id = self.db.get_event_id(inline_id)
            event = self.db.get_event(event_id)
            player_id = self.db.get_player_id(user_id)
            # TODO: set elo for player
            if not player_id:
                # player_id = self.db.add_player(username, user_id, DEFAULT_ELO)
                automat = self.automats[user_id] = BotAutomat(self.db, user_id)
                await automat.prompt(update, context)
                return
            # TODO: check max number
            if self.db.is_player_registered(player_id, event_id):
                self.db.unregister_player(player_id, event_id)
            else:
                self.db.register_player(player_id, event_id, user_name)
                
            players = self.db.registered_players(event_id)
            message = self._create_text(event, players)
            message_ids = self.db.get_messages(event_id)
            for id in message_ids:
                try:
                    await context.bot.edit_message_text(
                        inline_message_id=id,
                        text=message,
                        reply_markup=self._create_inline_markup(str(inline_id)),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.debug(f'Не удалось отредактировать сообщение: {id}')                
        except Exception as e:
            logger.debug(f'Ошибка: {str(e)}')

    async def private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        try:
            automat: BotAutomat = self.automats[user_id]
            await automat.process(update, context)
        except Exception as e:
            logger.debug(f'Ошибка: {str(e)}')
            await context.bot.send_message(chat_id=user_id, text='Что-то пошло не так. Запускаю заново.')            
            automat = self.automats[user_id] = BotAutomat(db=self.db, user_id=user_id)
            await automat.prompt(update, context)
    
    def run(self):
        self.application.add_handler(InlineQueryHandler(self.inline_query))
        self.application.add_handler(ChosenInlineResultHandler(self.chosen_inline_result))
        self.application.add_handler(CallbackQueryHandler(self.register_button, pattern='^inline'))
        self.application.add_handler(CallbackQueryHandler(self.chat_button, pattern='^chat'))
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.ChatType.PRIVATE, self.private_message))

        allowed_updates=['message', 'inline_query', 'chosen_inline_result', 'callback_query']
        self.application.run_polling(poll_interval=2, allowed_updates=allowed_updates)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        try:            
            automat = self.automats[user_id] = BotAutomat(self.db, user_id)
            await automat.prompt(update, context)
        except Exception as e:
            logger.debug(f'Ошибка: {str(e)}')
        # await update.message.reply_text(
        #     text="Для участия в событии нужно сначала добавиться в базу бота (Добавь меня)",
        #     reply_markup=self._create_private_markup()
        # )

    def _create_inline_markup(self, id: str) -> InlineKeyboardMarkup:
        join_button = BotButton(caption='Участвовать / Отмена', data=f'inline:{id}')
        action_button = BotButton(caption='Действия')

        keyboard = [
            [InlineKeyboardButton(join_button.caption, callback_data=join_button.data)],
            [InlineKeyboardButton(action_button.caption, url="https://t.me/FootballEloBot?start=register")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    # def _create_private_markup(self) -> InlineKeyboardMarkup:
    #     captions = [
    #         'Добавь меня',
    #         'Добавь участника',
    #         'Раздели команды',
    #         'Загрузить результаты',
    #         'Список активных событий'
    #     ]
    #     buttons = [BotButton(caption=caption, data=f'chat:{i}') for i, caption in enumerate(captions) ]
    #     keyboard = [
    #         [InlineKeyboardButton(button.caption, callback_data=button.data)] for button in buttons
    #     ]
    #     return InlineKeyboardMarkup(keyboard)

    
    def _create_text(self, event: dict, players: List[dict] | None, context: ContextTypes.DEFAULT_TYPE) -> str:
        title = f"<i>{event['event_title']}:</i>"
        if not players:
            return title
        message = f'{title}\n'
        names = [player['player_name'] for player in players]
        message += '\n'.join(names)
        return message
    
    # async def _send_add_player(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    #     self.automat.state = InitialState(
    #         message='Для участия в событии нужно сначала добавиться в базу бота ("Добавь меня")'
    #     )
    #     await self.automat.send_message()
    #     # await context.bot.send_message(
    #     #     chat_id=user_id, 
    #     #     text='Для участия в событии нужно сначала добавиться в базу бота ("Добавь меня")',
    #     #     reply_markup=self._create_private_markup()
    #     # )    
