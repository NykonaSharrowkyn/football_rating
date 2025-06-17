import logging
import pandas as pd

from enum import IntEnum, unique
from functools import wraps

from sqlalchemy import create_engine, Column, UUID, String, Integer, ForeignKey, func, exists, desc, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from typing import Callable, List, Tuple, Dict

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Owner(Base):
    __tablename__ = 'owners'
    id = Column(Integer, primary_key=True) # telegram id
    url = Column(String)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)    # active url
    
class Admin(Base)    :
    __tablename__ = 'admins'
    id = Column(Integer, ForeignKey('users.id'))
    url = Column(String, ForeignKey('owners.url'))

def model_to_dict(model):
    if model is None:
        return None
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}

def with_session(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.session() as session:
            try:
                return func(self, *args, session=session, **kwargs)
            except Exception as e:
                logger.debug(f'Ошибка в {func.__name__}: {str(e)}')
                logger.debug(args)
                logger.debug(kwargs)
                raise e
    return wrapper

def with_commit(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.session() as session:
            try:
                result = func(self, *args, session=session, **kwargs)
                session.commit()
                return result
            except Exception as e:
                logger.debug(f'Ошибка в {func.__name__}: {str(e)}')
                logger.debug(args)
                logger.debug(kwargs)
                session.rollback()
                raise e
    return wrapper

class RecordNotFound(LookupError):
    pass

# class OwnerExists(LookupError):
#     pass

class AdminRequired(PermissionError):
    pass

@unique
class UserRole(IntEnum):
    OWNER = 0,
    ADMIN = 1,
    USER = 2

class FootballDatabase:
    def __init__(self, db_path: str):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, sxc_val, exc_tb):
        pass
