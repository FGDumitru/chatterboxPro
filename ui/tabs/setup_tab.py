# ui/tabs/setup_tab.py
import customtkinter as ctk

class SetupTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance

        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text="Session & Source File", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.app.text_color).pack(pady=(10, 5), anchor="w", padx=10)
        
        ctk.CTkLabel(self, text="Session Name:", text_color=self.app.text_color).pack(anchor="w", padx=10)
        ctk.CTkEntry(self, textvariable=self.app.session_name, text_color=self.app.text_color).pack(fill="x", padx=10)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.pack(fill="x", pady=5, padx=5)
        btn_frame.grid_columnconfigure((0,1), weight=1)
        ctk.CTkButton(btn_frame, text="New Session", command=self.app.new_session, text_color="black").grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Load Session", command=self.app.load_session, text_color="black").grid(row=0, column=1, padx=5, sticky="ew")

        ctk.CTkLabel(self, text="Source File:", text_color=self.app.text_color).pack(anchor="w", padx=10, pady=(10,0))
        self.app.source_file_label = ctk.CTkLabel(self, text="No file selected.", wraplength=350, text_color=self.app.text_color); self.app.source_file_label.pack(anchor="w", padx=10)
        ctk.CTkButton(self, text="Select File...", command=self.app.select_source_file, text_color="black").pack(fill="x", padx=10, pady=5)
        self.app.process_button = ctk.CTkButton(self, text="Process Text File", command=self.app.process_file_content, text_color="black")
        self.app.process_button.pack(fill="x", padx=10, pady=10)

        # --- NEW FEATURE: Generation Templates ---
        template_frame = ctk.CTkFrame(self, fg_color=self.app.colors["tab_bg"])
        template_frame.pack(fill="x", padx=10, pady=(10,5))
        template_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(template_frame, text="Generation Templates", font=ctk.CTkFont(weight="bold"), text_color=self.app.text_color).grid(row=0, column=0, columnspan=2, pady=(5,0))
        self.app.template_option_menu = ctk.CTkOptionMenu(template_frame, variable=self.app.selected_template_str, values=["No templates found"], text_color=self.app.text_color)
        self.app.template_option_menu.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(template_frame, text="Load", command=self.app.load_generation_template, text_color="black", width=70).grid(row=1, column=1, padx=(0,10), pady=5)

        ctk.CTkLabel(self, text="Main Controls", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.app.text_color).pack(pady=(10, 5), anchor="w", padx=10)
        self.app.start_stop_button = ctk.CTkButton(self, text="Start Generation", command=self.app.toggle_generation_main, height=40, font=ctk.CTkFont(size=14, weight="bold"), text_color="black")
        self.app.start_stop_button.pack(fill="x", padx=10, pady=5)
        self.app.progress_bar = ctk.CTkProgressBar(self, progress_color="#3A7EBF"); self.app.progress_bar.pack(fill="x", padx=10, pady=(10,0)); self.app.progress_bar.set(0)
        self.app.progress_label = ctk.CTkLabel(self, text="0/0 (0.00%)", text_color=self.app.text_color); self.app.progress_label.pack()

        sys_check_frame = ctk.CTkFrame(self, fg_color=self.app.colors["tab_bg"]); sys_check_frame.pack(fill="x", padx=10, pady=(20, 5))
        ctk.CTkLabel(sys_check_frame, text="System Check", font=ctk.CTkFont(weight="bold"), text_color=self.app.text_color).pack()
        ctk.CTkLabel(sys_check_frame, text=f"FFmpeg: {'Found' if self.app.deps.ffmpeg_ok else 'Not Found'}", text_color="green" if self.app.deps.ffmpeg_ok else "#A40000").pack(anchor="w", padx=10)
        ctk.CTkLabel(sys_check_frame, text=f"auto-editor: {'Found' if self.app.deps.auto_editor_ok else 'Not Found'}", text_color="green" if self.app.deps.auto_editor_ok else "#A40000").pack(anchor="w", padx=10)