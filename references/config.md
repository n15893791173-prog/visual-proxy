# Visual Proxy 配置

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `VISION_API_KEY` | ✓ | - | API 密钥 |
| `VISION_API_BASE` | ✗ | `https://api.openai.com/v1` | API 端点 |
| `VISION_MODEL` | ✗ | `gpt-4o` | 模型名称 |
| `VISION_MAX_TOKENS` | ✗ | `2000` | 最大输出 token 数 |
| `VISION_CACHE_MAX_ENTRIES` | ✗ | `100` | 缓存最多保留图片数 |
| `VISION_CACHE_TTL_DAYS` | ✗ | `30` | 缓存过期天数 |

脚本会自动检测端点类型：
- 端点含 `anthropic` → 使用 Anthropic Messages API 格式
- 其他 → 使用 OpenAI Chat Completions API 格式

## 配置示例

### OpenAI

```bash
export VISION_API_KEY="sk-xxxx"
export VISION_API_BASE="https://api.openai.com/v1"
export VISION_MODEL="gpt-4o"
```

### Anthropic

```bash
export VISION_API_KEY="sk-ant-xxxx"
export VISION_API_BASE="https://api.anthropic.com/v1"
export VISION_MODEL="claude-sonnet-4-6"
```

### 阿里云 DashScope（Qwen3-VL / 通义千问视觉）

```bash
export VISION_API_KEY="sk-xxxx"
export VISION_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export VISION_MODEL="qwen3-vl-plus"
```

### 其他兼容 OpenAI 格式的服务

```bash
export VISION_API_KEY="your-key"
export VISION_API_BASE="https://your-custom-endpoint.com/v1"
export VISION_MODEL="your-model"
```

## 缓存

缓存文件位于 `scripts/cache.json`，结构如下：
```json
{
  "abc123...": {
    "updated": 1718400000,
    "pairs": [
      {"q": "描述这张图片", "a": "这是一张..."},
      {"q": "图中人名有哪些", "a": "墨子、庄子..."}
    ]
  }
}
```

### 自动清理

每次写入缓存时自动触发：
- **过期清理：** 超过 `VISION_CACHE_TTL_DAYS`（默认 30 天）未使用的条目自动删除
- **数量清理：** 超过 `VISION_CACHE_MAX_ENTRIES`（默认 100 张）时，删除最旧的

### 手动清理

```bash
python vision.py --prune   # 立即执行过期/超量清理
python vision.py --list    # 查看所有缓存及最后更新时间
```

如需完全清除缓存，删除 `scripts/cache.json` 即可。
