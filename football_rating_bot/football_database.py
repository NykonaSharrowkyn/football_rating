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

class OwnerExists(LookupError):
    pass

# class AdminRequired(PermissionError):
#     pass

@unique
class UserRole(IntEnum):
    OWNER = 0,
    ADMIN = 1,
    USER = 2

class FootballDatabase:  
    NOT_FOUND = 'Пользователь {} не найден'
    
    def __init__(self, db_path: str):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, sxc_val, exc_tb):
        pass

    def add_owner(self, id: int, url: str):
        self._add_owner(id, url)
       
    def get_owner(self, id: int) -> Owner:
        owner = self._get_owner(id)
        if not owner:
            raise RecordNotFound(self.NOT_FOUND.format(id))
        return owner
    
    def get_user(self, id: int) -> User:
        user = self._get_user(id)
        if not user:
            raise RecordNotFound(self.NOT_FOUND.format(id))
        return user
    
    def get_user_by_name(self, name: str) -> User:
        user = self._get_user_by_name(name)
        if not user:
            raise RecordNotFound(self.NOT_FOUND.format(name))
        return user    
    
    def is_admin(self, id: int, url: str) -> bool:
        return self._is_admin(id, url)
    
    def update_admin(self, admin_id: int, url: str, state: bool):
        self._update_admin(admin_id, url, state)

    def update_user(self, id: int, name: str, url: str):
        self._update_user(id, name, url)

    @with_commit
    def _add_owner(self, id: int, url: str, session: Session):
        owner = session.query(Owner).filter_by(id=id).first()
        if owner:
            raise OwnerExists(f'Владелец {id} уже существует')
        owner = Owner(id=id, url=url)
        session.add(owner)

    @with_session
    def _get_owner(self, id: int, session: Session):
        return session.query(Owner).filter_by(id=id).first()
    
    @with_session
    def _get_user(self, id: int, session: Session):
        return session.query(User).filter_by(id=id).first()
    
    @with_session
    def _get_user_by_name(self, name: str, session: Session):
        return session.query(User).filter_by(name=name).first()
    
    @with_session
    def _is_admin(self, id: int, url: str, session: Session) -> bool:
        return session.query(User).filter_by(id=id, url=url).first() is not None
    
    @with_commit
    def _update_admin(self, admin_id: int, url: str, state: bool, session: Session):
        admin = session.query(Admin).filter_by(id=admin_id, url=url).first()
        if state and not admin:
            admin = Admin(id=admin_id, url=url)
            session.add(admin)
        elif not state and admin:
            session.delete(admin)

    @with_commit
    def _update_user(self, id: int, name: str, url: str, session: Session):
        user = User(id=id, name=name, url=url)
        session.merge(user)
        session.commit()
