import pytest

from pythonchik.utils.event_system import (
    Event,
    EventBus,
    EventCategory,
    EventHandler,
    EventPriority,
    EventType,
)


class DummyHandler(EventHandler):
    def __init__(self):
        super().__init__()
        self.handled_events = []

    def handle(self, event: Event):
        self.handled_events.append(event.type)


def test_subscribe_unsubscribe():
    bus = EventBus()
    bus.clear_all_handlers()
    h = DummyHandler()

    bus.subscribe(EventType.DATA_UPDATED, h)
    assert bus.get_handlers_count(EventType.DATA_UPDATED) == 1

    bus.unsubscribe(EventType.DATA_UPDATED, h)
    assert bus.get_handlers_count(EventType.DATA_UPDATED) == 0


def test_publish_event():
    bus = EventBus()
    bus.clear_all_handlers()
    h = DummyHandler()
    bus.subscribe(EventType.DATA_UPDATED, h)

    e = Event(type=EventType.DATA_UPDATED, data={"info": "test"})
    bus.publish(e)

    # _process_queue() происходит синхронно, поэтому можем сразу проверить
    assert len(h.handled_events) == 1
    assert h.handled_events[0] == EventType.DATA_UPDATED


def test_error_handler():
    bus = EventBus()
    bus.clear_all_handlers()

    class BrokenHandler(EventHandler):
        def handle(self, event: Event):
            raise ValueError("Simulated error in handler")

    errors_caught = []

    def on_error(exc: Exception):
        errors_caught.append(str(exc))

    bus.add_error_handler(on_error)
    broken = BrokenHandler()
    bus.subscribe(EventType.TASK_COMPLETED, broken)

    bus.publish(Event(type=EventType.TASK_COMPLETED, data={"foo": "bar"}))
    # _process_queue() done
    assert len(errors_caught) == 1
    assert "Simulated error" in errors_caught[0]


def test_priority():
    bus = EventBus()
    bus.clear_all_handlers()
    h = DummyHandler()
    bus.subscribe(EventType.DATA_UPDATED, h)
    bus.subscribe(EventType.ERROR_OCCURRED, h)  # CRITICAL priority
    bus.subscribe(EventType.UI_ACTION, h)  # LOW priority

    # Публикуем 3 события: ERROR_OCCURRED (critical), DATA_UPDATED (normal), UI_ACTION (low)
    # Порядок добавления: first low, second normal, third critical
    # Но теперь immediate=False, чтобы они не обрабатывались по одному.
    e1 = Event(type=EventType.UI_ACTION)  # LOW
    e2 = Event(type=EventType.DATA_UPDATED)  # NORMAL
    e3 = Event(type=EventType.ERROR_OCCURRED)  # CRITICAL

    bus.publish(e1, immediate=False)
    bus.publish(e2, immediate=False)
    bus.publish(e3, immediate=False)

    # Теперь вручную вызываем _process_queue()
    bus._process_queue()

    # Ожидаем, что порядок будет: CRITICAL -> NORMAL -> LOW
    assert h.handled_events == [
        EventType.ERROR_OCCURRED,  # CRITICAL
        EventType.DATA_UPDATED,  # NORMAL
        EventType.UI_ACTION,  # LOW
    ]
