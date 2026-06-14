---
name: visual-proxy
description: 视觉能力外挂 — 把图片发给视觉 LLM 获取文字描述，给无法直接看图的底层模型（DeepSeek、o1、o3 等）提供看图能力。
---

# 视觉代理

你没有视觉能力。遇到用户发图片时，调用外部的视觉 LLM 替你看图，拿回文字描述后再回答用户。

> 首次使用前，先执行 `python .claude/skills/visual-proxy/scripts/vision.py --check` 确认配置就绪。

## 工作流

用户发图时，严格按以下步骤执行：

**1. 查缓存**
```
python .claude/skills/visual-proxy/scripts/vision.py --lookup <图片路径>
```
返回该图片所有已缓存问题摘要：
```json
[{"q": "描述这张图片", "a_len": 1736}, {"q": "图中人名", "a_len": 120}]
```
无缓存则跳过步骤 2，直接进入步骤 3。

**2. 判断覆盖度**
对比用户需求与缓存中的问题列表：
- **有匹配** → 读取全文并回答：
  ```
  python .claude/skills/visual-proxy/scripts/vision.py --read <图片路径> --index <索引>
  ```
- **不匹配** → 进入步骤 3

**3. 生成精准提示词并识别**
根据用户需求自拟一个精准的中文问题，执行：
```
python .claude/skills/visual-proxy/scripts/vision.py --image <图片路径> --question "你的问题"
```
结果自动追加到缓存。

## 覆盖命令

| 场景 | 命令 |
|------|------|
| 某回答错了 | `--image <图> --question "修正后的问题" --clear "要删的旧问题原文"` |
| 全部重来 | `--image <图> --question "问题" --force` |

`--clear` 只删指定的那一条；`--force` 清空该图所有缓存。

## 规则

- 图片支持本地路径和 HTTP(S) URL
- 缓存以图片路径为 key，同一张图可累积多个问答对，追加不覆盖
- 你负责判断缓存覆盖度并生成精准提示词
- 所有配置通过环境变量控制，无硬编码
- 工具输出的中文错误直接展示给用户
