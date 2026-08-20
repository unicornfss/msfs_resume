"""Windows system tray icon for when the window is minimised."""

from __future__ import annotations

from collections.abc import Callable

from .paths import bundled_file
from PIL import Image, ImageDraw


def _icon_image() -> Image.Image:
    ico = bundled_file("assets", "msfs-resume.ico")
    if ico.exists():
        return Image.open(ico).convert("RGBA").resize((64, 64))
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), fill=(212, 180, 90, 255))
    draw.rectangle((14, 16, 24, 48), fill=(18, 28, 48, 255))
    draw.polygon([(26, 16), (50, 32), (26, 48)], fill=(18, 28, 48, 255))
    return image


class TrayIcon:
    def __init__(self, on_show: Callable[[], None], on_exit: Callable[[], None]) -> None:
        self._on_show = on_show
        self._on_exit = on_exit
        self._icon = None

    @property
    def visible(self) -> bool:
        return self._icon is not None

    def show(self, tooltip: str = "MSFS Resume") -> None:
        if self._icon is not None:
            self._icon.title = tooltip
            return
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Open", self._show, default=True),
            pystray.MenuItem("Exit", self._exit),
        )
        self._icon = pystray.Icon("MSFS Resume", _icon_image(), tooltip, menu)
        self._icon.run_detached()

    def hide(self) -> None:
        icon = self._icon
        self._icon = None
        if icon is None:
            return
        try:
            icon.visible = False
            icon.stop()
        except Exception:
            pass

    def notify(self, message: str, title: str = "MSFS Resume") -> None:
        if self._icon is None:
            return
        try:
            self._icon.notify(message, title)
        except Exception:
            pass

    def set_tooltip(self, tooltip: str) -> None:
        if self._icon is not None:
            self._icon.title = tooltip

    def _show(self, _icon=None, _item=None) -> None:
        self._on_show()

    def _exit(self, _icon=None, _item=None) -> None:
        self._on_exit()
