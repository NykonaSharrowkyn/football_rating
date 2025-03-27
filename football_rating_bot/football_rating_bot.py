from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CallbackContext, InlineQueryHandler, ContextTypes

from .inline_prompt import InlinePrompt, InlineAction

import uuid

from typing import List

class FootballRatingBot:
    def __init__(self, token):
        self.token = token
        self.appliction = Application \
            .builder() \
            .token(self.token) \
            .read_timeout(30) \
            .write_timeout(30) \
            .build()

    async def inline_query(self, update: Update, context: CallbackContext):
        query = update.inline_query.query
        prompt = InlinePrompt(query)

        id = str(uuid.uuid4())
        results = [
            InlineQueryResultArticle(
                id=id,
                title=prompt.prompt(),
                description=prompt.description(),
                input_message_content=InputTextMessageContent(prompt.answer()),
                reply_markup=prompt.markup(id)
            )
        ]

        await update.inline_query.answer(results, cache_time=0)

    async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
        id = update.chosen_inline_result.result_id

    def run(self):
        self.appliction.add_handler(InlineQueryHandler(self.inline_query))

        self.appliction.run_polling(poll_interval=2)
