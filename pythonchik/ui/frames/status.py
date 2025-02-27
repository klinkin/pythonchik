"""Status frame component for displaying application state."""

import customtkinter as ctk

from pythonchik.core import ApplicationState
from pythonchik.utils.event_system import Event, EventType


class StatusFrame(ctk.CTkFrame):
    """Frame for displaying the current application state.

    Shows the current ApplicationState with appropriate styling.
    Subscribes to STATE_CHANGED events to update automatically.
    """

    # Color mapping for different states
    STATE_COLORS = {
        ApplicationState.IDLE: "#2ecc71",  # Green
        ApplicationState.PROCESSING: "#3498db",  # Blue
        ApplicationState.ERROR: "#e74c3c",  # Red
        ApplicationState.WAITING: "#f1c40f",  # Yellow
        ApplicationState.PAUSED: "#95a5a6",  # Gray
        ApplicationState.INITIALIZING: "#9b59b6",  # Purple
        ApplicationState.READY: "#2ecc71",  # Green
        ApplicationState.SHUTTING_DOWN: "#e67e22",  # Orange
    }

    def __init__(self, master, event_bus, **kwargs):
        """Initialize the status frame.

        Args:
            master: Parent widget
            event_bus: EventBus instance for subscribing to state changes
        """
        super().__init__(master, **kwargs)

        self.event_bus = event_bus

        # Create status label
        self.status_label = ctk.CTkLabel(
            self,
            text="IDLE",
            font=("Helvetica", 12, "bold"),
            text_color="white",
            width=100,
            fg_color=self.STATE_COLORS[ApplicationState.IDLE],
        )
        self.status_label.pack(padx=10, pady=5)

        # Subscribe to state changes
        self.event_bus.subscribe(EventType.STATE_CHANGED, self.on_state_changed)

    def on_state_changed(self, event: Event) -> None:
        """Handle state change events.

        Args:
            event (Event): The state change event containing new state
        """
        new_state = event.data.get("new_state")
        if new_state:
            self.update_status(new_state)

    def update_status(self, state: ApplicationState) -> None:
        """Update the status display with new state.

        Args:
            state (ApplicationState): New application state to display
        """
        # Update label text and color
        self.status_label.configure(
            text=state.value.upper(), fg_color=self.STATE_COLORS.get(state, "#95a5a6")
        )
