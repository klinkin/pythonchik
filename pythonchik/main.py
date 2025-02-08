"""Entry point for the Pythonchik application."""

from pythonchik.ui.app import ModernApp


def main() -> None:
    """Application entry point."""
    app = ModernApp()
    app.mainloop()


if __name__ == "__main__":
    main()
