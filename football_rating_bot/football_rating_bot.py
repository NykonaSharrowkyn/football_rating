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
            .read_timeout(30) \
            .write_timeout(30) \
            .build()
        # TODO: garbage collector
        self.automats = {}
        
    async def chat_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        if user_id not in self.automats:
            await context.bot.send_message(chat_id=user_id, text='Что-то пошло не так. Запускаю заново.')            
            automat = self.automats[user_id] = BotAutomat(db=self.db, user_id=user_id)
            await automat.prompt(update, context)
            return
        automat = self.automats[user_id]

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

    async def inline_button(self, update: Update, context: CallbackContext):
        query = update.callback_query
        try:
            button = int(query.data.split(':')[1])
            if button == 0:
                await self.register(update, context, RegisterType.MAIN)
            elif button == 1:
                await self.register(update, context, RegisterType.RESERVE)
            else:
                raise ValueError(f'Неверный id кнопки: {button}')
        except Exception as e:
            logger.debug(f'Ошибка: {str(e)}')


    async def inline_query(self, update: Update, context: CallbackContext):
        query = update.inline_query.query
        prompt = InlinePrompt(query)

        inline_id = str(uuid.uuid4())
        logger.debug(f'Получен inline-запрос: {query} от {update.inline_query.from_user.id}, id={id}')
        markup = None
        if prompt.check_data():
            markup = BotAutomat.create_inline_markup(inline_id)
            context.user_data['event_name'] = prompt.input['name']

        results = [
            InlineQueryResultArticle(
                id=inline_id,
                title=prompt.prompt(),
                description=prompt.description(),
                input_message_content=InputTextMessageContent(f'<i>{prompt.answer()}:</i>', parse_mode='HTML'),
                reply_markup=markup,
            )
        ]

        await update.inline_query.answer(results, cache_time=0)

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

    async def register(self, update: Update, context: ContextTypes.DEFAULT_TYPE, register_as: RegisterType.MAIN):        
        query = update.callback_query
        # username = query.from_user.username
        user_id = query.from_user.id
        user_name = query.from_user.full_name
        try:
            inline_id = uuid.UUID(query.data.split(':')[2])            
            event_id = self.db.get_event_by_inline(inline_id)
            player_id = self.db.get_player_id(user_id)
            # TODO: set elo for player
            if not player_id:
                # телега не разрешает боту писать первому, поэтому не имеет смысла
                automat = self.automats[user_id] = BotAutomat(self.db, user_id, event_id=event_id)
                automat.state = CommandState(automat, 'Для участия впервые, необходимо добавиться.')
                await automat.prompt(update, context)
                return
            # TODO: check max number            
            registered_as = self.db.is_player_registered(event_id, player_id)
            if register_as is None or register_as != registered_as:
                self.db.register_player(player_id, event_id, user_name, register_as)
            else:
                self.db.unregister_player(player_id, event_id)
                
            await BotAutomat.update_event_messages(self.db, event_id, context)
        except Exception as e:
            logger.debug(f'Ошибка: {str(e)}')
    
    def run(self):
        self.application.add_handler(InlineQueryHandler(self.inline_query))
        self.application.add_handler(ChosenInlineResultHandler(self.chosen_inline_result))
        self.application.add_handler(CallbackQueryHandler(self.inline_button, pattern='^inline'))
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
