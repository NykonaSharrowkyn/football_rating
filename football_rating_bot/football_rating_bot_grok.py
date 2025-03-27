import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, InlineQueryHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
import uuid

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(self.token).build()

    async def inline_query(self, update, context):
        query = update.inline_query.query

        if not query:
            return

        # Создаем подсказку с кнопками, изначально без истории
        bot_username = self.application.bot.username  # Получаем имя бота
        keyboard = [
            [InlineKeyboardButton("Кнопка 1", callback_data='1|'),
             InlineKeyboardButton("Кнопка 2", callback_data='2|')],
            [InlineKeyboardButton("Кнопка 3", url=f"https://t.me/{bot_username}?start=chat")]
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
        await update.inline_query.answer(results, cache_time=0)

    async def button(self, update, context):
        query = update.callback_query
        data = query.data  # Например, "2|" или "2|1_User123-3_AnotherUser"
        username = query.from_user.username or "Unknown"  # Имя пользователя или "Unknown"

        # Разделяем номер кнопки и историю нажатий
        if '|' in data:
            button_number, pressed_history = data.split('|', 1)
        else:
            button_number = data
            pressed_history = ""

        # Парсим историю нажатий
        pressed_buttons = pressed_history.split('-') if pressed_history else []

        # Текущий текст сообщения, если message существует, иначе начальный текст
        current_text = query.message.text if query.message else "Выбери кнопку:\n"

        # Добавляем новую запись (кнопка + имя пользователя), если кнопка ещё не нажата
        new_entry = f"{button_number}_{username}"
        button_was_pressed = button_number in [entry.split('_')[0] for entry in pressed_buttons]
        if not button_was_pressed:
            pressed_buttons.append(new_entry)

        # Формируем новый текст с использованием Markdown
        base_text = "Выбери кнопку:\n"
        if pressed_buttons:
            pressed_text = "\n".join([f"Нажата кнопка {entry.split('_')[0]} _@{entry.split('_')[1]}_" for entry in pressed_buttons])
            new_text = f"{base_text}{pressed_text}"
        else:
            new_text = base_text

        # Обновляем callback_data с новой историей
        new_history = '-'.join(pressed_buttons)
        bot_username = self.application.bot.username
        keyboard = [
            [InlineKeyboardButton("Кнопка 1", callback_data=f'1|{new_history}'),
             InlineKeyboardButton("Кнопка 2", callback_data=f'2|{new_history}')],
            [InlineKeyboardButton("Кнопка 3", url=f"https://t.me/{bot_username}?start=chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Проверяем, изменилось ли сообщение перед редактированием
        current_markup = query.message.reply_markup if query.message else None
        if new_text != current_text or str(reply_markup) != str(current_markup):
            try:
                await query.edit_message_text(new_text, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)
            except telegram.error.BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise  # Если ошибка не связана с "Message is not modified", пробрасываем её дальше

        # Сохраняем chat_id и message_id в bot_data для эхо
        user_id = query.from_user.id
        context.bot_data[f'chat_id_{user_id}'] = query.message.chat_id
        context.bot_data[f'message_id_{user_id}'] = query.message.message_id
        context.bot_data[f'pressed_buttons_{user_id}'] = pressed_buttons

    # Обработчик кнопок в личном чате
    async def private_button(self, update, context):
        query = update.callback_query
        button_pressed = query.data  # Например, "A", "B" или "C"

        await query.edit_message_text(f"Ты нажал кнопку {button_pressed}")

    # Эхо-обработчик текстовых сообщений в личном чате, обновляет inline-сообщение
    async def echo(self, update, context):
        text = update.message.text
        user_id = update.message.from_user.id
        chat_id = context.bot_data.get(f'chat_id_{user_id}')
        message_id = context.bot_data.get(f'message_id_{user_id}')
        pressed_buttons = context.bot_data.get(f'pressed_buttons_{user_id}', [])

        if chat_id and message_id:
            bot_username = self.application.bot.username
            base_text = "Выбери кнопку:\n"
            if pressed_buttons:
                pressed_text = "\n".join([f"Нажата кнопка {entry.split('_')[0]} _@{entry.split('_')[1]}_" for entry in pressed_buttons])
                new_text = f"{base_text}{pressed_text}\nЭхо: {text}"
            else:
                new_text = f"{base_text}Эхо: {text}"

            keyboard = [
                [InlineKeyboardButton("Кнопка 1", callback_data=f'1|{"-".join(pressed_buttons)}'),
                 InlineKeyboardButton("Кнопка 2", callback_data=f'2|{"-".join(pressed_buttons)}')],
                [InlineKeyboardButton("Кнопка 3", url=f"https://t.me/{bot_username}?start=chat")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_text,
                    reply_markup=reply_markup,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
                )
            except telegram.error.BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise

    # Обработчик команды /start с deeplinking
    async def start(self, update, context):
        if context.args and context.args[0] == "chat":  # Проверяем параметр из ссылки
            keyboard = [
                [InlineKeyboardButton("Кнопка A", callback_data='A'),
                 InlineKeyboardButton("Кнопка B", callback_data='B')],
                [InlineKeyboardButton("Кнопка C", callback_data='C')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Выбери кнопку в личке:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Привет! Используй меня в inline-режиме или нажми Кнопку 3.")

    def run(self):
        # Регистрируем обработчики
        self.application.add_handler(InlineQueryHandler(self.inline_query))
        self.application.add_handler(CallbackQueryHandler(self.button, pattern=r'^\d+\|'))  # Для inline-кнопок
        self.application.add_handler(CallbackQueryHandler(self.private_button, pattern=r'^[A-C]$'))  # Для кнопок A, B, C
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, self.echo))  # Эхо в личке
        self.application.add_handler(CommandHandler("start", self.start))  # Обработчик /start

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