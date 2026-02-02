"""Tests for progress manager and checkpointing."""

import json
from unittest.mock import MagicMock

from unlockegypt.utils.progress import (
    Checkpoint,
    ProgressManager,
    load_existing_output,
)


class TestCheckpoint:
    """Tests for Checkpoint dataclass."""

    def test_creation_default(self) -> None:
        """Test Checkpoint creation with defaults."""
        checkpoint = Checkpoint()
        assert checkpoint.processed_urls == []
        assert checkpoint.processed_names == []
        assert checkpoint.page_types_completed == []
        assert checkpoint.total_processed == 0

    def test_mark_processed(self) -> None:
        """Test marking a site as processed."""
        checkpoint = Checkpoint()
        checkpoint.mark_processed("http://test.com", "Test Site")
        assert "http://test.com" in checkpoint.processed_urls
        assert "Test Site" in checkpoint.processed_names
        assert checkpoint.total_processed == 1

    def test_mark_processed_no_duplicates(self) -> None:
        """Test that duplicates are not added."""
        checkpoint = Checkpoint()
        checkpoint.mark_processed("http://test.com", "Test Site")
        checkpoint.mark_processed("http://test.com", "Test Site")
        assert len(checkpoint.processed_urls) == 1
        assert len(checkpoint.processed_names) == 1

    def test_is_processed(self) -> None:
        """Test checking if a site is processed."""
        checkpoint = Checkpoint()
        checkpoint.mark_processed("http://test.com", "Test Site")
        assert checkpoint.is_processed("http://test.com", "Other")
        assert checkpoint.is_processed("http://other.com", "Test Site")
        assert not checkpoint.is_processed("http://other.com", "Other Site")

    def test_mark_page_type_completed(self) -> None:
        """Test marking a page type as completed."""
        checkpoint = Checkpoint()
        checkpoint.mark_page_type_completed("monuments")
        assert "monuments" in checkpoint.page_types_completed

    def test_is_page_type_completed(self) -> None:
        """Test checking if a page type is completed."""
        checkpoint = Checkpoint()
        checkpoint.mark_page_type_completed("monuments")
        assert checkpoint.is_page_type_completed("monuments")
        assert not checkpoint.is_page_type_completed("museums")


class TestProgressManager:
    """Tests for ProgressManager."""

    def test_initialization_default(self) -> None:
        """Test default initialization."""
        manager = ProgressManager()
        assert manager.checkpoint_file == ".unlockegypt_checkpoint.json"
        assert manager.auto_save is True
        assert manager.save_interval == 1

    def test_initialization_custom(self) -> None:
        """Test custom initialization."""
        manager = ProgressManager(
            checkpoint_file="custom.json",
            auto_save=False,
            save_interval=5,
        )
        assert manager.checkpoint_file == "custom.json"
        assert manager.auto_save is False
        assert manager.save_interval == 5

    def test_load_checkpoint_no_file(self, tmp_path) -> None:
        """Test loading checkpoint when file doesn't exist."""
        manager = ProgressManager(checkpoint_file=str(tmp_path / "nonexistent.json"))
        result = manager.load_checkpoint()
        assert result is False

    def test_load_checkpoint_valid_file(self, tmp_path) -> None:
        """Test loading checkpoint from valid file."""
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_data = {
            "processed_urls": ["http://test.com"],
            "processed_names": ["Test Site"],
            "page_types_completed": ["monuments"],
            "total_processed": 1,
            "version": "1.0",
        }
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        result = manager.load_checkpoint()

        assert result is True
        assert "http://test.com" in manager.checkpoint.processed_urls
        assert "Test Site" in manager.checkpoint.processed_names
        assert manager.checkpoint.total_processed == 1

    def test_load_checkpoint_invalid_json(self, tmp_path) -> None:
        """Test loading checkpoint with invalid JSON."""
        checkpoint_file = tmp_path / "invalid.json"
        checkpoint_file.write_text("not valid json")

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        result = manager.load_checkpoint()
        assert result is False

    def test_save_checkpoint(self, tmp_path) -> None:
        """Test saving checkpoint to file."""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        manager.checkpoint.mark_processed("http://test.com", "Test Site")

        manager.save_checkpoint()

        assert checkpoint_file.exists()
        data = json.loads(checkpoint_file.read_text())
        assert "http://test.com" in data["processed_urls"]

    def test_mark_site_processed(self, tmp_path) -> None:
        """Test marking site as processed."""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = ProgressManager(checkpoint_file=str(checkpoint_file), auto_save=True)

        manager.mark_site_processed("http://test.com", "Test Site")

        assert manager.checkpoint.is_processed("http://test.com", "Test Site")
        # Check auto-save worked
        assert checkpoint_file.exists()

    def test_should_skip_site(self) -> None:
        """Test should_skip_site check."""
        manager = ProgressManager()
        manager.checkpoint.mark_processed("http://test.com", "Test Site")

        assert manager.should_skip_site("http://test.com", "Other")
        assert manager.should_skip_site("http://other.com", "Test Site")
        assert not manager.should_skip_site("http://other.com", "Other Site")

    def test_mark_page_type_completed(self, tmp_path) -> None:
        """Test marking page type as completed."""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = ProgressManager(checkpoint_file=str(checkpoint_file))

        manager.mark_page_type_completed("monuments")

        assert manager.should_skip_page_type("monuments")
        assert not manager.should_skip_page_type("museums")

    def test_clear_checkpoint(self, tmp_path) -> None:
        """Test clearing checkpoint."""
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_file.write_text("{}")

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        manager.checkpoint.mark_processed("http://test.com", "Test")

        manager.clear_checkpoint()

        assert not checkpoint_file.exists()
        assert manager.checkpoint.total_processed == 0

    def test_get_stats(self) -> None:
        """Test getting progress stats."""
        manager = ProgressManager()
        manager.checkpoint.mark_processed("http://test.com", "Test")
        manager.checkpoint.mark_page_type_completed("monuments")

        stats = manager.get_stats()

        assert stats["total_processed"] == 1
        assert stats["page_types_completed"] == 1

    def test_set_progress_callback(self) -> None:
        """Test setting progress callback."""
        manager = ProgressManager()
        callback = MagicMock()

        manager.set_progress_callback(callback)
        manager.notify_progress(1, 10, "Test Site")

        callback.assert_called_once_with(1, 10, "Test Site")

    def test_notify_progress_no_callback(self) -> None:
        """Test notify_progress when no callback set."""
        manager = ProgressManager()
        # Should not raise
        manager.notify_progress(1, 10, "Test Site")


class TestLoadExistingOutput:
    """Tests for load_existing_output function."""

    def test_load_nonexistent_file(self, tmp_path) -> None:
        """Test loading from nonexistent file."""
        result = load_existing_output(str(tmp_path / "nonexistent.json"))
        assert result == set()

    def test_load_valid_output(self, tmp_path) -> None:
        """Test loading from valid output file."""
        output_file = tmp_path / "output.json"
        output_data = {
            "sites": [
                {"name": "Site 1"},
                {"name": "Site 2"},
                {"name": "Site 3"},
            ]
        }
        output_file.write_text(json.dumps(output_data))

        result = load_existing_output(str(output_file))

        assert "Site 1" in result
        assert "Site 2" in result
        assert "Site 3" in result
        assert len(result) == 3

    def test_load_invalid_json(self, tmp_path) -> None:
        """Test loading from invalid JSON file."""
        output_file = tmp_path / "invalid.json"
        output_file.write_text("not valid json")

        result = load_existing_output(str(output_file))
        assert result == set()

    def test_load_empty_sites(self, tmp_path) -> None:
        """Test loading from file with empty sites."""
        output_file = tmp_path / "output.json"
        output_file.write_text(json.dumps({"sites": []}))

        result = load_existing_output(str(output_file))
        assert result == set()
