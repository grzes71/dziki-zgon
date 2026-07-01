import logging
from pathlib import Path
from typing import Optional

from .validation import validate_emulator_path, validate_xex_path
from .process import AltirraProcess

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

logger = logging.getLogger(__name__)

class SmokeTestLauncher:
    """Orchestrates the smoke test workflow."""
    
    def __init__(self, process_manager: Optional[AltirraProcess] = None):
        self.process_manager = process_manager or AltirraProcess()

    def run(self, emulator_path: str, xex_path: str, timeout: float, screenshot_path: Optional[str] = None) -> None:
        """Runs the smoke test. Raises exceptions on failure."""
        logger.info("-" * 42)
        logger.info("Atari Smoke Test")
        logger.info("-" * 42)
        
        valid_emulator = validate_emulator_path(emulator_path)
        logger.info("Emulator:\nOK")
        
        valid_xex = validate_xex_path(xex_path)
        logger.info("XEX:\nOK")
        
        logger.info("Launching emulator...")
        self.process_manager.start(valid_emulator, valid_xex)
        
        try:
            logger.info("Running...")
            logger.info(f"Waiting {timeout} seconds...")
            self.process_manager.wait(timeout)
        finally:
            if screenshot_path and ImageGrab:
                logger.info(f"Capturing screenshot to {screenshot_path}...")
                try:
                    img = ImageGrab.grab()
                    img.save(screenshot_path)
                except Exception as e:
                    logger.error(f"Failed to capture screenshot: {e}")
                    
            logger.info("Stopping emulator...")
            self.process_manager.terminate()
            
        logger.info("Smoke Test PASSED")
        logger.info("-" * 42)
