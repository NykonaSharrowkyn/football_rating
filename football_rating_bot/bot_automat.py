from .bot_button import BotButton
from .football_database import FootballDatabase

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

@dataclass
class BotState(ABC):
    db: FootballDatabase
    message: str = "Базовое состоение"
    success: bool = False
    user_id: int = 0
    
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
class InitialState(BotState):
    message: str = 'Выберите действие'
    button_id: int = 0

    def next_state(self):
        class_dict = {
            0: AddMySelfState,
            # 1: AddSomeoneState,
            # 2: SplitState,
            # 3: LoadState,
            # 4: ListState
        }
        cls= class_dict[self.button_id]
        return cls(db=self.db, user_id=self.user_id)

    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.button_id = int(update.callback_query.data.split(':')[1])

    async def prompt(self, update, context):
        captions = [
            'Добавь меня',
            'Добавь участника',
            'Раздели команды',
            'Загрузить результаты',
            'Список активных событий'
        ]
        buttons = [BotButton(caption=caption, data=f'chat:{i}') for i, caption in enumerate(captions) ]
        keyboard = [
            [InlineKeyboardButton(button.caption, callback_data=button.data)] for button in buttons
        ]
        markup = InlineKeyboardMarkup(keyboard)        
        await context.bot.send_message(chat_id=self.user_id, text=self.message, reply_markup=markup)

@dataclass
class AddMySelfState(BotState):
    message: str = (
        '<b>Введите ваш начальный рейтинг (число 6-3000).</b>\n'
        'Текущий диапазон: <i>{} - {}</i>.\n'
        'Или по шкале от 1 до 5 <i>(1 - слабый, 5 - сильный)</i>'
    )
    max_elo: int = 0
    min_elo: int = 0    
    levels: list = field(default_factory=lambda: [800, 1200, 1600, 2000, 2400])
    limit: int = 3000

    def __post_init__(self):
        limits = self.db.get_elo_range()
        if limits is not None:
            self.min_elo, self.max_elo = limits
        self.message = self.message.format(self.min_elo, self.max_elo)

    def next_state(self):
        if not self.success:
            return self
        return InitialState(self.db, user_id=self.user_id)

    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = update.message.text
        try:
            value = int(msg)
            if value < 1 or value > self.limit:
                raise ValueError()
            if value <= 5:
                value = self.levels[value - 1]
            player_id = self.db.get_player_id(update.message.from_user.id)
            if not player_id:
                self.db.add_player(update.message.from_user.id, value)
            else:
                self.db.update_player(player_id, value)
            await update.message.reply_text('Данные успешно обновлены')
            self.success = True

        except ValueError:
            await update.message.reply_text('Введите корректное число')
            self.success = False

    async def prompt(self, update, context):
        await context.bot.send_message(chat_id=self.user_id, text=self.message, parse_mode='HTML')
    

@dataclass
class BotAutomat:
    db: FootballDatabase
    user_id: int
    
    def __post_init__(self):
        self.state = InitialState(db=self.db, user_id=self.user_id)

    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.state.process(update, context)
        self.state = self.state.next_state()
        await self.state.prompt(update, context)

    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.state.prompt(update, context)
        