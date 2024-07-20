import time
import unittest.mock
from collections.abc import Mapping

from prism.hypixel import (
    HypixelAPIError,
    HypixelAPIKeyError,
    HypixelAPIThrottleError,
    HypixelPlayerNotFoundError,
)
from prism.overlay.antisniper_api import AntiSniperAPIKeyHolder
from prism.overlay.controller import ERROR_DURING_PROCESSING, RealOverlayController
from prism.overlay.nick_database import NickDatabase
from prism.ratelimiting import RateLimiter
from tests.prism.overlay.utils import create_state, make_settings


def test_real_overlay_controller() -> None:
    controller = RealOverlayController(
        state=create_state(),
        settings=make_settings(
            antisniper_api_key="antisniper_key",
            use_antisniper_api=True,
        ),
        nick_database=NickDatabase([{}]),
    )

    assert controller.antisniper_key_holder is not None
    assert controller.antisniper_key_holder.key == "antisniper_key"


def test_real_overlay_controller_no_antisniper_key() -> None:
    controller = RealOverlayController(
        state=create_state(),
        settings=make_settings(
            antisniper_api_key=None,
            use_antisniper_api=True,
        ),
        nick_database=NickDatabase([{}]),
    )

    assert controller.antisniper_key_holder is None


def test_real_overlay_controller_get_playerdata() -> None:
    controller = RealOverlayController(
        state=create_state(),
        settings=make_settings(
            antisniper_api_key="antisniper_key",
            use_antisniper_api=True,
            user_id="1234",
        ),
        nick_database=NickDatabase([{}]),
    )

    error: Exception | None = None
    returned_playerdata: Mapping[str, object] = {}

    def get_playerdata(
        uuid: str,
        user_id: str,
        key_holder: AntiSniperAPIKeyHolder | None,
        api_limiter: RateLimiter,
        retry_limit: int = 5,
        initial_timeout: float = 2,
    ) -> Mapping[str, object]:
        assert uuid == "uuid"
        assert user_id == "1234"

        if error:
            raise error

        return returned_playerdata

    with unittest.mock.patch(
        "prism.overlay.controller.get_playerdata",
        get_playerdata,
    ):
        for error in [
            HypixelAPIError(),
            HypixelAPIKeyError(),
            HypixelAPIThrottleError(),
        ]:
            _, playerdata = controller.get_playerdata("uuid")
            assert playerdata is ERROR_DURING_PROCESSING

        error = HypixelPlayerNotFoundError()
        _, playerdata = controller.get_playerdata("uuid")
        assert playerdata is None

        error = None
        dataReceivedAtMs, playerdata = controller.get_playerdata("uuid")

        assert playerdata is returned_playerdata

        current_time_seconds = time.time()
        time_diff = current_time_seconds - dataReceivedAtMs / 1000
        assert abs(time_diff) < 0.1, "Time diff should be less than 0.1 seconds"
