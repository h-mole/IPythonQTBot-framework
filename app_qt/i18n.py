"""
Internationalization (i18n) module for IPythonQTBot
Uses gettext-style PO files with Qt integration
"""

import logging
import os
import gettext
from pathlib import Path
from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo
from PySide6.QtWidgets import QApplication
logger = logging.getLogger(__file__)
# Global translator instance
_translator = None

def get_locale_dir() -> Path:
    """Get the locale directory path"""
    return Path(__file__).parent / "locales"

def get_default_language() -> str:
    """Get default language from system locale"""
    
    locale = QLocale.system().name()  # e.g., "zh_CN", "en_US"
    print(f"[i18n] System locale: {locale}")
    # 如果是中文区域（包括简体、繁体等），使用中文
    if locale.startswith("zh"):
        return "zh_CN"
    # 其他所有区域使用英文
    return "en"

def install_translator(language: str = None) -> gettext.GNUTranslations:
    """
    Install gettext translator
    
    Args:
        language: Language code (e.g., "zh_CN", "en"). If None, uses system locale.
    
    Returns:
        gettext.GNUTranslations: The installed translator
    """
    global _translator
    
    if language is None:
        language = get_default_language()
    
    locale_dir = get_locale_dir()
    
    # For English, always use null translation (no translation needed)
    if language == "en":
        null_translator = gettext.NullTranslations()
        null_translator.install()
        _translator = null_translator
        print(f"[i18n] Using null translation for English")
        return null_translator
    
    try:
        # Try to load the specified language with fallback
        translator = gettext.translation(
            "messages",
            localedir=str(locale_dir),
            languages=[language],
            fallback=True  # Always use fallback to avoid errors
        )
        
        # Check if we got a real translation or just NullTranslations
        if isinstance(translator, gettext.GNUTranslations):
            translator.install()
            _translator = translator
            print(f"[i18n] Loaded translations for: {language}")
        else:
            # Got NullTranslations, means translation file not found
            print(f"[i18n] Translation file not found for {language}, using null translation")
            translator.install()
            _translator = translator
        
        return _translator
    except Exception as e:
        print(f"[i18n] Failed to load translations for {language}: {e}")
        # Fallback to English (null translation)
        null_translator = gettext.NullTranslations()
        null_translator.install()
        _translator = null_translator
        return null_translator

def _(message: str) -> str:
    """
    Translate a message
    
    Args:
        message: The message to translate (in English)
    
    Returns:
        str: The translated message
    """
    if _translator is None:
        install_translator()
    return _translator.gettext(message)

def ngettext(singular: str, plural: str, n: int) -> str:
    """
    Translate a message with plural forms
    
    Args:
        singular: Singular form message
        plural: Plural form message
        n: Count
    
    Returns:
        str: The translated message
    """
    if _translator is None:
        install_translator()
    return _translator.ngettext(singular, plural, n)

# Aliases for convenience
def tr(message: str) -> str:
    """Alias for _()"""
    return _(message)

class I18nManager:
    """
    Internationalization Manager - Singleton
    Manages language switching and translation loading
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if I18nManager._initialized:
            return
        I18nManager._initialized = True
        
        self._current_language = None
        self._qt_translator = None
        
        # Load default language
        self.set_language(get_default_language())
    
    def set_language(self, language: str):
        """
        Set the application language
        
        Args:
            language: Language code (e.g., "zh_CN", "en")
        """
        self._current_language = language
        
        # Install gettext translator
        install_translator(language)
        
        # Install Qt translator for standard Qt strings
        self._install_qt_translator(language)
        
        # Reload all plugin translations to match main app language
        try:
            from .plugin_i18n import reload_all_plugins
            reload_all_plugins(language)
        except Exception as e:
            print(f"[I18nManager] Failed to reload plugin translations: {e}")
        
        print(f"[I18nManager] Language set to: {language}")
    
    def _install_qt_translator(self, language: str):
        """Install Qt translator for standard Qt strings"""
        app = QApplication.instance()
        if app is None:
            return
        
        # Remove old translator
        if self._qt_translator is not None:
            app.removeTranslator(self._qt_translator)
            self._qt_translator = None
        
        # Load Qt's own translations (for standard dialogs, etc.)
        qt_translator = QTranslator()
        
        # Load from Qt's own translations
        qt_translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if qt_translator.load(f"qt_{language}", qt_translations_path):
            app.installTranslator(qt_translator)
            self._qt_translator = qt_translator
            print(f"[I18nManager] Qt translator loaded: {language}")
        else:
            # Try loading from our locales directory
            locale_dir = get_locale_dir()
            if qt_translator.load(f"qt_{language}", str(locale_dir)):
                app.installTranslator(qt_translator)
                self._qt_translator = qt_translator
                print(f"[I18nManager] Qt translator loaded from app: {language}")
    
    def get_current_language(self) -> str:
        """Get current language code"""
        return self._current_language
    
    def get_available_languages(self) -> list:
        """
        Get list of available languages
        
        Returns:
            list: List of tuples (language_code, language_name)
        """
        return [
            ("en", _("English")),
            ("zh_CN", _("Chinese (Simplified)")),
        ]

# Global i18n manager instance
_i18n_manager = None

def get_i18n_manager() -> I18nManager:
    """Get global i18n manager instance"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager

# Convenience function for late initialization
def init_i18n(language: str = None):
    """
    Initialize i18n with optional language override
    
    Args:
        language: Language code. If None, uses system locale or saved preference.
    
    Returns:
        I18nManager: The i18n manager instance
    """
    manager = get_i18n_manager()
    print("[i18n] Initializing i18n...")
    if language:
        # 如果显式指定了语言，使用指定的
        manager.set_language(language)
    else:
        # 尝试从配置读取语言设置
        try:
            # 延迟导入以避免循环导入
            from .configs import settings
            print("[i18n] Reading language from config...")
            config_language = settings.language.language
            if config_language and config_language != "auto":
                manager.set_language(config_language)
                logger.info(f"[i18n] Language set from config: {config_language}")
            else:
                # 使用系统默认
                manager.set_language(get_default_language())
        except Exception as e:
            # 如果读取配置失败，使用系统默认
            print(f"[i18n] Failed to read language from config: {e}")
            manager.set_language(get_default_language())
    
    return manager
