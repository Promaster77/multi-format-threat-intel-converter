"""SQLAlchemy tables + Pydantic v2 schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from database import Base


def _id() -> str:
    return str(uuid.uuid4())


# ---------- SQLAlchemy tables ----------------------------------------------


class Source(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True, default=_id)
    raw_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=_id)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    params_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class Artefact(Base):
    __tablename__ = "artefacts"
    id = Column(String, primary_key=True, default=_id)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    output_type = Column(String, nullable=False)
    content_json = Column(Text, nullable=True)
    raw_output = Column(Text, nullable=True)
    error_msg = Column(Text, nullable=True)
    model_id = Column(String, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ---------- Pydantic schemas ----------------------------------------------


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    raw_text: str


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_id: str
    output_types: list[str]
    tone: str = "formal"
    audience: str = "technical"
    force_failure_for: list[str] = []  # demo hook: route these types to a 500-only URL


class ArtefactOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    output_type: str
    content: dict | None
    status: str
    error_msg: str | None


class JobOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    status: str
    artefacts: list[ArtefactOut]
    created_at: datetime