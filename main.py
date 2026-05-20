"""Compatibility entry point — use: uvicorn raspi_turret.app.main:app"""

from raspi_turret.app.main import app

__all__ = ["app"]
