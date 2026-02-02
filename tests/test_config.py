"""Tests for configuration loading."""

from unlockegypt.utils.config import Config, config


class TestConfig:
    """Tests for Config singleton."""

    def test_singleton_pattern(self) -> None:
        """Test that Config follows singleton pattern."""
        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_global_config_instance(self) -> None:
        """Test that global config instance is available."""
        assert config is not None
        assert isinstance(config, Config)

    def test_base_url_property(self) -> None:
        """Test base_url property returns string."""
        url = config.base_url
        assert isinstance(url, str)
        assert url.startswith("http")

    def test_page_types_property(self) -> None:
        """Test page_types property returns list."""
        types = config.page_types
        assert isinstance(types, list)
        assert len(types) > 0

    def test_headless_property(self) -> None:
        """Test headless property returns bool."""
        headless = config.headless
        assert isinstance(headless, bool)

    def test_window_size_property(self) -> None:
        """Test window_size property returns tuple."""
        size = config.window_size
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert isinstance(size[0], int)
        assert isinstance(size[1], int)

    def test_user_agent_property(self) -> None:
        """Test user_agent property returns string."""
        ua = config.user_agent
        assert isinstance(ua, str)
        assert "Mozilla" in ua

    def test_implicit_wait_property(self) -> None:
        """Test implicit_wait property returns int."""
        wait = config.implicit_wait
        assert isinstance(wait, int)
        assert wait > 0

    def test_page_load_wait_property(self) -> None:
        """Test page_load_wait property returns float."""
        wait = config.page_load_wait
        assert isinstance(wait, (int, float))
        assert wait > 0

    def test_scroll_wait_property(self) -> None:
        """Test scroll_wait property returns float."""
        wait = config.scroll_wait
        assert isinstance(wait, (int, float))
        assert wait > 0

    def test_show_more_wait_property(self) -> None:
        """Test show_more_wait property returns float."""
        wait = config.show_more_wait
        assert isinstance(wait, (int, float))
        assert wait > 0

    def test_http_timeout_property(self) -> None:
        """Test http_timeout property returns int."""
        timeout = config.http_timeout
        assert isinstance(timeout, int)
        assert timeout > 0

    def test_geocoding_rate_limit_property(self) -> None:
        """Test geocoding_rate_limit property returns float."""
        rate = config.geocoding_rate_limit
        assert isinstance(rate, (int, float))
        assert rate > 0

    def test_nominatim_user_agent_property(self) -> None:
        """Test nominatim_user_agent property returns string."""
        ua = config.nominatim_user_agent
        assert isinstance(ua, str)
        assert "UnlockEgypt" in ua

    def test_get_method_with_valid_key(self) -> None:
        """Test get method with valid nested keys."""
        result = config.get("website", "base_url")
        assert result is not None
        assert isinstance(result, str)

    def test_get_method_with_invalid_key(self) -> None:
        """Test get method with invalid key returns default."""
        result = config.get("nonexistent", "key", default="default_value")
        assert result == "default_value"

    def test_get_method_partial_path(self) -> None:
        """Test get method with partial path returns nested dict."""
        result = config.get("website")
        assert isinstance(result, dict)
        assert "base_url" in result
