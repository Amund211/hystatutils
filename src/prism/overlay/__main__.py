"""
Parse the chat on Hypixel to detect players in your party and bedwars lobby

Run from the root dir by `python -m prism.overlay [--logfile <path-to-logfile>]`
"""

import sys

import truststore

from prism.overlay.commandline import get_options
from prism.overlay.directories import (
    CONFIG_DIR,
    DEFAULT_LOGFILE_CACHE_PATH,
    DEFAULT_SETTINGS_PATH,
    must_ensure_directory,
)
from prism.overlay.logging import setup_logging
from prism.overlay.nick_database import NickDatabase
from prism.overlay.not_parallel import ensure_not_parallel
from prism.overlay.settings import get_settings
from prism.overlay.thread_count import recommend_stats_thread_count
from prism.overlay.user_interaction.get_logfile import prompt_for_logfile_path
from prism.ssl_errors import is_missing_local_issuer_error


def main() -> None:  # pragma: nocover
    """Run the overlay"""
    options = get_options(default_settings_path=DEFAULT_SETTINGS_PATH)

    ensure_not_parallel()

    setup_logging(options.loglevel)

    must_ensure_directory(CONFIG_DIR)

    # Read settings and populate missing values
    settings = get_settings(
        options.settings_path,
        recommend_stats_thread_count(),
    )

    if not settings.use_included_certs:
        # Patch requests to use system certs
        truststore.inject_into_ssl()

    if options.logfile_path is None:
        logfile_path = prompt_for_logfile_path(
            DEFAULT_LOGFILE_CACHE_PATH, settings.autoselect_logfile
        )
    else:
        logfile_path = options.logfile_path

    with settings.mutex:
        default_database = {
            nick: value["uuid"] for nick, value in settings.known_nicks.items()
        }

    nick_database = NickDatabase.from_disk([], default_database=default_database)

    if options.test_ssl:
        test_ssl()
        return

    # Import late so we can patch ssl certs in requests
    from prism.overlay.process_loglines import watch_from_logfile

    watch_from_logfile(
        logfile_path,
        overlay=True,
        console=options.output_to_console,
        settings=settings,
        nick_database=nick_database,
    )


def test_ssl() -> None:  # pragma: nocover
    """Test SSL certificate patching"""
    import requests

    try:
        resp = requests.get("https://localhost:12345")
        print("Got response:", resp.text)
    except requests.exceptions.SSLError as e:
        if is_missing_local_issuer_error(e):
            print("Caught missing local issuer SSLError:", e)
        else:
            print("Caught unknown SSLError:", e)
    except Exception as e:
        print("Caught unknown exception:", e)


if __name__ == "__main__":  # pragma: nocover
    if len(sys.argv) >= 2 and sys.argv[1] == "--test":
        from prism.overlay.testing import test

        test()
    else:
        main()
