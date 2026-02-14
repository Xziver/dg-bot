# dg-bot

QQ bot client for the **Digital Ghost** TRPG engine. Players and DMs interact with the game through QQ group commands — the bot proxies all actions to the [dg-core](https://github.com) REST API and formats results as chat messages.

Built on [NoneBot2](https://nonebot.dev/) with the OneBot V11 adapter.

## Architecture

```
QQ群 A ──┐                          ┌── Region A (数据荒原)
QQ群 B ──┼── dg-bot ────────────►│── Region B (信号之海)  ──► dg-core
QQ群 C ──┘   (thin client)          └── Region C (灰山城)        (game engine)
```

- **Thin client** — all game state lives in dg-core; the bot only caches identity mappings and group-to-region bindings
- **Trusted proxy** — the bot authenticates with its own API key and submits actions on behalf of players
- **1 QQ group = 1 region** — each group is bound to a game region and hosts at most one session

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python >= 3.10 |
| Framework | NoneBot2 + FastAPI + WebSockets |
| QQ Protocol | nonebot-adapter-onebot (OneBot V11) |
| HTTP Client | httpx (async) |
| Local Storage | nonebot-plugin-localstore |
| Package Manager | uv |

## Getting Started

### Prerequisites

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) package manager
- A running [dg-core](https://github.com) server
- An OneBot V11 compatible QQ bot implementation (e.g., [Lagrange](https://github.com/LagrangeDev/Lagrange.Core), [NapCat](https://github.com/NapNeko/NapCatQQ))

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/dg-bot.git
cd dg-bot

# Install dependencies
uv sync
```

### Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DRIVER` | Yes | NoneBot driver (`~fastapi+~websockets`) |
| `DG_CORE_URL` | Yes | dg-core server URL |
| `DG_BOT_API_KEY` | Yes | Bot's 64-char hex API key from dg-core |
| `DG_GAME_ID` | Yes | Global game ID |
| `SUPERUSERS` | No | QQ UIDs with admin privileges (JSON array) |

### Running

```bash
uv run nb run
```

## Commands

All commands use `/` prefix. Chinese name is the primary trigger; English alias is also available.

### Account & Info

| Command | Alias | Description |
|---------|-------|-------------|
| `/注册 <用户名>` | `/register` | Create a dg-core account |
| `/状态` | `/status` | Show player + character summary |
| `/帮助 [命令]` | `/help` | Show help text |

### Game Setup (DM)

| Command | Alias | Description |
|---------|-------|-------------|
| `/开团 <名称>` | `/newgame` | Create a new game |
| `/加入 @玩家 [角色]` | `/join` | Add player to game |
| `/创建区域 <代号> <名称>` | `/newregion` | Create region |
| `/创建地点 <区域> <名称>` | `/newloc` | Create location |

### Region Binding

| Command | Alias | Description |
|---------|-------|-------------|
| `/绑定区域 <代号>` | `/bindregion` | Bind this QQ group to a region |
| `/区域信息` | `/regioninfo` | Show bound region info |

### Character

| Command | Alias | Description |
|---------|-------|-------------|
| `/创建患者 <名字> <颜色>` | `/newpatient` | Create a patient character |
| `/创建幽灵 <名字> <颜色>` | `/newghost` | Create a ghost (DM only) |
| `/角色` | `/char` | Show active character |
| `/切换角色 <患者>` | `/switchchar` | Switch active character |

### Session

| Command | Alias | Description |
|---------|-------|-------------|
| `/开始 [地点]` | `/start` | Start session in this group's region |
| `/结束` | `/end` | End active session |
| `/暂停` / `/恢复` | `/pause` / `/resume` | Pause / resume session |

### Gameplay

| Command | Alias | Description |
|---------|-------|-------------|
| `/设事件 <名称> <表达式>` | `/defevent` | Define an event check |
| `/检定 <事件名>` | `/check` | Perform event check |
| `/re <能力名>` | `/reroll` | Reroll (same color) |
| `/hre <能力名>` | `/hardreroll` | Hard reroll (any color, -1 MP) |
| `/攻击 @目标 <颜色>` | `/attack` | Attack target |
| `/防御 <颜色>` | `/defend` | Defend |
| `/通信 @目标` | `/comm` | Initiate communication |
| `/r <表达式>` | `/roll` | Roll dice (e.g., `2d6+3`) |

### DM Tools

| Command | Alias | Description |
|---------|-------|-------------|
| `/加碎片 @玩家 <数量>` | `/addfrag` | Add fragments |
| `/改hp @玩家 <数量>` | `/sethp` | Modify HP |
| `/移动区域 @玩家 <区域>` | `/moveregion` | Move player to region |
| `/加buff @玩家 <名称>` | `/addbuff` | Apply buff |
| `/创建物品 <名称>` | `/newitem` | Create item definition |
| `/给物品 @玩家 <物品>` | `/giveitem` | Give item to player |

## Project Structure

```
src/plugins/dg_trpg/
├── __init__.py              # Plugin entry point
├── config.py                # Pydantic settings
├── core/                    # Shared infrastructure
│   ├── api_client.py        # httpx wrapper for dg-core
│   ├── auth.py              # Trusted proxy auth
│   ├── state.py             # Local storage manager
│   ├── models.py            # Response models
│   ├── context.py           # Depends() DI chain
│   ├── errors.py            # Error handling
│   ├── formatters.py        # Output formatters
│   └── permissions.py       # Permission checks
└── plugins/                 # Sub-plugins (one per command group)
    ├── admin.py             # Registration, help
    ├── game_setup.py        # Game / region / location CRUD
    ├── region_bind.py       # Group-to-region binding
    ├── character.py         # Character management
    ├── session.py           # Session lifecycle
    ├── event_check.py       # Event checks & rerolls
    ├── dice.py              # Dice rolling
    ├── combat.py            # Attack / defend
    ├── communication.py     # Player communication
    ├── buff.py              # Buff management
    ├── item.py              # Items & inventory
    ├── timeline.py          # Timeline queries
    ├── player_info.py       # Status / info queries
    └── state_change.py      # DM state modifications
```

## Development

```bash
uv sync                     # Install dependencies
uv run nb run               # Start the bot
uv run pytest               # Run tests
uv add <package>            # Add a dependency
```

## License

All rights reserved.
