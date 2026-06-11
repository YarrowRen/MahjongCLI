# 🀄️ Japanese Riichi Mahjong - Terminal CLI

A fully-featured Japanese Riichi Mahjong terminal CLI game supporting 4-player (yonma) and 3-player (sanma) modes, with multilingual interface (Chinese/Japanese/English), built with Python + Rich.

[![PyPI](https://img.shields.io/pypi/v/riichi-mahjong-cli)](https://pypi.org/project/riichi-mahjong-cli/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/riichi-mahjong-cli?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/riichi-mahjong-cli)
[![GitHub](https://img.shields.io/badge/GitHub-YarrowRen%2FMahjongCLI-181717?logo=github)](https://github.com/YarrowRen/MahjongCLI)
[![MahjongCLI DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/YarrowRen/MahjongCLI)

[中文文档](https://github.com/YarrowRen/MahjongCLI/blob/master/README-CN.md)

## Preview

| Game Board | Winning Screen |
|---------|---------|
| ![Game Board](https://raw.githubusercontent.com/YarrowRen/MahjongCLI/master/data/static/img1.png) | ![Winning Screen](https://raw.githubusercontent.com/YarrowRen/MahjongCLI/master/data/static/img2.png) |

![Discard Action](https://raw.githubusercontent.com/YarrowRen/MahjongCLI/master/data/static/img3.png)

## Features

- **4-Player Mahjong** - Hanchan (half game) / Tonpuusen (east-only)
- **3-Player Mahjong** - Hanchan / Tonpuusen (no 2m-8m, no chi, kita)
- **Complete Rule Engine** - 30+ yaku detection, fu calculation, scoring
- **Greedy AI Opponents** - Shanten-based AI with basic defense
- **Spectator Mode** - AI vs AI auto-play
- **Multilingual** - Chinese, Japanese, and English interface
- **Colored Tiles** - Rich terminal rendering with colored tile display
- **A+B Time Control** - Base + bank seconds per action, real-time countdown with per-second refresh (unlimited by default)
- **Game Replay** - Browse finished games and step through every action in god view (menu option 7)
- **Game Logs** - Every finished game is recorded as JSON under `logs/` (full wall, all actions, results)
- **Adjustable AI Speed** - 1s / 3s / 5s / random delay presets in Settings

## Install

```bash
pipx install riichi-mahjong-cli
```

Or with pip:

```bash
pip install riichi-mahjong-cli
```

## Quick Start

```bash
riichi
```

Or run from source:

```bash
python main.py
```

The game starts in Chinese by default. Language, time control, and AI speed can be changed in **Settings** (main menu option 6). **Replay** (option 7) lets you review any finished game step by step.

### Run Tests

```bash
pytest tests/
```

## Controls

| Key | Action |
|------|------|
| 1-14 | Select tile to discard |
| `t` | Tsumo (self-draw win) |
| `h` | Ron (win off discard) |
| `r` | Declare Riichi |
| `p` | Pon |
| `c` | Chi |
| `k` | Kan (concealed/added/open) |
| `n` | Kita (3-player only) |
| `9` | Nine-tile draw |
| `s` | Skip |

### Replay Controls

| Key | Action |
|------|------|
| `Enter` | Next step |
| `b` | Previous step |
| number | Jump to step |
| `q` | Back |

## Project Structure

```
game/
├── main.py                     # Entry point (backward compatible)
├── mahjong/
│   ├── cli.py                  # CLI entry point (riichi command)
│   ├── core/                   # Core data models
│   │   ├── tile.py             # Tile definitions (136/34 dual encoding, red dora)
│   │   ├── meld.py             # Meld data structures
│   │   ├── hand.py             # Hand management
│   │   ├── wall.py             # Wall and dead wall
│   │   └── player_state.py     # Player state tracking
│   ├── rules/                  # Rule engine (pure functions, stateless)
│   │   ├── agari.py            # Win detection (LRU cached)
│   │   ├── shanten.py          # Shanten calculation (LRU cached)
│   │   ├── fu.py               # Fu calculation
│   │   ├── yaku.py             # Yaku detection (30+ types)
│   │   ├── scoring.py          # Score calculation
│   │   └── furiten.py          # Furiten detection
│   ├── engine/                 # Game engine
│   │   ├── game.py             # Hanchan/Tonpuusen management
│   │   ├── round.py            # Single round flow control
│   │   ├── action.py           # Action definitions
│   │   ├── event.py            # Event bus
│   │   ├── game_logger.py      # Game logging
│   │   ├── time_control.py     # A+B time control presets
│   │   └── ai_delay.py         # AI action speed presets
│   ├── player/                 # Player abstraction & AI
│   │   ├── base.py             # Player base class + GameView
│   │   ├── human.py            # Human player + timing logic
│   │   └── greedy_ai.py        # Greedy AI
│   ├── replay/                 # Game replay
│   │   ├── loader.py           # Log scanning & loading
│   │   └── state.py            # Step-by-step state reconstruction
│   └── ui/                     # Terminal UI
│       ├── renderer.py         # Rendering facade
│       ├── tile_display.py     # Tile display formatting
│       ├── board_layout.py     # Board layout rendering
│       ├── replay_screen.py    # Replay browser (menu option 7)
│       ├── input_handler.py    # User input handling
│       ├── timeout_input.py    # Timed input + live countdown (ANSI)
│       ├── i18n.py             # Internationalization (zh/ja/en)
│       ├── labels.py           # Localized label construction
│       └── locales/            # Translation files
│           ├── zh.py           # Chinese translations
│           ├── ja.py           # Japanese translations
│           └── en.py           # English translations
├── tests/                      # Unit tests (168 cases)
└── data/
    └── scoring_table.json      # Han/fu → points lookup table
```

## Supported Yaku

### 1 Han
Riichi, Menzen Tsumo, Tanyao, Pinfu, Iipeikou, Yakuhai (round/seat wind, dragons), Ippatsu, Haitei, Houtei, Rinshan Kaihou, Chankan

### 2 Han
Double Riichi, Chanta, Ittsu, Sanshoku Doujun, Sanshoku Doukou, Toitoi, San Ankou, Honroutou, Shousangen, Chiitoitsu

### 3 Han
Honitsu, Junchan, Ryanpeikou

### 6 Han
Chinitsu

### Yakuman
Kokushi Musou, Suu Ankou, Daisangen, Shousuushii, Daisuushii, Tsuuiisou, Chinroutou, Ryuuiisou, Chuuren Poutou, Suukantsu, Tenhou, Chiihou

## Rule Engine Verification

The rule engine has been verified against **1,000 real games** from [Tenhou](https://tenhou.net/) (the most popular online Japanese Mahjong platform). All 1,000 replays pass with 100% consistency.

### Verification Process

1. **Parse** Tenhou mjlog XML replay files into structured event streams (draws, discards, melds, riichi, agari, ryuukyoku)
2. **Reconstruct** the exact tile wall order from the replay data (initial hands, draw sequence, dead wall)
3. **Replay** each round step-by-step through our engine, feeding the same actions from the replay
4. **Validate** at every step:
   - Each draw, discard, meld, and riichi is legal according to the engine's rule checks
   - Ron/tsumo legality (furiten, valid yaku, score calculation)
   - Final scoring matches Tenhou's results (fu, han, points, payments)
   - Ryuukyoku (draw) tenpai status and point transfers match

```bash
# Run Tenhou replay verification
pytest tests/tenhou_replay/ -v
```

```
tests/tenhou_replay/test_tenhou_replay.py - 1000 passed
```

### What This Proves

- Yaku detection, fu calculation, and scoring are correct for real-world game scenarios
- Furiten rules (discard furiten, temporary furiten, riichi furiten) behave correctly
- Meld legality (chi, pon, kan) matches Tenhou's rule interpretation
- Edge cases (haitei, houtei, rinshan, chankan, double riichi) are handled correctly

## Design Highlights

- **Dual Encoding** - 136-encoding tracks unique tile identity, 34-encoding for efficient algorithms
- **GameView Barrier** - AI and human use the same interface, ensuring fairness
- **Strict Layering** - core/engine/rules never import the UI layer; translations live entirely in `ui/`
- **EventBus Logging** - the engine emits events consumed by the game logger; replays are rebuilt from these logs
- **Swappable AI** - Standard interface (a single `choose_action` protocol) allows future AI model integration
- **i18n Architecture** - `t()` translation function with locale dictionaries, yaku names used as stable keys; locale consistency is enforced by tests
- **Invariant Tests** - AI self-play smoke tests assert point conservation after every round

## Dependencies

- Python >= 3.10
- rich >= 13.0.0
- pytest >= 7.0.0 (development)

---

## About This Project

This project was **fully implemented by [Claude Code](https://claude.ai/claude-code)** from scratch. Humans only provided requirement documents — all code, tests, and documentation were generated by AI.

### Implementation Info

| Item | Details |
|------|------|
| AI Tool | Claude Code (Anthropic CLI) |
| Model | Claude Opus 4.6 (`claude-opus-4-6`) |
| Process | Complete code writing and debugging in a single session |
| Scale | ~30 source files, 120 unit tests |
| Tokens | ~200K+ tokens (planning, code generation, test fixing) |
| Date | 2025-02-12 |

### Later Iterations

All subsequent versions were also implemented by Claude Code, including: multilingual interface and PyPI release (v1.1.0), the A+B time control system and settings menu (v1.1.x), rule-engine verification against 1,000 real Tenhou games, a full engine audit in 2026-06 (fixed tenhou/chankan/kita-dora/riichi-stick-conservation bugs, removed dead code, enforced layering, added LRU caching), and the step-by-step game replay feature.
