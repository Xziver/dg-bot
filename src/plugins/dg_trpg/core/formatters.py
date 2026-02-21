from __future__ import annotations

from typing import Any


def format_character(data: dict[str, Any]) -> str:
    lines: list[str] = ["【角色信息】"]

    patient = data.get("patient") or data.get("active_patient") or {}
    ghost = data.get("ghost") or data.get("active_ghost") or {}

    if patient:
        name = patient.get("name", "未知")
        color = patient.get("soul_color", "?")
        lines.append(f"患者: {name} | 灵魂色: {color}")

    if ghost:
        name = ghost.get("name", "未知")
        hp = ghost.get("hp", 0)
        max_hp = ghost.get("hp_max", ghost.get("max_hp", hp))
        mp = ghost.get("mp", 0)
        max_mp = ghost.get("mp_max", ghost.get("max_mp", mp))
        lines.append(f"幽灵: {name} | HP: {hp}/{max_hp} | MP: {mp}/{max_mp}")

        cmyk = ghost.get("cmyk", {})
        if cmyk:
            c = cmyk.get("C", 0)
            m = cmyk.get("M", 0)
            y = cmyk.get("Y", 0)
            k = cmyk.get("K", 0)
            lines.append(f"CMYK: C{c} M{m} Y{y} K{k}")

        abilities = ghost.get("print_abilities", ghost.get("abilities", []))
        if abilities:
            ability_strs = [
                f"{a.get('name', '?')}({a.get('color', '?')})" for a in abilities
            ]
            lines.append(f"能力: {', '.join(ability_strs)}")

        buffs = ghost.get("buffs", [])
        if buffs:
            buff_strs = []
            for b in buffs:
                name_b = b.get("name", "?")
                expr = b.get("expression", "")
                rounds = b.get("remaining_rounds", -1)
                suffix = f", 剩余{rounds}轮" if rounds > 0 else ""
                if expr:
                    buff_strs.append(f"{name_b}({expr}{suffix})")
                else:
                    buff_strs.append(f"{name_b}{suffix}")
            lines.append(f"Buff: {', '.join(buff_strs)}")

    return "\n".join(lines)


def format_character_list(data: list[dict[str, Any]]) -> str:
    if not data:
        return "你还没有任何角色。"
    lines = ["【角色列表】"]
    for i, ch in enumerate(data, 1):
        name = ch.get("name", "未知")
        ch_id = ch.get("id", "?")
        ch_type = ch.get("type", "")
        color = ch.get("soul_color", "")
        type_label = f"[{ch_type}]" if ch_type else ""
        color_label = f" ({color})" if color else ""
        lines.append(f"{i}. {type_label}{name}{color_label} (ID: {ch_id})")
    return "\n".join(lines)


def format_event_check(data: dict[str, Any]) -> str:
    event_name = data.get("event_name", data.get("name", "检定"))
    color = data.get("color", "?")
    effective = data.get("effective_value", "?")
    player_total = data.get("player_total", 0)
    target_total = data.get("target_total", 0)
    success = data.get("check_success", False)
    player_rolls = data.get("player_rolls", [])
    target_info = data.get("target_rolls", {})

    lines = [f"【检定】{event_name}"]
    lines.append(f"颜色: {color} | 有效值: {effective}")

    rolls_str = str(player_rolls) if player_rolls else str(player_total)
    lines.append(f"🎲 你的骰子: {rolls_str} = {player_total}")

    if target_info:
        t_expr = target_info.get("expression", "?")
        t_rolls = target_info.get("individual_rolls", [])
        lines.append(f"🎯 目标骰子: {t_expr} {t_rolls} = {target_total}")

    icon = "✅" if success else "❌"
    result_text = "检定成功" if success else "检定失败"
    op = "≥" if success else "<"
    lines.append(f"{icon} {result_text}！({player_total} {op} {target_total})")

    if not success:
        lines.append("使用 /re <同色打印能力> 重投 或 /hre <任意打印能力> 消耗1MP重投")

    return "\n".join(lines)


def format_roll(data: dict[str, Any]) -> str:
    expression = data.get("expression", "?")
    results = data.get("results", data.get("individual_rolls", []))
    total = data.get("total", 0)

    if results:
        return f"🎲 {expression} = {results} = {total}"
    return f"🎲 {expression} = {total}"


def format_buff_list(data: list[dict[str, Any]]) -> str:
    if not data:
        return "当前没有任何BUFF/DEBUFF。"
    lines = ["【BUFF/DEBUFF列表】"]
    for b in data:
        name = b.get("name", "?")
        expr = b.get("expression", "")
        rounds = b.get("remaining_rounds", -1)
        rounds_text = f"永久" if rounds == -1 else f"剩余{rounds}轮"
        expr_text = f" ({expr})" if expr else ""
        lines.append(f"- {name}{expr_text} [{rounds_text}]")
    return "\n".join(lines)


def format_session_info(data: dict[str, Any]) -> str:
    lines = ["【场次信息】"]
    sid = data.get("id", "?")
    location = data.get("location", data.get("location_name", "未知"))
    status = data.get("status", "unknown")
    lines.append(f"Session ID: {sid}")
    lines.append(f"地点: {location}")
    lines.append(f"状态: {status}")

    players = data.get("players", [])
    if players:
        player_strs = []
        for p in players:
            name = p.get("username", p.get("name", "?"))
            char_name = p.get("character_name", "")
            if char_name:
                player_strs.append(f"{name}（{char_name}）")
            else:
                player_strs.append(name)
        lines.append(f"参与玩家: {', '.join(player_strs)}")
    else:
        lines.append("参与玩家: 无")

    events = data.get("current_events", data.get("events", []))
    if events:
        event_names = [e.get("name", "?") for e in events]
        lines.append(f"当前事件: {', '.join(event_names)}")

    return "\n".join(lines)


def format_timeline(data: list[dict[str, Any]]) -> str:
    if not data:
        return "暂无时间线记录。"
    lines = ["【时间线】"]
    for entry in data:
        ts = entry.get("timestamp", "")
        event_type = entry.get("event_type", "?")
        entry_data = entry.get("data") or {}
        summary = entry_data.get("summary", entry_data.get("description", ""))
        time_str = f"[{ts}] " if ts else ""
        detail = f": {summary}" if summary else ""
        lines.append(f"{time_str}{event_type}{detail}")
    return "\n".join(lines)


def format_inventory(data: list[dict[str, Any]]) -> str:
    if not data:
        return "背包空空如也。"
    lines = ["【背包】"]
    for item in data:
        name = item.get("name", "?")
        count = item.get("count", 1)
        desc = item.get("description", "")
        count_str = f" x{count}" if count > 1 else ""
        desc_str = f" - {desc}" if desc else ""
        lines.append(f"- {name}{count_str}{desc_str}")
    return "\n".join(lines)


def format_comm_list(data: list[dict[str, Any]]) -> str:
    if not data:
        return "你没有任何未处理的通信请求！"
    lines = ["【通信请求列表】"]
    for i, req in enumerate(data, 1):
        req_id = req.get("id", "?")
        initiator = req.get("initiator_name", req.get("initiator_id", "?"))
        target = req.get("target_name", req.get("target_id", "?"))
        lines.append(f"{i}. 来自{initiator}的请求 (目标: {target}) id={req_id}")
    return "\n".join(lines)


def format_abilities(data: list[dict[str, Any]]) -> str:
    if not data:
        return "当前没有任何打印能力。"
    lines = ["【打印能力】"]
    for a in data:
        name = a.get("name", "?")
        color = a.get("color", "?")
        desc = a.get("description", "")
        desc_str = f" - {desc}" if desc else ""
        lines.append(f"- {name} ({color}){desc_str}")
    return "\n".join(lines)


def format_engine_result(result: dict[str, Any]) -> str:
    if not result.get("success", True):
        return f"操作失败: {result.get('error', '未知错误')}"

    parts: list[str] = []

    narrative = result.get("narrative")
    if narrative:
        parts.append(narrative)

    event_type = result.get("event_type", "")
    data = result.get("data", {})
    if event_type == "event_check" and data:
        parts.append(format_event_check(data))
    elif data:
        for key, value in data.items():
            if isinstance(value, (str, int, float)):
                parts.append(f"{key}: {value}")

    state_changes = result.get("state_changes", [])
    if state_changes:
        parts.append(format_state_changes(state_changes))

    rolls = result.get("rolls", [])
    for roll in rolls:
        results = roll.get("results", [])
        total = roll.get("total", 0)
        if results:
            parts.append(f"🎲 [{', '.join(str(r) for r in results)}] = {total}")

    return "\n".join(parts) if parts else "操作成功！"


def format_state_changes(changes: list[dict[str, Any]]) -> str:
    if not changes:
        return ""
    lines: list[str] = []
    for ch in changes:
        field = ch.get("field", "?")
        old_val = ch.get("old_value", "?")
        new_val = ch.get("new_value", "?")
        lines.append(f"{field}: {old_val} → {new_val}")
    return "\n".join(lines)


def format_region_list(data: list[dict[str, Any]]) -> str:
    if not data:
        return "暂无区域。"
    lines = ["【区域列表】"]
    for r in data:
        code = r.get("code", "?")
        name = r.get("name", "?")
        desc = r.get("description", "")
        desc_str = f" - {desc}" if desc else ""
        lines.append(f"- [{code}] {name}{desc_str}")
    return "\n".join(lines)


def format_location_list(data: list[dict[str, Any]]) -> str:
    if not data:
        return "暂无地点。"
    lines = ["【地点列表】"]
    for loc in data:
        name = loc.get("name", "?")
        desc = loc.get("description", "")
        desc_str = f" - {desc}" if desc else ""
        lines.append(f"- {name}{desc_str}")
    return "\n".join(lines)


def format_location_players(data: list[dict[str, Any]]) -> str:
    if not data:
        return "当前地点没有玩家。"
    lines = ["【地点玩家列表】"]
    for p in data:
        name = p.get("username", p.get("name", "?"))
        char_name = p.get("character_name", "")
        if char_name:
            lines.append(f"- {name}（{char_name}）")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def format_event_list(data: list[dict[str, Any]]) -> str:
    if not data:
        return "当前没有活动事件。"
    lines = ["【事件列表】"]
    for ev in data:
        name = ev.get("name", "?")
        expr = ev.get("expression", "?")
        color = ev.get("color_restriction")
        color_str = f" [限定: {color}]" if color else ""
        lines.append(f"- {name}: {expr}{color_str}")
    return "\n".join(lines)


def format_item_definitions(data: list[dict[str, Any]]) -> str:
    if not data:
        return "暂无物品定义。"
    lines = ["【物品列表】"]
    for item in data:
        name = item.get("name", "?")
        desc = item.get("description", "")
        desc_str = f" - {desc}" if desc else ""
        lines.append(f"- {name}{desc_str}")
    return "\n".join(lines)
