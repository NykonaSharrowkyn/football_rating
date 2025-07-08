from .football_rating_bot import FootballRatingBot

import os

db_url = os.getenv('DATABASE_URL')

if not db_url:
    db_url='sqlite:///football-bot-db.db'

# Для SQLAlchemy 2.0+ замените postgres:// на postgresql://
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

bot = FootballRatingBot(
    db_url=db_url
)

bot.run()