# HTTP Server Plugin

Flask HTTP 服务器插件，为其他插件提供统一的 HTTP 服务基础设施。

## 功能特性

- ✅ 基于 Flask 的 HTTP 服务器
- ✅ 插件加载时**自动启动**（在独立线程中）
- ✅ 支持动态端口分配
- ✅ 支持注册 Blueprint（路由组）
- ✅ 支持注册单个路由函数
- ✅ 线程安全的服务器运行
- ✅ CORS 跨域支持

## 自动启动

插件加载时会**自动启动 HTTP 服务器**，无需手动调用 `start()`。

```python
# 加载插件时，服务器自动在后台线程中启动
load_plugin(plugin_manager)
# 输出: [HTTPServer] 服务器已启动: http://127.0.0.1:xxxxx
```

## API 接口

### start

手动启动 HTTP 服务器（通常不需要，插件加载时会自动启动）。

```python
result = plugin_manager.get_method("http_server.start")(
    host="127.0.0.1",  # 可选，默认 127.0.0.1
    port=8080          # 可选，默认 0（自动分配）
)

if result["success"]:
    print(f"服务器启动成功: {result['url']}")
else:
    print(f"启动失败: {result['error']}")
```

### stop

停止 HTTP 服务器。

```python
result = plugin_manager.get_method("http_server.stop")()
print(result["message"])
```

### is_running

检查服务器是否正在运行。

```python
running = plugin_manager.get_method("http_server.is_running")()
print(f"运行中: {running}")
```

### get_url

获取服务器访问 URL。

```python
url = plugin_manager.get_method("http_server.get_url")()
if url:
    print(f"访问地址: {url}")
```

### register_blueprint

注册 Flask Blueprint（路由组）。

```python
from flask import Blueprint

# 创建 Blueprint
my_blueprint = Blueprint('my_plugin', __name__)

@my_blueprint.route('/hello')
def hello():
    return {'message': 'Hello World'}

# 注册 Blueprint
result = plugin_manager.get_method("http_server.register_blueprint")(
    blueprint=my_blueprint,
    url_prefix='/api/my-plugin'  # 可选
)

if result["success"]:
    print("Blueprint 注册成功")
    # 现在可以通过 http://127.0.0.1:xxxx/api/my-plugin/hello 访问
```

### register_route

注册单个路由函数。

```python
def my_handler():
    return {'data': 'response'}

result = plugin_manager.get_method("http_server.register_route")(
    route='/my-endpoint',
    view_func=my_handler,
    methods=['GET', 'POST']  # 可选，默认 ['GET']
)

if result["success"]:
    print("路由注册成功")
    # 现在可以通过 http://127.0.0.1:xxxx/my-endpoint 访问
```

### get_app

获取 Flask 应用实例（高级用法）。

```python
app = plugin_manager.get_method("http_server.get_app")()
if app:
    # 可以直接操作 Flask 应用
    app.config['MY_SETTING'] = 'value'
```

## 使用示例

### 作为依赖使用

其他插件可以在 `plugin.json` 中声明依赖：

```json
{
  "dependencies": [
    {
      "name": "plugin:http_server",
      "version": ">=1.0.0",
      "required": true
    }
  ]
}
```

然后在插件加载时注册路由：

```python
def load_plugin(plugin_manager):
    # 确保服务器已启动（如果未自动启动）
    if not plugin_manager.get_method("http_server.is_running")():
        plugin_manager.get_method("http_server.start")()
    
    # 注册 Blueprint
    from flask import Blueprint
    bp = Blueprint('my_plugin', __name__)
    
    @bp.route('/data')
    def get_data():
        return {'data': [1, 2, 3]}
    
    register_bp = plugin_manager.get_method("http_server.register_blueprint")
    register_bp(blueprint=bp, url_prefix='/api/my-plugin')
    
    return {"namespace": "my_plugin"}
```

## 注意事项

1. **自动启动**：插件加载时服务器会自动启动，无需手动调用 `start()`
2. **后台线程**：服务器在独立的后台线程中运行，不会阻塞主程序
3. **端口分配**：默认自动分配可用端口，可通过 `get_url()` 获取实际地址
4. **建议每个插件使用自己的 URL 前缀**来避免路由冲突
