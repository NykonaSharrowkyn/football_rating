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
    owner_id = Column(Integer, primary_key=True) # telegram id
    active_id = Column(Integer, default=0)

class Group(Base):
    __tablename__ ='groups'
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey('owners.id'))

class Player(Base):
    __tablename__ = 'players'
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    elo = Column(Integer)
    matches = Column(Integer)
    owner_id = Column(Integer, ForeignKey('owners.id'))    
    group_id = Column(Integer, ForeignKey('groups.id'))    

class JoinUser(Base):
    __tablename__ = 'joined'
    user_id = Column(Integer, primary_key=True)
    owner_id = Column(Integer)
    role = Column(Integer)

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    user_name = Column(String)

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

class AdminRequired(LookupError):
    pass

@unique
class UserRole(IntEnum):
    ADMIN = 0,
    USER = 1

class FootballDatabase:
    def __init__(self, db_path: str):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, sxc_val, exc_tb):
        pass

    def add_admin(self, owner_id: int, name: str, state: bool):
        return self._add_admin(owner_id, name, state)
    
    def add_player(self, owner_id: int, name: str, elo: int):
        return self._add_player(owner_id, name, elo)

    def add_user(self, user_id: int, user_name: str):
        return self._add_user(user_id, user_name)    

    def get_groups(self, owner_id: int) -> List[str]:
        return self._get_groups(owner_id)

    def get_players(self, owner_id: int) -> pd.DataFrame:
        return self._get_players(self, owner_id)
    
    def join_to_user(self, user_id: int, name: str, state: bool):
        return self._join_to_user(user_id, name, state)
    
    def rename_player(self, owner_id: int, old_name: str, new_name: str):
        return self._rename_player(owner_id, old_name, new_name)

    def select_group(self, owner_id: int, name: str):
        return self._select_group(owner_id, name)
    
    def update_players(self, owner_id: int, new_data: Dict[str, Tuple[int, int]]):
        return self._update_players(owner_id, new_data)

    @with_commit
    def _add_admin(self, owner_id: int, name: str, state: bool, session: Session):
        user = session.query(User).filter_by(user_name=name).first()
        if not user:
            raise RecordNotFound()
        user_id = user.user_id
        user = session.query(JoinUser).filter_by(user_id=user_id, owner_id=owner_id).first()
        if not user:
            raise RecordNotFound()
        if state:
            user.role = UserRole.ADMIN
        else:
            user.role = UserRole.USER
        
        
    @with_commit
    def _add_player(self, owner_id: int, name: str, elo: int, session: Session):
        owner_id = self._change_user(owner_id, UserRole.ADMIN, session)
        owner = session.query(Owner).filter_by(id=owner_id).first()
        if not owner:
            raise RecordNotFound()
        new_player = Player(name=name, elo=elo, owner_id=owner_id, group_id=owner.active_id)
        session.add(new_player)

    @with_commit
    def _add_user(self, user_id: int, user_name: str, session: Session):
        user = session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.user_name = user_name
        else:
            new_user = User(user_id=user_id, user_name=user_name)
            session.add(new_user)
    
    @with_session
    def _change_user(self, user_id: int, required_role: UserRole, session: Session) -> int:
        # проверяем, присоединен ли user к другому
        user = session.query(JoinUser).filter_by(user_id=user_id).first()
        if not user:
            return user_id
        if required_role == UserRole.ADMIN and user.role == UserRole.USER:
            raise AdminRequired()
        return user.owner_id
    
    @with_session
    def _get_groups(self, owner_id: int, session: Session) ->  List[str]:
        owner_id = self._change_user(owner_id, UserRole.USER, session)
        groups = session.query(Group).filter_by(owner_id=owner_id).all()
        return [group.name for group in groups]    
    
    @with_session
    def _get_players(self, owner_id: int, session: Session) -> pd.DataFrame:
        owner_id = self._change_user(owner_id, UserRole.USER, session)
        players = (
            session.query(Player)
            .join(Owner)
            .filter(Player.owner_id == owner_id, Player.group_id == Owner.active_id)
        ).order_by(desc(Player.elo)).all()
        return pd.DataFrame([model_to_dict(player) for player in players])
    
    @with_commit
    def _join_to_user(self, user_id: int, name: str, state: bool, session: Session):
        owner = session.query(User).filter_by(user_name=name).first()
        if not owner:
            raise RecordNotFound()
        if state:
            if session.query(exists().where(JoinUser.user_id == user_id, JoinUser.owner_id == owner.user_id)):
                return
            new_user = JoinUser(user_id=user_id, owner_id=owner.user_id, role=UserRole.USER)
            session.add(new_user)
        else:
            stmt = delete(JoinUser).where(JoinUser.user_id == user_id, JoinUser.owner_id == owner.user_id)
            session.execute(stmt)

    @with_commit
    def _rename_player(self, owner_id: int, old_name: str, new_name: str, session: Session):
        owner_id = self._change_user(owner_id, UserRole.ADMIN, session)
        owner = session.query(Owner).filter_by(owner_id=owner_id).first()
        player = session.query(Player).filter_by(owner_id=owner_id, group_id=owner.active_id, name=old_name).first()
        if not player:
            raise RecordNotFound()
        player.name = new_name

    @with_commit
    def _select_group(self, owner_id: int, name: str, session: Session):
        owner_id = self._change_user(owner_id, UserRole.ADMIN, session)
                    
        if not session.query(exists().where(Owner.owner_id == owner_id)):
            new_owner = Owner(id=owner_id)
            session.add(new_owner)
        if not session.query(exists().where(Group.name == name)):
            new_group = Group(name=name, owner_id=owner_id)
            session.add(new_group)
        session.commit()
        new_owner.active_id = new_group.id

    @with_commit
    def _update_players(self, owner_id: int, new_data: Dict[str, Tuple[int, int]], session: Session):
        owner_id = self._change_user(owner_id, UserRole.ADMIN, session)

        owner = session.query(Owner).filter_by(owner_id=owner_id).first()

        for name in new_data:
            elo, mathces = new_data[name]
            player = session.query(Player).filter_by(owner_id=owner_id, group_id=owner.active_id).first()
            player.elo = elo
            player.matches = mathces