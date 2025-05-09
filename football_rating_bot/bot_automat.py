from .bot_button import BotButton
from .football_database import FootballDatabase, RegisterType

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from typing import Dict

import uuid

@dataclass
class BotAutomat:
    db: FootballDatabase
    user_id: int
    event_id: uuid.UUID | None = None

    @classmethod
    def create_event_text(cls, db: FootballDatabase, event_id: uuid.UUID) -> str:
        """Создает текстовое описание события

        Args:
            db (FootballDatabase): база
            event_id (uuid.UUID): uuid события

        Returns:
            str: Текст события
        """
        event = db.get_event(event_id)
        players = db.registered_players(event_id)
        title = f"<i>{event['event_title']}:</i>"
        if not players:
            return title
        message = f'{title}\n'
        names = [player['player_name'] for player in players]
        message += '\n'.join(names)
        return message
    
    @classmethod
    def create_inline_markup(cls, id: uuid.UUID) -> InlineKeyboardMarkup:
        id = str(id)
        join_button = BotButton(caption='Участвовать / Отмена', data=f'inline:0:{id}')
        reserve_button = BotButton(caption='Резерв / Отмена', data=f'inline:1:{id}')
        action_button = BotButton(caption='Действия')

        keyboard = [
            [InlineKeyboardButton(join_button.caption, callback_data=join_button.data)],
            [InlineKeyboardButton(reserve_button.caption, callback_data=reserve_button.data)],
            [InlineKeyboardButton(action_button.caption, url="https://t.me/FootballEloBot?start=register")]
        ]
        return InlineKeyboardMarkup(keyboard)    
    
    @classmethod
    async def update_event_messages(
        cls,
        db: FootballDatabase,
        event_id: uuid.UUID,        
        context: ContextTypes.DEFAULT_TYPE
    ):
        message = BotAutomat.create_event_text(db, event_id)
        messages = db.get_messages(event_id)
        for id in messages:
            await context.bot.edit_message_text(
                inline_message_id=id,
                text=message,
                reply_markup=BotAutomat.create_inline_markup(id),
                parse_mode='HTML'
            )

    
    def __post_init__(self):
        self.state = ListState(self)

    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.state.process(update, context)
        self.state = self.state.next_state()
        await self.state.prompt(update, context)

    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.state.prompt(update, context)

@dataclass
class BotState(ABC):
    automat: BotAutomat
    prompt_message: str = "Базовое состоение"
    success: bool = False
    
    @abstractmethod
    def next_state(self) -> 'BotState':
        pass
    
    @abstractmethod
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    @abstractmethod
    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

@dataclass
class ListState(BotState):    
    events: Dict[uuid.UUID, str] = field(default_factory=dict)
    prompt_message: str = "Выберите событие"
    
    def __post_init__(self):
        self.events = self.automat.db.get_events(self.automat.user_id)

    def next_state(self):
        return CommandState(self.automat)
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        id = update.callback_query.data.split(':')[1]
        self.automat.event_id = uuid.UUID(id)

    async def prompt(self, update, context):
        if not self.events:
            await context.bot.send_message(chat_id=self.automat.user_id, text='Нет активных событий')
            return
        buttons = [BotButton(caption=event['event_title'], data=f"chat:{event['event_id']}") for event in self.events]
        keyboard = [
            [InlineKeyboardButton(button.caption, callback_data=button.data)] for button in buttons
        ]
        markup = InlineKeyboardMarkup(keyboard)        
        await context.bot.send_message(chat_id=self.automat.user_id, text=self.prompt_message, reply_markup=markup)        

@dataclass
class CommandState(BotState):
    prompt_message: str = 'Выберите действие'
    button_id: int = 0

    def next_state(self):
        class_dict = {
            0: AddMySelfState,
            1: AddSomeoneState,
            # 2: SplitState,
            # 3: LoadState,
            # 4: ListState
        }
        cls= class_dict[self.button_id]
        return cls(self.automat)

    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.button_id = int(update.callback_query.data.split(':')[1])

    async def prompt(self, update, context):        
        captions = [
            'Добавь меня в базу',
            'Добавить/удалить участника',
            'Из резерва/в резерв',
            'Раздели команды',
            'Загрузить результаты',
            'Другие события'
        ]
        buttons = [BotButton(caption=caption, data=f'chat:{i}') for i, caption in enumerate(captions) ]
        keyboard = [
            [InlineKeyboardButton(button.caption, callback_data=button.data)] for button in buttons
        ]
        markup = InlineKeyboardMarkup(keyboard)        
        event = self.automat.db.get_event(self.automat.event_id)
        title = f"<i>{event['event_title']}</i>"
        text = f'{title}\n{self.prompt_message}'
        await context.bot.send_message(            
            chat_id=self.automat.user_id,
            text=text,
            reply_markup=markup,
            parse_mode='HTML'
        )

@dataclass
class AddPlayerState(BotState):
    elo_message: str = (
        '<b>Введите начальный рейтинг (число 6-3000).</b>\n'
        'Текущий диапазон: <i>{} - {}</i>.\n'
        'Или по шкале от 1 до 5 <i>(1 - слабый, 5 - сильный)</i>'
    )    
    max_elo: int = 0
    min_elo: int = 0    
    levels: list = field(default_factory=lambda: [800, 1200, 1600, 2000, 2400])
    limit: int = 3000

    def __post_init__(self):
        limits = self.automat.db.get_elo_range()
        if limits is not None:
            self.min_elo, self.max_elo = limits
        self.elo_message = self.elo_message.format(self.min_elo, self.max_elo)            

    def parse_elo(self, text):
        value = int(text)
        if value < 1 or value > self.limit:
            raise ValueError('Значение за границами диапазона')
        if value <= 5:
            value = self.levels[value - 1]
        return value
    
    async def prompt(self, update, context):
        await context.bot.send_message(chat_id=self.automat.user_id, text=self.elo_message, parse_mode='HTML')

@dataclass
class AddMySelfState(AddPlayerState):
    def __post_init__(self):
        super().__post_init__()

    def next_state(self):
        if not self.success:
            return self
        return CommandState(self.automat)

    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            value = self.parse_elo(update.message.text)
            player_id = self.automat.db.get_player_id(update.message.from_user.id)
            if not player_id:
                self.automat.db.add_player(update.message.from_user.id, value)
            else:
                self.automat.db.update_player(player_id, value)
            await update.message.reply_text('Данные успешно обновлены')
            self.success = True

        except ValueError:
            await update.message.reply_text('Введите корректное число')
            self.success = False
    
@dataclass
class AddSomeoneState(BotState):
    prompt_message: str = (
        '<b>Добавьте другого игрока.</b>\n'
        '<i>Рейтинг игрока не является глобальным и привязан к приглашающему.</i>'
    )
    player_name: str = ''
    player_exists: bool = False
    max_len: int = 64
    

    def next_state(self):
        if not self.success:
            return self
        if not self.player_exists:
            return InputSomeoneEloState(self.automat, player_name=self.player_name)
        return CommandState(self.automat)

   
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавляет/удаляет участника

        Args:
            update (Update): _description_
            context (ContextTypes.DEFAULT_TYPE): _description_
        """        
        try:
            msg = update.message.text
            if '\n' in msg or len(msg) > self.max_len:
                raise ValueError()
            self.player_name = msg
            player_id = self.automat.db.get_player_id(0, update.message.from_user.id, msg)
            self.success = True
            if not player_id:
                self.player_exists = False
                return
            if self.automat.db.is_player_registered(self.automat.event_id, player_id):
                self.automat.db.unregister_player(player_id, self.automat.event_id)
            else:
                self.automat.db.register_player(player_id, self.automat.event_id, msg)
            await BotAutomat.update_event_messages(self.automat.db, self.automat.event_id, context)

        except ValueError as e:
            await update.message.reply_text(f'Введите корректное имя: из одной строки не длиннее {self.max_len} символов')
            self.success = False

    async def prompt(self, update, context):
        await context.bot.send_message(chat_id=self.automat.user_id, text=self.prompt_message, parse_mode='HTML')


@dataclass
class InputSomeoneEloState(AddPlayerState):
    player_name: str = ''

    def __post_init__(self):
        return super().__post_init__()
    
    def next_state(self):
        if not self.success:
            return self
        return CommandState(self.db, self.user_id)
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            value = self.parse_elo(update.message.text)
            id = self.automat.db.add_invited_player(self.automat.user_id, self.player_name, value)
            self.automat.db.register_player(id, self.automat.event_id, self.player_name)
            await update.message.reply_text('Данные успешно обновлены')
            self.success = True
        except ValueError:
            await update.message.reply_text('Введите корректное число')
            self.success = False                
        