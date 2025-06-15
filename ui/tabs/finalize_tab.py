# ui/tabs/finalize_tab.py
import customtkinter as ctk

class FinalizeTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.text_color = self.app.text_color

        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Audiobook Assembly & Finalization", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.text_color).pack(pady=10, anchor="w", padx=10)

        ctk.CTkSwitch(self, text="Enable Smart Chunking", variable=self.app.chunking_enabled, text_color=self.text_color).pack(anchor="w", padx=10, pady=5)

        chunk_frame = ctk.CTkFrame(self, fg_color="transparent"); chunk_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(chunk_frame, text="Max Chars per Chunk:", text_color=self.text_color).pack(side="left")
        ctk.CTkEntry(chunk_frame, textvariable=self.app.max_chunk_chars_str, width=80, text_color=self.text_color).pack(side="left", padx=5)

        silence_frame = ctk.CTkFrame(self, fg_color="transparent"); silence_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(silence_frame, text="Silence Between Chunks (ms):", text_color=self.text_color).pack(side="left")
        ctk.CTkEntry(silence_frame, textvariable=self.app.silence_duration_str, width=80, text_color=self.text_color).pack(side="left", padx=5)

        norm_frame = ctk.CTkFrame(self, fg_color=self.app.colors["tab_bg"]); norm_frame.pack(fill="x", padx=10, pady=10)
        self.norm_switch = ctk.CTkSwitch(norm_frame, text="Enable Audio Normalization (EBU R128)", variable=self.app.norm_enabled, state="normal" if self.app.deps.ffmpeg_ok else "disabled", text_color=self.text_color)
        self.norm_switch.pack(anchor="w", padx=10, pady=(10,5))
        norm_level_frame = ctk.CTkFrame(norm_frame, fg_color="transparent"); norm_level_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(norm_level_frame, text="Target Loudness (LUFS):", text_color=self.text_color).pack(side="left")
        ctk.CTkEntry(norm_level_frame, textvariable=self.app.norm_level_str, width=80, text_color=self.text_color).pack(side="left", padx=5)

        silence_frame = ctk.CTkFrame(self, fg_color=self.app.colors["tab_bg"]); silence_frame.pack(fill="x", padx=10, pady=10)
        self.silence_switch = ctk.CTkSwitch(silence_frame, text="Enable Silence Removal (auto-editor)", variable=self.app.silence_removal_enabled, state="normal" if self.app.deps.auto_editor_ok else "disabled", text_color=self.text_color)
        self.silence_switch.pack(anchor="w", padx=10, pady=(10,5))
        silence_thresh_frame = ctk.CTkFrame(silence_frame, fg_color="transparent"); silence_thresh_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(silence_thresh_frame, text="Silence Threshold (e.g., 0.04):", text_color=self.text_color).pack(side="left")
        ctk.CTkEntry(silence_thresh_frame, textvariable=self.app.silence_threshold, width=80, text_color=self.text_color).pack(side="left", padx=5)

        ctk.CTkButton(self, text="Assemble Final Audiobook", command=lambda: self.app.audio_manager.assemble_audiobook(), height=40, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#1E8449", hover_color="#145A32", text_color="white").pack(fill="x", padx=10, pady=(20, 10))