# workers/tts_worker.py
import os
import re
import random
import logging
from pathlib import Path
import shutil
import difflib

import torch
import torchaudio

# Chatterbox-specific imports
from chatterbox.tts import ChatterboxTTS
import whisper

# --- Worker-Specific Globals ---
_WORKER_TTS_MODEL, _WORKER_WHISPER_MODEL = None, None

def get_or_init_worker_models(device_str: str):
    """Initializes models once per worker process to save memory and time."""
    global _WORKER_TTS_MODEL, _WORKER_WHISPER_MODEL
    pid = os.getpid()
    if _WORKER_TTS_MODEL is None:
        logging.info(f"[Worker-{pid}] Initializing models for device: {device_str}")
        try:
            _WORKER_TTS_MODEL = ChatterboxTTS.from_pretrained(device_str)
            whisper_device = torch.device(device_str if "cuda" in device_str and torch.cuda.is_available() else "cpu")
            _WORKER_WHISPER_MODEL = whisper.load_model("base.en", device=whisper_device, download_root=str(Path.home() / ".cache" / "whisper"))
            logging.info(f"[Worker-{pid}] Models loaded successfully on {device_str}.")
        except Exception as e:
            logging.critical(f"[Worker-{pid}] CRITICAL ERROR: Failed to initialize models: {e}", exc_info=True)
            _WORKER_TTS_MODEL, _WORKER_WHISPER_MODEL = None, None
            raise
    return _WORKER_TTS_MODEL, _WORKER_WHISPER_MODEL

def set_seed(seed: int):
    """Sets random seeds for reproducibility."""
    import numpy as np
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def get_similarity_ratio(text1, text2):
    norm1 = re.sub(r'[\W_]+', '', text1).lower()
    norm2 = re.sub(r'[\W_]+', '', text2).lower()
    if not norm1 or not norm2: return 0.0
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()

def fuzzy_match(text1, text2, threshold=0.85):
    return get_similarity_ratio(text1, text2) >= threshold

def worker_process_chunk(task_bundle):
    """The main function executed by each worker process to generate a single audio chunk."""
    # MODIFIED: Accept uuid
    (task_index, original_index, sentence_number, text_chunk, device_str, master_seed, ref_audio_path,
     exaggeration, temperature, cfg_weight, disable_watermark, num_candidates, max_attempts,
     bypass_asr, session_name, run_idx, output_dir_str, uuid) = task_bundle

    pid = os.getpid()
    logging.info(f"[Worker-{pid}] Starting chunk (Idx: {original_index}, #: {sentence_number}, UUID: {uuid[:8]}) on device {device_str}")

    try:
        tts_model, whisper_model = get_or_init_worker_models(device_str)
        if tts_model is None or whisper_model is None:
            raise RuntimeError(f"Model initialization failed for device {device_str}")
    except Exception as e_model_load:
        return {"original_index": original_index, "status": "error", "error_message": f"Model Load Fail: {e_model_load}", "path": None}

    run_temp_dir = Path(output_dir_str) / session_name / f"run_{run_idx+1}_temp"
    run_temp_dir.mkdir(exist_ok=True, parents=True)
    
    # MODIFIED: Use UUID for temporary file names for robustness
    base_candidate_path_prefix = run_temp_dir / f"c_{uuid}_cand"

    try:
        tts_model.prepare_conditionals(ref_audio_path, exaggeration=min(exaggeration, 1.0), use_cache=True)
    except Exception as e:
        logging.error(f"[Worker-{pid}] Failed to prepare conditionals for chunk {sentence_number}: {e}", exc_info=True)
        return {"original_index": original_index, "status": "error", "error_message": f"Conditional Prep Fail: {e}", "path": None}

    passed_candidates = []
    best_failed_candidate = {'ratio': -1.0, 'path': None, 'duration': 0, 'seed': 0}
    all_temp_files = []
    
    if master_seed != 0:
        base_seed_for_chunk = master_seed + original_index
    else:
        base_seed_for_chunk = 0 

    for attempt_num in range(max_attempts):
        if base_seed_for_chunk != 0:
            seed = base_seed_for_chunk + attempt_num
        else:
            seed = random.randint(1, 2**32 - 1)
        
        logging.info(f"[Worker-{pid}] Chunk #{sentence_number}, Attempt {attempt_num + 1}/{max_attempts} with seed {seed}")
        set_seed(seed)
        
        path_str = str(base_candidate_path_prefix) + f"_{attempt_num+1}_seed{seed}.wav"
        all_temp_files.append(path_str)

        try:
            wav_tensor = tts_model.generate(text_chunk, cfg_weight=cfg_weight, temperature=temperature, apply_watermark=not disable_watermark)
            if not (torch.is_tensor(wav_tensor) and wav_tensor.numel() > tts_model.sr * 0.1):
                logging.warning(f"Generation failed (empty audio) for chunk #{sentence_number}, attempt {attempt_num+1}.")
                continue
            
            torchaudio.save(path_str, wav_tensor.cpu(), tts_model.sr)
            duration = wav_tensor.shape[-1] / tts_model.sr
            
        except Exception as e:
            logging.error(f"Generation crashed for chunk #{sentence_number}, attempt {attempt_num+1}: {e}", exc_info=True)
            continue

        current_candidate_data = {"path": path_str, "duration": duration, "seed": seed}

        is_passed = False
        if bypass_asr:
            is_passed = True
            logging.info(f"ASR bypassed for chunk #{sentence_number}, attempt {attempt_num+1}")
        else:
            try:
                transcribed = whisper_model.transcribe(path_str, fp16=(whisper_model.device.type == 'cuda'))['text']
                ratio = get_similarity_ratio(text_chunk, transcribed)
                
                if ratio >= 0.85:
                    is_passed = True
                    logging.info(f"ASR PASSED for chunk #{sentence_number}, attempt {attempt_num+1} (Sim: {ratio:.2f})")
                else:
                    logging.warning(f"ASR FAILED for chunk #{sentence_number}, attempt {attempt_num+1} (Sim: {ratio:.2f})")
                    if ratio > best_failed_candidate['ratio']:
                        best_failed_candidate = {**current_candidate_data, 'ratio': ratio}
            except Exception as e:
                logging.error(f"Whisper transcription failed for {path_str}: {e}")

        if is_passed:
            passed_candidates.append(current_candidate_data)
            if len(passed_candidates) >= num_candidates:
                logging.info(f"Met required number of candidates ({num_candidates}). Stopping early.")
                break

    # MODIFIED: Use UUID for final file path
    final_wav_path = Path(output_dir_str) / session_name / "Sentence_wavs" / f"audio_{uuid}.wav"
    final_wav_path.parent.mkdir(exist_ok=True, parents=True)
    
    chosen_candidate = None
    status = "error"
    
    if passed_candidates:
        chosen_candidate = sorted(passed_candidates, key=lambda x: x["duration"])[0]
        status = "success"
    elif best_failed_candidate['path'] is not None:
        logging.warning(f"No candidates passed. Using best failure (Sim: {best_failed_candidate['ratio']:.2f}) as placeholder.")
        chosen_candidate = best_failed_candidate
        status = "failed_placeholder"
    
    if chosen_candidate:
        shutil.move(chosen_candidate['path'], final_wav_path)
        for temp_file in all_temp_files:
            if temp_file != chosen_candidate['path'] and Path(temp_file).exists():
                os.remove(temp_file)
        
        logging.info(f"Chunk #{sentence_number} (Status: {status}) processed. Final audio: {final_wav_path.name}")
        return {"original_index": original_index, "status": status, "path": str(final_wav_path)}
    else:
        return {"original_index": original_index, "status": "error", "error_message": "All generation attempts failed to produce audio.", "path": None}