from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codereview_ai.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True)
    repo_name = Column(String)
    pr_number = Column(Integer)
    title = Column(String)
    author = Column(String)
    state = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    reviews = relationship("Review", back_populates="pull_request")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"))
    review_status = Column(String)  # completed, failed, pending
    feedback = Column(JSON)  # List of JSON objects: {severity, line, fix_suggestion, comment}
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    pull_request = relationship("PullRequest", back_populates="reviews")

class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String)
    bug_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    avg_review_time = Column(Integer)  # in seconds
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    # Create tables
    init_db()
    print("Database initialized.")
