# visual-proxy

[![GitHub stars](https://img.shields.io/github/stars/daiuuuuuuuuuuuuu/visual-proxy?style=flat-square)](https://github.com/daiuuuuuuuuuuuuu/visual-proxy/stargazers)
[![GitHub license](https://img.shields.io/github/license/daiuuuuuuuuuuuuu/visual-proxy?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://www.python.org/)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen?style=flat-square)](scripts/vision.py)
[![Claude Code Skill](https://img.shields.io/badge/claude--code-skill-orange?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)

给没有视觉能力的底层模型（DeepSeek、o1、o3 等）外挂看图能力。通过调用可配置的视觉 LLM 把图片转成文字描述。

A vision proxy that gives image-seeing capability to text-only LLMs (DeepSeek, o1, o3, etc.). It routes images to a configurable vision LLM and converts them into text descriptions, which the text-only model can then read and reason about. Supports OpenAI, Anthropic, DashScope, Qwen3-VL, and any OpenAI-compatible endpoint.

## 安装 | Installation

### 方式一：全局安装（推荐，所有项目可用）

```bash
git clone https://github.com/daiuuuuuuuuuuuuu/visual-proxy.git /tmp/visual-proxy
mkdir -p ~/.claude/skills/visual-proxy
cp -r /tmp/visual-proxy/* ~/.claude/skills/visual-proxy/
```

然后修改 `~/.claude/skills/visual-proxy/SKILL.md`，把所有 `.claude/skills/visual-proxy` 替换为 `~/.claude/skills/visual-proxy`。

### Method 1: Global install (recommended, works across all projects)

Clone the repo to a temp location, copy the files into the Claude skills directory, then update `SKILL.md` to point to the correct global path (`~/.claude/skills/visual-proxy`).

### 方式二：项目级安装（仅当前项目）

```bash
cd your-project
git clone https://github.com/daiuuuuuuuuuuuuu/visual-proxy.git /tmp/visual-proxy
mkdir -p .claude/skills/visual-proxy
cp -r /tmp/visual-proxy/* .claude/skills/visual-proxy/
```

项目级安装无需修改路径，直接可用。

### Method 2: Project-level install (current project only)

Copy the skill into your project's `.claude/skills/visual-proxy` directory. No path changes needed -- it works out of the box since Claude Code resolves `.claude/` relative to the project root.

## 配置 | Configuration

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

Set three environment variables (recommended: write them to `.claude/settings.local.json`). The example above uses the DashScope (Qwen3-VL) provider. For OpenAI Vision, Anthropic Claude Vision, or other OpenAI-compatible endpoints, see the config reference below.

Choose a provider and model:

- **DashScope (Alibaba Cloud):** `VISION_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1`, `VISION_MODEL=qwen3-vl-plus`
- **OpenAI:** `VISION_API_BASE=https://api.openai.com/v1`, `VISION_MODEL=gpt-4o`
- **Anthropic:** `VISION_API_BASE=https://api.anthropic.com/v1`, `VISION_MODEL=claude-3-5-sonnet-20241022`
- **Custom:** Any OpenAI-compatible endpoint -- just set `VISION_API_BASE` and `VISION_MODEL` accordingly.

更多配置示例见 [references/config.md](references/config.md)。

For more configuration examples and provider details, see [references/config.md](references/config.md).

## 使用 | Usage

### 工作原理 | How It Works

```
┌──────────────────────────────────────────┐
│              用户发来一张图片               │
│        "帮我看看这页有哪些哲学家"            │
│     User sends an image:                  │
│     "What philosophers are on this page?" │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│  第一步：查缓存  Step 1: Check Cache       │
│  vision.py --lookup <image_path>          │
│                                           │
│  返回已缓存的问题摘要（不含回答全文）：        │
│  Returns cached question summaries        │
│  (without full answers):                  │
│  [                                        │
│    {"q": "描述这张图片", "a_len": 2345},    │
│    {"q": "图中人名",     "a_len": 120}     │
│  ]                                        │
│                                           │
│  无缓存 → 直接跳到第三步                    │
│  No cache → skip directly to Step 3        │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│  第二步：大模型判断覆盖度                    │
│  Step 2: LLM judges cache coverage        │
│                                           │
│  用户问"有哪些哲学家"                       │
│  缓存里有"图中人名" → 命中！                 │
│                                           │
│  User asks "what philosophers"            │
│  Cache has "people in image" → hit!       │
│                                           │
│  → vision.py --read <image> --index 1     │
│  → 读取该条回答全文                         │
│  → Read full cached answer                │
│  → 直接用它回答用户，不调 API ✓              │
│  → Answer user directly, no API call ✓    │
│                                           │
│  如果用户问"版式字体特征"                    │
│  缓存里两条都不覆盖 → 进入第三步              │
│  If user asks "typography features"       │
│  neither cache entry covers it → step 3   │
└────────────────┬─────────────────────────┘
                 ▼
┌──────────────────────────────────────────┐
│  第三步：生成精准 prompt，调视觉 API         │
│  Step 3: Generate precise prompt, call    │
│           vision API                      │
│                                           │
│  大模型根据用户需求自拟精准中文问题：          │
│  LLM crafts a precise question based on   │
│  the user's request:                      │
│  "描述这页的版式特征，包括字体字号、           │
│   行距、墨色浓淡、纸张状态"                  │
│                                           │
│  vision.py --image <img> --question "..."  │
│                                           │
│  结果自动追加到缓存，下次直接命中              │
│  Result auto-appended to cache; next time  │
│  it's a direct hit                        │
└──────────────────────────────────────────┘
```

The caching system works in three phases:

1. **Cache lookup** (`--lookup`): When the user asks about an image, the script first checks the cache file (keyed by SHA-256 hash of the image path). It returns only question summaries (`{q, a_len}`), avoiding flooding the LLM context window with full answer text.

2. **Coverage judgment**: The text-only LLM decides whether any existing cached question-answer pair covers the user's current query. If yes, the relevant answer is retrieved via `--read --index <N>` and used directly -- no API call needed, saving both time and cost.

3. **New vision query**: If no cache entry covers the request, the LLM crafts a precise question for the vision model, calls `vision.py --image --question "..."`, and the response is appended to the cache. This is an append-only strategy: new QA pairs are added without overwriting old ones, so knowledge accumulates over time.

### 命令速查 | Command Reference

| 命令 | 作用 |
|------|------|
| `--check` | 验证环境变量配置是否就绪 / Check environment config |
| `--lookup <图>` | 列出该图片所有已缓存问题摘要（不含全文） / List cached question summaries |
| `--read <图> --index <N>` | 读取第 N 条缓存的回答全文 / Read full answer for entry N |
| `--list` | 列出所有已缓存图片及问答数量 / List all cached images and QA counts |
| `--image <图> --question "问题"` | 识图并追加到缓存 / Analyze image and append to cache |
| `--image <图> --question "问题" --clear "旧问题"` | 删掉某条答错的缓存，重新识别 / Delete a wrong cache entry and re-analyze |
| `--image <图> --question "问题" --force` | 清空该图全部缓存，重新识别 / Clear all cache for this image and re-analyze |

### 缓存策略 | Cache Strategy

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

Multiple QA pairs accumulate per image (append-only, no overwrite). Each pair is independently managed, keyed by SHA-256 of the image path.

- `--lookup` 只返回 `{q, a_len}` 摘要，避免大段文字冲爆 context
  - `--lookup` returns only `{q, a_len}` summaries to avoid flooding the context window
- `--read <索引>` 按需取全文
  - `--read <index>` fetches full text on demand
- `--clear "旧问题"` 精确删除单条，不影响其他缓存
  - `--clear "old question"` deletes a single entry without affecting other cache entries
- `--force` 清空所有缓存，真正从头开始
  - `--force` clears all cache for the image, starting fresh

### 示例对话 | Example Conversation

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

**English summary:** The user sends an image. Claude (without vision) checks the cache, finds nothing, and calls the vision proxy with a precise question. The answer is cached. On follow-up questions, Claude re-checks the cache. If a cached QA pair is precise enough, it reads the full answer directly with no API call. If not, it makes another vision query and the new QA pair is appended to the cache. Wrong entries can be cleared individually without affecting valid ones.

## 架构 | Architecture

```
visual-proxy/
├── SKILL.md                 # 技能定义 / Skill definition
├── README.md                # 本文件 / This file
├── LICENSE
├── scripts/
│   └── vision.py            # 视觉代理脚本（纯标准库，无第三方依赖）
│                              Vision proxy script (stdlib only, zero deps)
└── references/
    └── config.md            # 环境变量说明和配置示例
                               Environment variable docs and config examples
```

## 许可 | License

MIT
