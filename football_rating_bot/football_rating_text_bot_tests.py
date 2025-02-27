import logging

from typing import Final
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, InlineQueryHandler, MessageHandler, filters, ContextTypes
from telegram.ext import CallbackQueryHandler

from pathlib import Path

TOKEN: Final = Path('token.txt').read_text()
BOT_USERNAME: Final = '@FootballEloBot'
DUMMY: Final = 'Спасибо! Бот сейчас в разработке!'

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(DUMMY)
    """Sends a message with three inline buttons attached."""
    # keyboard = [
    #     [
    #         InlineKeyboardButton("Option 1", callback_data="1"),
    #         InlineKeyboardButton("Option 2", callback_data="2"),
    #     ],
    #     [InlineKeyboardButton("Option 3", callback_data="3")],
    # ]
    #
    # reply_markup = InlineKeyboardMarkup(keyboard)
    #
    # await update.message.reply_text("Please choose:", reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(DUMMY)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(DUMMY)


def handle_response(text: str) -> str:
    return DUMMY


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type: str = update.message.chat.type
    text: str = update.message.text

    if chat_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)
    await update.message.reply_text(response)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query

    if not query:
        return

    keyboard = [
        [
            InlineKeyboardButton("Option 1", callback_data="1"),
            InlineKeyboardButton("Option 2", callback_data="2"),
        ],
        [InlineKeyboardButton("Option 3", callback_data="3")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    result = [
        InlineQueryResultArticle(
            id='1', title='Сообщение-заглушка',
            input_message_content=InputTextMessageContent(
                message_text=DUMMY
            ),
            reply_markup=reply_markup
        )
    ]
    await update.inline_query.answer(result)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('Тесто!')


if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('cancel', cancel_command))

    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    app.add_error_handler(error)

    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(InlineQueryHandler(inline_query))

    app.run_polling(poll_interval=5)
