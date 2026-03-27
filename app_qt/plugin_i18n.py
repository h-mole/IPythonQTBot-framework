"""
Plugin Internationalization (i18n) module

Provides independent translation system for plugins.
Each plugin should have its own locales directory.

Usage in plugin:
    from app_qt.plugin_i18n import PluginI18n
    
    # Initialize with plugin name and path
    i18n = PluginI18n("plugin_name", Path(__file__).parent)
    _ = i18n.gettext
    
    # Use translation
    self.button = QPushButton(_("Click Me"))
"""

import os
import gettext
from pathlib import Path
from typing import Optional

# Cache for plugin translators
_plugin_translators = {}


class PluginI18n:
    """
    Plugin-specific internationalization handler
    
    Each plugin gets its own translation domain and locale directory
    """
    
    def __init__(self, plugin_name: str, plugin_path: Path, language: str = None):
        """
        Initialize plugin i18n
        
        Args:
            plugin_name: Unique plugin identifier
            plugin_path: Path to plugin directory
            language: Language code (e.g., "zh_CN", "en"). If None, uses main app language.
        """
        self.plugin_name = plugin_name
        self.plugin_path = Path(plugin_path)
        self.locale_dir = self.plugin_path / "locales"
        
        # Determine language - follow main app's language
        if language is None:
            try:
                # Use absolute import to ensure we get the same module instance as main app
                from app_qt.i18n import get_i18n_manager
                manager = get_i18n_manager()
                self.language = manager.get_current_language()
                if self.language is None:
                    # Fallback to default if not initialized yet
                    from app_qt.i18n import get_default_language
                    self.language = get_default_language()
            except Exception as e:
                print(f"[PluginI18n] Failed to get main app language: {e}")
                from app_qt.i18n import get_default_language
                self.language = get_default_language()
        else:
            self.language = language
        
        # Initialize translator
        self._translator = self._load_translator()
        
        # Cache this instance
        _plugin_translators[plugin_name] = self
        
        print(f"[PluginI18n] '{plugin_name}' initialized with language: {self.language}")
    
    def _load_translator(self) -> gettext.GNUTranslations:
        """Load gettext translator for this plugin"""
        # Check if locale directory exists
        if not self.locale_dir.exists():
            # No translations available, use null translation
            return gettext.NullTranslations()
        
        try:
            translator = gettext.translation(
                self.plugin_name,  # Use plugin name as domain
                localedir=str(self.locale_dir),
                languages=[self.language],
                fallback=True  # Use fallback if translation not found
            )
            return translator
        except Exception as e:
            print(f"[PluginI18n] Failed to load translations for '{self.plugin_name}': {e}")
            return gettext.NullTranslations()
    
    def gettext(self, message: str) -> str:
        """
        Translate a message
        
        Args:
            message: The message to translate (in English)
        
        Returns:
            str: The translated message
        """
        return self._translator.gettext(message)
    
    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """
        Translate a message with plural forms
        
        Args:
            singular: Singular form message
            plural: Plural form message
            n: Count
        
        Returns:
            str: The translated message
        """
        return self._translator.ngettext(singular, plural, n)
    
    def reload(self, language: str = None):
        """
        Reload translations with new language
        
        Args:
            language: New language code. If None, follows main app language.
        """
        if language:
            self.language = language
        else:
            try:
                from app_qt.i18n import get_i18n_manager
                manager = get_i18n_manager()
                self.language = manager.get_current_language()
                if self.language is None:
                    from app_qt.i18n import get_default_language
                    self.language = get_default_language()
            except Exception:
                from app_qt.i18n import get_default_language
                self.language = get_default_language()
        
        self._translator = self._load_translator()
        print(f"[PluginI18n] '{self.plugin_name}' reloaded with language: {self.language}")


def get_plugin_i18n(plugin_name: str, plugin_path: Optional[Path] = None) -> PluginI18n:
    """
    Get or create a PluginI18n instance for a plugin
    
    Args:
        plugin_name: Unique plugin identifier
        plugin_path: Path to plugin directory (only needed for first call)
    
    Returns:
        PluginI18n: The plugin's i18n instance
    """
    if plugin_name in _plugin_translators:
        return _plugin_translators[plugin_name]
    
    if plugin_path is None:
        raise ValueError(f"Plugin '{plugin_name}' i18n not initialized and no path provided")
    
    return PluginI18n(plugin_name, plugin_path)


def reload_all_plugins(language: str = None):
    """
    Reload all plugin translations
    
    Args:
        language: New language code. If None, uses system locale.
    """
    for plugin_name, i18n in _plugin_translators.items():
        i18n.reload(language)
        print(f"[PluginI18n] Reloaded '{plugin_name}'")
