"""
Tests for ModuleRegistry.

This module tests the module registry system including:
- Module registration and metadata management
- Enable/disable functionality
- Category and logger management
- Debug flag handling
- Registry queries and filtering
"""

import logging
from unittest.mock import patch

import pytest

from nowplaying.module_registry import ModuleRegistry


class TestModuleRegistry:
    """Tests for ModuleRegistry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ModuleRegistry()

    def test_registry_initialization(self):
        """Test registry initialization."""
        assert len(self.registry._modules) == 0
        assert isinstance(self.registry._modules, dict)

    def test_register_module_basic(self):
        """Test registering a basic module."""
        self.registry.register_module(
            name="test_module",
            description="A test module",
            logger_name="test.module",
            debug_flag="--debug-test",
        )

        assert "test_module" in self.registry._modules
        module_info = self.registry._modules["test_module"]

        assert module_info["description"] == "A test module"
        assert module_info["logger_name"] == "test.module"
        assert module_info["debug_flag"] == "--debug-test"
        assert module_info["enabled"] is True  # Default
        assert module_info["category"] == "feature"  # Default
        assert isinstance(module_info["logger"], logging.Logger)

    def test_register_module_with_custom_options(self):
        """Test registering module with custom options."""
        self.registry.register_module(
            name="custom_module",
            description="Custom module",
            logger_name="custom.module",
            debug_flag="--debug-custom",
            enabled=False,
            category="experimental",
        )

        module_info = self.registry._modules["custom_module"]

        assert module_info["enabled"] is False
        assert module_info["category"] == "experimental"

    def test_register_multiple_modules(self):
        """Test registering multiple modules."""
        self.registry.register_module(
            name="module1",
            description="First module",
            logger_name="test.module1",
            debug_flag="--debug-mod1",
        )
        self.registry.register_module(
            name="module2",
            description="Second module",
            logger_name="test.module2",
            debug_flag="--debug-mod2",
        )

        assert len(self.registry._modules) == 2
        assert "module1" in self.registry._modules
        assert "module2" in self.registry._modules

    def test_enable_module(self):
        """Test enabling a module."""
        self.registry.register_module(
            name="test_module",
            description="Test module",
            logger_name="test.module",
            debug_flag="--debug-test",
            enabled=False,
        )

        result = self.registry.enable_module("test_module")

        assert result is True
        assert self.registry._modules["test_module"]["enabled"] is True

    def test_enable_nonexistent_module(self):
        """Test enabling nonexistent module returns False."""
        result = self.registry.enable_module("nonexistent")

        assert result is False

    def test_disable_module(self):
        """Test disabling a module."""
        self.registry.register_module(
            name="test_module",
            description="Test module",
            logger_name="test.module",
            debug_flag="--debug-test",
            enabled=True,
        )

        result = self.registry.disable_module("test_module")

        assert result is True
        assert self.registry._modules["test_module"]["enabled"] is False

    def test_disable_nonexistent_module(self):
        """Test disabling nonexistent module returns False."""
        result = self.registry.disable_module("nonexistent")

        assert result is False

    def test_is_module_enabled(self):
        """Test checking if module is enabled."""
        self.registry.register_module(
            name="enabled_module",
            description="Enabled module",
            logger_name="test.enabled",
            debug_flag="--debug-enabled",
            enabled=True,
        )
        self.registry.register_module(
            name="disabled_module",
            description="Disabled module",
            logger_name="test.disabled",
            debug_flag="--debug-disabled",
            enabled=False,
        )

        assert self.registry.is_module_enabled("enabled_module") is True
        assert self.registry.is_module_enabled("disabled_module") is False
        assert self.registry.is_module_enabled("nonexistent") is False

    def test_get_enabled_modules(self):
        """Test getting only enabled modules."""
        self.registry.register_module(
            name="enabled1",
            description="Enabled module 1",
            logger_name="test.enabled1",
            debug_flag="--debug-enabled1",
            enabled=True,
        )
        self.registry.register_module(
            name="enabled2",
            description="Enabled module 2",
            logger_name="test.enabled2",
            debug_flag="--debug-enabled2",
            enabled=True,
        )
        self.registry.register_module(
            name="disabled1",
            description="Disabled module",
            logger_name="test.disabled1",
            debug_flag="--debug-disabled1",
            enabled=False,
        )

        enabled_modules = self.registry.get_enabled_modules()

        assert len(enabled_modules) == 2
        assert "enabled1" in enabled_modules
        assert "enabled2" in enabled_modules
        assert "disabled1" not in enabled_modules

    def test_get_modules_by_category(self):
        """Test getting modules by category."""
        self.registry.register_module(
            name="core1",
            description="Core module 1",
            logger_name="core.module1",
            debug_flag="--debug-core1",
            category="core",
        )
        self.registry.register_module(
            name="core2",
            description="Core module 2",
            logger_name="core.module2",
            debug_flag="--debug-core2",
            category="core",
        )
        self.registry.register_module(
            name="feature1",
            description="Feature module",
            logger_name="feature.module1",
            debug_flag="--debug-feature1",
            category="feature",
        )

        core_modules = self.registry.get_modules_by_category("core")
        feature_modules = self.registry.get_modules_by_category("feature")
        empty_modules = self.registry.get_modules_by_category("nonexistent")

        assert len(core_modules) == 2
        assert "core1" in core_modules
        assert "core2" in core_modules
        assert len(feature_modules) == 1
        assert "feature1" in feature_modules
        assert len(empty_modules) == 0

    def test_get_all_modules(self):
        """Test getting all modules returns copy."""
        self.registry.register_module(
            name="module1",
            description="Module 1",
            logger_name="test.module1",
            debug_flag="--debug-mod1",
        )
        self.registry.register_module(
            name="module2",
            description="Module 2",
            logger_name="test.module2",
            debug_flag="--debug-mod2",
        )

        all_modules = self.registry.get_all_modules()

        assert len(all_modules) == 2
        assert "module1" in all_modules
        assert "module2" in all_modules

        # Verify it's a copy (modifying doesn't affect registry)
        all_modules["test"] = {}
        assert "test" not in self.registry._modules

    def test_get_module_names(self):
        """Test getting module names."""
        self.registry.register_module(
            name="module1",
            description="Module 1",
            logger_name="test.module1",
            debug_flag="--debug-mod1",
        )
        self.registry.register_module(
            name="module2",
            description="Module 2",
            logger_name="test.module2",
            debug_flag="--debug-mod2",
        )

        names = self.registry.get_module_names()

        assert isinstance(names, set)
        assert names == {"module1", "module2"}

    def test_get_debug_logger_names(self):
        """Test getting debug logger names."""
        self.registry.register_module(
            name="module1",
            description="Module 1",
            logger_name="test.logger1",
            debug_flag="--debug-mod1",
        )
        self.registry.register_module(
            name="module2",
            description="Module 2",
            logger_name="test.logger2",
            debug_flag="--debug-mod2",
        )

        logger_names = self.registry.get_debug_logger_names()

        assert isinstance(logger_names, set)
        assert logger_names == {"test.logger1", "test.logger2"}

    def test_get_debug_flags(self):
        """Test getting debug flags mapping."""
        self.registry.register_module(
            name="module1",
            description="Module 1",
            logger_name="test.logger1",
            debug_flag="--debug-mod1",
        )
        self.registry.register_module(
            name="module2",
            description="Module 2",
            logger_name="test.logger2",
            debug_flag="--debug-mod2",
        )

        debug_flags = self.registry.get_debug_flags()

        assert isinstance(debug_flags, dict)
        assert debug_flags == {"--debug-mod1": "module1", "--debug-mod2": "module2"}

    def test_get_module_info(self):
        """Test getting specific module info."""
        self.registry.register_module(
            name="test_module",
            description="Test module",
            logger_name="test.module",
            debug_flag="--debug-test",
            category="testing",
        )

        info = self.registry.get_module_info("test_module")

        assert info["description"] == "Test module"
        assert info["logger_name"] == "test.module"
        assert info["debug_flag"] == "--debug-test"
        assert info["category"] == "testing"
        assert info["enabled"] is True

        # Test nonexistent module
        empty_info = self.registry.get_module_info("nonexistent")
        assert empty_info == {}

    def test_get_categories(self):
        """Test getting all unique categories."""
        self.registry.register_module(
            name="core1",
            description="Core module",
            logger_name="core.module",
            debug_flag="--debug-core",
            category="core",
        )
        self.registry.register_module(
            name="feature1",
            description="Feature module",
            logger_name="feature.module",
            debug_flag="--debug-feature",
            category="feature",
        )
        self.registry.register_module(
            name="feature2",
            description="Another feature",
            logger_name="feature.module2",
            debug_flag="--debug-feature2",
            category="feature",  # Duplicate category
        )

        categories = self.registry.get_categories()

        assert isinstance(categories, set)
        assert categories == {"core", "feature"}

    def test_logger_creation(self):
        """Test that loggers are properly created."""
        self.registry.register_module(
            name="test_module",
            description="Test module",
            logger_name="test.logger.name",
            debug_flag="--debug-test",
        )

        module_info = self.registry._modules["test_module"]
        logger = module_info["logger"]

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.logger.name"

    def test_module_state_transitions(self):
        """Test enable/disable state transitions."""
        self.registry.register_module(
            name="test_module",
            description="Test module",
            logger_name="test.module",
            debug_flag="--debug-test",
            enabled=True,
        )

        # Initially enabled
        assert self.registry.is_module_enabled("test_module") is True

        # Disable it
        self.registry.disable_module("test_module")
        assert self.registry.is_module_enabled("test_module") is False

        # Enable it again
        self.registry.enable_module("test_module")
        assert self.registry.is_module_enabled("test_module") is True

    def test_empty_registry_queries(self):
        """Test queries on empty registry."""
        assert len(self.registry.get_module_names()) == 0
        assert len(self.registry.get_debug_logger_names()) == 0
        assert len(self.registry.get_debug_flags()) == 0
        assert len(self.registry.get_categories()) == 0
        assert len(self.registry.get_enabled_modules()) == 0
        assert len(self.registry.get_modules_by_category("any")) == 0
        assert len(self.registry.get_all_modules()) == 0
