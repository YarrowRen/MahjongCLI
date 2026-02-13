"""Parse Tenhou mjlog XML into structured per-round event data.

XML tag mapping:
  T0-T135 = P0 draw, D0-D135 = P0 discard
  U0-U135 = P1 draw, E0-E135 = P1 discard
  V0-V135 = P2 draw, F0-F135 = P2 discard
  W0-W135 = P3 draw, G0-G135 = P3 discard
  N who=X m=Y = meld call
  REACH step=1 = riichi declare, step=2 = riichi score deduction
  AGARI = win result
  RYUUKYOKU = draw result
  INIT = round init
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .decoder import decode_meld, DecodedMeld


class EventType(Enum):
    DRAW = "draw"
    DISCARD = "discard"
    MELD = "meld"
    RIICHI_DECLARE = "riichi_declare"
    RIICHI_SCORE = "riichi_score"
    AGARI = "agari"
    RYUUKYOKU = "ryuukyoku"


@dataclass
class Event:
    event_type: EventType
    player: int
    tile_id: int = -1                  # 136-encoding tile ID
    decoded_meld: Optional[DecodedMeld] = None
    # AGARI fields
    agari_who: int = -1                # winner seat
    agari_from: int = -1               # from whom (-1 for tsumo = same as who)
    agari_ten: Optional[List[int]] = None   # [fu, points, ...]
    agari_yaku: Optional[List[int]] = None  # [yaku_id, han, yaku_id, han, ...]
    agari_sc: Optional[List[int]] = None    # score changes [p0_score, p0_change, ...]
    agari_machi: int = -1              # winning tile
    agari_dora: Optional[List[int]] = None
    agari_uradora: Optional[List[int]] = None
    agari_ba: Optional[List[int]] = None       # [honba, riichi_sticks] at AGARI time
    # RYUUKYOKU fields
    ryuukyoku_type: str = ""
    ryuukyoku_sc: Optional[List[int]] = None
    ryuukyoku_hai: Optional[List[Optional[List[int]]]] = None  # tenpai hands


@dataclass
class RoundData:
    round_number: int       # 0=E1, 1=E2, ..., 4=S1, ...
    honba: int
    riichi_sticks: int
    dealer: int             # seat 0-3
    scores: List[int]       # initial scores (* 100)
    dora_indicator: int     # initial dora indicator tile_id
    hands: List[List[int]]  # 3 or 4 players' initial hands (tile_ids)
    is_sanma: bool = False  # True for 3-player games
    num_players: int = 4
    events: List[Event] = field(default_factory=list)


# Draw/discard tag patterns
_DRAW_TAGS = {
    'T': 0, 'U': 1, 'V': 2, 'W': 3,
}
_DISCARD_TAGS = {
    'D': 0, 'E': 1, 'F': 2, 'G': 3,
}

# Regex to match draw/discard tags like T72, D113, U118, E118, etc.
_TILE_TAG_RE = re.compile(r'^([TUVWDEFG])(\d+)$')


def parse(xml_path: str) -> List[RoundData]:
    """Parse a Tenhou mjlog XML file into a list of RoundData."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Detect sanma from GO element
    is_sanma = False
    for elem in root:
        if elem.tag == 'GO':
            go_type = int(elem.attrib.get('type', '0'))
            is_sanma = bool(go_type & 0x10)
            break

    rounds: List[RoundData] = []
    current_round: Optional[RoundData] = None

    for elem in root:
        tag = elem.tag

        if tag == 'INIT':
            current_round = _parse_init(elem, is_sanma)
            rounds.append(current_round)
            continue

        if current_round is None:
            continue

        # Try draw/discard tags
        m = _TILE_TAG_RE.match(tag)
        if m:
            letter = m.group(1)
            tile_id = int(m.group(2))
            if letter in _DRAW_TAGS:
                current_round.events.append(Event(
                    event_type=EventType.DRAW,
                    player=_DRAW_TAGS[letter],
                    tile_id=tile_id,
                ))
            elif letter in _DISCARD_TAGS:
                current_round.events.append(Event(
                    event_type=EventType.DISCARD,
                    player=_DISCARD_TAGS[letter],
                    tile_id=tile_id,
                ))
            continue

        if tag == 'N':
            who = int(elem.attrib['who'])
            m_val = int(elem.attrib['m'])
            decoded = decode_meld(m_val, is_sanma=is_sanma)
            current_round.events.append(Event(
                event_type=EventType.MELD,
                player=who,
                decoded_meld=decoded,
            ))
            continue

        if tag == 'REACH':
            who = int(elem.attrib['who'])
            step = int(elem.attrib['step'])
            if step == 1:
                current_round.events.append(Event(
                    event_type=EventType.RIICHI_DECLARE,
                    player=who,
                ))
            elif step == 2:
                current_round.events.append(Event(
                    event_type=EventType.RIICHI_SCORE,
                    player=who,
                ))
            continue

        if tag == 'AGARI':
            event = _parse_agari(elem)
            current_round.events.append(event)
            continue

        if tag == 'RYUUKYOKU':
            event = _parse_ryuukyoku(elem)
            current_round.events.append(event)
            continue

    return rounds


def _parse_init(elem: ET.Element, is_sanma: bool = False) -> RoundData:
    """Parse INIT element into RoundData."""
    seed = [int(x) for x in elem.attrib['seed'].split(',')]
    # seed: [round_number, honba, riichi_sticks, dice1, dice2, dora_indicator]
    round_number = seed[0]
    honba = seed[1]
    riichi_sticks = seed[2]
    dora_indicator = seed[5]

    scores = [int(x) * 100 for x in elem.attrib['ten'].split(',')]
    dealer = int(elem.attrib['oya'])

    num_players = 3 if is_sanma else 4
    hands = []
    for i in range(4):
        key = f'hai{i}'
        if key in elem.attrib and elem.attrib[key].strip():
            hand = [int(x) for x in elem.attrib[key].split(',')]
        else:
            hand = []
        hands.append(hand)

    return RoundData(
        round_number=round_number,
        honba=honba,
        riichi_sticks=riichi_sticks,
        dealer=dealer,
        scores=scores,
        dora_indicator=dora_indicator,
        hands=hands,
        is_sanma=is_sanma,
        num_players=num_players,
    )


def _parse_agari(elem: ET.Element) -> Event:
    """Parse AGARI element."""
    who = int(elem.attrib['who'])
    from_who = int(elem.attrib['fromWho'])
    machi = int(elem.attrib['machi'])
    ten = [int(x) for x in elem.attrib['ten'].split(',')]

    yaku = []
    if 'yaku' in elem.attrib:
        yaku = [int(x) for x in elem.attrib['yaku'].split(',')]
    elif 'yakuman' in elem.attrib:
        yaku = [int(x) for x in elem.attrib['yakuman'].split(',')]

    sc = [int(x) for x in elem.attrib['sc'].split(',')]

    dora = []
    if 'doraHai' in elem.attrib:
        dora = [int(x) for x in elem.attrib['doraHai'].split(',')]

    uradora = []
    if 'doraHaiUra' in elem.attrib:
        uradora = [int(x) for x in elem.attrib['doraHaiUra'].split(',')]

    ba = [0, 0]
    if 'ba' in elem.attrib:
        ba = [int(x) for x in elem.attrib['ba'].split(',')]

    return Event(
        event_type=EventType.AGARI,
        player=who,
        agari_who=who,
        agari_from=from_who,
        agari_ten=ten,
        agari_yaku=yaku,
        agari_sc=sc,
        agari_machi=machi,
        agari_dora=dora,
        agari_uradora=uradora,
        agari_ba=ba,
    )


def _parse_ryuukyoku(elem: ET.Element) -> Event:
    """Parse RYUUKYOKU element."""
    rtype = elem.attrib.get('type', 'exhaustive')

    sc = None
    if 'sc' in elem.attrib:
        sc = [int(x) for x in elem.attrib['sc'].split(',')]

    # Tenpai hands (hai0..hai3) - present if player is tenpai
    hai: List[Optional[List[int]]] = [None, None, None, None]
    for i in range(4):
        key = f'hai{i}'
        if key in elem.attrib:
            hai[i] = [int(x) for x in elem.attrib[key].split(',')]

    return Event(
        event_type=EventType.RYUUKYOKU,
        player=-1,
        ryuukyoku_type=rtype,
        ryuukyoku_sc=sc,
        ryuukyoku_hai=hai,
    )
