from typing import (
    Any,
    Callable,
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
    QSizePolicy,
    QLayout,
    QTabWidget,
    QStackedWidget,
    QLabel,
)
from PySide6.QtCore import Signal, QObject, Qt
from .fields import WidgetMetadata
from .widgets import TagInputWidget, PathBrowseWidget


class _SettingsBridge(QObject):
    value_changed = Signal(str, object)


class BaseSettings(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_get_all_enum_values=True,
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
        """Create a widget for editing a list of BaseSettings items (without scroll area)."""
        container = QWidget()
        # 设置 SizePolicy 让容器根据内容自动调整高度
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        # 关键：设置 sizeConstraint 让 widget 根据内容调整大小
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        
        # Store reference to item type
        container.setProperty("item_type", item_type)
        container.setProperty("field_name", name)
        
        # Container for items (直接使用容器，不使用滚动区域)
        items_container = QWidget()
        items_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._items_layout = QVBoxLayout(items_container)
        self._items_layout.setSpacing(5)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        # 关键：设置 sizeConstraint
        self._items_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        
        # Add existing items
        self._rebuild_settings_list_items(name, items_container, current_value, item_type)
        
        layout.addWidget(items_container)
        
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
            item_form = item_instance.create_form_widget(parent)
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
    
    def _update_parent_geometry(self, widget: QWidget):
        """向上传播 geometry 更新，确保 QScrollArea 能感知到内容大小变化。"""
        # 从当前 widget 开始，向上遍历所有父 widget，调用 updateGeometry
        current = widget
        while current is not None:
            current.updateGeometry()
            # 如果到达 QScrollArea，也更新它的 viewport
            if isinstance(current, QScrollArea):
                current.updateGeometry()
                # 强制调整内部 widget 大小
                if current.widget():
                    current.widget().adjustSize()
                break
            current = current.parentWidget()
    
    def _create_settings_tabs_widget(
        self, 
        name: str, 
        current_value: List[Any], 
        item_type: Type
    ) -> QWidget:
        """Create a widget for editing a list of BaseSettings items with tab-based display."""
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        
        # Store reference to item type
        container.setProperty("item_type", item_type)
        container.setProperty("field_name", name)
        
        # 创建标签栏（使用自定义按钮实现，以便控制样式）
        tab_bar = QWidget()
        tab_bar_layout = QHBoxLayout(tab_bar)
        tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        tab_bar_layout.setSpacing(5)
        
        # 创建内容区域（使用 QStackedWidget）
        content_stack = QStackedWidget()
        content_stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        # 存储标签按钮和内容 widget 的映射
        tab_buttons: List[QPushButton] = []
        tab_contents: List[QWidget] = []
        
        def select_tab(index: int):
            """切换到指定标签页"""
            content_stack.setCurrentIndex(index)
            # 更新按钮样式
            for i, btn in enumerate(tab_buttons):
                if i == index:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2196F3;
                            color: white;
                            font-weight: bold;
                            padding: 8px 16px;
                            border: none;
                            border-radius: 4px 4px 0 0;
                        }
                        QPushButton:hover {
                            background-color: #1976D2;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e0e0e0;
                            color: #333;
                            padding: 8px 16px;
                            border: none;
                            border-radius: 4px 4px 0 0;
                        }
                        QPushButton:hover {
                            background-color: #d0d0d0;
                        }
                    """)
        
        def delete_tab(index: int):
            """删除指定标签页"""
            nonlocal tab_buttons, tab_contents
            current_list = getattr(self, name, [])
            if 0 <= index < len(current_list):
                # 从列表中删除
                del current_list[index]
                setattr(self, name, current_list)
                
                # 移除按钮
                btn = tab_buttons.pop(index)
                btn.deleteLater()
                
                # 移除内容 widget
                content = tab_contents.pop(index)
                content_stack.removeWidget(content)
                content.deleteLater()
                
                # 更新剩余按钮的索引
                for i, btn in enumerate(tab_buttons):
                    # 断开旧连接并重新连接
                    try:
                        btn.clicked.disconnect()
                    except:
                        pass
                    btn.clicked.connect(lambda checked, idx=i: select_tab(idx))
                    # 更新删除按钮
                    # 需要重新创建标签按钮以更新删除功能
                
                # 如果没有标签了，显示空状态
                if len(tab_buttons) == 0:
                    content_stack.setCurrentIndex(-1)
                else:
                    # 选择前一个标签（或第一个）
                    new_index = min(index, len(tab_buttons) - 1)
                    select_tab(new_index)
                
                # 更新删除按钮的连接
                _reconnect_delete_buttons()
                
                # 触发 geometry 更新
                self._update_parent_geometry(container)
                
                # 保存设置
                self._save_settings()
        
        def _reconnect_delete_buttons():
            """重新连接所有删除按钮"""
            for i, (btn, content) in enumerate(zip(tab_buttons, tab_contents)):
                # 找到删除按钮并重新连接
                # 我们需要在内容 widget 中查找删除按钮
                header = content.findChild(QHBoxLayout)
                if header:
                    # 查找删除按钮（通过 objectName）
                    for j in range(header.count()):
                        item = header.itemAt(j)
                        if item and item.widget():
                            widget = item.widget()
                            if isinstance(widget, QPushButton) and widget.objectName() == "delete_btn":
                                try:
                                    widget.clicked.disconnect()
                                except:
                                    pass
                                widget.clicked.connect(lambda checked, idx=i: delete_tab(idx))
        
        def add_tab(item_data: Any = None, select: bool = True):
            """添加新标签页"""
            nonlocal tab_buttons, tab_contents
            
            index = len(tab_buttons)
            
            # 创建标签按钮
            tab_btn = QPushButton(f"{item_type.__name__} #{index + 1}")
            tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_btn.clicked.connect(lambda checked, idx=index: select_tab(idx))
            tab_bar_layout.insertWidget(index, tab_btn)
            tab_buttons.append(tab_btn)
            
            # 创建内容 widget
            content_widget = self._create_tab_content_widget(
                name, index, item_data or item_type(), item_type, 
                lambda idx=index: delete_tab(idx)
            )
            content_stack.addWidget(content_widget)
            tab_contents.append(content_widget)
            
            if select:
                select_tab(index)
            
            return content_widget
        
        # 添加现有 items
        for item_data in current_value:
            add_tab(item_data, select=False)
        
        # 默认选择第一个标签
        if tab_buttons:
            select_tab(0)
        
        # 添加按钮
        add_button = QPushButton("+ 添加")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        def on_add():
            current_list = getattr(self, name, [])
            new_item = item_type()
            current_list.append(new_item)
            setattr(self, name, current_list)
            
            add_tab(new_item, select=True)
            
            # 触发 geometry 更新
            self._update_parent_geometry(container)
            
            # 保存设置
            self._save_settings()
        
        add_button.clicked.connect(on_add)
        tab_bar_layout.addWidget(add_button)
        tab_bar_layout.addStretch()
        
        layout.addWidget(tab_bar)
        layout.addWidget(content_stack)
        
        return container
    
    def _create_tab_content_widget(
        self,
        name: str,
        index: int,
        item_data: Any,
        item_type: Type,
        delete_callback: Callable
    ) -> QWidget:
        """Create a single tab content widget for editing a settings instance."""
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        
        # 创建边框效果
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        frame.setStyleSheet("QFrame { border: 1px solid #e0e0e0; border-radius: 4px; background-color: #fafafa; }")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建 header（包含删除按钮）
        header_layout = QHBoxLayout()
        title_label = QLabel(f"{item_type.__name__} #{index + 1}")
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        delete_button = QPushButton("删除")
        delete_button.setObjectName("delete_btn")
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff5252;
            }
        """)
        delete_button.clicked.connect(delete_callback)
        header_layout.addWidget(delete_button)
        
        frame_layout.addLayout(header_layout)
        
        # 创建表单
        try:
            if not isinstance(item_data, item_type):
                item_instance = item_type(**(item_data if isinstance(item_data, dict) else {}))
            else:
                item_instance = item_data
            
            # 创建一个同步桥梁，用于同步数据变更
            def on_item_changed(field_name: str, value: Any):
                """当表单字段变化时更新数据"""
                current_list = getattr(self, name, [])
                if 0 <= index < len(current_list):
                    item = current_list[index]
                    if hasattr(item, field_name):
                        setattr(item, field_name, value)
                        self._save_settings()
            
            # 获取表单的 widget，但不使用 create_form_widget（避免嵌套）
            item_form = item_instance.create_form_widget(container)
            item_form.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Minimum
            )
            
            # 遍历表单中的所有输入控件，连接它们的值变化信号
            # 这里我们依赖 item_instance 自身的保存机制
            # 但由于是列表中的元素，需要确保修改能同步回列表
            # 由于 BaseSettings 的 __setattr__ 会自动保存，我们只需要确保引用正确
            
            frame_layout.addWidget(item_form)
            
        except Exception as e:
            error_label = QTextEdit(f"Error loading settings: {str(e)}")
            error_label.setReadOnly(True)
            error_label.setMaximumHeight(50)
            frame_layout.addWidget(error_label)
        
        layout.addWidget(frame)
        return container
    
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
        
        # 触发 geometry 更新，确保外层 QScrollArea 能感知到大小变化
        self._update_parent_geometry(items_container)
        
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
            
            # 触发 geometry 更新，确保外层 QScrollArea 能感知到大小变化
            self._update_parent_geometry(items_container)
            
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
                # Create form from the nested settings (without scroll area)
                nested_form = nested_settings.create_form_widget(container)
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
            # 根据 display_mode 决定使用列表还是选项卡展示
            if widget_metadata.display_mode == "tabs":
                widget = self._create_settings_tabs_widget(name, current_value, item_type)
            else:
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
        """Create PySide6 UI with form layout and group boxes, wrapped in a scroll area."""
        main_widget = self.create_form_widget(parent)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(main_widget)
        return scroll_area
    
    def create_form_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create PySide6 UI with form layout and group boxes, returns the plain widget without scroll area."""
        main_widget = QWidget(parent)
        main_widget.setMinimumWidth(600)
        # 不设置最小高度，让 widget 完全根据内容决定大小
        main_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        # 关键：设置 sizeConstraint 让 widget 根据内容调整大小
        main_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        # 检查类是否设置了 _form_display_mode = "tabs"
        form_display_mode = getattr(self, '_form_display_mode', 'vertical')
        
        if form_display_mode == 'tabs':
            # 选项卡式布局：每个子属性一个标签页
            self._create_tabs_layout_for_all_fields(main_layout)
        else:
            # 传统的 group 布局
            self._create_groups_layout(main_layout)

        return main_widget
    
    def _create_tabs_layout_for_all_fields(self, main_layout: QVBoxLayout):
        """Create a tab-based layout where each field is a tab."""
        # 创建标签栏和内容区域
        tab_bar = QWidget()
        tab_bar_layout = QHBoxLayout(tab_bar)
        tab_bar_layout.setContentsMargins(0, 5, 0, 5)
        tab_bar_layout.setSpacing(5)
        
        content_stack = QStackedWidget()
        content_stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        tab_buttons = []
        
        def select_tab(index: int):
            """切换到指定标签页"""
            content_stack.setCurrentIndex(index)
            # 更新按钮样式
            for i, btn in enumerate(tab_buttons):
                if i == index:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2196F3;
                            color: white;
                            font-weight: bold;
                            padding: 10px 20px;
                            border: none;
                            border-radius: 4px 4px 0 0;
                            border-bottom: 3px solid #1976D2;
                        }
                        QPushButton:hover {
                            background-color: #1976D2;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #f0f0f0;
                            color: #333;
                            padding: 10px 20px;
                            border: none;
                            border-radius: 4px 4px 0 0;
                            border-bottom: 3px solid transparent;
                        }
                        QPushButton:hover {
                            background-color: #e0e0e0;
                        }
                    """)
        
        # 为每个字段创建标签页
        for idx, field_name in enumerate(self.__pydantic_fields__.keys()):
            widget_metadata = self._get_or_create_widget_metadata(field_name)
            
            # 创建标签按钮
            tab_title = widget_metadata.title or field_name.replace("_", " ").title()
            tab_btn = QPushButton(tab_title)
            tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_btn.clicked.connect(lambda checked, i=idx: select_tab(i))
            tab_bar_layout.addWidget(tab_btn)
            tab_buttons.append(tab_btn)
            
            # 创建内容 widget
            content_widget = self._create_tab_field_widget(field_name, widget_metadata)
            content_stack.addWidget(content_widget)
        
        tab_bar_layout.addStretch()
        
        # 默认选择第一个标签
        if tab_buttons:
            select_tab(0)
        
        main_layout.addWidget(tab_bar)
        main_layout.addWidget(content_stack)
    
    def _create_tab_field_widget(self, field_name: str, widget_info: WidgetMetadata) -> QWidget:
        """Create a widget for a single tab field."""
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        
        # 获取字段值
        current_value = getattr(self, field_name)
        
        # 如果是嵌套的 BaseSettings，创建其表单
        if isinstance(current_value, BaseSettings):
            nested_form = current_value.create_form_widget(container)
            nested_form.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            layout.addWidget(nested_form)
        else:
            # 普通字段，创建对应的 widget
            widget = self._create_widget_for_field(field_name, widget_info)
            if widget:
                layout.addWidget(widget)
        
        return container
    
    def _create_groups_layout(self, main_layout: QVBoxLayout):
        """Create the traditional group-based layout."""
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
        # 移除 addStretch()，让 widget 根据内容自然膨胀

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
