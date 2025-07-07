from .football_rating_bot import FootballRatingBot
from .config import TOKEN_PATH, DB_PATH

from pathlib import Path

# import asyncio

bot = FootballRatingBot(
    db_path=DB_PATH
)
bot.run()
# try:
#     asyncio.run(bot.start())
# except RuntimeError as e:
#     if str(e) == "Cannot close a running event loop":
#         # Если event loop уже запущен (например, в Jupyter Notebook)
#         loop = asyncio.get_event_loop()
#         loop.run_until_complete(bot.start())