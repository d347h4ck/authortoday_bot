from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from models import Base

from sqlalchemy.orm import sessionmaker
from config import config

psql_url = f'postgresql+asyncpg://{config["db"]["user"]}:{config["db"]["password"]}@postgres_db:{config["db"]["port"]}/{config["db"]["db"]}'
print(psql_url)
engine = create_async_engine(psql_url)

async_session = sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )

async def recreate_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)