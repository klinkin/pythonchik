"""
Реализация обработчиков событий для приложения.

Содержит базовый класс EventHandler и конкретные реализации:
- StateChangeHandler
- ErrorHandler
- UIActionHandler

Каждый обработчик специализируется на своём типе события (или нескольких).
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from pythonchik.events.events import Event, EventType
from pythonchik.events.ui_events import UIEventType

# Предполагаем, что UIEventType приходит из pythonchik.ui.events,
# где UIEventType — это Enum для событий UI (extract_addresses, compress_images и т.д.).


logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """Абстрактный базовый класс для всех обработчиков событий.

    Все конкретные обработчики событий должны наследоваться от этого класса
    и реализовывать метод handle(event).
    """

    @abstractmethod
    def handle(self, event: Event) -> None:
        """Обработать событие.

        Args:
            event (Event): Событие для обработки.

        Raises:
            NotImplementedError: Если метод не реализован в подклассе.
        """
        pass


class StateChangeHandler(EventHandler):
    """Обработчик событий изменения состояния приложения.

    Сохраняет и валидирует переходы состояния (например, from X to Y).
    """

    def __init__(self, state_frame) -> None:
        """Инициализирует обработчик

        Args:
            state_frame: фрейм (или компонент), в котором есть метод update_state()
        """
        self.state_frame = state_frame

    def handle(self, event: Event) -> None:
        """Обрабатывает событие STATE_CHANGED.

        Args:
            event (Event): Событие, содержащее новое состояние в event.data["state"].

        Raises:
            ValueError: Если в данных события нет поля 'state' или поле некорректно.
            Exception: Любая ошибка при применении нового состояния (с последующим откатом).
        """
        if event.type != EventType.STATE_CHANGED:
            logger.debug("StateChangeHandler: игнорирую событие %s", event.type)
            return

        if not event.data or "new_state" not in event.data:
            error_msg = "Событие STATE_CHANGED должно содержать 'state' в data"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if event.type == EventType.STATE_CHANGED:
            new_state = event.data["new_state"]
            self.state_frame.update_state(new_state)


class ProgressEventHandler(EventHandler):
    """Обработчик событий PROGRESS_UPDATED, обновляющий прогрессбар в UI."""

    def __init__(self, result_frame, log_frame):
        """
        Args:
            result_frame: фрейм (или компонент), в котором есть метод update_progress(progress, message)
            log_frame: фрейм (или компонент), в котором есть метод log(message)
        """
        self.result_frame = result_frame
        self.log_frame = log_frame

    def handle(self, event: Event) -> None:
        """Основной метод обработки события."""
        if event.type != EventType.PROGRESS_UPDATED:
            logger.debug("ProgressEventHandle: игнорирую событие %s", event.type)
            return

        if not event.data or "progress" not in event.data:
            error_msg = "Событие PROGRESS_UPDATED должно содержать 'progress' в data"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if event.type == EventType.PROGRESS_UPDATED:
            data = event.data or {}
            progress = data.get("progress", 0)
            message = data.get("message", "")

            self.result_frame.update_progress(progress, message)
            self.log_frame.log(message)


class TaskEventHandler(EventHandler):
    """Обработчик событий TASK_COMPLETED, обновляющий прогрессбар в UI."""

    def __init__(self, result_frame, log_frame):
        """
        Args:
            result_frame: фрейм (или компонент), в котором есть метод update_progress(progress, message)
            log_frame: фрейм (или компонент), в котором есть метод log(message)
        """
        self.result_frame = result_frame
        self.log_frame = log_frame

    def handle(self, event: Event) -> None:
        """Основной метод обработки события."""
        if event.type != EventType.TASK_COMPLETED:
            logger.debug("TaskEventHandle: игнорирую событие %s", event.type)
            return

        if not event.data or "result" not in event.data:
            error_msg = "Событие TASK_COMPLETED должно содержать 'result' в data"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if event.type == EventType.TASK_COMPLETED:
            data = event.data or {}
            result = data.get("result")

            self.result_frame.reset_progress()
            self.result_frame.show_text(result)


class UIActionHandler(EventHandler):
    """Обработчик событий UI (действий), например UI_ACTION.

    Может переводить EventType.UI_ACTION -> UIEventType(event.data["action_type"]) и
    вызывать соответствующий метод (extract_addresses, compress_images и т.д.).
    """

    def handle(self, event: Event) -> None:
        """Обрабатывает событие UI_ACTION (или уже UIEventType).

        Args:
            event (Event): Событие, где event.data["action_type"] — строка из UIEventType.

        Raises:
            ValueError: При отсутствии или некорректности action_type.
            NotImplementedError: Если нет метода-обработчика для action_type.
        """
        logger.info("UIActionHandler получил событие: %s", event.type)
        logger.debug("Детали события: %s", event.data)

        # 1) Если это EventType.UI_ACTION, превращаем в UIEventType
        if event.type == EventType.UI_ACTION:
            action_type = event.data.get("action_type")
            if not action_type:
                error_msg = "UI_ACTION должно содержать action_type"
                logger.error(error_msg)
                raise ValueError(error_msg)

            try:
                event.type = UIEventType(action_type)
            except ValueError as e:
                error_msg = f"Недопустимый action_type: {action_type}"
                logger.error(error_msg)
                raise ValueError(error_msg) from e

        # 2) Теперь event.type — это UIEventType, проверяем обработчик
        if not isinstance(event.type, UIEventType):
            error_msg = f"Ожидается UIEventType, получено: {event.type}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        handler_method_name = event.type.value.lower()
        handler_method = getattr(self, handler_method_name, None)
        logger.debug("Найден метод: %s", handler_method_name)

        if not handler_method or not callable(handler_method):
            error_msg = f"Метод обработчика не найден для {event.type}"
            logger.error(error_msg)
            raise NotImplementedError(error_msg)

        # 3) Запускаем метод
        logger.info("Выполнение обработчика: %s", handler_method_name)
        handler_method()

    def extract_addresses(self) -> None:
        """Обработчик действия extract_addresses."""
        logger.info("Начало извлечения адресов")
        # ...Реализация
        logger.debug("Извлечение адресов успешно завершено")

    def compress_images(self) -> None:
        """Обработчик действия compress_images."""
        logger.info("Начало сжатия изображений")
        # ...
        logger.debug("Сжатие изображений успешно завершено")

    def check_coordinates(self) -> None:
        """Обработчик действия check_coordinates."""
        logger.info("Начало проверки координат")
        # ...
        logger.debug("Проверка координат успешно завершена")

    def extract_barcodes(self) -> None:
        """Обработчик действия extract_barcodes."""
        logger.info("Начало извлечения штрих-кодов")
        # ...
        logger.debug("Извлечение штрих-кодов успешно завершено")

    def write_test_json(self) -> None:
        """Обработчик действия write_test_json."""
        logger.info("Начало записи тестового JSON")
        # ...
        logger.debug("Запись тестового JSON успешно завершена")

    def convert_image_format(self) -> None:
        """Обработчик действия convert_image_format."""
        logger.info("Начало конвертации формата изображений")
        # ...
        logger.debug("Конвертация формата изображений успешно завершена")

    def count_unique_offers(self) -> None:
        """Обработчик действия count_unique_offers."""
        logger.info("Начало подсчета уникальных предложений")
        # ...
        logger.debug("Подсчет уникальных предложений успешно завершен")

    def compare_prices(self) -> None:
        """Обработчик действия compare_prices."""
        logger.info("Начало сравнения цен")
        # ...
        logger.debug("Сравнение цен успешно завершено")
