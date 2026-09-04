"""Entrypoint for the crews web UI.

Run from the project root::

    python web_server.py

Or after installing the package::

    crew-web
"""

from web.app import main

if __name__ == "__main__":
    main()
