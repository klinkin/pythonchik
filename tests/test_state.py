import pytest
from unittest.mock import MagicMock

from pythonchik.core.application_state import ApplicationState, ApplicationStateManager
from pythonchik.utils.event_system import Event, EventBus, EventType

@pytest.fixture
def mock_event_bus():
    """Фикстура для создания мок-объекта EventBus."""
    bus = EventBus()
    bus.clear_all_handlers()
    bus.publish = MagicMock()
    return bus

@pytest.fixture
def state_manager(mock_event_bus):
    """Фикстура для создания StateManager с мок-шиной событий."""
    return ApplicationStateManager(mock_event_bus)

def test_initial_state(state_manager):
    """Проверяем начальное состояние после создания."""
    assert state_manager.state == ApplicationState.IDLE

def test_update_state(state_manager, mock_event_bus):
    """Проверяем корректное обновление состояния и публикацию события."""
    state_manager.update_state(ApplicationState.PROCESSING)

    assert state_manager.state == ApplicationState.PROCESSING
    mock_event_bus.publish.assert_called_once()

    # Проверяем параметры опубликованного события
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == EventType.STATE_CHANGED
    assert event.data == {
        'old_state': ApplicationState.IDLE,
        'new_state': ApplicationState.PROCESSING
    }

def test_update_same_state(state_manager, mock_event_bus):
    """Проверяем, что при установке того же состояния событие не публикуется."""
    state_manager.update_state(ApplicationState.IDLE)
    mock_event_bus.publish.assert_not_called()

def test_error_state_transition(state_manager, mock_event_bus):
    """Проверяем переход в состояние ERROR и обратно."""
    # Переход IDLE -> ERROR
    state_manager.update_state(ApplicationState.ERROR)
    assert state_manager.state == ApplicationState.ERROR

    # Проверяем первое событие
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == EventType.STATE_CHANGED
    assert event.data['new_state'] == ApplicationState.ERROR

    # Переход ERROR -> IDLE
    state_manager.update_state(ApplicationState.IDLE)
    assert state_manager.state == ApplicationState.IDLE

    # Проверяем второе событие
    event = mock_event_bus.publish.call_args_list[-1][0][0]
    assert event.data['old_state'] == ApplicationState.ERROR
    assert event.data['new_state'] == ApplicationState.IDLE

def test_invalid_state_transition(state_manager):
    """Проверяем, что нельзя установить некорректное состояние."""
    with pytest.raises(ValueError):
        state_manager.update_state('INVALID_STATE')

    # Состояние не должно измениться
    assert state_manager.state == ApplicationState.IDLE

def test_state_history(state_manager, mock_event_bus):
    """Проверяем корректность истории состояний."""
    # Создаём последовательность переходов
    transitions = [
        ApplicationState.PROCESSING,
        ApplicationState.ERROR,
        ApplicationState.IDLE,
        ApplicationState.PROCESSING
    ]

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
            assert event.data['old_state'] == transitions[i-1]
        assert event.data['new_state'] == transitions[i]
