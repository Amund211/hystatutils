import logging

from prism.overlay.__main__ import main

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Exception caught in main!")
