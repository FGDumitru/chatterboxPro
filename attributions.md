# Attributions and Open Source Notices

Chatterbox Pro is built upon the incredible work of the open-source community. We are deeply grateful to the developers and maintainers of the following projects, whose code, concepts, and inspiration have made this tool possible.

---

## Project History & Core Components

This project has a direct lineage from the following repositories, which form its foundation.

### Chatterbox-TTS-Extended by petermg
- **Repository:** https://github.com/petermg/Chatterbox-TTS-Extended
- **License:** *MIT*
- **Note:** The Chatterbox Pro project began as a fork of or was heavily based on this repository. While it has since evolved significantly with the addition of a graphical user interface and a different backend architecture, its origins are gratefully acknowledged and some of its original code lives on within this project.

### Chatterbox by Resemble AI
- **Repository:** https://github.com/resemble-ai/chatterbox
- **License:** *(MIT)*
- **Note:** This project serves as a professional-grade extension and user interface for the core Chatterbox TTS technology developed by Resemble AI. The core principles and models are derived from this work.

---

## Adapted Modules & Libraries

The following projects' code was adapted for use in specific modules within Chatterbox Pro. Original copyright notices have been retained in the relevant source files where applicable.

### CosyVoice
- **Repository:** https://github.com/FunAudioLLM/CosyVoice
- **License:** Apache License 2.0
- **Note:** Several modules, particularly within the `chatterbox/models/s3gen` directory, are adapted from the CosyVoice project.

### ESPnet
- **Repository:** https://github.com/espnet/espnet
- **License:** Apache License 2.0
- **Note:** The Conformer implementation and related transformer utilities are adapted from ESPnet.

### Matcha-TTS
- **Repository:** https://github.com/shivammehta25/Matcha-TTS
- **License:** MIT License
- **Note:** The flow-matching and decoder architecture in `chatterbox/models/s3gen/matcha` is based on Matcha-TTS.

### 3D-Speaker (FunASR)
- **Repository:** https://github.com/alibaba-damo-academy/3D-Speaker
- **License:** MIT License
- **Note:** The x-vector speaker encoder (`chatterbox/models/s3gen/xvector.py`) is adapted from this project.

### Real-Time-Voice-Cloning
- **Repository:** https://github.com/CorentinJ/Real-Time-Voice-Cloning
- **License:** MIT License
- **Note:** The voice encoder implementation (`chatterbox/models/voice_encoder`) is adapted from this project.

---

## Inspirations & Acknowledgements

We also wish to acknowledge projects that provided conceptual inspiration for our features and workflow.

### Pandrator by lukaszliniewicz
- **Repository:** https://github.com/lukaszliniewicz/Pandrator
- **Note:** While no code was directly used from this project, its concepts and workflow provided valuable inspiration for the development of some of Chatterbox Pro's automation and processing features.

---

This project also uses numerous other open-source libraries, which are governed by their own licenses. Please see `requirements_pro.txt` for a full list of dependencies.