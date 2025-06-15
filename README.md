# Chatterbox Pro Audiobook Generator



**Chatterbox Pro** is a powerful, user-friendly graphical interface for generating high-quality audiobooks using the cutting-edge **Chatterbox** text-to-speech model. This tool is designed for creators, authors, and hobbyists who want to convert long-form text into professional-sounding audio with a consistent, cloned voice.

This application provides a complete end-to-end workflow: from text processing and voice cloning to multi-GPU audio generation and final audiobook assembly.

## ✨ Features

-   **High-Quality Voice Cloning**: Utilizes the Chatterbox model to clone a voice from a short audio sample.
-   **Intuitive GUI**: A clean, tab-based interface built with CustomTkinter for easy navigation and control.
-   **Comprehensive Text Processing**:
    -   Supports various input formats: `.txt`, `.pdf`, `.epub`, and with Pandoc installed, `.docx` and `.mobi`.
    -   Intelligent sentence and chapter detection.
    -   In-app text editor for reviewing and correcting source material.
-   **Powerful Generation Controls**:
    -   Adjust TTS parameters like emotional exaggeration, temperature, and speaker similarity (CFG).
    -   Multi-GPU support for parallel processing, significantly speeding up generation.
    -   Smart ASR (Automatic Speech Recognition) validation to ensure generated audio matches the source text.
-   **Robust Failure & Regeneration Workflow**:
    -   **Intelligent Placeholders**: If a text chunk fails ASR validation, the *best-sounding failure* is used as a placeholder, eliminating silent gaps in the output.
    -   **Automatic Marking**: All failed chunks are automatically marked for easy, one-click regeneration.
    -   **Incremental Seeding**: Regeneration attempts use different seeds to increase the chance of success.
-   **Advanced Playlist Management**:
    -   Edit, delete, and insert new text blocks or pauses directly into the playlist.
    -   The entire project is automatically renumbered and saved.
-   **Streamlined Project Management**:
    -   Session-based workflow saves all your text, generated audio, and settings.
    -   Save and load generation parameter templates for consistent results across projects.
-   **Post-Processing**:
    -   Optional audio normalization (via `ffmpeg`) and silence removal (via `auto-editor`) for a polished final product.

## 🔧 Installation

This project requires Python 3.10 or higher and a system with at least one NVIDIA GPU with CUDA support for optimal performance.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ChatterboxPro.git
cd ChatterboxPro
```

### 2. Set Up the `chatterbox` Model

This GUI is a wrapper around the original **Chatterbox** model. You must download the source code of the model and place it correctly in the project directory.

1.  Download the `chatterbox` source code from its original repository (e.g., as a ZIP file).
2.  Extract the ZIP file.
3.  You will see a folder named `chatterbox-main` or similar. Inside it, there is another folder named `chatterbox`.
4.  Copy this **inner** `chatterbox` folder into the root of the `ChatterboxPro` directory.

Your directory structure should look like this:

```
ChatterboxPro/
├── chatterbox/        <-- The model source code
│   ├── models/
│   ├── tts.py
│   └── ...
├── core/
├── ui/
├── chatter_pro.py
└── requirements_pro.txt
```

### 3. Create a Virtual Environment and Install Dependencies

It is highly recommended to use a virtual environment.

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the required Python packages
pip install -r requirements_pro.txt
```

### 4. Install Optional System Dependencies

For full functionality, you need to install these command-line tools and ensure they are in your system's PATH.

-   **FFmpeg**: Required for audio normalization and assembling the final audiobook.
    -   Download from [ffmpeg.org](https://ffmpeg.org/download.html).
-   **Pandoc**: Required for processing `.docx` and `.mobi` files.
    -   Download from [pandoc.org](https://pandoc.org/installing.html).
-   **auto-editor**: Required for smart silence removal.
    -   Install via pip: `pip install auto-editor`

The application will still run without these, but the corresponding features will be disabled.

## 🚀 How to Use

1.  **Launch the Application**:
    ```bash
    python chatter_pro.py
    ```

2.  **Tab 1: Setup**
    -   **Create a Session**: Click "New Session" and give your project a name (e.g., `my-first-book`). All files will be saved in an `Outputs_Pro/<session_name>` directory.
    -   **Select Source File**: Click "Select File..." to choose your text document (`.txt`, `.pdf`, `.epub`, etc.).
    -   **Process Text**: Click "Process Text File". An editor window will pop up. Review your text and make any corrections, then click "Confirm". Your text will be split into chunks and displayed in the playlist on the right.
    -   **Load a Template (Optional)**: If you have saved generation settings, you can load them here.

3.  **Tab 2: Generation**
    -   **Reference Audio**: Select a high-quality, clean WAV file (10-30 seconds is ideal) of the voice you want to clone.
    -   **Adjust Parameters**:
        -   **Exaggeration**: Controls emotional intensity.
        -   **CFG Weight**: Higher values make the generated voice sound more like the reference.
        -   **Temperature**: Controls the randomness of the output.
    -   **Save a Template (Optional)**: If you like your settings, click "Save as Template..." to reuse them later.

4.  **Start Generation**
    -   Go back to the **Setup** tab and click the big **"Start Generation"** button.
    -   The progress bar will update as chunks are generated. Failed chunks (which did not pass ASR) will be marked in red but will still have placeholder audio.

5.  **Review and Regenerate**
    -   Listen to the generated audio clips by selecting them in the playlist and clicking "▶ Play".
    -   Failed chunks are automatically marked. To retry them, simply adjust your generation settings (e.g., change the "Master Seed") and click **"↻ Regen Marked"**.

6.  **Tab 3: Finalize**
    -   Once you are happy with all the generated audio, click the **"Assemble Final Audiobook"** button.
    -   This will concatenate all the audio clips, add pauses for chapters and paragraphs, and apply any selected post-processing. You will be prompted to save the final `.wav` file.

## 📁 Project Structure

A brief overview of the code structure:

-   `chatter_pro.py`: Main entry point for the application.
-   `core/`: Contains the core logic.
    -   `orchestrator.py`: Manages the multi-GPU generation process.
    -   `audio_manager.py`: Handles post-processing and audiobook assembly.
-   `ui/`: All graphical user interface components.
    -   `main_window.py`: The main application class and window.
    -   `playlist.py`: The interactive playlist widget.
    -   `tabs/`: Individual files for each settings tab.
-   `utils/`: Helper modules.
    -   `text_processor.py`: Logic for parsing and cleaning text.
    -   `dependency_checker.py`: Checks for system dependencies like `ffmpeg`.
-   `workers/`: Code that runs in separate processes.
    -   `tts_worker.py`: The core TTS generation function executed by each GPU worker.
-   `chatterbox/`: The original Chatterbox model source code (must be added by user).
-   `Outputs_Pro/`: Default directory where all generated sessions and audio are saved.
-   `Templates/`: Where generation setting templates are stored.

## 🙏 Acknowledgements

This project is a graphical user interface built on top of the powerful **Chatterbox TTS model**. All credit for the underlying voice cloning and speech synthesis technology goes to the creators of Chatterbox.

This tool aims to make their incredible model more accessible for long-form content creation.


TLDR License info; If you are trying to sell the software you have to open source your code, if you are building your personal audiobooks and selling those audiobooks on that's licensed. As the lawyers say read the actual license languge but as an author first and programmer second if you're an author using it as a personal audiobook generator you don't need to worry about it being a violation.

# Chatterbox Pro 🎙️

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

*(Your project description, features, installation instructions, etc., go here)*

---

## 📜 Licensing

Chatterbox Pro is released under a dual-license model to support its ongoing development while providing a free and open-source version for the community.

### Open Source License (AGPLv3)

For open source projects, academic research, and non-commercial personal use, Chatterbox Pro is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**.

Under the AGPLv3, you are free to:
*   Use and modify the software.
*   Distribute your modified versions.

However, if you use Chatterbox Pro (or any modified version) as part of a service that is accessible over a network, you are required to make the full source code of your service available to its users under the same AGPLv3 license. You can find the full license text in the [LICENSE](LICENSE) file.

### Commercial License

For businesses and commercial use cases where the obligations of the AGPLv3 are not suitable, we offer a commercial license. A commercial license allows you to embed Chatterbox Pro in your proprietary applications and services without the source-sharing requirements of the AGPLv3.

| Use Case                                                    | License Required                                       |
| ----------------------------------------------------------- | ------------------------------------------------------ |
| Personal projects, experimentation, and personal content creation | AGPLv3 (Free)                                          |
| Academic and non-commercial research                        | AGPLv3 (Free)                                          |
| Open source projects licensed under AGPLv3 or a compatible license | AGPLv3 (Free)                                          |
| **Proprietary/closed-source applications or commercial services** | **Commercial License (Required)**                      |

To inquire about a commercial license, please **[open an issue on GitHub using our Commercial License Inquiry template](https://github.com/YOUR_USERNAME/chatterboxPro/issues/new?assignees=&labels=licensing&template=commercial-license-inquiry.md&title=Commercial+License+Inquiry)**.
