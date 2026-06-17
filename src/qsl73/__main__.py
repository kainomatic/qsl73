# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Einstiegspunkt für `python -m qsl73`."""


def main() -> None:
    from qsl73.gui.app import run_app
    run_app()


if __name__ == "__main__":
    main()
