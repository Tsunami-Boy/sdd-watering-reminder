"""Local run: `python -m waterbot` (same app as production; use RUN_MODE=polling locally)."""

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "waterbot.app:build_app",
        factory=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
    )


if __name__ == "__main__":
    main()
