from __future__ import annotations

from ai_dubbing_studio.config import get_settings
from ai_dubbing_studio.ui.desktop import run_app


def main() -> int:
    settings = get_settings()
    return run_app(settings)


if __name__ == "__main__":
    raise SystemExit(main())
