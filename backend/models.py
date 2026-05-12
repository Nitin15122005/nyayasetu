from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="lawyer")  # admin, lawyer, client
    phone = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True)

    cases = relationship("Case", back_populates="lawyer")
    tasks = relationship("Task", back_populates="assignee")
    calendar_events = relationship("CalendarEvent", back_populates="user")

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    cnr_number = Column(String, unique=True, index=True, nullable=True)
    title = Column(String, index=True)
    status = Column(String, default="Active")
    court_name = Column(String)
    client_name = Column(String)
    lawyer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    lawyer = relationship("User", back_populates="cases")
    hearings = relationship("Hearing", back_populates="case")
    tasks = relationship("Task", back_populates="case")

class Hearing(Base):
    __tablename__ = "hearings"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    hearing_date = Column(DateTime)
    purpose = Column(String)
    notes = Column(String, nullable=True)

    case = relationship("Case", back_populates="hearings")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(String, nullable=True)
    due_date = Column(DateTime)
    is_completed = Column(Boolean, default=False)

    case = relationship("Case", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    lawyer_id = Column(Integer, ForeignKey("users.id"))
    client_name = Column(String)
    amount = Column(Float)
    status = Column(String, default="Pending")  # Pending, Paid, Overdue
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class StatutoryAct(Base):
    __tablename__ = "statutory_acts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(String)
    jurisdiction = Column(String, index=True)
    category = Column(String, index=True)
    year = Column(String)
    url = Column(String)
    doc_id = Column(String, unique=True, index=True)
    act_type = Column(String)


# ══════════════════════════════════════════════════════════════════════════════
# CALENDAR EVENT MODEL (NEW)
# ══════════════════════════════════════════════════════════════════════════════
class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    event_type = Column(String, default="hearing")  # hearing, deadline, meeting, reminder
    event_date = Column(String, nullable=False)      # YYYY-MM-DD
    event_time = Column(String, nullable=True)       # HH:MM
    court = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    matter_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="calendar_events")