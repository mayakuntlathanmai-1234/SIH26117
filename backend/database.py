from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "kaizen.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentSession(Base):
    __tablename__ = "document_sessions"
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    status = Column(String, default="pending") # pending, extracting, embedding, completed, error
    mode = Column(String, nullable=True) # direct, rag
    message = Column(Text, nullable=True)
    
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True)
    role = Column(String) # user, ai
    content = Column(Text)
    file_json = Column(Text, nullable=True) # store generated file info as JSON string

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
