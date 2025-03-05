"""Точка входа в приложение Pythonchik.

Этот модуль содержит основную точку входа для запуска приложения. Он инициализирует
ключевые компоненты системы: шину событий, ядро приложения и пользовательский интерфейс,
обеспечивая их корректное взаимодействие.

Основные функции:
    - Настройка системы логирования
    - Инициализация шины событий для обмена сообщениями между компонентами
    - Создание и настройка ядра приложения
    - Запуск пользовательского интерфейса

Пример запуска приложения:
    $ python -m pythonchik.main

Зависимости:
    - pythonchik.core.application_core: Ядро приложения
    - pythonchik.events.eventbus: Система событий
    - pythonchik.logging: Конфигурация логирования
    - pythonchik.ui.app: Пользовательский интерфейс
"""

from pythonchik.core.application_core import ApplicationCore
from pythonchik.events.eventbus import EventBus
from pythonchik.logging import setup_logging
from pythonchik.ui.app import ModernApp


def main() -> None:
    """Точка входа в приложение.

    Функция инициализирует ключевые компоненты приложения и запускает
    главный цикл обработки событий. Последовательность инициализации:
    1. Настройка логирования для отслеживания работы приложения
    2. Создание шины событий для асинхронного взаимодействия компонентов
    3. Инициализация ядра приложения, отвечающего за бизнес-логику
    4. Запуск пользовательского интерфейса, связанного с ядром и шиной событий

    Note:
        Создает экземпляр приложения и запускает главный цикл событий.
        При завершении цикла событий происходит корректное освобождение ресурсов.
    """
    setup_logging()
    bus = EventBus()
    core = ApplicationCore(bus)
    app = ModernApp(core, event_bus=bus)
    app.mainloop()


if __name__ == "__main__":
    main()
