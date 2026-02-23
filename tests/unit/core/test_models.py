"""单元测试 — src/plugins/dg_trpg/core/models.py

覆盖范围: Pydantic 模型的字段默认值、验证、嵌套结构解析。
"""
from __future__ import annotations

import pytest

from src.plugins.dg_trpg.core.models import (
    AbilityInfo,
    BuffInfo,
    CMYKValues,
    CharacterInfo,
    EngineResult,
    EventDefinition,
    GhostInfo,
    PatientInfo,
    PlayerSnapshotInfo,
    RollDetail,
    SessionInfo,
    StateChange,
    UserInfo,
)


class TestCMYKValues:
    def test_defaults_are_zero(self):
        cmyk = CMYKValues()
        assert cmyk.C == 0
        assert cmyk.M == 0
        assert cmyk.Y == 0
        assert cmyk.K == 0

    def test_custom_values(self):
        cmyk = CMYKValues(C=3, M=1, Y=0, K=2)
        assert cmyk.C == 3
        assert cmyk.K == 2


class TestBuffInfo:
    def test_permanent_by_default(self):
        buff = BuffInfo(id="b1", name="护盾")
        assert buff.remaining_rounds == -1

    def test_finite_rounds(self):
        buff = BuffInfo(id="b2", name="加速", remaining_rounds=3)
        assert buff.remaining_rounds == 3

    def test_expression_default_empty(self):
        buff = BuffInfo(id="b3", name="测试")
        assert buff.expression == ""


class TestEngineResult:
    def test_success_defaults(self):
        result = EngineResult()
        assert result.success is True
        assert result.rolls == []
        assert result.state_changes == []
        assert result.error is None

    def test_failure_with_error(self):
        result = EngineResult(success=False, error="HP不足")
        assert result.success is False
        assert result.error == "HP不足"

    def test_narrative_and_state_changes(self):
        change = StateChange(field="hp", old_value="10", new_value="5")
        result = EngineResult(narrative="你受到了伤害", state_changes=[change])
        assert result.narrative == "你受到了伤害"
        assert result.state_changes[0].field == "hp"


class TestStateChange:
    def test_fields(self):
        sc = StateChange(
            entity_type="ghost",
            entity_id="g-1",
            field="hp",
            old_value="10",
            new_value="7",
        )
        assert sc.field == "hp"
        assert sc.old_value == "10"
        assert sc.new_value == "7"


class TestRollDetail:
    def test_defaults(self):
        roll = RollDetail()
        assert roll.dice_count == 0
        assert roll.dice_type == 6
        assert roll.results == []
        assert roll.success is None

    def test_with_results(self):
        roll = RollDetail(dice_count=2, dice_type=6, results=[3, 4], total=7)
        assert roll.total == 7
        assert len(roll.results) == 2


class TestSessionInfo:
    def test_players_list(self):
        session = SessionInfo(
            id="s-1",
            players=[{"patient_name": "小明"}, {"patient_name": "小红"}],
        )
        assert len(session.players) == 2
        assert session.players[0]["patient_name"] == "小明"

    def test_empty_players(self):
        session = SessionInfo(id="s-2")
        assert session.players == []


class TestGhostInfo:
    def test_defaults(self):
        ghost = GhostInfo(id="g1", name="影子")
        assert ghost.hp == 0
        assert ghost.abilities == []
        assert ghost.buffs == []
        assert isinstance(ghost.cmyk, CMYKValues)

    def test_full_ghost(self):
        ghost = GhostInfo(
            id="g2",
            name="幻影",
            hp=15,
            max_hp=20,
            mp=8,
            max_mp=10,
            cmyk=CMYKValues(C=2, M=1, Y=0, K=0),
        )
        assert ghost.hp == 15
        assert ghost.cmyk.C == 2


class TestCharacterInfo:
    def test_both_none_by_default(self):
        char = CharacterInfo()
        assert char.patient is None
        assert char.ghost is None

    def test_with_patient(self):
        patient = PatientInfo(id="p1", name="张三", soul_color="C")
        char = CharacterInfo(patient=patient)
        assert char.patient is not None
        assert char.patient.name == "张三"


class TestEventDefinition:
    def test_color_restriction_optional(self):
        ev = EventDefinition(id="ev-1", name="心灵感应", expression="C+2")
        assert ev.color_restriction is None

    def test_with_color_restriction(self):
        ev = EventDefinition(
            id="ev-2", name="黑暗感知", expression="K+3", color_restriction="K"
        )
        assert ev.color_restriction == "K"


class TestUserInfo:
    def test_api_key_optional(self):
        user = UserInfo(user_id="u1", username="alice")
        assert user.api_key is None

    def test_with_api_key(self):
        user = UserInfo(user_id="u2", username="bob", api_key="secret")
        assert user.api_key == "secret"


class TestPlayerSnapshotInfo:
    def test_defaults(self):
        snap = PlayerSnapshotInfo()
        assert snap.user_id == ""
        assert snap.buffs == []
        assert snap.cmyk is None

    def test_with_buffs(self):
        buff = BuffInfo(id="b1", name="护盾")
        snap = PlayerSnapshotInfo(user_id="u1", buffs=[buff])
        assert len(snap.buffs) == 1
