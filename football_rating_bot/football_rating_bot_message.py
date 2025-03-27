import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, InlineQueryHandler, CallbackQueryHandler
import uuid

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(self.token).build()

    async def inline_query(self, update, context):
        query = update.inline_query.query

        if not query:
            return

        # Создаем подсказку с кнопками
        keyboard = [
            [InlineKeyboardButton("Кнопка 1", callback_data='1'),
             InlineKeyboardButton("Кнопка 2", callback_data='2')],
            [InlineKeyboardButton("Кнопка 3", callback_data='3')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Формируем результат inline-запроса
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="Нажми меня",
                input_message_content=InputTextMessageContent("Выбери кнопку:"),
                reply_markup=reply_markup
            )
        ]

        # Отправляем результаты
        await update.inline_query.answer(results)

    async def button(self, update, context):
        query = update.callback_query
        button_number = query.data

        # Отправляем сообщение с номером нажатой кнопки
        await query.edit_message_text(f"Вы нажали кнопку номер {button_number}")

    def run(self):
        # Регистрируем обработчики
        self.application.add_handler(InlineQueryHandler(self.inline_query))
        self.application.add_handler(CallbackQueryHandler(self.button))

        # Запускаем бота
        self.application.run_polling()

def main():
    # Токен вашего бота от BotFather
    TOKEN = 'YOUR_BOT_TOKEN'
    
    # Создаем экземпляр бота и запускаем его
    bot = TelegramBot(TOKEN)
    bot.run()

if __name__ == '__main__':
    main()