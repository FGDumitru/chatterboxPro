# ui/tabs/generation_tab.py
import customtkinter as ctk
from tkinter import filedialog
from CTkToolTip import CTkToolTip

class GenerationTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.text_color = self.app.text_color

        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="TTS Generation Parameters", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.text_color).grid(row=0, column=0, columnspan=3, pady=10, padx=10)
        
        row = 1
        def add_slider(label, var, from_, to, steps, tooltip):
            nonlocal row
            ctk.CTkLabel(self, text=label, text_color=self.text_color).grid(row=row, column=0, padx=10, pady=5, sticky="w")
            slider = ctk.CTkSlider(self, from_=from_, to=to, number_of_steps=steps, variable=var)
            slider.grid(row=row, column=1, sticky="ew", padx=10)
            ctk.CTkLabel(self, textvariable=var, width=40, text_color=self.text_color).grid(row=row, column=2, padx=5)
            CTkToolTip(slider, message=tooltip, delay=0.2)
            row += 1

        ctk.CTkLabel(self, text="Reference Audio:", text_color=self.text_color).grid(row=row, column=0, padx=10, pady=5, sticky="w")
        ref_entry = ctk.CTkEntry(self, textvariable=self.app.ref_audio_path, text_color=self.text_color); ref_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self, text="...", width=30, command=lambda: self.app.ref_audio_path.set(filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav")]))).grid(row=row, column=2, padx=5); row += 1
        CTkToolTip(ref_entry, "Path to the WAV file to be used for voice cloning.", delay=0.2)
        
        add_slider("Exaggeration:", self.app.exaggeration, 0.0, 1.0, 100, "Controls the emotional intensity. 0.5 is neutral.")
        add_slider("CFG Weight:", self.app.cfg_weight, 0.0, 3.0, 60, "Classifier-Free Guidance. Higher values make the voice more like the reference.")
        add_slider("Temperature:", self.app.temperature, 0.1, 1.5, 140, "Controls randomness. Higher values are more diverse, lower are more deterministic.")

        def add_entry(label, var, tooltip):
            nonlocal row
            ctk.CTkLabel(self, text=label, text_color=self.text_color).grid(row=row, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(self, textvariable=var, text_color=self.text_color); entry.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
            CTkToolTip(entry, message=tooltip, delay=0.2)
            row += 1

        add_entry("Target Devices:", self.app.target_gpus_str, "Comma-separated list of devices (e.g., cuda:0,cuda:1,cpu).")
        add_entry("# of Full Outputs:", self.app.num_full_outputs_str, "How many complete audiobooks to generate (each with a different master seed if seed=0).")
        add_entry("Master Seed (0=random):", self.app.master_seed_str, "Set a seed for reproducible results. Set to 0 for random.")
        add_entry("Candidates per Chunk:", self.app.num_candidates_str, "Number of audio options to generate for each text chunk before picking the best one.")
        add_entry("ASR Max Retries:", self.app.max_attempts_str, "If ASR fails, how many times to retry generating a candidate.")
        
        ctk.CTkSwitch(self, text="Bypass ASR Validation", variable=self.app.asr_validation_enabled, onvalue=False, offvalue=True, text_color=self.text_color).grid(row=row, columnspan=3, pady=5, sticky="w", padx=10); row += 1
        ctk.CTkSwitch(self, text="Disable Perth Watermark", variable=self.app.disable_watermark, text_color=self.text_color).grid(row=row, columnspan=3, pady=5, sticky="w", padx=10); row += 1

        # --- NEW FEATURE: Save Template Button ---
        ctk.CTkButton(self, text="Save as Template...", command=self.app.save_generation_template, text_color="black").grid(row=row, column=0, columnspan=3, padx=10, pady=(20, 10), sticky="ew")