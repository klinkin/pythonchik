"""Точка входа в приложение Pythonchik.

Этот модуль содержит основную точку входа для запуска приложения.
"""

from pythonchik.ui.app import ModernApp
from pythonchik.utils.logging_config import setup_logging


def main() -> None:
    """Точка входа в приложение.

    Описание:
        Инициализирует и запускает главное окно приложения.

    Note:
        Создает экземпляр приложения и запускает главный цикл событий.
    """
    setup_logging()
    app = ModernApp()
    app.mainloop()


if __name__ == "__main__":
    main()
