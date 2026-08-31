#!/usr/bin/env python3
"""One-shot factory setup: data → ICM folders → graph seed."""

from graph_seed import seed
from init_workspace import init_workspace
from mock_data_generator import generate


def main() -> None:
    generate()
    init_workspace(reset_outputs=True)
    seed()


if __name__ == "__main__":
    main()
