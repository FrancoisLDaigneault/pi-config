"""Thin wrapper - logic lives in src/pi_config_tools/backup.py."""

import sys

from pi_config_tools.backup import main

if __name__ == "__main__":
    sys.exit(main())
