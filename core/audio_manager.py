# core/audio_manager.py
import logging
import subprocess
from pathlib import Path
import shutil
from tkinter import filedialog, messagebox

import ffmpeg
from pydub import AudioSegment

from chatterbox.models.s3gen import S3GEN_SR

class AudioManager:
    """Handles final audiobook assembly and post-processing."""
    def __init__(self, app_instance):
        self.app = app_instance

    def assemble_audiobook(self, auto_path=None):
        app = self.app
        if not app.session_name.get(): return
        if (app.silence_removal_enabled.get() and not app.deps.auto_editor_ok) or \
           (app.norm_enabled.get() and not app.deps.ffmpeg_ok):
            return messagebox.showerror("Dependency Error", "Cannot assemble audiobook. Please fix missing dependencies (see warnings at startup) or disable the feature.")

        session_path = Path(app.OUTPUTS_DIR) / app.session_name.get()
        all_items_in_order = sorted(app.sentences, key=lambda s: int(s['sentence_number']))
        
        if not all_items_in_order:
            if not auto_path: messagebox.showerror("Error", "No text chunks to assemble.")
            return

        logging.info(f"Assembling audiobook from {len(all_items_in_order)} playlist items...")
        combined = AudioSegment.empty()
        
        for i, s_data in enumerate(all_items_in_order):
            if s_data.get("is_pause"):
                pause_duration = s_data.get("duration", 1000)
                combined += AudioSegment.silent(duration=pause_duration)
                logging.info(f"Added manual pause of {pause_duration}ms")
                continue

            # MODIFIED: Use UUID to find the audio file
            f_path = session_path / "Sentence_wavs" / f"audio_{s_data['uuid']}.wav"
            
            if f_path.exists():
                try:
                    if s_data.get("is_chapter_heading"):
                        combined += AudioSegment.silent(duration=2000)
                        logging.info("Added chapter heading pause.")
                    
                    segment = AudioSegment.from_wav(f_path)
                    
                    is_para = not app.chunking_enabled.get() and s_data.get('paragraph') == 'yes'
                    pause_duration = 750 if is_para else app.get_validated_int(app.silence_duration_str, 250)
                    
                    if combined: combined += AudioSegment.silent(duration=pause_duration)
                    
                    combined += segment
                except Exception as e:
                    logging.error(f"Could not process segment {f_path}: {e}")
            else:
                logging.warning(f"Audio file for sentence {s_data['sentence_number']} not found, skipping.")

        if len(combined) == 0:
            if not auto_path: messagebox.showerror("Error", "No generated audio files were found to assemble.")
            return

        raw_concatenated_path = session_path / f"{app.session_name.get()}_raw_concat.wav"
        combined.export(raw_concatenated_path, format="wav")
        processed_path, temp_files = str(raw_concatenated_path), []

        try:
            if app.silence_removal_enabled.get() and app.deps.auto_editor_path:
                temp_silence_removed_path = session_path / "temp_silence_removed.wav"
                temp_files.append(temp_silence_removed_path)
                cmd = [app.deps.auto_editor_path, str(processed_path), '--silent_speed', '99999', '--frame_margin', '6', '-o', str(temp_silence_removed_path)]
                logging.info(f"Running auto-editor with command: {' '.join(cmd)}")
                subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                processed_path = str(temp_silence_removed_path)
                logging.info("Silence removal successful.")

            if app.norm_enabled.get() and app.deps.ffmpeg_path:
                temp_normalized_path = session_path / "temp_normalized.wav"
                temp_files.append(temp_normalized_path)
                (ffmpeg.input(processed_path)
                       .output(str(temp_normalized_path), af=f"loudnorm=I={float(app.norm_level_str.get())}:TP=-1.5:LRA=11", ar=S3GEN_SR)
                       .overwrite_output().run(quiet=True, capture_stderr=True))
                processed_path = str(temp_normalized_path)
                logging.info("Normalization successful.")

        except subprocess.CalledProcessError as e:
            error_message = f"An external tool failed with exit code {e.returncode}.\n\nCommand: {' '.join(map(str, e.args))}\n\nError Output:\n{e.stderr or e.stdout}"
            logging.error(error_message)
            messagebox.showerror("Post-Processing Error", error_message)
            return
        except Exception as e:
            logging.error(f"Post-processing failed: {e}", exc_info=True)
            messagebox.showerror("Post-Processing Error", f"An unexpected error occurred: {e}")
            return

        finally:
            if os.path.exists(raw_concatenated_path) and str(raw_concatenated_path) != processed_path:
                 os.remove(raw_concatenated_path)
            for f in temp_files:
                if os.path.exists(f) and str(f) != processed_path:
                    os.remove(f)

        output_path = auto_path or filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV", "*.wav"), ("MP3", "*.mp3")], initialdir=session_path, initialfile=f"{app.session_name.get()}_final.wav")
        if output_path:
            shutil.move(processed_path, output_path)
            logging.info(f"Final audiobook saved to {output_path}")
            if not auto_path: messagebox.showinfo("Success", f"Audiobook saved to {output_path}")