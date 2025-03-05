"""Система событий приложения Pythonchik.

Этот модуль реализует паттерн "Наблюдатель" через механизм шины событий,
позволяя различным компонентам приложения взаимодействовать через слабо
связанную архитектуру, основанную на событиях.

Основные компоненты:
- EventBus: Центральная шина событий, обеспечивающая публикацию и подписку на события
- Event: Базовый класс события с типом, данными, источником и временной меткой
- EventType: Перечисление типов событий, сгруппированных по категориям
- EventHandler: Абстрактный базовый класс для обработчиков событий
- EventHandlerFunction: Функциональный обработчик событий

Категории событий:
- SYSTEM: Системные события (изменение состояния, ошибки)
- UI: События пользовательского интерфейса
- TASK: События, связанные с выполнением задач
- DATA: События, связанные с данными

Примеры использования:
    >>> from pythonchik.events.eventbus import EventBus
    >>> from pythonchik.events.events import Event, EventType
    >>> from pythonchik.events.handlers import EventHandler
    >>>
    >>> # Создание шины событий
    >>> bus = EventBus()
    >>>
    >>> # Определение обработчика
    >>> class MyHandler(EventHandler):
    ...     def handle(self, event):
    ...         print(f"Обработка события: {event.type}, данные: {event.data}")
    >>>
    >>> # Подписка на события
    >>> handler = MyHandler()
    >>> bus.subscribe(EventType.STATE_CHANGED, handler)
    >>>
    >>> # Публикация события
    >>> event = Event(EventType.STATE_CHANGED, {"old_state": "idle", "new_state": "processing"})
    >>> bus.publish(event)
"""
