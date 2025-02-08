import customtkinter as ctk


class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Modern CustomTkinter Example")
        self.geometry("1100x580")

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # Create sidebar frame with widgets
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ModernApp",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_1 = ctk.CTkButton(
            self.sidebar_frame, text="Dashboard", command=self.sidebar_button_event
        )
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        self.sidebar_button_2 = ctk.CTkButton(
            self.sidebar_frame, text="Analytics", command=self.sidebar_button_event
        )
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
        self.sidebar_button_3 = ctk.CTkButton(
            self.sidebar_frame, text="Settings", command=self.sidebar_button_event
        )
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        # Create main entry and button
        self.entry = ctk.CTkEntry(self, placeholder_text="Search...")
        self.entry.grid(
            row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew"
        )

        self.main_button_1 = ctk.CTkButton(
            master=self,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            text="Search",
            command=self.search_button_event,
        )
        self.main_button_1.grid(
            row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )

        # Create tabview
        self.tabview = ctk.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("Overview")
        self.tabview.add("Analytics")
        self.tabview.add("Settings")

        # Add widgets to tabs
        self.label_tab_1 = ctk.CTkLabel(
            self.tabview.tab("Overview"), text="Overview Tab"
        )
        self.label_tab_1.grid(row=0, column=0, padx=20, pady=20)

        # Create slider and progressbar frame
        self.slider_progressbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.slider_progressbar_frame.grid(
            row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew"
        )
        self.slider_progressbar_frame.grid_columnconfigure(0, weight=1)
        self.slider_progressbar_frame.grid_rowconfigure(4, weight=1)

        self.progressbar_1 = ctk.CTkProgressBar(self.slider_progressbar_frame)
        self.progressbar_1.grid(
            row=1, column=0, padx=(20, 10), pady=(10, 10), sticky="ew"
        )
        self.progressbar_1.set(0.7)

        self.slider_1 = ctk.CTkSlider(
            self.slider_progressbar_frame, from_=0, to=1, number_of_steps=4
        )
        self.slider_1.grid(row=3, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")

        # Create right sidebar frame
        self.appearance_mode_label = ctk.CTkLabel(
            self, text="Appearance Mode:", anchor="w"
        )
        self.appearance_mode_label.grid(row=0, column=2, padx=(20, 20), pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(
            self,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
        )
        self.appearance_mode_optionemenu.grid(
            row=1, column=2, padx=(20, 20), pady=(10, 10)
        )

        # Set default values
        self.appearance_mode_optionemenu.set("Dark")
        self.slider_1.set(0.7)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def sidebar_button_event(self):
        print("Sidebar button clicked")

    def search_button_event(self):
        print("Search button clicked")


if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()
