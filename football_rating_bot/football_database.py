import logging
import uuid

from functools import wraps

from sqlalchemy import create_engine, Column, UUID, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from typing import Callable, List

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(Integer)
    event_title = Column(String)

    players = relationship('EventPlayer', back_populates='event')
    messages = relationship('Message', back_populates='event')

class Player(Base):
    __tablename__ = 'players'
    player_id = Column(UUID(as_uuid=True), primary_key=True)
    player_name = Column(String)
    telegram_id = Column(Integer)
    chat_id = Column(Integer, default=0)
    elo = Column(Integer, default=1250)
    matches = Column(Integer, default=0)

    events = relationship('EventPlayer', back_populates='player')

class Message(Base):
    __tablename__ = 'messages'
    inline_id = Column(UUID(as_uuid=True), primary_key=True)
    message_id = Column(String, unique=True)    
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.event_id'))

    event = relationship('Event', back_populates='messages')

class EventPlayer(Base):
    __tablename__ = 'event_players'
    player_id = Column(UUID, ForeignKey('players.player_id'), primary_key=True)
    event_id = Column(UUID, ForeignKey('events.event_id'), primary_key=True)
    
    event = relationship("Event", back_populates='players')
    player = relationship("Player", back_populates='events')

# class Player(Base):
#     __tablename__ = 'players'
#     player_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(Integer)
#     user

def model_to_dict(model):
    if model is None:
        return None
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}

def with_session(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.session() as session:
            try:
                return func(self, session, *args, **kwargs)
            except Exception as e:
                logger.debug(f'Ошибка в {func.__name__}: {str(e)}')
                logger.debug(args)
                logger.debug(kwargs)
    return wrapper

def with_commit(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.session() as session:
            try:
                result = func(self, session, *args, **kwargs)
                session.commit()
                return result
            except Exception as e:
                logger.debug(f'Ошибка в {func.__name__}: {str(e)}')
                logger.debug(args)
                logger.debug(kwargs)
                session.rollback()
    return wrapper

class FootballDatabase:
    def __init__(self, db_path: str):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)

    def add_event(self, event_id: uuid.UUID, owner_id: str, event_title: str) -> uuid.UUID | None:
        return self._add_event(event_id, owner_id, event_title)    
    
    def add_event_message(self, inline_id: uuid.UUID, message_id: uuid.UUID, event_id: uuid.UUID) -> uuid.UUID | None:
        return self._add_event_message(inline_id, message_id, event_id)

    def add_player(self, name: str, telegram_id: int, elo: int) -> uuid.UUID | None:
        return self._add_player(name, telegram_id, elo)
    
    def get_event(self, event_id: uuid.UUID) -> dict | None:
        return self._get_event(event_id)
   
    def get_event_id(self, inline_id: uuid.UUID) -> uuid.UUID | None:
        return self._get_event_id(inline_id)
    
    def get_messages(self, event_id: uuid.UUID) -> List[str] | None:
        return self._get_messages(event_id)
  
    def get_player_id(self, telegram_id: int) -> uuid.UUID | None:
        return self._get_player_id(telegram_id)
    
    def is_player_registered(self, player_id: uuid.UUID, event_id: uuid.UUID) -> bool:
        return self._is_player_registered(player_id, event_id)
    
    # def is_player_registered(self, player_id, event_id) -> bool:
    #     return self._is_player_registered(player_id, event_id)

    def register_player(self, player_id: uuid.UUID, event_id: uuid.UUID) -> bool | None:
        return self._register_player(player_id, event_id)
    
    def registered_players(self, event_id: uuid.UUID) -> bool | None:
        return self._registered_players(event_id)
    
    def remove_event(self, session: Session, event_id: uuid.UUID):
        raise NotImplementedError('delete messages from table')
        with self.session() as session:            
            try:
                logger.debug(f'Удаление из базы: event_id = {event_id}')
                event = session.query(Event).filter(Event.evnet_id == event_id).first()
                if not event:
                    return
                session.delete(event)
                session.commit()
                logger.debug('Commit')
            except Exception as e:
                session.rollback()
                logger.debug('Rollback')

    def unregister_player(self, player_id: uuid.UUID, event_id: uuid.UUID) -> bool | None:                
        return self._unregister_player(player_id, event_id)

    # def update_event_text(self, event_id: uuid.UUID, new_text: str) -> None:
    #     return self._update_event_text(event_id, new_text)    
    
    @with_commit
    def _add_event(self, session: Session, event_id: uuid.UUID, owner_id: str, event_title: str) -> uuid.UUID | None:
        new_event = Event(
            event_id=event_id,
            owner_id=owner_id,
            event_title=event_title
        )
        session.add(new_event)
        return event_id    
    
    @with_commit
    def _add_event_message(self, session: Session, inline_id: uuid.UUID, message_id: uuid.UUID, event_id: uuid.UUID) -> uuid.UUID | None:
        new_message = Message(inline_id=inline_id, message_id=message_id, event_id=event_id)
        session.add(new_message)
        return inline_id    
    
    @with_commit
    def _add_player(self, session: Session, name: str, telegram_id: int, elo: int) -> uuid.UUID | None:
        id = uuid.uuid4()
        new_player = Player(
            player_id=id,
            player_name=name,
            telegram_id=telegram_id,
            elo=elo
        )
        session.add(new_player)
        return id    
    
    @with_session
    def _get_event(self, session: Session, event_id: uuid.UUID) -> dict | None:
        event = session.query(Event).filter_by(event_id=event_id).first()
        return model_to_dict(event)
    
    @with_session
    def _get_event_id(self, session: Session, inline_id: uuid.UUID) -> uuid.UUID | None:
        rec = session.query(Message).filter_by(inline_id=inline_id).first()
        if not rec:
            return None
        return rec.event_id
    
    @with_session
    def _get_messages(self, session: Session, event_id: uuid.UUID) -> List[str] | None:
        event = session.query(Event).filter_by(event_id=event_id).first()        
        return [message.message_id for message in event.messages]
    
    @with_session
    def _get_player_id(self, session: Session, telegram_id: int) -> uuid.UUID | None:
        rec = session.query(Player).filter_by(telegram_id=telegram_id).first()
        if not rec:
            return None
        return rec.player_id            
    
    @with_session
    def _is_player_registered(self, session: Session, player_id: uuid.UUID, event_id: uuid.UUID) -> bool:
        rec = session.query(EventPlayer).filter_by(player_id=player_id, event_id=event_id).first()
        return bool(rec)
    
    @with_commit
    def _register_player(self, session: Session, player_id: uuid.UUID, event_id: uuid.UUID) -> bool | None:
        link = EventPlayer(player_id=player_id, event_id=event_id)
        session.add(link)
        return True
    
    @with_session
    def _registered_players(self, session: Session, event_id: uuid.UUID) -> List[dict] | None:
        event = session.query(Event).filter_by(event_id=event_id).first()        
        return [model_to_dict(player.player) for player in event.players]
    
    # @with_session
    # def is_player_registered(self, session: Session, player_id, event_id) -> bool:
    #     rec = session.query(EventPlayer).filter(
    #         EventPlayer.event_id == event_id,
    #         EventPlayer.player_id == player_id
    #     ).first()
    #     return bool(rec)

    # @with_commit
    # def _update_event_text(self, session: Session, event_id: uuid.UUID, new_text: str) -> None:
    #     event = session.query(Event).filter(Event.event_id == event_id).first()
    #     event.event_text = new_text
    #     return new_text
    @with_commit
    def _unregister_player(self, session: Session, player_id: uuid.UUID, event_id: uuid.UUID) -> bool | None:                
        link = session.query(EventPlayer).filter_by(player_id=player_id, event_id=event_id).first()
        session.delete(link)
        return True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, sxc_val, exc_tb):
        pass