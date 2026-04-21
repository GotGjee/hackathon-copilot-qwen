"""
State Manager Service
Handles session state persistence using JSON files + in-memory cache.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from loguru import logger


class StateManager:
    """
    Manages session state persistence.
    Uses JSON files for durability and in-memory cache for performance.
    """

    def __init__(self, data_dir: str = "data/sessions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, dict] = {}

    def _get_file_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.data_dir / f"{session_id}.json"

    def save(self, session_id: str, state_data: dict) -> bool:
        """
        Save session state to JSON file and update cache.

        Args:
            session_id: Unique session identifier
            state_data: Dictionary representation of the state

        Returns:
            True if save was successful
        """
        try:
            # Update cache
            self._cache[session_id] = state_data

            # Write to file
            file_path = self._get_file_path(session_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, default=str)

            logger.debug(f"Saved state for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save state for session {session_id}: {str(e)}")
            return False

    def load(self, session_id: str) -> Optional[dict]:
        """
        Load session state from cache or JSON file.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with state data, or None if not found
        """
        # Check cache first
        if session_id in self._cache:
            return self._cache[session_id]

        # Try to load from file
        file_path = self._get_file_path(session_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Update cache
            self._cache[session_id] = data
            return data

        except Exception as e:
            logger.error(f"Failed to load state for session {session_id}: {str(e)}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete session state."""
        try:
            # Remove from cache
            self._cache.pop(session_id, None)

            # Remove file
            file_path = self._get_file_path(session_id)
            if file_path.exists():
                file_path.unlink()

            logger.debug(f"Deleted state for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete state for session {session_id}: {str(e)}")
            return False

    def list_sessions(self) -> list:
        """List all available session IDs."""
        sessions = set(self._cache.keys())

        # Also check files
        for f in self.data_dir.glob("*.json"):
            sessions.add(f.stem)

        return list(sessions)

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()