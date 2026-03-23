"""Audit API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLooseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class AuditStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AuditEventResponse(AuditLooseModel):
    id: str
    tenant_id: str | None
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    integrity_hash: str
    ip_address: str | None
    user_agent: str | None
    ts: datetime


class AuditVerifyResponse(AuditStrictModel):
    verified: bool
    id: str
    reason: str | None = None
