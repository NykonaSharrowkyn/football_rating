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
    
    def __post_init__(self):
        self.state = StartState(self)

    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.state.process(update, context)
        self.state = self.state.next_state()
        await self.state.prompt(update, context)

    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.state.prompt(update, context)

@dataclass
class BotState(ABC):
    automat: BotAutomat
    
   
    @abstractmethod
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> 'BotState':
        pass

@dataclass
class StartState(BotState):
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> 'BotState':
        text: str = (
            '<b>Список команд:</b>\n'
            '\\start [Имя группы] - запуск или переключение между группами участников\n'
            '\\add [Имя] - добавить участника\n'
            '\\rename [Имя] - [Имя] - переименовать участника\n'
            '\\split [Список участников] [Количество команд]\n'
            '\\results [Результаты] - загрузить результаты'
        )
            
        