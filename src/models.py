from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean,  DateTime, func, ForeignKey, Float
from sqlalchemy.orm import relationship


Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    __mapper_args__ = {"eager_defaults": True}
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, nullable=False, unique=True)
    create_date = Column(DateTime, server_default=func.now())
    watch_end_books = relationship('Book', secondary = 'link_watch_end', back_populates='subs_end_users')
    watch_books = relationship('Book', secondary = 'link_watch', back_populates='subs_users')
    watch_disc_books = relationship('Book', secondary = 'link_watch_disc', back_populates='subs_users_disc')

class Book(Base):
    __tablename__ = 'books'
    __mapper_args__ = {"eager_defaults": True}
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, nullable=False, unique=True)
    create_date = Column(DateTime, server_default=func.now())
    status = Column(Boolean)
    title = Column(String(150))
    author_fio = Column(String(200))
    chapter_count = Column(Integer)
    discount = Column(Float, nullable=False)
    subs_end_users = relationship('User', secondary= 'link_watch_end', back_populates='watch_end_books')
    subs_users = relationship('User', secondary= 'link_watch', back_populates='watch_books')
    subs_users_disc = relationship('User', secondary= 'link_watch_disc', back_populates='watch_disc_books')

    def __repr__(self) -> str:
        return f'Book {self.title} from {self.author_fio} with status {self.status} and {self.chapter_count} chapters.'

class LinkWatchEnd(Base):
    __tablename__ = 'link_watch_end'
    __mapper_args__ = {"eager_defaults": True}
    user_id = Column(
      Integer, 
      ForeignKey('users.id'), 
      primary_key = True)

    book_id = Column(
        Integer, 
        ForeignKey('books.id'), 
        primary_key = True)

class LinkWatch(Base):
    __tablename__ = 'link_watch'
    __mapper_args__ = {"eager_defaults": True}
    user_id = Column(
        Integer,
        ForeignKey('users.id'), 
        primary_key = True)

    book_id = Column(
        Integer,
        ForeignKey('books.id'),
        primary_key = True)

class LinkWatchDisc(Base):
    __tablename__ = 'link_watch_disc'
    __mapper_args__ = {"eager_defaults": True}
    user_id = Column(
        Integer,
        ForeignKey('users.id'), 
        primary_key = True)

    book_id = Column(
        Integer,
        ForeignKey('books.id'),
        primary_key = True)