"""Тесты для менеджера состояния приложения (ApplicationState).

Этот модуль содержит тесты для проверки функциональности управления состоянием:
- Инициализация менеджера состояния
- Обновление состояния и публикация событий
- Переходы между различными состояниями
- Отслеживание истории состояний
- Потокобезопасность доступа к состоянию
- Корректность логирования
- Обработка сбоев шины событий

Фикстуры:
- mock_event_bus: Мок объект шины событий
- state_manager: Настроенный экземпляр ApplicationStateManager
"""

import logging
import threading
from unittest.mock import MagicMock

import pytest

from pythonchik.core.application_state import ApplicationState, ApplicationStateManager
from pythonchik.events.eventbus import EventBus
from pythonchik.events.events import Event, EventType


@pytest.fixture
def mock_event_bus():
    """Создает мок-объект шины событий для тестирования.

    Подготавливает экземпляр EventBus, очищает имеющиеся обработчики
    и мокает метод publish для проверки публикации событий.

    Returns:
        EventBus: Настроенный мок-объект шины событий.
    """
    bus = EventBus()
    bus.clear_all_handlers()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def state_manager(mock_event_bus):
    """Создает экземпляр менеджера состояния с мок-шиной событий.

    Args:
        mock_event_bus: Фикстура, предоставляющая мок-объект шины событий.

    Returns:
        ApplicationStateManager: Экземпляр менеджера состояния для тестирования.
    """
    manager = ApplicationStateManager(mock_event_bus)
    # Устанавливаем состояние IDLE для совместимости с существующими тестами
    manager.update_state(ApplicationState.IDLE)
    return manager


def test_initial_state(mock_event_bus):
    """Проверяет начальное состояние после создания экземпляра.

    Тест проверяет:
    1. Корректное начальное состояние менеджера (должно быть INITIALIZING)

    Args:
        mock_event_bus: Фикстура, предоставляющая мок-объект шины событий.
    """
    # Создаем новый экземпляр менеджера без использования фикстуры,
    # так как фикстура устанавливает состояние в IDLE
    fresh_manager = ApplicationStateManager(mock_event_bus)
    assert fresh_manager.state == ApplicationState.INITIALIZING


def test_update_state(state_manager, mock_event_bus):
    """Проверяет корректное обновление состояния и публикацию события.

    Тест проверяет:
    1. Успешное изменение состояния через метод update_state
    2. Публикацию события о смене состояния в шину событий
    3. Корректные данные в опубликованном событии (старое и новое состояния)

    Args:
        state_manager: Фикстура, предоставляющая экземпляр ApplicationStateManager.
        mock_event_bus: Фикстура, предоставляющая мок шины событий.
    """
    # Сохраняем текущее состояние перед обновлением
    old_state = state_manager.state

    # Сбрасываем счетчик вызовов publish, чтобы не учитывать вызов в фикстуре
    mock_event_bus.publish.reset_mock()

    # Обновляем состояние
    state_manager.update_state(ApplicationState.PROCESSING)

    # Проверяем новое состояние
    assert state_manager.state == ApplicationState.PROCESSING

    # Проверяем, что метод publish был вызван один раз
    mock_event_bus.publish.assert_called_once()

    # Проверяем параметры опубликованного события
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == EventType.STATE_CHANGED
    assert event.data == {"old_state": old_state, "new_state": ApplicationState.PROCESSING}


def test_update_same_state(state_manager, mock_event_bus):
    """Проверяет, что при установке того же состояния событие не публикуется.

    Тест проверяет:
    1. Отсутствие публикации события при обновлении состояния на то же самое
    2. Сохранение текущего состояния без изменений

    Args:
        state_manager: Фикстура, предоставляющая экземпляр ApplicationStateManager.
        mock_event_bus: Фикстура, предоставляющая мок шины событий.
    """
    # Запоминаем текущее состояние
    current_state = state_manager.state

    # Сбрасываем счетчик вызовов publish, чтобы не учитывать вызов в фикстуре
    mock_event_bus.publish.reset_mock()

    # Пытаемся обновить состояние на то же самое
    state_manager.update_state(current_state)

    # Проверяем, что метод publish не был вызван
    mock_event_bus.publish.assert_not_called()

    # Проверяем, что состояние не изменилось
    assert state_manager.state == current_state


def test_error_state_transition(state_manager, mock_event_bus):
    """Проверяем переход в состояние ERROR и обратно."""
    # Переход IDLE -> ERROR
    state_manager.update_state(ApplicationState.ERROR)
    assert state_manager.state == ApplicationState.ERROR

    # Проверяем первое событие
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == EventType.STATE_CHANGED
    assert event.data["new_state"] == ApplicationState.ERROR

    # Переход ERROR -> IDLE
    state_manager.update_state(ApplicationState.IDLE)
    assert state_manager.state == ApplicationState.IDLE

    # Проверяем второе событие
    event = mock_event_bus.publish.call_args_list[-1][0][0]
    assert event.data["old_state"] == ApplicationState.ERROR
    assert event.data["new_state"] == ApplicationState.IDLE


def test_invalid_state_transition(state_manager):
    """Проверяем, что нельзя установить некорректное состояние."""
    with pytest.raises(ValueError):
        state_manager.update_state("INVALID_STATE")

    # Состояние не должно измениться
    assert state_manager.state == ApplicationState.IDLE

    # Проверяем другие некорректные типы
    with pytest.raises(ValueError):
        state_manager.update_state(None)

    with pytest.raises(ValueError):
        state_manager.update_state(123)

    # Состояние все еще не должно измениться
    assert state_manager.state == ApplicationState.IDLE


def test_state_history(state_manager, mock_event_bus):
    """Проверяем корректность истории состояний."""
    # Создаём последовательность переходов
    transitions = [
        ApplicationState.PROCESSING,
        ApplicationState.ERROR,
        ApplicationState.IDLE,
        ApplicationState.PROCESSING,
    ]

    # Сбрасываем счетчик вызовов publish, чтобы не учитывать вызов в фикстуре
    mock_event_bus.publish.reset_mock()

    # Выполняем переходы
    for new_state in transitions:
        state_manager.update_state(new_state)

    # Проверяем последнее состояние
    assert state_manager.state == ApplicationState.PROCESSING

    # Проверяем, что все события были опубликованы
    assert mock_event_bus.publish.call_count == len(transitions)

    # Проверяем последовательность переходов в событиях
    events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
    for i, event in enumerate(events):
        assert event.type == EventType.STATE_CHANGED
        if i > 0:
            assert event.data["old_state"] == transitions[i - 1]
        assert event.data["new_state"] == transitions[i]


def test_thread_safety(state_manager):
    """Проверяем потокобезопасность обновления состояния."""

    def update_state_repeatedly():
        for _ in range(100):
            state_manager.update_state(ApplicationState.PROCESSING)
            state_manager.update_state(ApplicationState.IDLE)

    # Запускаем параллельные потоки
    threads = [threading.Thread(target=update_state_repeatedly) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Проверяем, что финальное состояние валидно
    assert state_manager.state in [ApplicationState.PROCESSING, ApplicationState.IDLE]


def test_state_property_thread_safety(state_manager):
    """Проверяем потокобезопасность доступа к свойству state."""
    states = []

    def read_state_repeatedly():
        for _ in range(100):
            states.append(state_manager.state)

    # Запускаем параллельные потоки для чтения состояния
    threads = [threading.Thread(target=read_state_repeatedly) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Проверяем, что все прочитанные состояния валидны
    for state in states:
        assert isinstance(state, ApplicationState)


def test_shutdown_state_transition(state_manager):
    """Проверяем переход в состояние SHUTTING_DOWN и обратно."""
    # Переход в SHUTTING_DOWN
    state_manager.update_state(ApplicationState.SHUTTING_DOWN)
    assert state_manager.state == ApplicationState.SHUTTING_DOWN

    # Проверяем возможность перехода из SHUTTING_DOWN в другие состояния
    state_manager.update_state(ApplicationState.IDLE)
    assert state_manager.state == ApplicationState.IDLE


def test_state_transitions_under_load(state_manager):
    """Проверяем корректность переходов состояний при высокой нагрузке."""
    states = [
        ApplicationState.PROCESSING,
        ApplicationState.WAITING,
        ApplicationState.READY,
        ApplicationState.PAUSED,
    ]

    def rapid_state_changes():
        for _ in range(50):  # Большое количество быстрых переходов
            for state in states:
                state_manager.update_state(state)

    # Запускаем несколько потоков для создания нагрузки
    threads = [threading.Thread(target=rapid_state_changes) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Проверяем, что финальное состояние валидно
    assert isinstance(state_manager.state, ApplicationState)
    assert state_manager.state in states


def test_logging_correctness(state_manager, monkeypatch):
    """Проверяем корректность логирования изменений состояния."""
    # Создаем мок-объект для логгера
    mock_logger = MagicMock()
    # Сохраняем оригинальный логгер
    original_logger = state_manager._logger
    # Заменяем логгер на мок
    monkeypatch.setattr(state_manager, "_logger", mock_logger)

    try:
        # Выполняем тестируемые действия
        state_manager.update_state(ApplicationState.PROCESSING)
        state_manager.update_state(ApplicationState.ERROR)

        # Проверяем, что метод info логгера был вызван с нужными сообщениями
        # Ищем вызов с сообщением о переходе IDLE -> PROCESSING
        idle_to_processing_call = any(
            "Смена состояния: IDLE -> PROCESSING" in call[0][0] for call in mock_logger.info.call_args_list
        )

        # Ищем вызов с сообщением о переходе PROCESSING -> ERROR
        processing_to_error_call = any(
            "Смена состояния: PROCESSING -> ERROR" in call[0][0] for call in mock_logger.info.call_args_list
        )

        # Проверяем наличие обоих вызовов
        assert idle_to_processing_call, "Не найден лог о переходе IDLE -> PROCESSING"
        assert processing_to_error_call, "Не найден лог о переходе PROCESSING -> ERROR"

    finally:
        # Восстанавливаем оригинальный логгер
        monkeypatch.setattr(state_manager, "_logger", original_logger)


def test_event_bus_failure(state_manager, mock_event_bus):
    """Проверяем поведение при сбое event_bus."""
    # Симулируем сбой при публикации события
    mock_event_bus.publish.side_effect = Exception("Event bus failure")

    try:
        # Проверяем, что состояние обновляется даже при сбое event_bus
        state_manager.update_state(ApplicationState.PROCESSING)
        assert state_manager.state == ApplicationState.PROCESSING
    except Exception as e:
        # Проверяем, что исключение от event_bus не повлияло на состояние
        assert state_manager.state == ApplicationState.PROCESSING
        assert str(e) == "Event bus failure"
