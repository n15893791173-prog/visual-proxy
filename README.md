# visual-proxy

[![GitHub stars](https://img.shields.io/github/stars/n15893791173-prog/visual-proxy?style=flat-square)](https://github.com/n15893791173-prog/visual-proxy/stargazers)
[![GitHub license](https://img.shields.io/github/license/n15893791173-prog/visual-proxy?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://www.python.org/)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen?style=flat-square)](scripts/vision.py)
[![Claude Code Skill](https://img.shields.io/badge/claude--code-skill-orange?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)

给没有视觉能力的底层模型（DeepSeek、o1、o3 等）外挂看图能力。通过调用可配置的视觉 LLM 把图片转成文字描述。

> Vision proxy for text-only LLMs — supports OpenAI / Anthropic / DashScope / Qwen3-VL and any OpenAI-compatible endpoint.

## 安装

### 方式一：全局安装（推荐，所有项目可用）

```bash
git clone https://github.com/n15893791173-prog/visual-proxy.git /tmp/visual-proxy
mkdir -p ~/.claude/skills/visual-proxy
cp -r /tmp/visual-proxy/* ~/.claude/skills/visual-proxy/
```

然后修改 `~/.claude/skills/visual-proxy/SKILL.md`，把所有 `.claude/skills/visual-proxy` 替换为 `~/.claude/skills/visual-proxy`。

### 方式二：项目级安装（仅当前项目）

```bash
cd your-project
git clone https://github.com/n15893791173-prog/visual-proxy.git /tmp/visual-proxy
mkdir -p .claude/skills/visual-proxy
cp -r /tmp/visual-proxy/* .claude/skills/visual-proxy/
```

项目级安装无需修改路径，直接可用。

## 配置

设置三个环境变量（推荐写入 `.claude/settings.local.json`）：

```json
{
  "env": {
    "VISION_API_KEY": "sk-xxxx",
    "VISION_API_BASE": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "VISION_MODEL": "qwen3-vl-plus"
  }
}
```

更多配置示例见 [references/config.md](references/config.md)。

## 使用

### 工作原理

```
┌──────────────────────────────────────────┐
│              用户发来一张图片               │
│        "帮我看看这页有哪些哲学家"            │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│  第一步：查缓存                            │
│  vision.py --lookup <图片路径>             │
│                                           │
│  返回已缓存的问题摘要（不含回答全文）：        │
│  [                                        │
│    {"q": "描述这张图片", "a_len": 2345},    │
│    {"q": "图中人名",     "a_len": 120}     │
│  ]                                        │
│                                           │
│  无缓存 → 直接跳到第三步                     │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│  第二步：大模型判断覆盖度                     │
│                                           │
│  用户问"有哪些哲学家"                       │
│  缓存里有"图中人名" → 命中！                 │
│                                           │
│  → vision.py --read <图> --index 1        │
│  → 读取该条回答全文                         │
│  → 直接用它回答用户，不调 API ✓              │
│                                           │
│  如果用户问"版式字体特征"                    │
│  缓存里两条都不覆盖 → 进入第三步              │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│  第三步：生成精准 prompt，调视觉 API         │
│                                           │
│  大模型根据用户需求自拟精准中文问题：          │
│  "描述这页的版式特征，包括字体字号、           │
│   行距、墨色浓淡、纸张状态"                  │
│                                           │
│  vision.py --image <图> --question "..."   │
│                                           │
│  结果自动追加到缓存，下次直接命中              │
└──────────────────────────────────────────┘
```

### 命令速查

| 命令 | 作用 |
|------|------|
| `--check` | 验证环境变量配置是否就绪 |
| `--lookup <图>` | 列出该图片所有已缓存问题摘要（不含全文） |
| `--read <图> --index <N>` | 读取第 N 条缓存的回答全文 |
| `--list` | 列出所有已缓存图片及问答数量 |
| `--image <图> --question "问题"` | 识图并追加到缓存 |
| `--image <图> --question "问题" --clear "旧问题"` | 删掉某条答错的缓存，重新识别 |
| `--image <图> --question "问题" --force` | 清空该图全部缓存，重新识别 |

### 缓存策略

同一张图片可累积多个问答对，追加不覆盖。结构中每个问答对独立管理：

```json
{
  "<图片路径SHA256>": {
    "updated": 1718400000,
    "pairs": [
      {"q": "描述这张图片", "a": "这是一张..."},
      {"q": "图中人名",     "a": "墨子、庄子..."}
    ]
  }
}
```

- `--lookup` 只返回 `{q, a_len}` 摘要，避免大段文字冲爆 context
- `--read <索引>` 按需取全文
- `--clear "旧问题"` 精确删除单条，不影响其他缓存
- `--force` 清空所有缓存，真正从头开始

### 示例对话

```
用户：帮我看看 screenshot.png 上写了什么

Claude（无视觉）：
  → vision.py --lookup screenshot.png
  → 空缓存
  → vision.py --image screenshot.png --question "描述图片的完整文字内容"
  → 返回："这是一张错误日志截图，显示 NullPointerException at line 42..."
  → "图片上是一段 Java 错误日志，NullPointerException，第 42 行..."

用户：错误是哪个类抛出的？

Claude（无视觉）：
  → vision.py --lookup screenshot.png
  → [{"q": "描述图片的完整文字内容", "a_len": 350}]
  → 缓存不够精准（通用描述里可能没提取到具体类名）
  → vision.py --image screenshot.png --question "列出图中所有 Java 类名和包名"
  → 缓存现在有 2 条问答对

用户：类名不对，重新看看

Claude（无视觉）：
  → vision.py --image screenshot.png
      --question "精确列出错误日志中的所有 Java 完整限定类名"
      --clear "列出图中所有 Java 类名和包名"
  → 只删这条，通用描述那保留
```

## 架构

```
visual-proxy/
├── SKILL.md                 # 技能定义
├── README.md                # 本文件
├── LICENSE
├── scripts/
│   └── vision.py            # 视觉代理脚本（纯标准库，无第三方依赖）
└── references/
    └── config.md            # 环境变量说明和配置示例
```

## 许可

MIT
