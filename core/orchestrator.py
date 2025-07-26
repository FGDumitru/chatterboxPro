# core/orchestrator.py
import logging
import random
from pathlib import Path
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from tkinter import messagebox

from workers.tts_worker import worker_process_chunk
from utils.text_processor import punc_norm

class GenerationOrchestrator:
    """Handles the entire multi-GPU generation process."""
    def __init__(self, app_instance):
        self.app = app_instance

    def run(self, indices_to_process=None):
        app = self.app
        num_runs = app.get_validated_int(app.num_full_outputs_str, 1) if not indices_to_process else 1

        for run_idx in range(num_runs):
            run_temp_dir = Path(app.OUTPUTS_DIR) / app.session_name.get() / f"run_{run_idx+1}_temp"
            try:
                if app.stop_flag.is_set(): break

                if run_idx > 0 and not indices_to_process:
                    logging.info(f"Resetting generation status for Run {run_idx + 1}")
                    for s in app.sentences: s['tts_generated'] = 'no'
                    app.after(0, app.playlist_frame.display_page, app.playlist_frame.current_page)
                    app.save_session()

                master_seed = app.get_validated_int(app.master_seed_str, 0)
                # ACX FIX: This is the single seed for the entire run.
                current_run_master_seed = (master_seed + run_idx) if master_seed != 0 else random.randint(1, 2**32 - 1)

                process_list = indices_to_process if indices_to_process is not None else [i for i, s in enumerate(app.sentences) if s.get('tts_generated') != 'yes']
                process_list = [i for i in process_list if not app.sentences[i].get('is_pause')]

                logging.info(f"\n--- Starting {'Regeneration' if indices_to_process else f'Full Run {run_idx+1}/{num_runs}'} with Master Seed: {current_run_master_seed} for {len(process_list)} chunks ---")

                if not process_list:
                    logging.info("All chunks already generated.")
                    if not indices_to_process: continue
                    else: break

                devices = [s.strip() for s in app.target_gpus_str.get().split(',') if s.strip()] or ["cpu"]
                
                generation_order = app.generation_order.get()
                if generation_order == "Fastest First":
                    chunks_to_process_sorted = sorted(process_list, key=lambda i: len(app.sentences[i]['original_sentence']), reverse=True)
                else: # "In Order"
                    chunks_to_process_sorted = sorted(process_list, key=lambda i: int(app.sentences[i]['sentence_number']))
                
                tasks = []
                for i, original_idx in enumerate(chunks_to_process_sorted):
                    sentence_data = app.sentences[original_idx]
                    task = (
                        i, original_idx, int(sentence_data['sentence_number']),
                        punc_norm(sentence_data['original_sentence']),
                        devices[i % len(devices)], 
                        current_run_master_seed, # ACX FIX: Pass the run's master seed to all chunks
                        app.ref_audio_path.get(), app.exaggeration.get(), app.temperature.get(),
                        app.cfg_weight.get(), app.disable_watermark.get(),
                        app.get_validated_int(app.num_candidates_str, 1),
                        app.get_validated_int(app.max_attempts_str, 1),
                        not app.asr_validation_enabled.get(), app.session_name.get(),
                        run_idx, app.OUTPUTS_DIR, sentence_data['uuid'],
                        app.get_validated_float(app.asr_threshold_str, 0.85)
                    )
                    tasks.append(task)

                app.after(0, app.update_progress_display, 0, 0, len(tasks))
                completed_count = 0

                ctx = multiprocessing.get_context('spawn')
                with ProcessPoolExecutor(max_workers=len(devices), mp_context=ctx) as executor:
                    futures = {executor.submit(worker_process_chunk, task): task[1] for task in tasks}
                    for future in as_completed(futures):
                        if app.stop_flag.is_set():
                            for f in futures.keys(): f.cancel()
                            break
                        try:
                            result = future.result()
                            if result and 'original_index' in result:
                                original_idx = result['original_index']
                                
                                app.sentences[original_idx].pop('similarity_ratio', None)
                                app.sentences[original_idx].pop('generation_seed', None)

                                status = result.get('status')
                                app.sentences[original_idx]['generation_seed'] = result.get('seed')
                                app.sentences[original_idx]['similarity_ratio'] = result.get('similarity_ratio')

                                if status == 'success':
                                    app.sentences[original_idx]['tts_generated'] = 'yes'
                                    app.sentences[original_idx]['marked'] = False
                                else:
                                    app.sentences[original_idx]['tts_generated'] = 'failed'
                                    app.sentences[original_idx]['marked'] = True
                                    if status == 'failed_placeholder':
                                        logging.warning(f"Chunk {app.sentences[original_idx]['sentence_number']} failed validation. A placeholder audio was saved. Marked for regeneration.")
                                    else: 
                                        logging.error(f"Chunk {app.sentences[original_idx]['sentence_number']} had a hard error during generation and was marked.")
                                        
                                app.after(0, app.playlist_frame.update_item, original_idx)
                        except Exception as e:
                            logging.error(f"A worker process for index {futures[future]} failed: {e}", exc_info=True)
                        finally:
                            completed_count += 1
                            app.after(0, app.update_progress_display, completed_count / len(tasks), completed_count, len(tasks))

                if not app.stop_flag.is_set() and not indices_to_process and app.auto_assemble_after_run.get():
                    logging.info(f"Auto-assembly triggered for run {run_idx+1}.")
                    run_output_path = Path(app.OUTPUTS_DIR) / app.session_name.get() / f"{app.session_name.get()}_run{run_idx+1}_seed{current_run_master_seed}.wav"
                    app.audio_manager.assemble_audiobook(auto_path=str(run_output_path))
                elif app.stop_flag.is_set():
                    logging.info(f"Run {run_idx+1} was stopped by user.")
                    break
            finally:
                if run_temp_dir.exists():
                    try:
                        shutil.rmtree(run_temp_dir)
                        logging.info(f"Cleaned up temporary directory: {run_temp_dir}")
                    except Exception as e:
                        logging.error(f"Failed to clean up temp directory {run_temp_dir}: {e}")

        app.after(0, app.reinit_audio_player)
        app.after(0, lambda: app.start_stop_button.configure(text="Start Generation", state="normal", fg_color=app.button_color, hover_color=app.button_hover_color))
        app.save_session()
        app.after(0, lambda: messagebox.showinfo("Complete", "All generation runs are complete!"))