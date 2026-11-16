#!/usr/bin/env python
"""Django command-line entry point (runserver, migrate, etc.)"""
import os
import sys


def main():
    # Batata Django ko settings kaha hai
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django install nahi hai ya venv active nahi hai."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()