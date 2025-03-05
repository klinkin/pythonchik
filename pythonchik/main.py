"""Точка входа в приложение Pythonchik.

Этот модуль содержит основную точку входа для запуска приложения.
"""

from pythonchik.core.application_core import ApplicationCore
from pythonchik.ui.app import ModernApp
from pythonchik.utils.event_system import EventBus
from pythonchik.utils.logging_config import setup_logging


def main() -> None:
    """Точка входа в приложение.

    Описание:
        Инициализирует и запускает главное окно приложения.

    Note:
        Создает экземпляр приложения и запускает главный цикл событий.
    """
    setup_logging()
    bus = EventBus()
    core = ApplicationCore(bus)
    app = ModernApp(core, event_bus=bus)
    app.mainloop()


if __name__ == "__main__":
    main()
