# 配置面板使用指南

## 启动配置面板

运行以下命令启动配置面板：

```bash
python single_component_tests/start_config_panel.py
```

## 界面布局

```
┌─────────────────────────────────────┐
│  💾 保存配置                        │ ← 手动保存按钮（顶部）
├─────────────────────────────────────┤
│  General                            │
│  ┌───────────────────────────────┐  │
│  │ LLM Config                    │  │
│  │ ┌───────────────────────────┐ │  │
│  │ │ Provider: [________]      │ │  │
│  │ │ Model: [________]         │ │  │
│  │ │ Max Context Messages: [10]│ │  │
│  │ │ Customization Name: [...] │ │  │
│  │ │ Provider List:            │ │  │
│  │ │ [+ 添加]                  │ │  │
│  │ │ ┌─────────────────────┐   │ │  │
│  │ │ │ openai #1    [删除] │   │ │  │
│  │ │ │ Name: [openai]      │   │ │  │
│  │ │ │ API Key: [***]      │   │ │  │
│  │ │ │ API URL: [https://] │   │ │  │
│  │ │ └─────────────────────┘   │ │  │
│  │ └───────────────────────────┘ │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 功能说明

### 1. 手动保存配置

- 点击顶部的 **"💾 保存配置"** 按钮
- 所有修改会立即保存到 `config.json` 文件
- 保存时按钮会变色提示

### 2. 自动保存

- 修改任何字段时会自动保存
- 无需手动点击保存按钮

### 3. 管理 Provider 列表

#### 添加 Provider
1. 找到 "Provider List" 部分
2. 点击 **"+ 添加"** 按钮
3. 填写新 Provider 的信息：
   - Name: 提供商名称
   - API Key: API 密钥
   - API URL: API 地址

#### 删除 Provider
1. 找到要删除的 Provider 卡片
2. 点击卡片右上角的 **"删除"** 按钮（红色）
3. 该 Provider 会立即被移除

### 4. 嵌套设置

- "LLM Config" 是一个嵌套的设置对象
- 点击后会展开显示所有子字段
- 可以独立编辑每个子字段

## 配置文件格式

配置文件 (`config.json`) 的格式如下：

```json
{
  "general": {
    "llm_config": {
      "provider": "",
      "model": "",
      "max_context_messages": 10,
      "customization_name": "default",
      "provider_list": [
        {
          "name": "openai",
          "api_key": "sk-xxx",
          "api_url": "https://api.openai.com/v1"
        },
        {
          "name": "zhipu",
          "api_key": "xxx",
          "api_url": "https://open.bigmodel.cn/api/paas/v4"
        }
      ]
    }
  }
}
```

## 快捷键

- 修改任何字段后按 `Enter` 键可以触发保存
- 使用 `Tab` 键在字段间切换

## 注意事项

1. **API Key 安全**：请妥善保管 API 密钥，不要提交到版本控制系统
2. **数据备份**：建议定期备份 `config.json` 文件
3. **格式验证**：所有字段都有类型验证，输入无效值会被拒绝

## 常见问题

### Q: 修改后忘记保存怎么办？
A: 不用担心，修改会自动保存。如果不确定，可以点击顶部的"保存配置"按钮手动保存。

### Q: 如何重置某个字段？
A: 直接删除字段内容或输入默认值即可。

### Q: 可以添加多少个 Provider？
A: 没有数量限制，可以根据需要添加任意多个 Provider。

## 技术细节

- 使用 PySide6 构建 UI
- 基于 Pydantic 进行数据验证
- 支持嵌套的 BaseSettings 对象
- 支持 List[BaseSettings] 动态列表
- 所有更改实时同步到配置文件
