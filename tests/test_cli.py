"""Tests for CLI argument parsing."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from unlockegypt.cli import main, parse_arguments, setup_logging
from unlockegypt.site_researcher import PageType


class TestParseArguments:
    """Tests for argument parsing."""

    def test_default_arguments(self) -> None:
        """Test default argument values."""
        with patch.object(sys, "argv", ["unlockegypt"]):
            args = parse_arguments()
            assert args.page_types is None
            assert args.max_sites is None
            assert args.verbose is False
            assert args.no_headless is False
            assert args.dry_run is False
            assert args.resume is False

    def test_type_argument_single(self) -> None:
        """Test single type argument."""
        with patch.object(sys, "argv", ["unlockegypt", "-t", "monuments"]):
            args = parse_arguments()
            assert args.page_types == ["monuments"]

    def test_type_argument_multiple(self) -> None:
        """Test multiple type arguments."""
        with patch.object(
            sys, "argv", ["unlockegypt", "-t", "monuments", "-t", "museums"]
        ):
            args = parse_arguments()
            assert args.page_types == ["monuments", "museums"]

    def test_output_argument(self) -> None:
        """Test output argument."""
        with patch.object(sys, "argv", ["unlockegypt", "-o", "custom.json"]):
            args = parse_arguments()
            assert args.output == "custom.json"

    def test_max_sites_argument(self) -> None:
        """Test max-sites argument."""
        with patch.object(sys, "argv", ["unlockegypt", "-m", "5"]):
            args = parse_arguments()
            assert args.max_sites == 5

    def test_verbose_flag(self) -> None:
        """Test verbose flag."""
        with patch.object(sys, "argv", ["unlockegypt", "-v"]):
            args = parse_arguments()
            assert args.verbose is True

    def test_no_headless_flag(self) -> None:
        """Test no-headless flag."""
        with patch.object(sys, "argv", ["unlockegypt", "--no-headless"]):
            args = parse_arguments()
            assert args.no_headless is True

    def test_dry_run_flag(self) -> None:
        """Test dry-run flag."""
        with patch.object(sys, "argv", ["unlockegypt", "--dry-run"]):
            args = parse_arguments()
            assert args.dry_run is True

    def test_resume_flag(self) -> None:
        """Test resume flag."""
        with patch.object(sys, "argv", ["unlockegypt", "--resume"]):
            args = parse_arguments()
            assert args.resume is True

    def test_checkpoint_argument(self) -> None:
        """Test checkpoint argument."""
        with patch.object(
            sys, "argv", ["unlockegypt", "--checkpoint", "my_checkpoint.json"]
        ):
            args = parse_arguments()
            assert args.checkpoint == "my_checkpoint.json"

    def test_skip_existing_flag(self) -> None:
        """Test skip-existing flag."""
        with patch.object(sys, "argv", ["unlockegypt", "--skip-existing"]):
            args = parse_arguments()
            assert args.skip_existing is True

    def test_no_progress_flag(self) -> None:
        """Test no-progress flag."""
        with patch.object(sys, "argv", ["unlockegypt", "--no-progress"]):
            args = parse_arguments()
            assert args.no_progress is True

    def test_invalid_type_raises_error(self) -> None:
        """Test that invalid type raises error."""
        with (
            patch.object(sys, "argv", ["unlockegypt", "-t", "invalid-type"]),
            pytest.raises(SystemExit),
        ):
            parse_arguments()


class TestSetupLogging:
    """Tests for logging setup."""

    def test_setup_logging_default(self) -> None:
        """Test default logging setup."""
        setup_logging(verbose=False)
        # Should not raise

    def test_setup_logging_verbose(self) -> None:
        """Test verbose logging setup."""
        setup_logging(verbose=True)
        # Should not raise


class TestPageType:
    """Tests for PageType constants."""

    def test_all_types_contains_all(self) -> None:
        """Test ALL_TYPES contains all page types."""
        assert PageType.ARCHAEOLOGICAL_SITES in PageType.ALL_TYPES
        assert PageType.MONUMENTS in PageType.ALL_TYPES
        assert PageType.MUSEUMS in PageType.ALL_TYPES
        assert PageType.SUNKEN_MONUMENTS in PageType.ALL_TYPES

    def test_get_display_name(self) -> None:
        """Test get_display_name returns human-readable names."""
        assert (
            PageType.get_display_name(PageType.ARCHAEOLOGICAL_SITES)
            == "Archaeological Sites"
        )
        assert PageType.get_display_name(PageType.MONUMENTS) == "Monuments"
        assert PageType.get_display_name(PageType.MUSEUMS) == "Museums"
        assert PageType.get_display_name(PageType.SUNKEN_MONUMENTS) == "Sunken Monuments"

    def test_get_display_name_unknown(self) -> None:
        """Test get_display_name with unknown type."""
        result = PageType.get_display_name("unknown-type")
        assert result == "Unknown Type"


class TestMainFunction:
    """Tests for main CLI function."""

    def test_main_with_mock_researcher(self, tmp_path) -> None:
        """Test main function with mocked researcher."""
        output_file = tmp_path / "output.json"

        with (
            patch.object(
                sys, "argv", ["unlockegypt", "-o", str(output_file), "-m", "1"]
            ),
            patch("unlockegypt.cli.SiteResearcher") as MockResearcher,
        ):
            # Set up the mock
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_site_links.return_value = []
            mock_instance.sites = []
            MockResearcher.return_value = mock_instance

            # Run main
            main()

            # Verify researcher was called correctly
            MockResearcher.assert_called_once()
            # get_site_links should be called for each page type
            assert mock_instance.get_site_links.call_count >= 1

    def test_main_with_page_types(self, tmp_path) -> None:
        """Test main function with specific page types."""
        output_file = tmp_path / "output.json"

        with (
            patch.object(
                sys, "argv", ["unlockegypt", "-t", "monuments", "-o", str(output_file)]
            ),
            patch("unlockegypt.cli.SiteResearcher") as MockResearcher,
        ):
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_site_links.return_value = []
            mock_instance.sites = []
            MockResearcher.return_value = mock_instance

            main()

            # Verify get_site_links was called with monuments page type
            mock_instance.get_site_links.assert_called_once()
            call_kwargs = mock_instance.get_site_links.call_args
            assert call_kwargs[1]["page_type"] == "monuments"

    def test_main_verbose_logging(self, tmp_path) -> None:
        """Test main function with verbose logging."""
        output_file = tmp_path / "output.json"

        with (
            patch.object(
                sys, "argv", ["unlockegypt", "-v", "-o", str(output_file)]
            ),
            patch("unlockegypt.cli.SiteResearcher") as MockResearcher,
        ):
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_site_links.return_value = []
            mock_instance.sites = []
            MockResearcher.return_value = mock_instance

            main()

            # Should not raise

    def test_main_headless_option(self, tmp_path) -> None:
        """Test main function with no-headless option."""
        output_file = tmp_path / "output.json"

        with (
            patch.object(
                sys, "argv", ["unlockegypt", "--no-headless", "-o", str(output_file)]
            ),
            patch("unlockegypt.cli.SiteResearcher") as MockResearcher,
        ):
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_site_links.return_value = []
            mock_instance.sites = []
            MockResearcher.return_value = mock_instance

            main()

            # Verify headless=False was passed
            MockResearcher.assert_called_once_with(headless=False)

    def test_main_dry_run(self, tmp_path) -> None:
        """Test main function with dry-run mode."""
        output_file = tmp_path / "output.json"

        with (
            patch.object(
                sys,
                "argv",
                ["unlockegypt", "--dry-run", "-t", "monuments", "-o", str(output_file)],
            ),
            patch("unlockegypt.cli.SiteResearcher") as MockResearcher,
        ):
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_site_links.return_value = [
                {"name": "Test Site", "url": "http://test.com", "location": "Cairo"}
            ]
            mock_instance.sites = []
            MockResearcher.return_value = mock_instance

            main()

            # In dry-run, research_site should NOT be called
            mock_instance.research_site.assert_not_called()

    def test_main_processes_sites(self, tmp_path) -> None:
        """Test main function processes sites correctly."""
        output_file = tmp_path / "output.json"

        with (
            patch.object(
                sys,
                "argv",
                [
                    "unlockegypt",
                    "-t",
                    "monuments",
                    "-m",
                    "1",
                    "-o",
                    str(output_file),
                    "--no-progress",
                ],
            ),
            patch("unlockegypt.cli.SiteResearcher") as MockResearcher,
        ):
            mock_site = MagicMock()
            mock_site.name = "Test Temple"
            mock_site.governorate = "Luxor"
            mock_site.era = "New Kingdom"
            mock_site.tourismType = "Pharaonic"
            mock_site.placeType = "Temple"
            mock_site.uniqueFacts = []
            mock_site.tips = []

            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_site_links.return_value = [
                {"name": "Test Temple", "url": "http://test.com", "location": "Luxor"}
            ]
            mock_instance.research_site.return_value = mock_site
            mock_instance.sites = []
            MockResearcher.return_value = mock_instance

            main()

            # Verify research_site was called
            mock_instance.research_site.assert_called_once()
            # Verify export was called
            mock_instance.export_to_json.assert_called_once_with(str(output_file))
