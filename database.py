import hashlib
from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.future import select

from config import settings


Base = declarative_base()


class User(Base):
    """User model for storing maternal health information."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    phone_hash = Column(String, unique=True, index=True)
    language = Column(String, default="en")
    pregnancy_due_date = Column(Date, nullable=True)
    pregnancy_weeks = Column(Integer, nullable=True)
    last_interaction = Column(DateTime)
    history = Column(JSON, default=list)  # list of {"role": str, "content": str}, last 8-10


# Create async engine
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Create async session maker
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(phone: str):
    """Get existing user or create new one based on phone number."""
    phone_hash = hashlib.sha256(phone.encode()).hexdigest()
    
    async with AsyncSessionLocal() as session:
        # Query by phone_hash
        result = await session.execute(
            select(User).where(User.phone_hash == phone_hash)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                phone_hash=phone_hash, 
                last_interaction=datetime.utcnow(),
                history=[]
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user


async def update_user(phone_hash: str, **kwargs):
    """Update user fields."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.phone_hash == phone_hash)
        )
        user = result.scalar_one_or_none()
        
        if user:
            for k, v in kwargs.items():
                setattr(user, k, v)
            await session.commit()


async def append_history(phone_hash: str, role: str, content: str):
    """Append message to user's conversation history."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.phone_hash == phone_hash)
        )
        user = result.scalar_one_or_none()
        
        if user:
            history = user.history or []
            history.append({"role": role, "content": content})
            user.history = history[-10:]  # Keep last 10 messages
            user.last_interaction = datetime.utcnow()
            await session.commit()
