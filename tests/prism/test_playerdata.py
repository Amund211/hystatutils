from typing import Any

import pytest

from prism.playerdata import HypixelAPIKeyHolder, MissingStatsError, get_gamemode_stats


def test_hypixel_key_holder() -> None:
    HypixelAPIKeyHolder("fakekey", limit=10, window=5.5)


@pytest.mark.parametrize(
    "playerdata, gamemode, stats",
    (
        ({}, "game", None),
        ({"stats": 234}, "game", None),
        ({"stats": {}}, "game", None),
        ({"stats": {"othergame": {}}}, "game", None),
        ({"stats": {"othergame": {}}}, "othergame", {}),
        # TODO: test with real data
    ),
)
def test_get_gamemode_stats(
    playerdata: dict[str, Any], gamemode: str, stats: dict[str, Any] | None
) -> None:
    if stats is None:
        with pytest.raises(MissingStatsError):
            get_gamemode_stats(playerdata, gamemode)
    else:
        assert get_gamemode_stats(playerdata, gamemode) == stats
