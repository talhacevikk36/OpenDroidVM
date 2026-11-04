"""PyInstaller entry point (the package uses relative imports, so it needs a launcher)."""
from opendroidvm.cli import main

raise SystemExit(main())
