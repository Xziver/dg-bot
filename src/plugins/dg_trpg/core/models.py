from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    user_id: str
    username: str
    api_key: str | None = None


class CMYKValues(BaseModel):
    C: int = 0
    M: int = 0
    Y: int = 0
    K: int = 0


class AbilityInfo(BaseModel):
    id: str
    name: str
    color: str
    description: str = ""


class BuffInfo(BaseModel):
    id: str
    name: str
    expression: str = ""
    buff_type: str = ""
    remaining_rounds: int = -1


class GhostInfo(BaseModel):
    id: str
    name: str
    hp: int = 0
    max_hp: int = 0
    mp: int = 0
    max_mp: int = 0
    cmyk: CMYKValues = Field(default_factory=CMYKValues)
    abilities: list[AbilityInfo] = Field(default_factory=list)
    buffs: list[BuffInfo] = Field(default_factory=list)


class PatientInfo(BaseModel):
    id: str
    name: str
    soul_color: str = ""
    gender: str = ""
    age: int | None = None
    identity: str = ""


class CharacterInfo(BaseModel):
    patient: PatientInfo | None = None
    ghost: GhostInfo | None = None


class RollDetail(BaseModel):
    dice_count: int = 0
    dice_type: int = 6
    results: list[int] = Field(default_factory=list)
    total: int = 0
    success: bool | None = None


class StateChange(BaseModel):
    entity_type: str = ""
    entity_id: str = ""
    field: str = ""
    old_value: str = ""
    new_value: str = ""


class EngineResult(BaseModel):
    success: bool = True
    event_type: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    narrative: str | None = None
    state_changes: list[StateChange] = Field(default_factory=list)
    rolls: list[RollDetail] = Field(default_factory=list)
    error: str | None = None


class EventDefinition(BaseModel):
    id: str
    name: str
    expression: str = ""
    color_restriction: str | None = None


class SessionInfo(BaseModel):
    id: str
    location: str = ""
    location_id: str = ""
    players: list[dict[str, Any]] = Field(default_factory=list)
    status: str = ""
    current_events: list[EventDefinition] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    id: str = ""
    event_type: str = ""
    timestamp: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class ItemDefinition(BaseModel):
    id: str
    name: str
    description: str = ""
    effects: list[dict[str, Any]] = Field(default_factory=list)
    item_type: str = ""


class InventoryItem(BaseModel):
    item_def_id: str = ""
    name: str = ""
    count: int = 1
    description: str = ""


class CommRequest(BaseModel):
    id: str
    initiator_id: str = ""
    initiator_name: str = ""
    target_id: str = ""
    target_name: str = ""
    status: str = ""


class RegionInfo(BaseModel):
    id: str
    code: str = ""
    name: str = ""
    description: str = ""


class LocationInfo(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    region_id: str = ""
