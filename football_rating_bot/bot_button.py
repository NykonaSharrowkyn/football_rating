from dataclasses import dataclass, asdict

@dataclass
class BotButton:
    caption: str
    data: str = ''