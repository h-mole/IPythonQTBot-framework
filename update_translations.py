#!/usr/bin/env python3
"""
Translation File Update Script

Features:
1. Extract translatable strings from Python source code (supports _() and gettext() calls)
2. Merge into existing .po files (preserving existing translations)
3. Compile .po files to .mo files

Usage:
    python update_translations.py              # Update all translations
    python update_translations.py --main       # Update main UI translation only
    python update_translations.py --plugins    # Update plugin translations only
    python update_translations.py --plugin daily_tasks  # Update specific plugin

Requirements:
    - Mark strings for translation using _() or gettext()
    - .po files should use UTF-8 encoding
"""

import ast
import os
import re
import struct
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Main application code directory
APP_DIR = PROJECT_ROOT / "app_qt"

# Plugins directory
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# Default language
DEFAULT_LANGUAGE = "zh_CN"


class TranslationExtractor(ast.NodeVisitor):
    """Extract translatable strings from Python AST"""
    
    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.strings: List[Tuple[str, int, str]] = []  # (msgid, lineno, context)
        self.file_content = source_file.read_text(encoding="utf-8")
        
    def extract(self) -> List[Tuple[str, int, str]]:
        """Extract all translatable strings"""
        try:
            tree = ast.parse(self.file_content)
            self.visit(tree)
        except SyntaxError as e:
            print(f"  [WARN] Syntax error: {self.source_file} - {e}")
        return self.strings
    
    def visit_Call(self, node: ast.Call):
        """Visit function calls, check for _() or gettext()"""
        func_name = self._get_func_name(node.func)
        
        if func_name in ("_", "gettext", "tr", "ngettext"):
            # Get first argument (the string to translate)
            if node.args and isinstance(node.args[0], ast.Constant):
                if isinstance(node.args[0].value, str):
                    msgid = node.args[0].value
                    lineno = node.lineno
                    self.strings.append((msgid, lineno, self.file_content.split('\n')[lineno-1].strip()[:60]))
            elif node.args and isinstance(node.args[0], ast.JoinedStr):
                # f-string case, try to extract prefix
                msgid = self._extract_fstring_prefix(node.args[0])
                if msgid:
                    lineno = node.lineno
                    self.strings.append((msgid, lineno, self.file_content.split('\n')[lineno-1].strip()[:60]))
        
        self.generic_visit(node)
    
    def _get_func_name(self, func: ast.AST) -> Optional[str]:
        """Get function name"""
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return func.attr
        return None
    
    def _extract_fstring_prefix(self, node: ast.JoinedStr) -> Optional[str]:
        """Try to extract translatable prefix from f-string"""
        # Simplified handling: if f-string contains variables, return first constant part
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
        return None


class PoFile:
    """PO file handler"""
    
    def __init__(self, po_file: Path):
        self.po_file = po_file
        self.translations: Dict[str, str] = {}  # msgid -> msgstr
        self.metadata: Dict[str, str] = {}
        self._parse()
    
    def _parse(self):
        """Parse PO file"""
        if not self.po_file.exists():
            return
        
        content = self.po_file.read_text(encoding="utf-8")
        
        # Extract metadata
        header_match = re.search(r'msgid ""\s+msgstr ""\s+((?:"[^"]*"\s*)+)', content)
        if header_match:
            header = header_match.group(1)
            for line in header.split('"\n"'):
                line = line.strip('"')
                if ':' in line:
                    key, value = line.split(':', 1)
                    self.metadata[key.strip()] = value.strip()
        
        # Extract translation entries
        # Pattern: msgid "..." msgstr "..."
        pattern = r'(?:#:.*?\n)*msgid\s+((?:"[^"]*"\s*)+)msgstr\s+((?:"[^"]*"\s*)+)'
        for match in re.finditer(pattern, content):
            msgid = self._unquote(match.group(1))
            msgstr = self._unquote(match.group(2))
            if msgid:  # Skip empty msgid (metadata)
                self.translations[msgid] = msgstr
    
    def _unquote(self, s: str) -> str:
        """Remove quotes and handle escapes"""
        lines = s.strip().split('\n')
        result = ""
        for line in lines:
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                result += line[1:-1]
        # Handle escape characters
        result = result.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
        return result
    
    def _quote(self, s: str) -> str:
        """Add quotes and handle escapes"""
        # Handle escape characters
        s = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')
        
        # If string is long, split into multiple lines
        if len(s) > 76:
            lines = []
            while s:
                chunk = s[:76]
                s = s[76:]
                lines.append(f'"{chunk}"')
            return '\n'.join(lines)
        return f'"{s}"'
    
    def merge(self, new_strings: List[Tuple[str, int, str]], source_file: str = "") -> Set[str]:
        """
        Merge new translatable strings
        
        Args:
            new_strings: [(msgid, lineno, context), ...]
            source_file: Source file path (for comments)
        
        Returns:
            Set of newly added msgids
        """
        existing = set(self.translations.keys())
        new_msgids = set(s[0] for s in new_strings)
        
        # Find newly added
        added = new_msgids - existing
        
        # Find removed (keep but mark as obsolete)
        removed = existing - new_msgids
        
        # Add new entries
        for msgid, lineno, context in new_strings:
            if msgid not in self.translations:
                self.translations[msgid] = ""
        
        return added
    
    def write(self, source_refs: Dict[str, List[Tuple[str, int]]] = None):
        """
        Write PO file
        
        Args:
            source_refs: {msgid: [(filename, lineno), ...]}
        """
        lines = []
        
        # Write header
        lines.append(f'# Chinese (Simplified) translations')
        lines.append(f'msgid ""')
        lines.append(f'msgstr ""')
        lines.append(f'"Project-Id-Version: PROJECT 1.0.0\\n"')
        lines.append(f'"Content-Type: text/plain; charset=UTF-8\\n"')
        lines.append(f'"Content-Transfer-Encoding: 8bit\\n"')
        lines.append(f'"Language: {DEFAULT_LANGUAGE}\\n"')
        lines.append('')
        
        # Sort entries alphabetically
        for msgid in sorted(self.translations.keys()):
            if not msgid:  # Skip empty string
                continue
            
            msgstr = self.translations[msgid]
            
            # Write source file reference comments
            if source_refs and msgid in source_refs:
                refs = source_refs[msgid]
                ref_str = " ".join([f"{f}:{l}" for f, l in refs[:5]])  # Show at most 5 refs
                lines.append(f'#: {ref_str}')
            
            # Write msgid and msgstr
            lines.append(f'msgid {self._quote(msgid)}')
            lines.append(f'msgstr {self._quote(msgstr)}')
            lines.append('')
        
        # Ensure directory exists
        self.po_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        content = '\n'.join(lines)
        self.po_file.write_text(content, encoding="utf-8")
    
    def compile_to_mo(self, mo_file: Path):
        """Compile to MO file using Python's built-in msgfmt"""
        # Use a simpler approach: write a temporary .po and use msgfmt if available
        # Otherwise, use our own implementation
        
        try:
            # Try to use msgfmt from pygettext if available
            import subprocess
            result = subprocess.run(
                ['msgfmt', '-o', str(mo_file), str(self.po_file)],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if result.returncode == 0:
                return
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
        
        # Fallback: our own implementation
        self._compile_to_mo_fallback(mo_file)
    
    def _compile_to_mo_fallback(self, mo_file: Path):
        """Fallback MO file compiler"""
        entries = [(msgid, msgstr) for msgid, msgstr in self.translations.items() if msgid]
        entries.sort(key=lambda x: x[0])
        
        # Magic number and version
        magic = 0x950412de
        version = 0
        
        # Metadata entry
        metadata = f'Project-Id-Version: PROJECT 1.0.0\nContent-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\nLanguage: {DEFAULT_LANGUAGE}\n\n'
        
        # Prepare all strings (including metadata)
        all_strings = [(b'', metadata.encode('utf-8'))]  # Empty key for metadata
        for msgid, msgstr in entries:
            all_strings.append((msgid.encode('utf-8'), msgstr.encode('utf-8')))
        
        n_entries = len(all_strings)
        
        # Offsets
        header_size = 7 * 4  # 28 bytes
        orig_tab_offset = header_size
        trans_tab_offset = orig_tab_offset + n_entries * 8
        data_offset = trans_tab_offset + n_entries * 8
        
        # Build string data and tables
        key_table = []
        val_table = []
        string_data = b''
        
        for key_bytes, val_bytes in all_strings:
            # Key (original string)
            key_table.append((len(key_bytes), data_offset + len(string_data)))
            string_data += key_bytes + b'\x00'
            
            # Value (translation)
            val_table.append((len(val_bytes), data_offset + len(string_data)))
            string_data += val_bytes + b'\x00'
        
        # Build MO file
        mo_data = struct.pack('<IIIIIII',
            magic,
            version,
            n_entries,
            orig_tab_offset,
            trans_tab_offset,
            0,  # hash table size
            orig_tab_offset  # hash table offset (unused)
        )
        
        # Key table (length, offset pairs)
        for length, offset in key_table:
            mo_data += struct.pack('<II', length, offset)
        
        # Value table (length, offset pairs)
        for length, offset in val_table:
            mo_data += struct.pack('<II', length, offset)
        
        # String data
        mo_data += string_data
        
        # Write file
        mo_file.parent.mkdir(parents=True, exist_ok=True)
        mo_file.write_bytes(mo_data)


def extract_from_file(py_file: Path) -> List[Tuple[str, int, str]]:
    """Extract translatable strings from a single Python file"""
    extractor = TranslationExtractor(py_file)
    return extractor.extract()


def extract_from_directory(directory: Path) -> Tuple[Dict[str, List[Tuple[str, int]]], int]:
    """
    Extract all translatable strings from a directory
    
    Returns:
        (msgid_to_refs, total_files)
        msgid_to_refs: {msgid: [(filename, lineno), ...]}
    """
    msgid_to_refs: Dict[str, List[Tuple[str, int]]] = {}
    total_files = 0
    
    for py_file in directory.rglob("*.py"):
        # Skip __pycache__ and venv
        if "__pycache__" in str(py_file) or "venv" in str(py_file):
            continue
        
        strings = extract_from_file(py_file)
        if strings:
            total_files += 1
            for msgid, lineno, _ in strings:
                if msgid not in msgid_to_refs:
                    msgid_to_refs[msgid] = []
                # Store relative path
                rel_path = py_file.relative_to(PROJECT_ROOT)
                msgid_to_refs[msgid].append((str(rel_path), lineno))
    
    return msgid_to_refs, total_files


def update_main_translation():
    """Update main UI translation"""
    print("[Main] Updating main UI translation...")
    
    po_file = APP_DIR / "locales" / DEFAULT_LANGUAGE / "LC_MESSAGES" / "messages.po"
    mo_file = po_file.with_suffix('.mo')
    
    # Extract translatable strings
    print("  [Extract] Extracting strings...")
    msgid_to_refs, total_files = extract_from_directory(APP_DIR)
    print(f"     Scanned {total_files} files, found {len(msgid_to_refs)} unique strings")
    
    # Load existing PO file
    po = PoFile(po_file)
    print(f"     Existing PO file has {len(po.translations)} entries")
    
    # Convert to list format [(msgid, lineno, context), ...]
    all_strings = []
    for msgid, refs in msgid_to_refs.items():
        for ref in refs[:1]:  # Take only first reference
            all_strings.append((msgid, ref[1], ""))
    
    # Merge
    added = po.merge(all_strings)
    if added:
        print(f"  [NEW] Added {len(added)} new entries")
    
    # Write PO file
    print("  [Write] Writing PO file...")
    po.write(msgid_to_refs)
    
    # Compile MO file
    print("  [Compile] Compiling MO file...")
    po.compile_to_mo(mo_file)
    
    print(f"  [OK] Done: {po_file}")
    return True


def update_plugin_translation(plugin_name: str) -> bool:
    """Update translation for a specific plugin"""
    plugin_dir = PLUGINS_DIR / plugin_name
    if not plugin_dir.exists():
        print(f"  [ERROR] Plugin not found: {plugin_name}")
        return False
    
    po_file = plugin_dir / "locales" / DEFAULT_LANGUAGE / "LC_MESSAGES" / f"{plugin_name}.po"
    mo_file = po_file.with_suffix('.mo')
    
    # Extract translatable strings
    print(f"  [Extract] Extracting strings...")
    msgid_to_refs, total_files = extract_from_directory(plugin_dir)
    print(f"     Scanned {total_files} files, found {len(msgid_to_refs)} unique strings")
    
    # Load existing PO file
    po = PoFile(po_file)
    print(f"     Existing PO file has {len(po.translations)} entries")
    
    # Convert to list format
    all_strings = []
    for msgid, refs in msgid_to_refs.items():
        for ref in refs[:1]:
            all_strings.append((msgid, ref[1], ""))
    
    # Merge
    added = po.merge(all_strings)
    if added:
        print(f"  [NEW] Added {len(added)} new entries")
    
    # Write PO file
    print("  [Write] Writing PO file...")
    po.write(msgid_to_refs)
    
    # Compile MO file
    print("  [Compile] Compiling MO file...")
    po.compile_to_mo(mo_file)
    
    print(f"  [OK] Done: {po_file}")
    return True


def update_all_plugin_translations():
    """Update all plugin translations"""
    print("[Plugins] Updating plugin translations...")
    
    plugin_count = 0
    for plugin_dir in PLUGINS_DIR.iterdir():
        if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
            plugin_name = plugin_dir.name
            print(f"\n  [Plugin] {plugin_name}")
            if update_plugin_translation(plugin_name):
                plugin_count += 1
    
    print(f"\n  [OK] Updated {plugin_count} plugins")
    return True


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update and compile translation files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python update_translations.py              # Update all translations
    python update_translations.py --main       # Update main UI translation only
    python update_translations.py --plugins    # Update plugin translations only
    python update_translations.py --plugin daily_tasks  # Update specific plugin
"""
    )
    
    parser.add_argument("--main", action="store_true", help="Update main UI translation only")
    parser.add_argument("--plugins", action="store_true", help="Update plugin translations only")
    parser.add_argument("--plugin", type=str, metavar="NAME", help="Update specific plugin translation")
    parser.add_argument("--list", action="store_true", help="List all translatable plugins")
    
    args = parser.parse_args()
    
    if args.list:
        print("[List] Translatable plugins:")
        for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
            if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                po_file = plugin_dir / "locales" / DEFAULT_LANGUAGE / "LC_MESSAGES" / f"{plugin_dir.name}.po"
                if po_file.exists():
                    print(f"  [OK] {plugin_dir.name} (initialized)")
                else:
                    print(f"  [TODO] {plugin_dir.name} (not initialized)")
        return
    
    # If not specified, update all by default
    update_main = not (args.plugins or args.plugin)
    update_plugins = not (args.main or args.plugin)
    update_specific = args.plugin
    
    print("=" * 60)
    print("Translation File Updater")
    print("=" * 60)
    print()
    
    success = True
    
    if update_specific:
        success = update_plugin_translation(update_specific)
    else:
        if update_main:
            success = update_main_translation() and success
            print()
        
        if update_plugins:
            success = update_all_plugin_translations() and success
    
    print()
    print("=" * 60)
    if success:
        print("[SUCCESS] Translation update complete!")
    else:
        print("[FAILED] Translation update failed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
