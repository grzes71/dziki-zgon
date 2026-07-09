"""
Screenshot tracking.
"""

from typing import Dict

def generate_screenshots_map(frame: int, filename: str) -> Dict[str, str]:
    """
    Generates the screenshots map for screenshots.json.
    """
    return {
        str(frame): filename
    }
