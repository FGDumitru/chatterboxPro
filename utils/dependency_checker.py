# utils/dependency_checker.py
import shutil
import logging
import subprocess

try:
    import pypandoc
except ImportError:
    pypandoc = None

class DependencyManager:
    """Proactively checks for required external command-line tools at startup."""
    def __init__(self):
        logging.info("Initializing Dependency Manager and checking system tools...")
        self.pandoc_ok = self._check_pandoc()
        self.ffmpeg_ok, self.ffmpeg_path = self._check_command("ffmpeg")
        self.auto_editor_ok, self.auto_editor_path = self._check_command("auto-editor")
        logging.info("Dependency check complete.")

    def _check_pandoc(self):
        """Checks for the pypandoc library and the pandoc command-line tool."""
        if pypandoc is None:
            logging.warning("Pypandoc library not found. DOCX and MOBI file processing will be disabled.")
            return False
        try:
            pypandoc.get_pandoc_version()
            logging.info("Pandoc is available.")
            return True
        except OSError:
            logging.warning("Pandoc command-line tool not found in system PATH. DOCX and MOBI support disabled.")
            return False

    def _check_command(self, cmd):
        """
        FIXED: This is a simpler, more compatible check that only verifies
        the command's existence in the system's PATH, without trying to run it.
        This resolves issues with different ffmpeg builds.
        """
        path = shutil.which(cmd) or shutil.which(f"{cmd}.exe")
        if path:
            logging.info(f"Dependency '{cmd}' found and executable at: {path}")
            return True, path
        
        logging.warning(f"Dependency '{cmd}' not found in system PATH.")
        return False, None