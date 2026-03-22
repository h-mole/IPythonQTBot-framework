from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Self,
    Tuple,
    Type,
    get_args,
    get_origin,
)
from pydantic import BaseModel, ConfigDict
from pathlib import Path
from .loaders import DEFAULT_LOADERS, BaseConfigLoader
from .type_parser import TypeParser
from PySide6.QtWidgets import (
    QWidget,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QPushButton,
    QFrame,
    QSizePolicy
)
from PySide6.QtCore import Signal, QObject
from .fields import WidgetMetadata
from .widgets import TagInputWidget, PathBrowseWidget


class _SettingsBridge(QObject):
    value_changed = Signal(str, object)


class BaseSettings(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        extra='ignore',  # Ignore extra fields to exclude private attributes
    )
    _type_parser: ClassVar[TypeParser] = TypeParser()

    def model_post_init(self, context: Any) -> None:
        self._widgets: Dict[str, QWidget] = {}
        self._bridge: _SettingsBridge = _SettingsBridge()
        self._config_file: Optional[Path] = None
        self._config_loader: Optional[BaseConfigLoader] = None

    def __init__(self, **data):
        for key, val in data.items():
            data[key] = self._type_parser.parse_value(val)
        super().__init__(**data)

    @classmethod
    def load(cls, config_file: str | Path, auto_create: bool = False) -> Self:
        config_file = Path(config_file)
        config_loader = DEFAULT_LOADERS.get(config_file.suffix, None)
        if config_loader is None:
            raise Exception(
                f"Config loader for .{config_file.suffix} format, does not exist,"
                f" available file formats: {','.join(DEFAULT_LOADERS.keys())} "
            )

        # Create instance of config loader
        config_loader_instance = config_loader(config_file)

        # Load config
        if config_file.exists():
            data = config_loader_instance.load()
        else:
            data = {}

        # Create settings instance and set fields
        instance = cls(**data)
        instance._config_file = config_file
        instance._config_loader = config_loader_instance

        # If True, create config file with default values first time
        if auto_create and not config_file.exists():
            instance._save_settings()

        return instance

    def _get_field_info(self, field_name: str):
        if field_name not in self.__pydantic_fields__:
            raise RuntimeError(f"No such field: {field_name}")
        return self.__pydantic_fields__[field_name]

    def _get_or_create_widget_metadata(self, field_name: str) -> WidgetMetadata:
        field_info = self._get_field_info(field_name)
        metadata = field_info.json_schema_extra.get(  # type: ignore
            "widget_metadata",
            WidgetMetadata(
                title=field_info.title,
                description=field_info.description,
            ),
        )
        return metadata  # type: ignore

    def _save_settings(self):
        if not hasattr(self, "_config_file") or self._config_file is None:
            # No config file set, skip saving
            return

        if not hasattr(self, "_config_loader") or self._config_loader is None:
            # No config loader set, skip saving
            return

        data = {}
        for field_name, field_info in self.__pydantic_fields__.items():
            # Skipp config value if excluded
            if field_info.exclude:
                continue

            # Get widget metadata
            widget_metadata = self._get_or_create_widget_metadata(field_name)
            # Get python value and try serialize type if necessary
            value = getattr(self, field_name)
            
            # Handle BaseSettings instances by converting them to dict
            if isinstance(value, BaseSettings):
                value = value.model_dump()
            elif isinstance(value, list):
                # Handle lists of BaseSettings instances
                new_value = []
                for item in value:
                    if isinstance(item, BaseSettings):
                        new_value.append(item.model_dump())
                    else:
                        new_value.append(self._type_parser.serialize_value(item))
                value = new_value
            else:
                value = self._type_parser.serialize_value(value)

            # Save settings by groups
            if widget_metadata and widget_metadata.group:
                if widget_metadata.group not in data:
                    data[widget_metadata.group] = {}
                data[widget_metadata.group][field_name] = value
            else:
                data[field_name] = value

        self._config_loader.save(data)

    def _on_value_changed(self, name: str, value: Any):
        setattr(self, name, value)
        self._save_settings()

        # Emit value changed signal in bridge
        if self._bridge:
            self._bridge.value_changed.emit(name, value)

    def _is_list_of_settings(self, field_type: Any) -> tuple[bool, Optional[Type]]:
        """Check if field type is List[BaseSettings] and return the item type."""
        origin = get_origin(field_type)
        if origin is list or origin is List:
            args = get_args(field_type)
            if args:
                item_type = args[0]
                # Check if item type is a subclass of BaseSettings
                try:
                    from .settings import BaseSettings as SettingsBase
                    if isinstance(item_type, type) and issubclass(item_type, SettingsBase):
                        return True, item_type
                except (ImportError, TypeError):
                    pass
                # Also check with self's class
                if isinstance(item_type, type) and issubclass(item_type, BaseSettings):
                    return True, item_type
        return False, None

    def _is_nested_settings(self, field_type: Any) -> tuple[bool, Optional[Type]]:
        """Check if field type is a subclass of BaseSettings."""
        try:
            from .settings import BaseSettings as SettingsBase
            if isinstance(field_type, type) and issubclass(field_type, SettingsBase):
                return True, field_type
        except (ImportError, TypeError):
            pass
        if isinstance(field_type, type) and issubclass(field_type, BaseSettings):
            return True, field_type
        return False, None

    def _create_settings_list_widget(
        self, 
        name: str, 
        current_value: List[Any], 
        item_type: Type
    ) -> QWidget:
        """Create a widget for editing a list of BaseSettings items."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Store reference to item type
        container.setProperty("item_type", item_type)
        container.setProperty("field_name", name)
        
        # Create scroll area for items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        from PySide6.QtCore import Qt
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for items
        items_container = QWidget()
        self._items_layout = QVBoxLayout(items_container)
        self._items_layout.setSpacing(5)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add existing items
        self._rebuild_settings_list_items(name, items_container, current_value, item_type)
        
        scroll_area.setWidget(items_container)
        layout.addWidget(scroll_area)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("+ 添加")
        add_button.clicked.connect(lambda: self._on_add_settings_item(name, items_container, item_type))
        button_layout.addWidget(add_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return container
    
    def _rebuild_settings_list_items(
        self,
        name: str,
        items_container: QWidget,
        items_list: List[Any],
        item_type: Type
    ):
        """Rebuild all items in the settings list."""
        # Clear existing items
        while self._items_layout.count():
            item = self._items_layout.takeAt(0)
            if item is not None and item.widget():
                item.widget().deleteLater()
        
        # Add each item
        for idx, item_data in enumerate(items_list):
            item_widget = self._create_settings_list_item_widget(
                name, idx, item_data, item_type, items_container
            )
            self._items_layout.addWidget(item_widget)
        
        self._items_layout.addStretch()
    
    def _create_settings_list_item_widget(
        self,
        name: str,
        index: int,
        item_data: Any,
        item_type: Type,
        parent: QWidget
    ) -> QFrame:
        """Create a single item widget for editing a settings instance."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create header with delete button
        header_layout = QHBoxLayout()
        title_label = QLineEdit(f"{item_type.__name__} #{index + 1}")
        title_label.setReadOnly(True)
        header_layout.addWidget(title_label)
        
        delete_button = QPushButton("删除")
        delete_button.setStyleSheet("background-color: #ff6b6b; color: white;")
        delete_button.clicked.connect(lambda: self._on_delete_settings_item(name, index, parent))
        header_layout.addWidget(delete_button)
        
        frame_layout.addLayout(header_layout)
        
        # Create form for this item's settings
        try:
            # Create temporary instance if needed
            if not isinstance(item_data, item_type):
                item_instance = item_type(**(item_data if isinstance(item_data, dict) else {}))
            else:
                item_instance = item_data
            
            # Get the item's form - create without scroll area
            item_form = item_instance.create_form(parent)
            
            # Extract the inner widget from scroll area if present
            if isinstance(item_form, QScrollArea):
                inner_widget = item_form.widget()
                if inner_widget:
                    inner_widget.setSizePolicy(
                        QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.MinimumExpanding
                    )
                    frame_layout.addWidget(inner_widget)
            else:
                item_form.setSizePolicy(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.MinimumExpanding
                )
                frame_layout.addWidget(item_form)
            
        except Exception as e:
            error_label = QTextEdit(f"Error loading settings: {str(e)}")
            error_label.setReadOnly(True)
            error_label.setMaximumHeight(50)
            frame_layout.addWidget(error_label)
        
        return frame
    
    def _on_add_settings_item(
        self,
        name: str,
        items_container: QWidget,
        item_type: Type
    ):
        """Handle adding a new settings item."""
        # Get current list
        current_list = getattr(self, name, [])
        
        # Create new instance with defaults
        new_item = item_type()
        current_list.append(new_item)
        
        # Update model
        setattr(self, name, current_list)
        
        # Rebuild UI
        self._rebuild_settings_list_items(name, items_container, current_list, item_type)
        
        # Save settings
        self._save_settings()
    
    def _on_delete_settings_item(
        self,
        name: str,
        index: int,
        items_container: QWidget
    ):
        """Handle deleting a settings item."""
        # Get current list
        current_list = getattr(self, name, [])
        
        # Remove item at index
        if 0 <= index < len(current_list):
            del current_list[index]
            
            # Update model
            setattr(self, name, current_list)
            
            # Rebuild UI - need to get the type from remaining items or stored type
            if current_list:
                first_item = current_list[0]
                item_type = type(first_item)
                self._rebuild_settings_list_items(name, items_container, current_list, item_type)
            else:
                # If list is empty, just clear the layout
                while self._items_layout.count():
                    item = self._items_layout.takeAt(0)
                    if item is not None and item.widget():
                        item.widget().deleteLater()
                self._items_layout.addStretch()
            
            # Save settings
            self._save_settings()

    def _create_nested_settings_widget(
        self,
        name: str,
        current_value: Any
    ) -> QWidget:
        """Create a widget for editing a nested BaseSettings instance."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a form for the nested settings
        try:
            # Get the nested settings instance
            nested_settings = current_value
            if isinstance(nested_settings, BaseSettings):
                # Create form from the nested settings
                nested_form = nested_settings.create_form(container)
                layout.addWidget(nested_form)
            else:
                # Fallback to line edit if not a BaseSettings instance
                line_edit = QLineEdit(str(current_value) if current_value is not None else "")
                line_edit.textChanged.connect(lambda v: self._on_value_changed(name, v))
                layout.addWidget(line_edit)
        except Exception as e:
            error_label = QTextEdit(f"Error loading nested settings: {str(e)}")
            error_label.setReadOnly(True)
            error_label.setMaximumHeight(50)
            layout.addWidget(error_label)
        
        return container

    def _create_widget_for_field(self, name: str, widget_metadata: WidgetMetadata):
        field_info = self._get_field_info(name)
        field_type = field_info.annotation

        # Handle optional types
        origin = get_origin(field_type)
        if origin is type(Optional):
            args = get_args(field_type)
            field_type = args[0] if args else str

        # Create widget
        widget = None
        current_value = getattr(self, name)

        # Exclude
        if field_info.exclude or widget_metadata.widget == "hidden":
            return None

        # Check if this is List[BaseSettings]
        is_list_settings, item_type = self._is_list_of_settings(field_type)
        if is_list_settings and item_type:
            widget = self._create_settings_list_widget(name, current_value, item_type)
        # Check if this is a nested BaseSettings
        elif self._is_nested_settings(field_type)[0]:
            widget = self._create_nested_settings_widget(name, current_value)
        elif widget_metadata.choices:
            widget = QComboBox()
            widget.addItems([str(c) for c in widget_metadata.choices])
            if current_value in widget_metadata.choices:
                widget.setCurrentText(str(current_value))
            widget.currentTextChanged.connect(
                lambda v: self._on_value_changed(
                    name, type(current_value)(v) if v else v
                )
            )
        elif get_origin(field_type) is list or widget_metadata.widget == "tags":
            widget = TagInputWidget()
            widget.set_tags(list(current_value))
            widget.tags_changed.connect(lambda v: self._on_value_changed(name, list(v)))

        elif (
            field_type == Path
            or widget_metadata.fs_mode
            or widget_metadata.widget == "path"
        ):
            widget = PathBrowseWidget(widget_metadata.fs_mode or "file")
            widget.set_path(Path(current_value))
            widget.path_changed.connect(lambda v: self._on_value_changed(name, Path(v)))

        elif field_type is bool or widget_metadata.widget == "checkbox":
            widget = QCheckBox()
            widget.setChecked(bool(current_value))
            widget.stateChanged.connect(
                lambda state: self._on_value_changed(name, bool(state))
            )

        elif field_type is int or widget_metadata.widget == "spinbox":
            widget = QSpinBox()
            constraints = field_info.metadata
            ge = next(
                (c.ge for c in constraints if hasattr(c, "ge") and c.ge is not None),
                None,
            )
            le = next(
                (c.le for c in constraints if hasattr(c, "le") and c.le is not None),
                None,
            )

            widget.setMinimum(int(ge) if ge is not None else -2147483648)
            widget.setMaximum(int(le) if le is not None else 2147483647)
            widget.setValue(int(current_value))
            widget.valueChanged.connect(lambda v: self._on_value_changed(name, v))

        elif field_type is float or widget_metadata.widget == "doublespinbox":
            widget = QDoubleSpinBox()
            constraints = field_info.metadata
            ge = next(
                (c.ge for c in constraints if hasattr(c, "ge") and c.ge is not None),
                None,
            )
            le = next(
                (c.le for c in constraints if hasattr(c, "le") and c.le is not None),
                None,
            )

            widget.setMinimum(ge if ge is not None else -2147483648)
            widget.setMaximum(le if le is not None else 2147483647)
            widget.setValue(float(current_value))
            widget.valueChanged.connect(lambda v: self._on_value_changed(name, v))

        elif widget_metadata.widget == "password":
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.EchoMode.Password)
            widget.setText(str(current_value) if current_value is not None else "")
            widget.textChanged.connect(lambda v: self._on_value_changed(name, v))

        elif widget_metadata.widget == "textarea":
            widget = QTextEdit()
            widget.setText(str(current_value) if current_value is not None else "")
            widget.textChanged.connect(
                lambda: self._on_value_changed(name, widget.toPlainText())
            )

        # Default to line edit
        else:
            widget = QLineEdit()
            widget.setText(str(current_value) if current_value is not None else "")
            widget.textChanged.connect(lambda v: self._on_value_changed(name, v))

        # Set tooltip
        tooltip = field_info.description or widget_metadata.description
        if tooltip:
            widget.setToolTip(tooltip)

        # Connect bridge signal for synchronization
        if self._bridge:
            self._connect_bridge_signal(widget, name)
        return widget

    def _connect_bridge_signal(self, widget: QWidget, name: str):
        """Connect bridge signal for widget synchronization."""

        def handler(changed_name, new_value):
            if changed_name != name:
                return

            # Sync widget from model change
            if isinstance(widget, QLineEdit):
                if widget.text() != str(new_value):
                    widget.blockSignals(True)
                    widget.setText(str(new_value))
                    widget.blockSignals(False)
            elif isinstance(widget, QCheckBox):
                if widget.isChecked() != bool(new_value):
                    widget.blockSignals(True)
                    widget.setChecked(bool(new_value))
                    widget.blockSignals(False)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                if widget.value() != new_value:
                    widget.blockSignals(True)
                    widget.setValue(new_value)
                    widget.blockSignals(False)
            elif isinstance(widget, QComboBox):
                if widget.currentText() != str(new_value):
                    widget.blockSignals(True)
                    widget.setCurrentText(str(new_value))
                    widget.blockSignals(False)
            elif isinstance(widget, QTextEdit):
                if widget.toPlainText() != str(new_value):
                    widget.blockSignals(True)
                    widget.setPlainText(str(new_value))
                    widget.blockSignals(False)
            elif isinstance(widget, PathBrowseWidget):
                if widget.get_path() != Path(new_value):
                    widget.blockSignals(True)
                    widget.set_path(Path(new_value))
                    widget.blockSignals(False)
            elif isinstance(widget, TagInputWidget):
                if widget.get_tags() != list(new_value):
                    widget.blockSignals(True)
                    widget.set_tags(list(new_value))
                    widget.blockSignals(False)

        self._bridge.value_changed.connect(handler)

    def __setattr__(self, name: str, value: Any) -> None:
        """Overide __setattr__ to emit value changed signal if directly updated settings attribute"""

        # Check if the attribute is a Pydantic field
        if name in self.__pydantic_fields__:
            old_value = getattr(self, name, None)
            super().__setattr__(name, value)
            # Update if value different
            if old_value != value:
                self._on_value_changed(name, value)
        else:
            super().__setattr__(name, value)

    def get_widget(self, field_name: str, with_label: bool = True) -> QWidget:
        """Return a cloned widget for a specific field (synchronized)."""
        # Get widget metadata
        widget_metadata = self._get_or_create_widget_metadata(field_name)

        # Clone widget (recreate it with same setup)
        widget = self._create_widget_for_field(field_name, widget_metadata)
        if widget is None:
            raise ValueError("Field exists but widget was disabled or excluded")

        # Create form layout it with label flag
        if with_label:
            form = QFormLayout()
            form.addRow(
                widget_metadata.title or field_name.replace("_", " ").title(), widget
            )
            widget = QWidget()
            widget.setLayout(form)

        return widget

    def get_group(self, group_name: str, group_title: Optional[str] = None) -> QGroupBox:
        fields = []

        # Get widget metadata by group
        for field_name in self.__pydantic_fields__.keys():
            widget_metadata = self._get_or_create_widget_metadata(field_name)
            if widget_metadata.group.lower() == group_name.lower():
                fields.append((field_name, widget_metadata))

        if len(fields) == 0:
            raise ValueError(f"No such group: {group_name}")

        return self._create_groupbox_for_group(group_name, fields, group_title)

    def create_form(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create PySide6 UI with form layout and group boxes."""
        main_widget = QWidget(parent)
        main_widget.resize(600, 400)
        main_layout = QVBoxLayout(main_widget)

        # Group fields by group name
        groups: Dict[str, list] = {}
        for field_name in self.__pydantic_fields__.keys():
            widget_metadata = self._get_or_create_widget_metadata(field_name)

            group_name = widget_metadata.group
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append((field_name, widget_metadata))

        # Create grouped fields in group boxes
        for group_name in sorted(groups.keys()):
            group_box = self._create_groupbox_for_group(group_name, groups[group_name])
            main_layout.addWidget(group_box)
        main_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(main_widget)
        return scroll_area

    def _create_groupbox_for_group(
        self, group_name: str, fields: List[Tuple[str, WidgetMetadata]], group_title: Optional[str] = None
    ):
        """Helper to create groupbox from field in same group"""
        group_box = QGroupBox(group_title or group_name.replace("_", " ").title())
        group_layout = QFormLayout(group_box)
        
        # Set size policy to expand vertically based on content
        group_box.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.MinimumExpanding
        )

        for field_name, widget_info in fields:
            widget = self._create_widget_for_field(field_name, widget_info)
            if widget is None:
                continue

            label = widget_info.title or field_name.replace("_", " ").title()
            group_layout.addRow(label, widget)
        
        # Adjust size to fit content
        group_box.adjustSize()

        return group_box
