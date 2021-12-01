import os
from typing import Optional, Sequence, Union

from sidelay.stats import PropertyName, Stats, rate_stats_for_non_party_members

from hystatutils.colors import Color

# Column separator
SEP = " " * 4


COLUMN_NAMES: dict[str, PropertyName] = {
    "IGN": "username",
    "Stars": "stars",
    "FKDR": "fkdr",
    "WLR": "wlr",
    "WS": "winstreak",
}


LEVEL_COLORMAP = (
    Color.LIGHT_GRAY,
    Color.LIGHT_WHITE,
    Color.YELLOW,
    Color.LIGHT_RED,
    Color.LIGHT_RED + Color.BG_WHITE,
)


STAT_LEVELS: dict[PropertyName, Optional[Sequence[Union[int, float]]]] = {
    "stars": (100, 300, 500, 800),
    "fkdr": (0.5, 2, 4, 8),
    "wlr": (0.3, 1, 2, 4),
    "winstreak": (5, 15, 30, 50),
    "username": None,
}

assert set(STAT_LEVELS.keys()).issubset(set(COLUMN_NAMES.values()))

# COLUMN_ORDER = ("IGN", "Stars", "FKDR", "WLR", "WS")
COLUMN_ORDER = ("IGN", "Stars", "FKDR", "WS")

assert set(COLUMN_ORDER).issubset(set(COLUMN_NAMES.keys()))


def clear_screen() -> None:
    """Blank the screen"""
    os.system("cls" if os.name == "nt" else "clear")


def title(text: str) -> str:
    """Format the given text like a title (in bold)"""
    return Color.BOLD + text + Color.END


def color(
    text: str, value: Union[int, float], levels: Sequence[Union[int, float]]
) -> str:
    """
    Color the given text according to the thresholds in `levels`

    The level is computed as the smallest index i in levels that is such that
    value < levels[i]
    Alternatively the largest index i in levels such that
    value >= levels[i]

    This i is used to select the color from the global LEVEL_COLORMAP
    """

    assert len(levels) + 1 <= len(LEVEL_COLORMAP)

    for i, level in enumerate(levels):
        if value < level:
            break
    else:
        # Passed all levels
        i += 1

    color = LEVEL_COLORMAP[i]

    return color + text + Color.END


def get_sep(column: str) -> str:
    """Get the separator used in prints for this column"""
    return "\n" if column == COLUMN_ORDER[-1] else SEP


def print_stats_table(
    stats: list[Stats],
    party_members: set[str],
    out_of_sync: bool,
    clear_between_draws: bool = True,
) -> None:

    # Sort the the players by stats and order party members last
    sorted_stats = list(
        sorted(
            stats,
            key=rate_stats_for_non_party_members(party_members),
            reverse=True,
        )
    )

    column_widths = {
        column: len(
            max(
                (stat.get_string(COLUMN_NAMES[column]) for stat in sorted_stats),
                default="",
                key=len,
            )
        )
        for column in COLUMN_ORDER
    }

    if clear_between_draws:
        clear_screen()

    if out_of_sync:
        print(
            title(
                Color.LIGHT_RED
                + Color.BG_WHITE
                + "The overlay is out of sync with the lobby. Please use /who."
            )
        )

    # Table header
    for column in COLUMN_ORDER:
        print(title(column.ljust(column_widths[column])), end=get_sep(column))

    for stat in sorted_stats:
        for column in COLUMN_ORDER:
            # Left justify the username, right justify the cells
            justify = str.ljust if column == "IGN" else str.rjust

            stat_name = COLUMN_NAMES[column]

            levels = STAT_LEVELS.get(stat_name, None)

            stat_string = stat.get_string(stat_name)
            stat_value = stat.get_value(stat_name)

            if levels is None or isinstance(stat_value, str):
                final_string = stat_string
            else:
                final_string = color(stat_string, stat_value, levels)

            print(
                justify(
                    final_string,
                    column_widths[column] + (len(final_string) - len(stat_string)),
                ),
                end=get_sep(column),
            )
