"""单元测试 — src/plugins/dg_trpg/core/formatters.py

覆盖范围: 所有 format_* 函数的输出格式与边界情况。
测试策略: 断言关键片段出现在输出中，而非做整串精确匹配，
          以便在格式微调时不需要逐一更新断言。
"""
from __future__ import annotations

import pytest

from src.plugins.dg_trpg.core.formatters import (
    format_abilities,
    format_buff_list,
    format_character,
    format_character_list,
    format_comm_list,
    format_engine_result,
    format_event_check,
    format_event_list,
    format_inventory,
    format_item_definitions,
    format_location_list,
    format_location_players,
    format_region_list,
    format_roll,
    format_session_info,
    format_state_changes,
    format_timeline,
)


# ---------------------------------------------------------------------------
# format_roll
# ---------------------------------------------------------------------------

class TestFormatRoll:
    def test_basic_with_results(self):
        data = {"expression": "2d6+3", "results": [3, 4], "total": 10}
        out = format_roll(data)
        assert "2d6+3" in out
        assert "10" in out
        assert "🎲" in out

    def test_no_results_fallback(self):
        data = {"expression": "d100", "results": [], "total": 42}
        out = format_roll(data)
        assert "42" in out

    def test_individual_rolls_key(self):
        """兼容 individual_rolls 字段名。"""
        data = {"expression": "2d6", "individual_rolls": [2, 5], "total": 7}
        out = format_roll(data)
        assert "7" in out


# ---------------------------------------------------------------------------
# format_character
# ---------------------------------------------------------------------------

class TestFormatCharacter:
    def _full_char(self):
        return {
            "patient": {"name": "张三", "soul_color": "C"},
            "ghost": {
                "name": "影子",
                "hp": 10,
                "max_hp": 15,
                "mp": 5,
                "max_mp": 10,
                "cmyk": {"C": 2, "M": 1, "Y": 0, "K": 0},
                "abilities": [{"name": "心灵感应", "color": "C"}],
                "buffs": [{"name": "护盾", "expression": "+2", "remaining_rounds": 3}],
            },
        }

    def test_patient_line(self):
        out = format_character(self._full_char())
        assert "张三" in out
        assert "C" in out  # soul_color

    def test_ghost_hp_mp(self):
        out = format_character(self._full_char())
        assert "影子" in out
        assert "10/15" in out
        assert "5/10" in out

    def test_cmyk_line(self):
        out = format_character(self._full_char())
        assert "C2" in out or "C: 2" in out or "C2 " in out

    def test_abilities_shown(self):
        out = format_character(self._full_char())
        assert "心灵感应" in out

    def test_buffs_shown(self):
        out = format_character(self._full_char())
        assert "护盾" in out
        assert "3" in out  # remaining_rounds

    def test_empty_ghost(self):
        data = {"patient": {"name": "李四", "soul_color": "M"}}
        out = format_character(data)
        assert "李四" in out

    def test_empty_dict(self):
        out = format_character({})
        assert "角色信息" in out  # header still present


# ---------------------------------------------------------------------------
# format_character_list
# ---------------------------------------------------------------------------

class TestFormatCharacterList:
    def test_empty_list(self):
        out = format_character_list([])
        assert "没有" in out or "无" in out

    def test_single_character(self):
        out = format_character_list([
            {"name": "小明", "patient_id": "p1", "type": "patient", "soul_color": "C"}
        ])
        assert "小明" in out
        assert "p1" in out

    def test_multiple_characters_numbered(self):
        chars = [
            {"name": "角色A", "id": "a1"},
            {"name": "角色B", "id": "b2"},
        ]
        out = format_character_list(chars)
        assert "1." in out
        assert "2." in out


# ---------------------------------------------------------------------------
# format_event_check
# ---------------------------------------------------------------------------

class TestFormatEventCheck:
    def _success_data(self):
        return {
            "event_name": "心灵感应",
            "color": "C",
            "effective_value": 5,
            "player_total": 8,
            "target_total": 6,
            "check_success": True,
            "player_rolls": [3, 5],
        }

    def _failure_data(self):
        return {
            "event_name": "黑暗感知",
            "color": "K",
            "effective_value": 2,
            "player_total": 3,
            "target_total": 7,
            "check_success": False,
            "player_rolls": [1, 2],
        }

    def test_success_marker(self):
        out = format_event_check(self._success_data())
        assert "✅" in out
        assert "检定成功" in out

    def test_failure_marker(self):
        out = format_event_check(self._failure_data())
        assert "❌" in out
        assert "检定失败" in out

    def test_failure_shows_reroll_hint(self):
        out = format_event_check(self._failure_data())
        assert "/re" in out or "/hre" in out

    def test_event_name_in_output(self):
        out = format_event_check(self._success_data())
        assert "心灵感应" in out

    def test_target_rolls_shown_when_present(self):
        data = {**self._success_data(), "target_rolls": {"expression": "2d6", "individual_rolls": [3, 3]}}
        out = format_event_check(data)
        assert "🎯" in out


# ---------------------------------------------------------------------------
# format_buff_list
# ---------------------------------------------------------------------------

class TestFormatBuffList:
    def test_empty(self):
        out = format_buff_list([])
        assert "没有" in out or "无" in out

    def test_permanent_buff(self):
        out = format_buff_list([{"name": "永久护盾", "expression": "+5", "remaining_rounds": -1}])
        assert "永久" in out
        assert "永久护盾" in out

    def test_finite_rounds(self):
        out = format_buff_list([{"name": "加速", "expression": "+2", "remaining_rounds": 3}])
        assert "剩余3轮" in out or "3" in out

    def test_multiple_buffs(self):
        buffs = [
            {"name": "护盾", "remaining_rounds": 2},
            {"name": "中毒", "remaining_rounds": -1},
        ]
        out = format_buff_list(buffs)
        assert "护盾" in out
        assert "中毒" in out


# ---------------------------------------------------------------------------
# format_session_info
# ---------------------------------------------------------------------------

class TestFormatSessionInfo:
    def test_basic_info(self):
        data = {
            "session_id": "s-1",
            "location_name": "诊室",
            "status": "active",
            "players": [],
        }
        out = format_session_info(data)
        assert "s-1" in out
        assert "诊室" in out
        assert "active" in out

    def test_no_players(self):
        data = {"session_id": "s-2", "players": []}
        out = format_session_info(data)
        assert "无" in out

    def test_with_players(self):
        data = {
            "session_id": "s-3",
            "players": [{"patient_name": "小明"}, {"patient_name": "小红"}],
        }
        out = format_session_info(data)
        assert "小明" in out
        assert "小红" in out


# ---------------------------------------------------------------------------
# format_timeline
# ---------------------------------------------------------------------------

class TestFormatTimeline:
    def test_empty(self):
        out = format_timeline([])
        assert "暂无" in out

    def test_single_entry(self):
        entries = [
            {
                "created_at": "2024-01-01T12:30:00Z",
                "event_type": "event_check",
                "seq": 1,
                "player_snapshot": {"display_name": "小明"},
                "narrative": "检定通过",
            }
        ]
        out = format_timeline(entries)
        assert "12:30" in out
        assert "小明" in out
        assert "检定" in out

    def test_event_type_label(self):
        entries = [{"event_type": "attack", "created_at": "2024-01-01T10:00:00Z"}]
        out = format_timeline(entries)
        assert "攻击" in out


# ---------------------------------------------------------------------------
# format_engine_result
# ---------------------------------------------------------------------------

class TestFormatEngineResult:
    def test_success_default(self):
        out = format_engine_result({"success": True})
        assert "成功" in out

    def test_failure_shows_error(self):
        out = format_engine_result({"success": False, "error": "HP不足"})
        assert "HP不足" in out or "失败" in out

    def test_narrative_shown(self):
        out = format_engine_result({"success": True, "narrative": "神秘的光芒闪过"})
        assert "神秘的光芒闪过" in out

    def test_state_changes_in_output(self):
        result = {
            "success": True,
            "state_changes": [{"field": "hp", "old_value": "10", "new_value": "7"}],
        }
        out = format_engine_result(result)
        assert "hp" in out
        assert "10" in out
        assert "7" in out


# ---------------------------------------------------------------------------
# format_state_changes
# ---------------------------------------------------------------------------

class TestFormatStateChanges:
    def test_empty_returns_empty(self):
        assert format_state_changes([]) == ""

    def test_arrow_format(self):
        changes = [{"field": "hp", "old_value": "10", "new_value": "5"}]
        out = format_state_changes(changes)
        assert "→" in out
        assert "hp" in out
        assert "10" in out
        assert "5" in out

    def test_multiple_changes(self):
        changes = [
            {"field": "hp", "old_value": "10", "new_value": "5"},
            {"field": "mp", "old_value": "8", "new_value": "6"},
        ]
        out = format_state_changes(changes)
        assert "hp" in out
        assert "mp" in out


# ---------------------------------------------------------------------------
# format_region_list
# ---------------------------------------------------------------------------

class TestFormatRegionList:
    def test_empty(self):
        out = format_region_list([])
        assert "暂无" in out

    def test_with_regions(self):
        regions = [{"code": "R01", "name": "第一区域", "description": ""}]
        out = format_region_list(regions)
        assert "R01" in out
        assert "第一区域" in out


# ---------------------------------------------------------------------------
# format_location_list
# ---------------------------------------------------------------------------

class TestFormatLocationList:
    def test_empty(self):
        out = format_location_list([])
        assert "暂无" in out

    def test_with_locations(self):
        locs = [{"name": "诊室", "description": "安静的房间"}]
        out = format_location_list(locs)
        assert "诊室" in out
        assert "安静的房间" in out


# ---------------------------------------------------------------------------
# format_event_list
# ---------------------------------------------------------------------------

class TestFormatEventList:
    def test_empty(self):
        out = format_event_list([])
        assert "没有" in out or "无" in out

    def test_with_color_restriction(self):
        events = [{"name": "黑暗检定", "expression": "K+2", "color_restriction": "K"}]
        out = format_event_list(events)
        assert "黑暗检定" in out
        assert "K" in out
        assert "限定" in out

    def test_without_color_restriction(self):
        events = [{"name": "通用检定", "expression": "2d6", "color_restriction": None}]
        out = format_event_list(events)
        assert "限定" not in out


# ---------------------------------------------------------------------------
# format_item_definitions
# ---------------------------------------------------------------------------

class TestFormatItemDefinitions:
    def test_empty(self):
        out = format_item_definitions([])
        assert "暂无" in out

    def test_with_items(self):
        items = [{"name": "急救包", "description": "恢复5HP"}]
        out = format_item_definitions(items)
        assert "急救包" in out
        assert "恢复5HP" in out


# ---------------------------------------------------------------------------
# format_abilities
# ---------------------------------------------------------------------------

class TestFormatAbilities:
    def test_empty(self):
        out = format_abilities([])
        assert "没有" in out or "无" in out

    def test_with_ability(self):
        abilities = [{"name": "心灵感应", "color": "C", "description": "感知他人思想"}]
        out = format_abilities(abilities)
        assert "心灵感应" in out
        assert "C" in out
        assert "感知他人思想" in out


# ---------------------------------------------------------------------------
# format_comm_list
# ---------------------------------------------------------------------------

class TestFormatCommList:
    def test_empty(self):
        out = format_comm_list([])
        assert "没有" in out

    def test_with_request(self):
        reqs = [{"id": "req-1", "initiator_patient_name": "小明", "target_patient_name": "小红"}]
        out = format_comm_list(reqs)
        assert "小明" in out
        assert "req-1" in out


# ---------------------------------------------------------------------------
# format_inventory
# ---------------------------------------------------------------------------

class TestFormatInventory:
    def test_empty(self):
        out = format_inventory([])
        assert "空" in out

    def test_single_item_no_count(self):
        out = format_inventory([{"name": "急救包"}])
        assert "急救包" in out

    def test_item_with_count(self):
        out = format_inventory([{"name": "子弹", "count": 5}])
        assert "x5" in out or "5" in out


# ---------------------------------------------------------------------------
# format_location_players
# ---------------------------------------------------------------------------

class TestFormatLocationPlayers:
    def test_empty(self):
        out = format_location_players([])
        assert "没有" in out

    def test_with_player_and_character(self):
        players = [{"username": "Alice", "character_name": "影子"}]
        out = format_location_players(players)
        assert "Alice" in out
        assert "影子" in out
