#!/usr/bin/env python3
"""Vision Agent — 把图片发给视觉 LLM，拿回文字描述。

纯标准库实现，不依赖第三方包。
支持本地路径和 HTTP(S) URL。
缓存结构：{image_hash: [{q: ..., a: ...}]}，同一张图可缓存多个问答对。
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

# 强制 stdout/stderr 使用 utf-8，避免 Windows GBK 终端崩溃
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_FILE = SCRIPT_DIR / "cache.json"


# ── 环境变量 ──────────────────────────────────────────────

def get_config():
    key = os.environ.get("VISION_API_KEY", "")
    base = os.environ.get("VISION_API_BASE", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("VISION_MODEL", "gpt-4o")
    max_tokens = int(os.environ.get("VISION_MAX_TOKENS", "2000"))
    return {"api_key": key, "api_base": base, "model": model, "max_tokens": max_tokens}


# ── 缓存层 ────────────────────────────────────────────────

def _cache_key(image: str) -> str:
    return hashlib.sha256(image.encode("utf-8")).hexdigest()

def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def lookup_qa_pairs(image: str) -> List[dict]:
    """返回该图片的所有已缓存问答对 [{q, a}, ...]。"""
    return load_cache().get(_cache_key(image), [])

def append_qa(image: str, question: str, answer: str):
    cache = load_cache()
    key = _cache_key(image)
    if key not in cache:
        cache[key] = []
    cache[key].append({"q": question, "a": answer})
    save_cache(cache)

def clear_image_cache(image: str):
    cache = load_cache()
    cache.pop(_cache_key(image), None)
    save_cache(cache)

def remove_qa(image: str, question: str):
    """删除该图片缓存中匹配指定问题的单个问答对。"""
    cache = load_cache()
    key = _cache_key(image)
    if key in cache:
        cache[key] = [p for p in cache[key] if p["q"] != question]
        if not cache[key]:
            del cache[key]
        save_cache(cache)


# ── 图片处理 ──────────────────────────────────────────────

def _mime_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    mapping = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    }
    return mapping.get(suffix, "image/png")

def _read_local_b64(path: str) -> Tuple[str, str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(p, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("ascii"), _mime_type(path)

def _fetch_url_b64(url: str) -> Tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "vision-agent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    mime = resp.headers.get("Content-Type", "image/png")
    return base64.standard_b64encode(data).decode("ascii"), mime


# ── API 调用 ──────────────────────────────────────────────

def call_api(image: str, question: str, config: dict) -> str:
    api_key = config["api_key"]
    api_base = config["api_base"]
    model = config["model"]

    if image.startswith(("http://", "https://")):
        b64, mime = _fetch_url_b64(image)
    else:
        b64, mime = _read_local_b64(image)

    max_tokens = config["max_tokens"]
    if "anthropic" in api_base.lower():
        return _call_anthropic(api_base, api_key, model, b64, mime, question, max_tokens)
    else:
        return _call_openai(api_base, api_key, model, b64, mime, question, max_tokens)


def _call_openai(base: str, key: str, model: str, b64: str, mime: str, question: str, max_tokens: int) -> str:
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
    }
    url = f"{base}/chat/completions"
    result = _http_post(url, key, payload)
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"无法解析 OpenAI 响应: {json.dumps(result, ensure_ascii=False)}")


def _call_anthropic(base: str, key: str, model: str, b64: str, mime: str, question: str, max_tokens: int) -> str:
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
            ],
        }],
    }
    url = f"{base}/messages"
    extra_headers = {"anthropic-version": "2023-06-01"}
    result = _http_post(url, key, payload, extra_headers)
    try:
        return result["content"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"无法解析 Anthropic 响应: {json.dumps(result, ensure_ascii=False)}")


def _http_post(url: str, key: str, payload: dict, extra_headers: dict = None,
               max_retries: int = 3) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    if extra_headers:
        headers.update(extra_headers)
    body = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 503) and attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
                last_error = e
                continue
            raise RuntimeError(f"API 请求失败 (HTTP {e.code}): {err_body}")
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                last_error = e
                continue
            raise RuntimeError(f"网络错误: {e.reason}")
    raise RuntimeError(f"重试 {max_retries} 次后仍失败: {last_error}")


# ── CLI ────────────────────────────────────────────────────

def cmd_check():
    config = get_config()
    if not config["api_key"]:
        print("错误: 未配置 VISION_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)
    print("[OK] 配置正常")
    print(f"  API Base:   {config['api_base']}")
    print(f"  Model:      {config['model']}")
    print(f"  Max Tokens: {config['max_tokens']}")

def cmd_lookup(image: str):
    """输出该图片所有已缓存问题（不含回答全文）。"""
    pairs = lookup_qa_pairs(image)
    if pairs:
        summary = [{"q": p["q"], "a_len": len(p["a"])} for p in pairs]
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        sys.exit(1)

def cmd_read(image: str, index: int):
    """读取指定索引的缓存回答全文。——read 直接接图片路径，不需要 --lookup。"""
    pairs = lookup_qa_pairs(image)
    if not pairs:
        print("错误: 该图片无缓存", file=sys.stderr)
        sys.exit(1)
    if 0 <= index < len(pairs):
        print(pairs[index]["a"])
    else:
        print(f"错误: 索引 {index} 超出范围（共 {len(pairs)} 条）", file=sys.stderr)
        sys.exit(1)

def cmd_list():
    """列出所有已缓存图片及问答数量。"""
    cache = load_cache()
    if not cache:
        print("(空)")
        return
    for key_hash, pairs in cache.items():
        questions = [p["q"][:50] for p in pairs]
        print(f"{key_hash[:12]}  {len(pairs)} 条  {questions}")

def cmd_image(image: str, question: str, force: bool = False, clear: str = None):
    """识别图片并缓存。"""
    if force:
        clear_image_cache(image)
    elif clear:
        remove_qa(image, clear)

    config = get_config()
    if not config["api_key"]:
        print("错误: 未配置 VISION_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    try:
        result = call_api(image, question, config)
        append_qa(image, question, result)
        print(result)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Vision Agent")
    parser.add_argument("--image", help="图片路径或 URL")
    parser.add_argument("--question", default="请详细描述这张图片的内容。", help="对图片的提问")
    parser.add_argument("--lookup", help="列出该图片所有已缓存问题（不含回答全文）")
    parser.add_argument("--read", metavar="图片路径", help="--read <图片路径> --index <N>  读取第 N 条缓存回答全文")
    parser.add_argument("--index", type=int, default=0, help="配合 --read 指定读取第几条")
    parser.add_argument("--list", action="store_true", help="列出所有已缓存图片")
    parser.add_argument("--force", action="store_true", help="清除该图片所有旧缓存，重新识别")
    parser.add_argument("--clear", default=None, help="只删除匹配此问题的旧缓存，然后重新识别")
    parser.add_argument("--check", action="store_true", help="验证配置是否就绪")
    args = parser.parse_args()

    if args.check:
        cmd_check()
    elif args.list:
        cmd_list()
    elif args.read:
        cmd_read(args.read, args.index)
    elif args.lookup:
        cmd_lookup(args.lookup)
    elif args.image:
        cmd_image(args.image, args.question, force=args.force, clear=args.clear)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
