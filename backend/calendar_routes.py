"""
Calendar Module for NyayaSetu - SQLAlchemy-based
Drop this into: backend/calendar_routes.py

Provides full CRUD for calendar events with user-scoped data.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from database import get_db
from api import get_current_user

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    event_type: str = Field(default="hearing", pattern="^(hearing|deadline|meeting|reminder)$")
    event_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    event_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    court: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    matter_id: Optional[int] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    event_type: Optional[str] = Field(default=None, pattern="^(hearing|deadline|meeting|reminder)$")
    event_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    event_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    court: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    matter_id: Optional[int] = None


class CalendarEventOut(BaseModel):
    id: int
    title: str
    event_type: str
    event_date: str
    event_time: Optional[str]
    court: Optional[str]
    description: Optional[str]
    matter_id: Optional[int]
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────────────────────────
def event_to_dict(event):
    return {
        "id": event.id,
        "title": event.title,
        "event_type": event.event_type,
        "event_date": event.event_date,
        "event_time": event.event_time,
        "court": event.court,
        "description": event.description,
        "matter_id": event.matter_id,
        "created_at": str(event.created_at),
        "updated_at": str(event.updated_at) if event.updated_at else None
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/events", response_model=CalendarEventOut)
def create_event(
    event: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new calendar event scoped to the current user."""
    db_event = models.CalendarEvent(
        title=event.title,
        event_type=event.event_type,
        event_date=event.event_date,
        event_time=event.event_time,
        court=event.court,
        description=event.description,
        matter_id=event.matter_id,
        user_id=current_user.id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return event_to_dict(db_event)


@router.get("/events")
def list_events(
    year: Optional[int] = None,
    month: Optional[int] = None,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List calendar events for the current user, optionally filtered by year/month/type."""
    query = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.user_id == current_user.id
    )

    if year and month:
        month_str = f"{month:02d}"
        query = query.filter(models.CalendarEvent.event_date.like(f"{year}-{month_str}-%"))
    elif year:
        query = query.filter(models.CalendarEvent.event_date.like(f"{year}-%"))

    if event_type:
        query = query.filter(models.CalendarEvent.event_type == event_type)

    events = query.order_by(
        models.CalendarEvent.event_date.asc(),
        models.CalendarEvent.event_time.asc()
    ).all()

    return [event_to_dict(e) for e in events]


@router.get("/events/{event_id}", response_model=CalendarEventOut)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a single calendar event by ID."""
    event = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.id == event_id,
        models.CalendarEvent.user_id == current_user.id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event_to_dict(event)


@router.put("/events/{event_id}", response_model=CalendarEventOut)
def update_event(
    event_id: int,
    event: CalendarEventUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a calendar event."""
    db_event = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.id == event_id,
        models.CalendarEvent.user_id == current_user.id
    ).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    for field, value in event.model_dump(exclude_unset=True).items():
        setattr(db_event, field, value)

    db.commit()
    db.refresh(db_event)
    return event_to_dict(db_event)


@router.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a calendar event."""
    event = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.id == event_id,
        models.CalendarEvent.user_id == current_user.id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"message": "Event deleted", "id": event_id}


@router.get("/stats/summary")
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get calendar statistics for the current user."""
    today = date.today().isoformat()
    week_later = (date.today() + timedelta(days=7)).isoformat()

    total = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.user_id == current_user.id
    ).count()

    upcoming = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.user_id == current_user.id,
        models.CalendarEvent.event_date >= today
    ).count()

    this_week = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.user_id == current_user.id,
        models.CalendarEvent.event_date >= today,
        models.CalendarEvent.event_date <= week_later
    ).count()

    by_type = db.query(
        models.CalendarEvent.event_type,
        func.count(models.CalendarEvent.id).label("count")
    ).filter(
        models.CalendarEvent.user_id == current_user.id,
        models.CalendarEvent.event_date >= today
    ).group_by(models.CalendarEvent.event_type).all()

    return {
        "total_events": total,
        "upcoming_events": upcoming,
        "this_week": this_week,
        "by_type": {t.event_type: t.count for t in by_type}
    }