#!/usr/bin/env python3
"""
core/llm_gateway.py: 统一 LLM Provider 抽象层 (Agent v5.0)

支持主流 LLM：
  - gemini   : Google Gemini 2.0/2.5 Pro (google-genai SDK)
  - openai   : GPT-4o / GPT-4.1 (openai SDK)
  - claude   : Claude Sonnet/Opus (anthropic SDK)
  - ollama   : 本地 Ollama (HTTP, 无需 API Key)
  - deepseek : DeepSeek-V3 (OpenAI 兼容协议)

API Key 读取优先级:
  1. 函数参数 api_key
  2. 环境变量 / .env 文件
  3. 未设置时降级到模板模式并给出提示

零硬编码 Key，全部通过环境变量注入。
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

# ─── 自动加载 .env 文件 ────────────────────────────────────────────────────────
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

def _load_dotenv():
    if not _ENV_FILE.exists():
        return
    with open(_ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

_load_dotenv()

# ─── Provider 枚举 ─────────────────────────────────────────────────────────────
class LLMProvider(str, Enum):
    GEMINI    = "gemini"
    OPENAI    = "openai"
    CLAUDE    = "claude"
    OLLAMA    = "ollama"
    DEEPSEEK  = "deepseek"

# ─── 默认模型映射 ──────────────────────────────────────────────────────────────
DEFAULT_MODELS: Dict[LLMProvider, str] = {
    LLMProvider.GEMINI:   "gemini-2.0-flash",
    LLMProvider.OPENAI:   "gpt-4o-mini",
    LLMProvider.CLAUDE:   "claude-sonnet-4-5",
    LLMProvider.OLLAMA:   "llama3.2",
    LLMProvider.DEEPSEEK: "deepseek-chat",
}

# ─── API Key 环境变量映射 ──────────────────────────────────────────────────────
API_KEY_ENV: Dict[LLMProvider, str] = {
    LLMProvider.GEMINI:   "GEMINI_API_KEY",
    LLMProvider.OPENAI:   "OPENAI_API_KEY",
    LLMProvider.CLAUDE:   "ANTHROPIC_API_KEY",
    LLMProvider.OLLAMA:   "",   # 不需要 Key
    LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
}

# ─── 降级顺序 ──────────────────────────────────────────────────────────────────
FALLBACK_ORDER: List[LLMProvider] = [
    LLMProvider.GEMINI,
    LLMProvider.DEEPSEEK,
    LLMProvider.OPENAI,
    LLMProvider.CLAUDE,
    LLMProvider.OLLAMA,
]


class LLMResponse:
    """统一响应格式"""
    def __init__(self, text: str, provider: str, model: str,
                 input_tokens: int = 0, output_tokens: int = 0,
                 success: bool = True, error: str = ""):
        self.text = text
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.success = success
        self.error = error

    def __repr__(self):
        status = "✅" if self.success else "❌"
        return (f"LLMResponse({status} {self.provider}/{self.model} "
                f"in={self.input_tokens} out={self.output_tokens})")


class LLMGateway:
    """
    统一 LLM 调用网关

    用法：
        gw = LLMGateway(provider="gemini")
        resp = gw.call("帮我写一个贪吃蛇游戏的 HTML5 代码")
        print(resp.text)

    或者一次性调用：
        resp = LLMGateway.quick_call("你好", provider="deepseek")
    """

    def __init__(
        self,
        provider: str = "gemini",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        timeout: int = 60,
        auto_fallback: bool = True,
        verbose: bool = False,
    ):
        env_timeout = os.environ.get("LLM_TIMEOUT")
        if env_timeout and timeout == 60:
            try: timeout = int(env_timeout)
            except ValueError: pass

        env_max_tokens = os.environ.get("LLM_MAX_TOKENS")
        if env_max_tokens and max_tokens == 8192:
            try: max_tokens = int(env_max_tokens)
            except ValueError: pass

        env_fallback = os.environ.get("LLM_AUTO_FALLBACK")
        if env_fallback and auto_fallback is True:
            auto_fallback = env_fallback.lower() in ("true", "1", "yes")

        self.provider = LLMProvider(provider.lower())
        self.model = model or DEFAULT_MODELS[self.provider]
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.auto_fallback = auto_fallback
        self.verbose = verbose

        # 获取 API Key
        env_key = API_KEY_ENV.get(self.provider, "")
        self.api_key = api_key or (os.environ.get(env_key, "") if env_key else "")

    # ─── 统一调用入口 ──────────────────────────────────────────────────────────
    def call(
        self,
        prompt: str,
        system: str = "",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """调用 LLM，自动重试并按 FALLBACK_ORDER 降级"""
        max_tok = max_tokens or self.max_tokens
        temp = temperature if temperature is not None else self.temperature

        providers_to_try = [self.provider]
        if self.auto_fallback:
            for p in FALLBACK_ORDER:
                if p != self.provider:
                    env_k = API_KEY_ENV.get(p, "")
                    if p == LLMProvider.OLLAMA or os.environ.get(env_k, ""):
                        providers_to_try.append(p)

        last_error = ""
        for prov in providers_to_try:
            if self.verbose:
                print(f"[LLMGateway] 尝试 {prov.value}/{DEFAULT_MODELS[prov]} ...", flush=True)
            try:
                resp = self._dispatch(prov, prompt, system, max_tok, temp)
                if resp.success:
                    return resp
                last_error = resp.error
            except Exception as e:
                last_error = str(e)
                if self.verbose:
                    print(f"[LLMGateway] {prov.value} 失败: {e}", flush=True)

        return LLMResponse(
            text="", provider=str(self.provider), model=self.model,
            success=False, error=f"所有 Provider 均失败: {last_error}"
        )

    # ─── 快捷静态方法 ──────────────────────────────────────────────────────────
    @staticmethod
    def quick_call(prompt: str, provider: str = "gemini", **kwargs) -> LLMResponse:
        gw = LLMGateway(provider=provider, **kwargs)
        return gw.call(prompt)

    # ─── Provider 分发 ─────────────────────────────────────────────────────────
    def _dispatch(self, provider: LLMProvider, prompt: str, system: str,
                  max_tokens: int, temperature: float) -> LLMResponse:
        if provider == LLMProvider.GEMINI:
            return self._call_gemini(prompt, system, max_tokens, temperature)
        elif provider == LLMProvider.OPENAI:
            return self._call_openai_compat(
                prompt, system, max_tokens, temperature,
                base_url="https://api.openai.com/v1",
                api_key=os.environ.get("OPENAI_API_KEY", self.api_key),
                model=DEFAULT_MODELS[provider],
                provider_name="openai"
            )
        elif provider == LLMProvider.CLAUDE:
            return self._call_claude(prompt, system, max_tokens, temperature)
        elif provider == LLMProvider.OLLAMA:
            return self._call_ollama(prompt, system, max_tokens, temperature)
        elif provider == LLMProvider.DEEPSEEK:
            return self._call_openai_compat(
                prompt, system, max_tokens, temperature,
                base_url="https://api.deepseek.com/v1",
                api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
                model=DEFAULT_MODELS[provider],
                provider_name="deepseek"
            )
        else:
            return LLMResponse(text="", provider=str(provider), model="",
                               success=False, error=f"未知 Provider: {provider}")

    # ─── Gemini ────────────────────────────────────────────────────────────────
    def _call_gemini(self, prompt: str, system: str, max_tokens: int,
                     temperature: float) -> LLMResponse:
        api_key = os.environ.get("GEMINI_API_KEY", self.api_key)
        if not api_key:
            return LLMResponse("", "gemini", self.model, success=False,
                               error="GEMINI_API_KEY 未设置")
        model = self.model if self.provider == LLMProvider.GEMINI else DEFAULT_MODELS[LLMProvider.GEMINI]

        # 尝试 google-genai SDK
        try:
            import google.genai as genai  # type: ignore
            client = genai.Client(api_key=api_key)
            contents = prompt
            cfg = {"max_output_tokens": max_tokens, "temperature": temperature}
            if system:
                cfg["system_instruction"] = system
            from google.genai import types  # type: ignore
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(**cfg)
            )
            text = resp.text or ""
            return LLMResponse(text, "gemini", model, success=True)
        except ImportError:
            pass  # SDK 未安装，降级到 REST
        except Exception as e:
            return LLMResponse("", "gemini", model, success=False, error=str(e))

        # REST fallback
        return self._call_gemini_rest(prompt, system, max_tokens, temperature, api_key, model)

    def _call_gemini_rest(self, prompt: str, system: str, max_tokens: int,
                          temperature: float, api_key: str, model: str) -> LLMResponse:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={api_key}")
        parts = [{"text": prompt}]
        if system:
            parts.insert(0, {"text": f"[SYSTEM] {system}\n\n"})
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}
        }
        return self._http_post_json(url, body, "gemini", model)

    # ─── OpenAI 兼容协议 (OpenAI / DeepSeek) ──────────────────────────────────
    def _call_openai_compat(self, prompt: str, system: str, max_tokens: int,
                             temperature: float, base_url: str, api_key: str,
                             model: str, provider_name: str) -> LLMResponse:
        if not api_key:
            return LLMResponse("", provider_name, model, success=False,
                               error=f"{provider_name.upper()}_API_KEY 未设置")

        # 尝试 SDK
        try:
            import openai  # type: ignore
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=model, messages=messages,
                max_tokens=max_tokens, temperature=temperature
            )
            text = resp.choices[0].message.content or ""
            in_t = resp.usage.prompt_tokens if resp.usage else 0
            out_t = resp.usage.completion_tokens if resp.usage else 0
            return LLMResponse(text, provider_name, model, in_t, out_t, success=True)
        except ImportError:
            pass
        except Exception as e:
            return LLMResponse("", provider_name, model, success=False, error=str(e))

        # REST fallback
        url = f"{base_url}/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {"model": model, "messages": messages,
                "max_tokens": max_tokens, "temperature": temperature}
        return self._http_post_json(url, body, provider_name, model,
                                    headers={"Authorization": f"Bearer {api_key}"},
                                    response_extractor=self._extract_openai_text)

    # ─── Claude ────────────────────────────────────────────────────────────────
    def _call_claude(self, prompt: str, system: str, max_tokens: int,
                     temperature: float) -> LLMResponse:
        api_key = os.environ.get("ANTHROPIC_API_KEY", self.api_key)
        if not api_key:
            return LLMResponse("", "claude", self.model, success=False,
                               error="ANTHROPIC_API_KEY 未设置")
        model = self.model if self.provider == LLMProvider.CLAUDE else DEFAULT_MODELS[LLMProvider.CLAUDE]

        try:
            import anthropic  # type: ignore
            client = anthropic.Anthropic(api_key=api_key)
            kwargs: Dict[str, Any] = {
                "model": model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system:
                kwargs["system"] = system
            resp = client.messages.create(**kwargs)
            text = resp.content[0].text if resp.content else ""
            return LLMResponse(text, "claude", model,
                               resp.usage.input_tokens, resp.usage.output_tokens, success=True)
        except ImportError:
            pass
        except Exception as e:
            return LLMResponse("", "claude", model, success=False, error=str(e))

        # REST fallback
        url = "https://api.anthropic.com/v1/messages"
        body = {
            "model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system:
            body["system"] = system
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        return self._http_post_json(url, body, "claude", model,
                                    headers=headers,
                                    response_extractor=self._extract_claude_text)

    # ─── Ollama (本地) ─────────────────────────────────────────────────────────
    def _call_ollama(self, prompt: str, system: str, max_tokens: int,
                     temperature: float) -> LLMResponse:
        model = self.model if self.provider == LLMProvider.OLLAMA else DEFAULT_MODELS[LLMProvider.OLLAMA]
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        url = f"{ollama_url}/api/generate"
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        body = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }
        return self._http_post_json(url, body, "ollama", model,
                                    response_extractor=self._extract_ollama_text)

    # ─── HTTP 通用 POST ────────────────────────────────────────────────────────
    def _http_post_json(
        self, url: str, body: dict, provider_name: str, model: str,
        headers: Optional[Dict[str, str]] = None,
        response_extractor=None
    ) -> LLMResponse:
        try:
            data = json.dumps(body).encode("utf-8")
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)
            req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                result = json.loads(raw)
                if response_extractor:
                    text = response_extractor(result)
                else:
                    text = self._extract_gemini_text(result)
                return LLMResponse(text, provider_name, model, success=True)
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")
            return LLMResponse("", provider_name, model, success=False,
                               error=f"HTTP {e.code}: {body_err[:200]}")
        except Exception as e:
            return LLMResponse("", provider_name, model, success=False, error=str(e))

    # ─── 响应文本提取器 ────────────────────────────────────────────────────────
    @staticmethod
    def _extract_gemini_text(result: dict) -> str:
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _extract_openai_text(result: dict) -> str:
        try:
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _extract_claude_text(result: dict) -> str:
        try:
            return result["content"][0]["text"]
        except (KeyError, IndexError):
            return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _extract_ollama_text(result: dict) -> str:
        return result.get("response", json.dumps(result, ensure_ascii=False))

    # ─── 工具方法 ─────────────────────────────────────────────────────────────
    @staticmethod
    def available_providers() -> List[str]:
        """检测当前环境中可用的 Provider"""
        available = []
        for prov, env_key in API_KEY_ENV.items():
            if prov == LLMProvider.OLLAMA:
                # 尝试 ping Ollama
                try:
                    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
                    urllib.request.urlopen(f"{base}/api/tags", timeout=2)
                    available.append(prov.value)
                except Exception:
                    pass
            elif env_key and os.environ.get(env_key):
                available.append(prov.value)
        return available

    @staticmethod
    def get_config_from_args(args) -> Dict[str, Any]:
        """从 argparse.Namespace 提取 LLM 配置"""
        return {
            "provider": getattr(args, "llm_provider", "gemini") or "gemini",
            "model":    getattr(args, "llm_model", None),
            "auto_fallback": not getattr(args, "no_fallback", False),
            "verbose":  getattr(args, "verbose", False),
        }


# ─── 模块级单例（可选使用） ────────────────────────────────────────────────────
def get_gateway(provider: str = "gemini", model: Optional[str] = None,
                **kwargs) -> LLMGateway:
    """工厂函数，从环境变量自动选择可用 Provider"""
    if provider == "auto":
        avail = LLMGateway.available_providers()
        provider = avail[0] if avail else "gemini"
    return LLMGateway(provider=provider, model=model, **kwargs)


# ─── CLI 测试入口 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM Gateway 快速测试")
    parser.add_argument("--provider", default="gemini", choices=[p.value for p in LLMProvider])
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt", default="用一句话介绍你自己")
    parser.add_argument("--check", action="store_true", help="检测可用 Provider")
    a = parser.parse_args()

    if a.check:
        avail = LLMGateway.available_providers()
        print(f"[LLMGateway] 可用 Provider: {avail if avail else '无（请配置 .env 或环境变量）'}")
        sys.exit(0)

    print(f"[LLMGateway] 调用 {a.provider} ...")
    gw = LLMGateway(provider=a.provider, model=a.model, verbose=True)
    resp = gw.call(a.prompt)
    if resp.success:
        print(f"\n{'='*60}")
        print(resp.text)
        print(f"{'='*60}")
        print(repr(resp))
    else:
        print(f"[ERROR] {resp.error}")
        sys.exit(1)
