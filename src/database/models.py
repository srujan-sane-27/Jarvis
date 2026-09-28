from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AuditLog(Base):
    """Tracks all security-critical operations, authentication attempts, and tool dispatches."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(50), nullable=False)  # AUTH_SUCCESS, AUTH_FAIL, TOOL_EXEC, SYSTEM_LOCK
    agent_name = Column(String(50), default="JARVIS")
    details = Column(Text, nullable=True)
    status = Column(String(20), default="INFO")  # SUCCESS, FAILED, DENIED, WARNING


class ConversationMessage(Base):
    """Persists chat turns between User and JARVIS for conversational continuity."""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), default="default", index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    voice_used = Column(Boolean, default=False)


class EmailCache(Base):
    """Local offline cache for email summaries to minimize IMAP network hits."""
    __tablename__ = "email_cache"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, index=True)
    sender = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    date_received = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False)


class UserSetting(Base):
    """Key-value user preferences (e.g. customized voice speed, preferred news categories)."""
    __tablename__ = "user_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
