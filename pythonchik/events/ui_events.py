"""UI-специфичные типы событий и сигналы для приложения Pythonchik.

Описание:
Этот модуль определяет UI-специфичные события и сигналы для реализации правильной
событийно-ориентированной архитектуры для UI действий. Он предоставляет типобезопасный
способ обработки UI событий и связанных с ними данных во всем приложении.

Note:
Использует систему типизированных событий для UI взаимодействий

Пример использования:
from pythonchik.ui.events import UIEventType, UIActionEvent

event = UIActionEvent(type=UIEventType.NAVIGATE_HOME)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pythonchik.events.events import Event, EventCategory, EventPriority, EventType


class UIEventType(Enum):
    """UI-специфичные типы событий с их категориями и приоритетами.

    Описание:
        Этот класс определяет все возможные типы UI событий, которые могут быть
        отправлены и обработаны в приложении, организованные по функциональным категориям.

    Note:
        Группирует события по категориям и приоритетам
    """

    # Операции с JSON
    EXTRACT_ADDRESSES = "EXTRACT_ADDRESSES"
    CHECK_COORDINATES = "CHECK_COORDINATES"
    EXTRACT_BARCODES = "EXTRACT_BARCODES"
    WRITE_TEST_JSON = "WRITE_TEST_JSON"

    # Операции с изображениями
    COMPRESS_IMAGES = "COMPRESS_IMAGES"
    CONVERT_IMAGE_FORMAT = "CONVERT_IMAGE_FORMAT"

    # Операции анализа
    COUNT_UNIQUE_OFFERS = "COUNT_UNIQUE_OFFERS"
    COMPARE_PRICES = "COMPARE_PRICES"

    # События навигации
    NAVIGATE_HOME = "NAVIGATE_HOME"
    NAVIGATE_SETTINGS = "NAVIGATE_SETTINGS"

    # События изменения состояния
    UPDATE_THEME = "UPDATE_THEME"
    UPDATE_LANGUAGE = "UPDATE_LANGUAGE"

    def get_category(self) -> EventCategory:
        """Get the event category for this UI event type."""
        return EventCategory.UI

    def get_priority(self) -> EventPriority:
        """Get the event priority for this UI event type."""
        return (
            EventPriority.HIGH
            if self in [self.NAVIGATE_HOME, self.NAVIGATE_SETTINGS, self.UPDATE_THEME, self.UPDATE_LANGUAGE]
            else EventPriority.NORMAL
        )


@dataclass()
class UIActionEvent(Event):
    """Класс событий для UI действий с определенными типами данных.

    Описание:
        Определяет структуру данных для UI событий с типизированными полями.

    Args:
        type: Тип UI действия
        data: Дополнительные данные события (опционально)
        target_format: Целевой формат для операций преобразования (опционально)
        image_paths: Пути к изображениям для обработки (опционально)
        output_path: Путь для сохранения результатов (опционально)

    Note:
        Использует dataclass для автоматической генерации методов
    """

    type: UIEventType
    data: Optional[Dict[str, Any]] = None
    target_format: Optional[str] = None
    image_paths: Optional[List[str]] = None
    output_path: Optional[str] = None
