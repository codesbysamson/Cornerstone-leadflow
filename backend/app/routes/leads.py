from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lead, LeadNote
from app.schemas import (
    FollowUpClear,
    FollowUpSet,
    LeadCreate,
    LeadRead,
    LeadStatusUpdate,
    NoteCreate,
    NoteRead,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _require_lead(lead_id: int, db: Session) -> Lead:
    """Loads a lead or raises 404.

    The CRM activity and follow-up routes all need the same check, and
    returning a fresh error per route repeated it four times.
    """
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )
    return lead


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("", response_model=list[LeadRead])
def list_leads(db: Session = Depends(get_db)) -> list[Lead]:
    # Newest first. Lead id is a tiebreaker so rows written in the same instant
    # still have a deterministic order.
    result = db.execute(select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc()))
    return list(result.scalars().all())


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> Lead:
    return _require_lead(lead_id, db)


@router.post("/{lead_id}/status", response_model=LeadRead)
def update_lead_status(
    lead_id: int, payload: LeadStatusUpdate, db: Session = Depends(get_db)
) -> Lead:
    lead = _require_lead(lead_id, db)

    lead.status = payload.status.value
    db.commit()
    db.refresh(lead)
    return lead


# ---------------------------------------------------------------------------
# Activity notes
#
# Notes are a separate append-only collection rather than part of LeadRead, so
# the lead list does not carry the whole history of every lead on every load.
# ---------------------------------------------------------------------------


@router.get("/{lead_id}/notes", response_model=list[NoteRead])
def list_notes(lead_id: int, db: Session = Depends(get_db)) -> list[LeadNote]:
    _require_lead(lead_id, db)

    result = db.execute(
        select(LeadNote)
        .where(LeadNote.lead_id == lead_id)
        # Newest first, matching the lead list. Id is the tiebreaker so notes
        # written in the same instant still have a deterministic order.
        .order_by(LeadNote.created_at.desc(), LeadNote.id.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/{lead_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED
)
def create_note(
    lead_id: int, payload: NoteCreate, db: Session = Depends(get_db)
) -> LeadNote:
    _require_lead(lead_id, db)

    note = LeadNote(lead_id=lead_id, body=payload.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# ---------------------------------------------------------------------------
# Next follow-up
#
# One endpoint covers set, reschedule and clear, so CORS stays on GET and POST
# and a reschedule is just a second POST of the same shape. The request is a
# discriminated union: either a follow-up or a clear instruction, never both.
# ---------------------------------------------------------------------------


@router.post("/{lead_id}/follow-up", response_model=LeadRead)
def set_follow_up(
    lead_id: int,
    payload: Annotated[FollowUpSet | FollowUpClear, Body()],
    db: Session = Depends(get_db),
) -> Lead:
    lead = _require_lead(lead_id, db)

    if isinstance(payload, FollowUpClear):
        # Both columns are cleared together so a lead can never be left with a
        # date and no action to describe it.
        lead.next_follow_up_at = None
        lead.next_follow_up_action = None
    else:
        lead.next_follow_up_at = payload.due_at
        lead.next_follow_up_action = payload.action

    db.commit()
    db.refresh(lead)
    return lead
