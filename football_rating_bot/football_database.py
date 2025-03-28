import logging
import uuid

from sqlalchemy import create_engine, Column, UUID, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'
    evnet_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(String)
    message_id = Column(String)
    event_name = Column(String)

class FootballDatabase:
    def __init__(self, db_path: str):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)

    def add_event(self, event_id: uuid.UUID, owner_id: str, message_id: str, event_name: str):
        with self.session() as session:
            logger.debug(f'Сохранение в базу: event_id = {event_id}, owner_id={owner_id}, message_id={message_id}')
            try:
                new_event = Event(
                    evnet_id=event_id,
                    owner_id=owner_id,
                    message_id=message_id,
                    event_name=event_name
                )                
                session.add(new_event)                
                session.commit()
                logger.debug(f'Commit')
            except Exception as e:
                session.rollback()
                logger.debug(f'Rollback')

    def get_event(self, event_id: uuid.UUID) -> dict | None:
        with self.session() as session:
            try:
                logger.debug(f'Чтение из базы: event_id = {event_id}')
                event = session.query(Event).filter(Event.evnet_id == event_id).first()
                if not event:
                    return None
                event_dict = event._asdict()
                return event_dict
            except Exception as e:
                pass
            
    def remove_event(self, event_id: uuid.UUID):
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
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, sxc_val, exc_tb):
        pass