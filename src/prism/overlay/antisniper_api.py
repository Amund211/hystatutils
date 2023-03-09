import logging
import threading
from enum import Enum, auto
from json import JSONDecodeError
from typing import Any

from cachetools import TTLCache
from requests.exceptions import RequestException

from prism.overlay.player import MISSING_WINSTREAKS, GamemodeName, Winstreaks
from prism.ratelimiting import RateLimiter
from prism.requests import make_prism_requests_session

logger = logging.getLogger(__name__)

DENICK_ENDPOINT = "https://api.antisniper.net/denick"
WINSTREAK_ENDPOINT = "https://api.antisniper.net/v2/player/winstreak"

REQUEST_LIMIT, REQUEST_WINDOW = 100, 60  # Max requests per time window


class Flag(Enum):
    NOT_SET = auto()  # Singleton for cache misses


# Cache both successful and failed denicks for 60 mins
LOWERCASE_DENICK_CACHE = TTLCache[str, str | None](maxsize=1024, ttl=60 * 60)
DENICK_MUTEX = threading.Lock()

# Use a connection pool for the requests
SESSION = make_prism_requests_session()


def set_denick_cache(nick: str, uuid: str | None) -> str | None:
    """Set the cache entry for nick, and return the uuid"""
    with DENICK_MUTEX:
        LOWERCASE_DENICK_CACHE[nick.lower()] = uuid

    return uuid


def get_denick_cache(nick: str) -> str | None | Flag:
    """Get the cache entry for nick"""
    with DENICK_MUTEX:
        return LOWERCASE_DENICK_CACHE.get(nick.lower(), Flag.NOT_SET)


class AntiSniperAPIKeyHolder:
    """Class associating an api key with a RateLimiter instance"""

    def __init__(
        self, key: str, limit: int = REQUEST_LIMIT, window: float = REQUEST_WINDOW
    ):
        self.key = key
        self.limiter = RateLimiter(limit=limit, window=window)


def denick(
    nick: str, key_holder: AntiSniperAPIKeyHolder
) -> str | None:  # pragma: nocover
    """Get data about the given nick from the /denick API endpoint"""
    cache_hit = get_denick_cache(nick)

    # If cache hits and was not a failure, return it
    if cache_hit is not Flag.NOT_SET and cache_hit is not None:
        return cache_hit

    try:
        # Uphold our prescribed rate-limits
        with key_holder.limiter:
            response = SESSION.get(
                f"{DENICK_ENDPOINT}?key={key_holder.key}&nick={nick}"
            )
    except RequestException:
        logger.exception("Request to denick endpoint failed due to a connection error.")
        return set_denick_cache(nick, None)

    if response.status_code == 404:
        logger.debug(f"Request to denick endpoint failed 404 for {nick=}.")
        return set_denick_cache(nick, None)

    if not response:
        logger.error(
            f"Request to denick endpoint failed with status code {response.status_code}"
            f" when getting name for nick {nick}. Response: {response.text}"
        )
        return set_denick_cache(nick, None)

    try:
        response_json = response.json()
    except JSONDecodeError:
        logger.error(
            "Failed parsing the response from the denick endpoint. "
            f"Raw content: {response.text}"
        )
        return set_denick_cache(nick, None)

    return set_denick_cache(nick, parse_denick_response(response_json))


def parse_denick_response(response_json: dict[str, Any]) -> str | None:
    """Parse the response from the denick endpoint"""
    if not response_json.get("success", False):
        logger.error(f"Denick endpoint returned an error. Response: {response_json}")
        return None

    playerdata = response_json.get("player", "INVALIDTYPE")

    if playerdata is None:
        logger.debug("Denick failed")
        return None

    if not isinstance(playerdata, dict):
        logger.error(
            f"Got wrong return type for playerdata from denick endpoint {playerdata}"
        )
        return None

    uuid = playerdata.get("uuid", None)

    if not isinstance(uuid, str):
        logger.error(f"Got wrong return type for uuid from denick endpoint {uuid}")
        return None

    return uuid


def get_estimated_winstreaks(
    uuid: str, key_holder: AntiSniperAPIKeyHolder
) -> tuple[Winstreaks, bool]:  # pragma: nocover
    """Get the estimated winstreaks of the given uuid"""
    try:
        # Uphold our prescribed rate-limits
        with key_holder.limiter:
            response = SESSION.get(
                f"{WINSTREAK_ENDPOINT}?key={key_holder.key}&player={uuid}"
            )
    except RequestException:
        logger.exception(
            "Request to winstreak endpoint failed due to a connection error."
        )
        return MISSING_WINSTREAKS, False

    if not response:
        logger.error(
            f"Request to winstreak endpoint failed with status code "
            f"{response.status_code} for {uuid=}. Response: {response.text}"
        )
        return MISSING_WINSTREAKS, False

    try:
        response_json = response.json()
    except JSONDecodeError:
        logger.error(
            "Failed parsing the response from the winstreak endpoint. "
            f"Raw content: {response.text}"
        )
        return MISSING_WINSTREAKS, False

    return parse_estimated_winstreaks_response(response_json)


def parse_estimated_winstreaks_response(
    response_json: dict[str, Any]
) -> tuple[Winstreaks, bool]:
    """Parse the reponse from the winstreaks endpoint"""
    if not response_json.get("success", False):
        logger.error(f"Winstreak endpoint returned an error. Response: {response_json}")
        return MISSING_WINSTREAKS, False

    winstreaks_accurate = response_json.get("overall_accurate", None)

    if not isinstance(winstreaks_accurate, bool):
        logger.error(
            f"Got wrong return type for accurate from ws endpoint {winstreaks_accurate}"
        )
        return MISSING_WINSTREAKS, False

    # Getting the winstreaks
    winstreaks: dict[GamemodeName, int | None] = {}

    DATA_NAMES: dict[GamemodeName, str] = {
        "overall": "overall",
        "solo": "eight_one",
        "doubles": "eight_two",
        "threes": "four_three",
        "fours": "four_four",
    }

    for gamemode, data_name in DATA_NAMES.items():
        winstreak = response_json.get(f"{data_name}_winstreak", None)
        if winstreak is not None and not isinstance(winstreak, int):
            logger.error(f"Got wrong return type for {gamemode} winstreak {winstreak=}")
            winstreak = None

        winstreaks[gamemode] = winstreak

    return (
        Winstreaks(
            overall=winstreaks["overall"],
            solo=winstreaks["solo"],
            doubles=winstreaks["doubles"],
            threes=winstreaks["threes"],
            fours=winstreaks["fours"],
        ),
        winstreaks_accurate,
    )
