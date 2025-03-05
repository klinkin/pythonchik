"""State frame component for displaying application state."""

import customtkinter as ctk

from pythonchik.core.application_state import ApplicationState
from pythonchik.utils.event_system import Event, EventType


class StateFrame(ctk.CTkFrame):
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

    def __init__(self, master, **kwargs):
        """Initialize the state frame.

        Args:
            master: Parent widget
            event_bus: EventBus instance for subscribing to state changes
        """
        super().__init__(master, **kwargs)

        # Create state label
        self.state_label = ctk.CTkLabel(
            self,
            text="IDLE",
            font=("Helvetica", 12, "bold"),
            text_color="white",
            width=100,
            fg_color=self.STATE_COLORS[ApplicationState.IDLE],
        )
        self.state_label.pack(padx=10, pady=5)

    def update_state(self, state: ApplicationState) -> None:
        """Update the state display with new state.

        Args:
            state (ApplicationState): New application state to display
        """

        def _update():
            self.state_label.configure(
                text=state.value.upper(), fg_color=self.STATE_COLORS.get(state, "#95a5a6")
            )

        # Schedule the update on the main thread
        self.after(0, _update)
