"""Chinese localization strings."""

# Wind names
WIND_NAMES = {0: "東", 1: "南", 2: "西", 3: "北"}

# Tile suit names
SUIT_NAMES = {"m": "万", "p": "筒", "s": "索"}

# Tile display names (34 encoding)
TILE_DISPLAY_NAMES = [
    "一万", "二万", "三万", "四万", "五万", "六万", "七万", "八万", "九万",
    "一筒", "二筒", "三筒", "四筒", "五筒", "六筒", "七筒", "八筒", "九筒",
    "一索", "二索", "三索", "四索", "五索", "六索", "七索", "八索", "九索",
    "東", "南", "西", "北", "白", "發", "中",
]

# Game messages
MSG_GAME_START = "游戏开始！"
MSG_ROUND_START = "{round_label}  场风:{wind}  宝牌:{dora}"
MSG_YOUR_TURN = "轮到你了"
MSG_CHOOSE_DISCARD = "请选择打出的牌 (输入编号1-{n}):"
MSG_CHOOSE_ACTION = "可用操作:"
MSG_TSUMO = "[T] 自摸"
MSG_RON = "[H] 荣和"
MSG_RIICHI = "[R] 立直"
MSG_PON = "[P] 碰"
MSG_CHI = "[C] 吃"
MSG_KAN = "[K] 杠"
MSG_SKIP = "[S] 跳过"
MSG_KITA = "[N] 北抜き"
MSG_KYUUSHU = "[9] 九种九牌流局"

MSG_TSUMO_WIN = "{player} 自摸！"
MSG_RON_WIN = "{player} 荣和！放铳: {loser}"
MSG_EXHAUSTIVE_DRAW = "荒牌流局"
MSG_ABORTIVE_DRAW_4WIND = "四风连打 - 途中流局"
MSG_ABORTIVE_DRAW_4KAN = "四开杠 - 途中流局"
MSG_ABORTIVE_DRAW_4RIICHI = "四家立直 - 途中流局"
MSG_ABORTIVE_DRAW_KYUUSHU = "九种九牌 - 途中流局"

MSG_RIICHI_DECLARE = "{player} 宣言立直！"
MSG_CALL_PON = "{player} 碰！"
MSG_CALL_CHI = "{player} 吃！"
MSG_CALL_KAN = "{player} 杠！"

MSG_GAME_END = "游戏结束！"
MSG_FINAL_SCORES = "最终得分:"
MSG_WINNER = "优胜: {player}"

MSG_SCORE_DETAIL = "{han}翻{fu}符 {points}点"
MSG_YAKUMAN = "役满！{points}点"
MSG_DEALER = "庄家"
MSG_NON_DEALER = "子家"

MSG_REMAINING = "剩余: {n}张"
MSG_RIICHI_STICKS = "立直棒: {n}"
MSG_HONBA = "{n}本场"

MSG_TENPAI = "听牌"
MSG_NOTEN = "不听"

# Mode selection
MSG_MODE_SELECT = "请选择游戏模式:"
MSG_MODE_4P = "四人麻将 (半荘)"
MSG_MODE_4P_TONPUU = "四人麻将 (東風戦)"
MSG_MODE_3P = "三人麻将 (半荘)"
MSG_MODE_3P_TONPUU = "三人麻将 (東風戦)"
MSG_QUIT = "退出"

ABORTIVE_DRAW_MESSAGES = {
    "4wind": MSG_ABORTIVE_DRAW_4WIND,
    "4kan": MSG_ABORTIVE_DRAW_4KAN,
    "4riichi": MSG_ABORTIVE_DRAW_4RIICHI,
    "kyuushu": MSG_ABORTIVE_DRAW_KYUUSHU,
    "triple_ron": "三家和了 - 途中流局",
}
