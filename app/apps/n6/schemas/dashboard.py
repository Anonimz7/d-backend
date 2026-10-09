from __future__ import annotations
"""Dashboard aggregates (menus: Dashboard Coach, Dashboard Head Coach).

Read-only rollups built from the tables the coach screens already write:
clients, attendance, schedules, commissions, athlete notes and schedule
requests. No new writes here - this module only reads and sums.
"""


from datetime import date, datetime

from pydantic import BaseModel, Field


class ClientCount(BaseModel):
    total: int = 0
    aktif: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)


class ClientProgressItem(BaseModel):
    client_id: int
    name: str
    pct: float = 0.0
    sessions: int = 0
    hadir: int = 0
    last_session: date | None = None
    note: str | None = None


class TodaySlot(BaseModel):
    start_time: str
    end_time: str | None = None
    location: str | None = None
    training_category: str | None = None
    note: str | None = None


class CommissionInfo(BaseModel):
    period: str
    gross: float = 0.0
    amount: float = 0.0
    paid: bool = False
    rate: float = 0.0


class CoachDashboard(BaseModel):
    """GET /dashboards/coach/me"""

    coach_id: int
    coach_name: str | None = None
    clients: ClientCount = Field(default_factory=ClientCount)
    progress: list[ClientProgressItem] = Field(default_factory=list)
    today_schedule: list[TodaySlot] = Field(default_factory=list)
    commission: CommissionInfo | None = None


class TeamCoachItem(BaseModel):
    coach_id: int
    name: str
    client_count: int = 0
    attendance_pct: float = 0.0
    rating: float | None = None


class ActivityItem(BaseModel):
    type: str
    label: str
    at: datetime | None = None
    client_id: int | None = None
    client_name: str | None = None
    coach_name: str | None = None


class AttendanceTrend(BaseModel):
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)


class HeadcoachDashboard(BaseModel):
    """GET /dashboards/headcoach/team"""

    coaches: list[TeamCoachItem] = Field(default_factory=list)
    client_status: dict[str, int] = Field(default_factory=dict)
    attendance_trend: AttendanceTrend = Field(default_factory=AttendanceTrend)
    activities: list[ActivityItem] = Field(default_factory=list)


class ClientProgressSessions(BaseModel):
    total: int = 0
    hadir: int = 0
    pct: float = 0.0


class ClientReport(BaseModel):
    pace_target: str | None = None
    intensity: int | None = None
    note: str | None = None
    distance_total: float | None = None


class SessionHistoryItem(BaseModel):
    session_on: date
    status: str
    note: str | None = None


class ClientProgress(BaseModel):
    """GET /dashboards/clients/{id}/progress"""

    client_id: int
    name: str
    sessions: ClientProgressSessions = Field(default_factory=ClientProgressSessions)
    report: ClientReport = Field(default_factory=ClientReport)
    history: list[SessionHistoryItem] = Field(default_factory=list)
