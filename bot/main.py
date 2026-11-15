"""Точка входа: python -m bot.main morning|day|evening|inbox"""
import sys

from . import inbox, post


def main() -> None:
    task = sys.argv[1] if len(sys.argv) > 1 else ""
    if task == "inbox":
        inbox.run()
    elif task in ("morning", "day", "evening"):
        post.run(task)
    else:
        raise SystemExit("Укажи задачу: morning, day, evening или inbox")


if __name__ == "__main__":
    main()
