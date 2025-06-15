# ui/main_window.py
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pygame
import os
import gc
import json
import logging
import re
from pathlib import Path
import shutil
import threading
import torch
import time
import uuid # NEW: Import for generating unique IDs

from ui.playlist import PlaylistFrame
from ui.tabs.setup_tab import SetupTab
from ui.tabs.generation_tab import GenerationTab
from ui.tabs.finalize_tab import FinalizeTab
from ui.tabs.advanced_tab import AdvancedTab

from core.orchestrator import GenerationOrchestrator
from core.audio_manager import AudioManager
from utils.text_processor import TextPreprocessor

# Optional dependencies for file processing
try:
    from bs4 import BeautifulSoup
    from pdftextract import XPdf
    import ebooklib
    from ebooklib import epub
    import pypandoc
except ImportError as e:
    logging.warning(f"Optional file processing dependency missing. Some file types may not be supported: {e}")

class ChatterboxProGUI(ctk.CTk):
    """The main application window class."""
    def __init__(self, dependency_manager):
        super().__init__()
        self.deps = dependency_manager
        self.title("Chatterbox Pro Audiobook Generator")
        self.geometry("1600x900")

        # --- UI THEME ---
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.text_color = "#101010"
        self.colors = {
            "frame_bg": "#F9F9F9", "tab_bg": "#EAEAEA", "selection": "#3A7EBF",
            "marked": "#FFDCDC", "failed": "#A40000"
        }
        self.button_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        self.button_hover_color = ctk.ThemeManager.theme["CTkButton"]["hover_color"]

        pygame.mixer.init()

        try:
            self.iconbitmap("assets/icon.ico")
        except tk.TclError:
            logging.warning("assets/icon.ico not found. Continuing without an icon.")

        # Core Components & State
        self.orchestrator = GenerationOrchestrator(self)
        self.audio_manager = AudioManager(self)
        self.text_processor = TextPreprocessor()
        self.OUTPUTS_DIR = "Outputs_Pro"
        self.TEMPLATES_DIR = "Templates"
        os.makedirs(self.TEMPLATES_DIR, exist_ok=True)
        
        self.session_name, self.source_file_path, self.sentences = ctk.StringVar(), "", []
        self.generation_thread, self.stop_flag = None, threading.Event()
        self.is_playlist_playing, self.current_playing_sound, self.playlist_index = False, None, 0

        # UI Config Variables
        self.ref_audio_path = ctk.StringVar()
        self.exaggeration, self.cfg_weight, self.temperature = ctk.DoubleVar(value=0.5), ctk.DoubleVar(value=0.7), ctk.DoubleVar(value=0.8)
        self.target_gpus_str = ctk.StringVar(value=",".join([f"cuda:{i}" for i in range(torch.cuda.device_count())]) if torch.cuda.is_available() else "cpu")
        self.num_full_outputs_str, self.master_seed_str = ctk.StringVar(value="1"), ctk.StringVar(value="0")
        self.num_candidates_str, self.max_attempts_str = ctk.StringVar(value="1"), ctk.StringVar(value="3")
        self.asr_validation_enabled = ctk.BooleanVar(value=True)
        self.disable_watermark = ctk.BooleanVar(value=True)
        
        self.chunking_enabled = ctk.BooleanVar(value=True)
        self.max_chunk_chars_str = ctk.StringVar(value="350")
        self.silence_duration_str = ctk.StringVar(value="250")
        self.norm_enabled, self.silence_removal_enabled = ctk.BooleanVar(value=False), ctk.BooleanVar(value=False)
        self.norm_level_str = ctk.StringVar(value="-23.0")
        self.silence_threshold = ctk.StringVar(value="0.04")

        self.llm_api_url = ctk.StringVar(value="http://127.0.0.1:5000/v1/chat/completions")
        self.llm_enabled = ctk.BooleanVar(value=False)
        
        self.selected_template_str = ctk.StringVar()

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.show_dependency_warnings)
        self.populate_template_dropdown()

    def show_dependency_warnings(self):
        warnings = []
        if not self.deps.pandoc_ok: warnings.append("- Pandoc not found. DOCX and MOBI file support is disabled.")
        if not self.deps.ffmpeg_ok: warnings.append("- FFmpeg not found. Audio normalization will be disabled.")
        if not self.deps.auto_editor_ok: warnings.append("- auto-editor not found. Silence removal will be disabled.")
        if warnings: messagebox.showwarning("Dependency Warning", "Some features are disabled due to missing dependencies:\n\n" + "\n".join(warnings) + "\n\nPlease install/update them and restart the application to enable all features.")

    def get_validated_int(self, var, default_val):
        try: return int(var.get())
        except (ValueError, tk.TclError): return default_val

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit? This will stop any ongoing generation."):
            logging.info("Shutdown signal received. Terminating processes.")
            self.stop_flag.set()
            self.stop_playback()
            if self.generation_thread and self.generation_thread.is_alive():
                self.generation_thread.join(timeout=5)
            self.save_session()
            self.destroy()

    def toggle_generation_main(self):
        if self.generation_thread and self.generation_thread.is_alive():
            self.stop_generation()
        else:
            self.start_generation_orchestrator()

    def start_generation_orchestrator(self, indices_to_process=None):
        if not self.sentences: return messagebox.showerror("Error", "No sentences to generate. Process a text file first.")
        if not self.ref_audio_path.get() or not os.path.exists(self.ref_audio_path.get()): return messagebox.showerror("Error", "Please provide a valid reference audio file.")
        self.stop_flag.clear()
        self.start_stop_button.configure(text="Stop Generation", fg_color="#D22B2B", hover_color="#B02525")
        self.generation_thread = threading.Thread(target=self.orchestrator.run, args=(indices_to_process,), daemon=True)
        self.generation_thread.start()

    def stop_generation(self):
        if self.generation_thread and self.generation_thread.is_alive():
            self.stop_flag.set()
            self.start_stop_button.configure(text="Stopping...", state="disabled")
            logging.info("Stop signal sent. Generation will halt after the current chunks complete.")

    def new_session(self):
        name = ctk.CTkInputDialog(text="Enter session name (letters, numbers, _, -):", title="New Session").get_input()
        if name and re.match("^[a-zA-Z0-9_-]*$", name):
            session_path = Path(self.OUTPUTS_DIR) / name
            if session_path.exists():
                if not messagebox.askyesno("Overwrite?", f"Session '{name}' exists. This will delete its contents. Continue?"): return
                shutil.rmtree(session_path)
            session_path.mkdir(parents=True)
            self.session_name.set(name)
            self.source_file_path, self.sentences = "", []
            self.source_file_label.configure(text="No file selected.")
            self.playlist_frame.load_data(self.sentences)
            self.update_progress_display(0,0,0)
            self.save_session()
        elif name:
            messagebox.showerror("Invalid Name", "Session name can only contain letters, numbers, underscores, and hyphens.")

    def load_session(self):
        path_str = filedialog.askdirectory(initialdir=self.OUTPUTS_DIR, title="Select Session Folder")
        if path_str:
            session_path = Path(path_str)
            json_path = session_path / f"{session_path.name}_session.json"
            if not json_path.exists(): return messagebox.showerror("Error", "Session file not found.")
            with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
            
            self.session_name.set(session_path.name)
            self.source_file_path = data.get("source_file_path", "")
            self.source_file_label.configure(text=os.path.basename(self.source_file_path) or "No file selected.")
            self.sentences = data.get("sentences", [])
            
            session_upgraded = False
            for sentence in self.sentences:
                if 'uuid' not in sentence:
                    sentence['uuid'] = uuid.uuid4().hex
                    session_upgraded = True
            
            if session_upgraded:
                logging.warning("Old session format detected. Upgrading with UUIDs. The session will be saved in the new format.")
                self.save_session()
            
            if "generation_settings" in data:
                self._apply_generation_settings(data["generation_settings"])
                logging.info("Loaded generation settings from session file.")

            self.playlist_frame.load_data(self.sentences)
            gen_count = sum(1 for s in self.sentences if s.get("tts_generated") == "yes")
            self.update_progress_display(gen_count/len(self.sentences) if self.sentences else 0, gen_count, len(self.sentences))
            logging.info(f"Loaded session: {session_path.name}")

    def save_session(self):
        if not self.session_name.get(): return
        session_path = Path(self.OUTPUTS_DIR) / self.session_name.get()
        session_path.mkdir(exist_ok=True)
        
        session_data = {
            "source_file_path": self.source_file_path,
            "sentences": self.sentences,
            "generation_settings": self._get_generation_settings()
        }
        
        with open(session_path / f"{self.session_name.get()}_session.json", 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=4)
        logging.info(f"Session '{self.session_name.get()}' saved.")

    def select_source_file(self):
        file_types = [("All Supported", "*.txt *.pdf *.epub")]
        if self.deps.pandoc_ok:
            file_types[0] = ("All Supported", "*.txt *.pdf *.epub *.docx *.mobi")
            file_types.extend([("Word", "*.docx"), ("MOBI", "*.mobi")])
        path = filedialog.askopenfilename(filetypes=file_types)
        if path:
            self.source_file_path = path
            self.source_file_label.configure(text=os.path.basename(path))

    def process_file_content(self):
        if not self.source_file_path or not self.session_name.get(): return messagebox.showerror("Error", "Please create/load a session and select a source file.")
        self.process_button.configure(state="disabled", text="Processing...")
        threading.Thread(target=self._process_file_content_threaded, daemon=True).start()

    def _process_file_content_threaded(self):
        try:
            ext = Path(self.source_file_path).suffix.lower()
            text = ""
            if ext == '.txt':
                with open(self.source_file_path, 'r', encoding='utf-8', errors='ignore') as f: text = f.read()
            elif ext == '.pdf':
                text = XPdf(self.source_file_path).to_text()
            elif ext == '.epub':
                book = epub.read_epub(self.source_file_path)
                html_content = "".join([item.get_body_content().decode('utf-8', 'ignore') for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)])
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text("\n\n", strip=True)
            elif ext in ['.docx', '.mobi'] and self.deps.pandoc_ok:
                text = pypandoc.convert_file(self.source_file_path, 'plain', encoding='utf-8')

            if not text:
                self.after(0, lambda: messagebox.showerror("Error", "Could not extract text from file."))
                return
            self.after(0, self.show_editor_window, text)
        except Exception as e:
            logging.error(f"Error processing file: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to process file: {e}\n\nNote: For .docx/.mobi, ensure Pandoc is installed."))
        finally:
            self.after(0, lambda: self.process_button.configure(state="normal", text="Process Text File"))

    def show_editor_window(self, text):
        editor = ctk.CTkToplevel(self)
        editor.title("Review and Edit Text")
        editor.geometry("800x600"); editor.grab_set()
        textbox = ctk.CTkTextbox(editor, wrap="word"); textbox.pack(fill="both", expand=True, padx=10, pady=10); textbox.insert("1.0", text)
        def on_confirm():
            # Initial processing of raw text
            sentences_data = self.text_processor.preprocess_text(textbox.get("1.0", "end-1c"), is_edited_text=True)
            
            # Perform chunking if enabled
            if self.chunking_enabled.get():
                self.sentences = self.text_processor.group_sentences_into_chunks(sentences_data, self.get_validated_int(self.max_chunk_chars_str, 350))
            else:
                self.sentences = sentences_data
            
            ### BUG FIX: Assign UUIDs *after* all processing and chunking is complete.
            for item in self.sentences:
                # Only add a UUID if one doesn't already exist (e.g., from a previously chunked item)
                if 'uuid' not in item:
                    item['uuid'] = uuid.uuid4().hex

            self._renumber_sentences()
            self.playlist_frame.load_data(self.sentences)
            self.save_session()
            editor.destroy()
        ctk.CTkButton(editor, text="Confirm and Process Sentences", command=on_confirm).pack(pady=10)

    def update_progress_display(self, progress, completed, total):
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"{completed}/{total} ({progress:.2%})")

    def play_selected_sentence(self, index=None):
        indices = [index] if index is not None else self.playlist_frame.get_selected_indices()
        if not indices: return
        self.stop_playback()
        self._play_audio_at_index(indices[0])

    def stop_playback(self):
        pygame.mixer.stop()
        self.is_playlist_playing = False
        if self.current_playing_sound:
            self.current_playing_sound = None; gc.collect()

    def mark_current_sentence(self, event=None):
        for idx in self.playlist_frame.get_selected_indices():
            if 0 <= idx < len(self.sentences):
                self.sentences[idx]['marked'] = not self.sentences[idx].get('marked', False)
                self.playlist_frame.update_item(idx)
        self.save_session()
    
    def play_from_selection(self):
        if not self.sentences: return
        self.stop_playback()
        selected_indices = self.playlist_frame.get_selected_indices()
        start_index = selected_indices[0] if selected_indices else 0
        self.playlist_index = start_index
        self.is_playlist_playing = True
        self._check_and_play_next()

    def _check_and_play_next(self):
        if not self.is_playlist_playing or self.stop_flag.is_set(): return self.stop_playback()
        if not pygame.mixer.get_busy():
            if self.playlist_index < len(self.sentences):
                if self.playlist_index // self.playlist_frame.items_per_page != self.playlist_frame.current_page:
                    self.playlist_frame.display_page(self.playlist_index // self.playlist_frame.items_per_page)
                self.playlist_frame.selected_indices = {self.playlist_index}
                self.playlist_frame._update_all_visuals()
                duration_s = self._play_audio_at_index(self.playlist_index)
                self.playlist_index += 1
                self.after(int(duration_s * 1000) if duration_s > 0 else 100, self._check_and_play_next)
            else: self.stop_playback()
        else: self.after(100, self._check_and_play_next)

    def _play_audio_at_index(self, index):
        if index >= len(self.sentences): return 0
        item = self.sentences[index]
        if item.get("is_pause"): return item.get("duration", 1000) / 1000.0

        wav_path = Path(self.OUTPUTS_DIR) / self.session_name.get() / "Sentence_wavs" / f"audio_{item['uuid']}.wav"
        
        for _ in range(3):
            if wav_path.exists():
                break
            time.sleep(0.05)
        
        if wav_path.exists():
            try:
                if self.current_playing_sound: self.current_playing_sound.stop()
                self.current_playing_sound = pygame.mixer.Sound(str(wav_path))
                self.current_playing_sound.play()
                return self.current_playing_sound.get_length()
            except Exception as e:
                logging.error(f"Error playing sound: {e}")
        else:
            logging.warning(f"Playback failed: Audio file not found at {wav_path}")
        return 0

    def edit_selected_sentence(self):
        indices = self.playlist_frame.get_selected_indices()
        if len(indices) != 1: return messagebox.showinfo("Info", "Please select exactly one item to edit.")
        idx = indices[0]
        
        if self.sentences[idx].get("is_pause"): return messagebox.showinfo("Info", "Cannot edit a pause marker. Delete and re-insert it if you wish to change the duration.")
        
        original_text = self.sentences[idx].get('original_sentence', '')
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Text"); dialog.geometry("600x250"); dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1); dialog.grid_rowconfigure(0, weight=1)
        
        textbox = ctk.CTkTextbox(dialog, wrap="word", height=150)
        textbox.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        textbox.insert("1.0", original_text)
        
        result = {"text": None}
        def on_ok():
            result["text"] = textbox.get("1.0", "end-1c")
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
            
        ok_button = ctk.CTkButton(dialog, text="OK", command=on_ok); ok_button.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        cancel_button = ctk.CTkButton(dialog, text="Cancel", command=on_cancel, fg_color="gray"); cancel_button.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        self.wait_window(dialog)
        
        new_text = result.get("text")
        if new_text and new_text.strip() and new_text != original_text:
            self.sentences[idx]['original_sentence'] = new_text
            self.sentences[idx]['tts_generated'] = 'no'
            self.sentences[idx]['marked'] = True
            self.playlist_frame.update_item(idx)
            self.save_session()

    def regenerate_marked_sentences(self):
        indices = [i for i, s in enumerate(self.sentences) if s.get('marked')]
        if not indices: return messagebox.showinfo("Info", "No sentences are marked for regeneration.")
        self.start_generation_orchestrator(indices)

    def _renumber_sentences(self):
        for i, item in enumerate(self.sentences):
            item['sentence_number'] = str(i + 1)

    def insert_pause(self):
        selected_indices = self.playlist_frame.get_selected_indices()
        insert_index = selected_indices[0] if selected_indices else len(self.sentences)
        
        dialog = ctk.CTkInputDialog(text="Enter pause duration in milliseconds (e.g., 1000):", title="Insert Pause")
        duration_str = dialog.get_input()
        
        if not duration_str or not duration_str.isdigit():
            if duration_str is not None: messagebox.showerror("Error", "Please enter a valid number for milliseconds.")
            return
            
        duration_ms = int(duration_str)
        pause_item = {"uuid": uuid.uuid4().hex, "original_sentence": f"--- PAUSE ({duration_ms}ms) ---", "is_pause": True, "duration": duration_ms, "tts_generated": "n/a"}
        self.sentences.insert(insert_index, pause_item)
        self._renumber_sentences()
        self.playlist_frame.load_data(self.sentences)
        self.save_session()

    def insert_text_block(self):
        selected_indices = self.playlist_frame.get_selected_indices()
        insert_index = selected_indices[0] if selected_indices else len(self.sentences)

        dialog = ctk.CTkInputDialog(text="Enter new text:", title="Insert Text Block")
        new_text = dialog.get_input()

        if new_text and new_text.strip():
            new_item = {"uuid": uuid.uuid4().hex, "original_sentence": new_text.strip(), "paragraph": "no", "tts_generated": "no", "marked": True, "is_chapter_heading": False}
            self.sentences.insert(insert_index, new_item)
            self._renumber_sentences()
            self.playlist_frame.load_data(self.sentences)
            self.save_session()
            
    def delete_selected_blocks(self):
        indices = self.playlist_frame.get_selected_indices()
        if not indices: return messagebox.showwarning("Warning", "Please select one or more items to delete.")
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {len(indices)} item(s)? This cannot be undone."): return
            
        for idx in sorted(indices, reverse=True):
            del self.sentences[idx]
            
        self._renumber_sentences()
        self.playlist_frame.load_data(self.sentences)
        self.save_session()

    def _get_generation_settings(self):
        return {
            "ref_audio_path": self.ref_audio_path.get(), "exaggeration": self.exaggeration.get(),
            "cfg_weight": self.cfg_weight.get(), "temperature": self.temperature.get(),
            "target_gpus_str": self.target_gpus_str.get(), "num_full_outputs_str": self.num_full_outputs_str.get(),
            "master_seed_str": self.master_seed_str.get(), "num_candidates_str": self.num_candidates_str.get(),
            "max_attempts_str": self.max_attempts_str.get(), "asr_validation_enabled": self.asr_validation_enabled.get(),
            "disable_watermark": self.disable_watermark.get()
        }

    def _apply_generation_settings(self, settings):
        def safe_set(variable, key, value):
            try: variable.set(value)
            except Exception as e: logging.warning(f"Could not apply setting for '{key}': {e}")
        
        safe_set(self.ref_audio_path, 'ref_audio_path', settings.get('ref_audio_path', ''))
        safe_set(self.exaggeration, 'exaggeration', settings.get('exaggeration', 0.5))
        safe_set(self.cfg_weight, 'cfg_weight', settings.get('cfg_weight', 0.7))
        safe_set(self.temperature, 'temperature', settings.get('temperature', 0.8))
        safe_set(self.target_gpus_str, 'target_gpus_str', settings.get('target_gpus_str', 'cpu'))
        safe_set(self.num_full_outputs_str, 'num_full_outputs_str', settings.get('num_full_outputs_str', '1'))
        safe_set(self.master_seed_str, 'master_seed_str', settings.get('master_seed_str', '0'))
        safe_set(self.num_candidates_str, 'num_candidates_str', settings.get('num_candidates_str', '1'))
        safe_set(self.max_attempts_str, 'max_attempts_str', settings.get('max_attempts_str', '3'))
        safe_set(self.asr_validation_enabled, 'asr_validation_enabled', settings.get('asr_validation_enabled', True))
        safe_set(self.disable_watermark, 'disable_watermark', settings.get('disable_watermark', True))

    def populate_template_dropdown(self):
        try:
            templates = sorted([f.stem for f in Path(self.TEMPLATES_DIR).glob("*.json")])
            if templates:
                self.template_option_menu.configure(values=templates)
                self.selected_template_str.set(templates[0])
            else:
                self.template_option_menu.configure(values=["No templates found"])
                self.selected_template_str.set("No templates found")
        except Exception as e:
            logging.error(f"Failed to populate template dropdown: {e}")
            self.template_option_menu.configure(values=["Error loading"])
            self.selected_template_str.set("Error loading")
            
    def save_generation_template(self):
        name = ctk.CTkInputDialog(text="Enter template name:", title="Save Template").get_input()
        if not name or not re.match("^[a-zA-Z0-9_-]*$", name):
            if name is not None: messagebox.showerror("Invalid Name", "Template name can only contain letters, numbers, underscores, and hyphens.")
            return

        settings = self._get_generation_settings()
        template_path = Path(self.TEMPLATES_DIR) / f"{name}.json"
        
        with open(template_path, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4)
        
        logging.info(f"Saved generation template to {template_path}")
        messagebox.showinfo("Success", f"Template '{name}' saved successfully.")
        self.populate_template_dropdown()

    def load_generation_template(self):
        template_name = self.selected_template_str.get()
        if not template_name or template_name == "No templates found":
            return messagebox.showwarning("Warning", "No template selected or no templates exist.")

        template_path = Path(self.TEMPLATES_DIR) / f"{template_name}.json"
        if not template_path.exists():
            return messagebox.showerror("Error", f"Template file '{template_path}' not found.")
            
        with open(template_path, 'r', encoding='utf-8') as f: settings = json.load(f)
        
        self._apply_generation_settings(settings)
        logging.info(f"Loaded generation template: {template_name}")
        messagebox.showinfo("Success", f"Template '{template_name}' loaded.")

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1, minsize=400)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(self, fg_color=self.colors["frame_bg"])
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(0, weight=1); left_frame.grid_columnconfigure(0, weight=1)

        tabview = ctk.CTkTabview(left_frame, fg_color=self.colors["tab_bg"], text_color=self.text_color, segmented_button_selected_color="#3A7EBF")
        tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        setup_frame = tabview.add("1. Setup"); self.setup_tab = SetupTab(setup_frame, self); self.setup_tab.pack(fill="both", expand=True)
        generation_frame = tabview.add("2. Generation"); self.generation_tab = GenerationTab(generation_frame, self); self.generation_tab.pack(fill="both", expand=True)
        finalize_frame = tabview.add("3. Finalize"); self.finalize_tab = FinalizeTab(finalize_frame, self); self.finalize_tab.pack(fill="both", expand=True)
        advanced_frame = tabview.add("4. Advanced"); self.advanced_tab = AdvancedTab(advanced_frame, self); self.advanced_tab.pack(fill="both", expand=True)

        right_frame = ctk.CTkFrame(self, fg_color=self.colors["frame_bg"])
        right_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1); right_frame.grid_columnconfigure(0, weight=1)
        self.playlist_frame = PlaylistFrame(master=right_frame, app_instance=self, fg_color=self.colors["tab_bg"])
        self.playlist_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5,0))
        
        controls_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        controls_frame.grid(row=1, column=0, pady=(5, 10), sticky="ew")
        controls_frame.grid_columnconfigure(tuple(range(9)), weight=1) 
        button_kwargs = {"text_color": "black"}
        
        ctk.CTkButton(controls_frame, text="▶ Play", command=self.play_selected_sentence, **button_kwargs).grid(row=0, column=0, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="■ Stop", command=self.stop_playback, **button_kwargs).grid(row=0, column=1, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="▶ Play From Selection", command=self.play_from_selection, **button_kwargs).grid(row=0, column=2, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="✎ Edit", command=self.edit_selected_sentence, **button_kwargs).grid(row=0, column=3, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="➕ Insert Text", command=self.insert_text_block, **button_kwargs).grid(row=0, column=4, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="⏸ Insert Pause", command=self.insert_pause, **button_kwargs).grid(row=0, column=5, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="❌ Delete", command=self.delete_selected_blocks, fg_color="#E59866", hover_color="#D35400", **button_kwargs).grid(row=0, column=6, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="M Mark", command=self.mark_current_sentence, **button_kwargs).grid(row=0, column=7, padx=2, sticky="ew")
        ctk.CTkButton(controls_frame, text="↻ Regen Marked", command=self.regenerate_marked_sentences, fg_color="#A40000", hover_color="#800000", text_color="white").grid(row=0, column=8, padx=2, sticky="ew")
        
        self.bind("<m>", self.mark_current_sentence)