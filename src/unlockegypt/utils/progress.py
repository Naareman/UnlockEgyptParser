"""
Progress Manager - Handles checkpointing and progress tracking.

Features:
- Save/load checkpoint files for resumability
- Track processed URLs to skip duplicates
- Progress callbacks for UI updates
"""

import json
import logging
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("UnlockEgyptParser")


@dataclass
class Checkpoint:
    """Checkpoint data for resuming interrupted runs."""

    processed_urls: list[str] = field(default_factory=list)
    processed_names: list[str] = field(default_factory=list)
    page_types_completed: list[str] = field(default_factory=list)
    current_page_type: str = ""
    total_processed: int = 0
    last_updated: str = ""
    version: str = "1.0"

    def mark_processed(self, url: str, name: str) -> None:
        """Mark a site as processed."""
        if url and url not in self.processed_urls:
            self.processed_urls.append(url)
        if name and name not in self.processed_names:
            self.processed_names.append(name)
        self.total_processed = len(self.processed_urls)
        self.last_updated = datetime.now().isoformat()

    def is_processed(self, url: str, name: str) -> bool:
        """Check if a site has already been processed."""
        return url in self.processed_urls or name in self.processed_names

    def mark_page_type_completed(self, page_type: str) -> None:
        """Mark a page type as fully processed."""
        if page_type not in self.page_types_completed:
            self.page_types_completed.append(page_type)
        self.last_updated = datetime.now().isoformat()

    def is_page_type_completed(self, page_type: str) -> bool:
        """Check if a page type has been fully processed."""
        return page_type in self.page_types_completed


class ProgressManager:
    """
    Manages progress tracking and checkpointing for long-running research tasks.

    Features:
    - Automatic checkpoint saving
    - Resume from previous run
    - Duplicate detection
    - Progress callbacks for UI updates
    """

    DEFAULT_CHECKPOINT_FILE = ".unlockegypt_checkpoint.json"

    def __init__(
        self,
        checkpoint_file: str | None = None,
        auto_save: bool = True,
        save_interval: int = 1,
    ) -> None:
        """
        Initialize the progress manager.

        Args:
            checkpoint_file: Path to checkpoint file (None = default location)
            auto_save: Whether to auto-save after each site
            save_interval: Save checkpoint every N sites
        """
        self.checkpoint_file = checkpoint_file or self.DEFAULT_CHECKPOINT_FILE
        self.auto_save = auto_save
        self.save_interval = save_interval
        self.checkpoint = Checkpoint()
        self._sites_since_save = 0
        self._progress_callback: Callable[[int, int, str], None] | None = None

    def set_progress_callback(
        self, callback: Callable[[int, int, str], None]
    ) -> None:
        """
        Set a callback for progress updates.

        Args:
            callback: Function(current, total, site_name) called on progress
        """
        self._progress_callback = callback

    def notify_progress(self, current: int, total: int, site_name: str) -> None:
        """Notify progress callback if set."""
        if self._progress_callback:
            self._progress_callback(current, total, site_name)

    def load_checkpoint(self) -> bool:
        """
        Load checkpoint from file.

        Returns:
            True if checkpoint was loaded, False if no checkpoint exists
        """
        if not os.path.exists(self.checkpoint_file):
            logger.info("No checkpoint file found, starting fresh")
            return False

        try:
            with open(self.checkpoint_file, encoding="utf-8") as f:
                data = json.load(f)

            self.checkpoint = Checkpoint(
                processed_urls=data.get("processed_urls", []),
                processed_names=data.get("processed_names", []),
                page_types_completed=data.get("page_types_completed", []),
                current_page_type=data.get("current_page_type", ""),
                total_processed=data.get("total_processed", 0),
                last_updated=data.get("last_updated", ""),
                version=data.get("version", "1.0"),
            )

            logger.info(
                f"Loaded checkpoint: {self.checkpoint.total_processed} sites already processed"
            )
            return True

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not load checkpoint: {e}")
            return False

    def save_checkpoint(self) -> None:
        """Save current checkpoint to file."""
        try:
            self.checkpoint.last_updated = datetime.now().isoformat()
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self.checkpoint), f, indent=2, ensure_ascii=False)
            logger.debug(f"Checkpoint saved: {self.checkpoint.total_processed} sites")
        except OSError as e:
            logger.warning(f"Could not save checkpoint: {e}")

    def mark_site_processed(self, url: str, name: str) -> None:
        """
        Mark a site as processed and optionally save checkpoint.

        Args:
            url: Site URL
            name: Site name
        """
        self.checkpoint.mark_processed(url, name)
        self._sites_since_save += 1

        if self.auto_save and self._sites_since_save >= self.save_interval:
            self.save_checkpoint()
            self._sites_since_save = 0

    def should_skip_site(self, url: str, name: str) -> bool:
        """
        Check if a site should be skipped (already processed).

        Args:
            url: Site URL
            name: Site name

        Returns:
            True if site should be skipped
        """
        return self.checkpoint.is_processed(url, name)

    def mark_page_type_completed(self, page_type: str) -> None:
        """Mark a page type as completed."""
        self.checkpoint.mark_page_type_completed(page_type)
        self.save_checkpoint()

    def should_skip_page_type(self, page_type: str) -> bool:
        """Check if a page type should be skipped."""
        return self.checkpoint.is_page_type_completed(page_type)

    def clear_checkpoint(self) -> None:
        """Clear checkpoint file and reset state."""
        self.checkpoint = Checkpoint()
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            logger.info("Checkpoint cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get current progress statistics."""
        return {
            "total_processed": self.checkpoint.total_processed,
            "page_types_completed": len(self.checkpoint.page_types_completed),
            "last_updated": self.checkpoint.last_updated,
        }


def load_existing_output(output_path: str) -> set[str]:
    """
    Load existing output file to get already-processed site names.

    Args:
        output_path: Path to existing output JSON file

    Returns:
        Set of site names already in the output
    """
    if not os.path.exists(output_path):
        return set()

    try:
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        sites = data.get("sites", [])
        names = {site.get("name", "") for site in sites if site.get("name")}
        logger.info(f"Found {len(names)} existing sites in output file")
        return names

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Could not load existing output: {e}")
        return set()
