# visual-proxy

给没有视觉能力的底层模型（DeepSeek、o1、o3 等）外挂看图能力。通过调用可配置的视觉 LLM 把图片转成文字描述。

## 安装

```bash
git clone https://github.com/<your-repo>/visual-proxy.git
cp -r visual-proxy/.claude/skills/visual-proxy ~/your-project/.claude/skills/

# 或者直接在项目里
cd your-project
mkdir -p .claude/skills
cp -r <path-to>/visual-proxy .claude/skills/
```

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

在 Claude Code 中，skill 激活后遇到图片会自动走以下流程：

```
用户发图 → 查缓存 → 大模型判断缓存覆盖度
                      ├─ 覆盖 → 直接用，不调 API
                      └─ 不覆盖 → 大模型生成精准问题 → 调视觉 LLM → 追加到缓存
```

核心设计：文本模型做"调度者"（判断匹配度 + 生成精准 prompt），视觉模型做"感知者"（看图回答），同一张图可累积多个不同角度的问答对。

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
