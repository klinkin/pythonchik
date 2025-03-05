"""Тесты компонентов ядра приложения Pythonchik.

Этот пакет содержит тесты для компонентов ядра приложения, отвечающих за
управление жизненным циклом, обработку задач в фоновом режиме, управление
состоянием и взаимодействие с системой событий.

Основные тестовые модули:
- test_application_core.py: Проверка функциональности базового ядра приложения
- test_core.py: Тесты интерфейсов и основных операций ядра
- test_state.py: Тесты менеджера состояния и переходов между состояниями

Фикстуры:
- event_bus: Изолированная шина событий для тестирования
- app_core: Настроенный экземпляр ApplicationCore
- state_manager: Экземпляр ApplicationStateManager с начальным состоянием

Тестовые сценарии:
- Инициализация и корректное завершение работы ядра
- Добавление и выполнение задач в фоновом режиме
- Обработка ошибок в задачах
- Переходы между состояниями приложения
- Потокобезопасность операций
- Публикация событий о смене состояния
- Восстановление после ошибок в рабочем потоке

Примеры тестов:
    # Проверка инициализации
    def test_initialization(app_core):
        # Проверка начальных значений
        assert not app_core._is_running
        assert isinstance(app_core._processing_queue, Queue)
        assert app_core.state_manager.state == ApplicationState.IDLE

    # Проверка переходов состояний
    def test_state_transitions(state_manager):
        # Тестирование последовательности переходов
        state_manager.update_state(ApplicationState.PROCESSING)
        assert state_manager.state == ApplicationState.PROCESSING

        state_manager.update_state(ApplicationState.IDLE)
        assert state_manager.state == ApplicationState.IDLE

Для запуска тестов ядра используйте:
    $ poetry run pytest tests/core/
"""
