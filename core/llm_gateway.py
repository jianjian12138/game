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

def _load_dotenv(path=None):
    env_file = Path(path) if path else _ENV_FILE
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def ensure_env_loaded(path=None) -> None:
    """显式确保 .env 已加载（幂等；已存在的环境变量优先）。

    原先只有导入本模块时才顺带加载 .env，属于隐式副作用：
    某些命令路径若不经过本模块，读到的就永远是空配置，
    会让「明明填了 .env 却报未配置」。入口统一调用本函数后不再依赖导入顺序。
    """
    _load_dotenv(path)


_load_dotenv()

# ─── Provider 枚举 ─────────────────────────────────────────────────────────────
class LLMProvider(str, Enum):
    GEMINI    = "gemini"
    OPENAI    = "openai"
    CLAUDE    = "claude"
    OLLAMA    = "ollama"
    DEEPSEEK  = "deepseek"
    OPENAI_COMPAT = "openai_compat"   # 任意 OpenAI 兼容端点（免费额度池走这里）

# ─── 默认模型映射 ──────────────────────────────────────────────────────────────
DEFAULT_MODELS: Dict[LLMProvider, str] = {
    LLMProvider.GEMINI:   "gemini-2.0-flash",
    LLMProvider.OPENAI:   "gpt-4o-mini",
    LLMProvider.CLAUDE:   "claude-sonnet-4-5",
    LLMProvider.OLLAMA:   "llama3.2",
    LLMProvider.DEEPSEEK: "deepseek-chat",
    LLMProvider.OPENAI_COMPAT: "",   # 运行时从端点池取
}

# ─── API Key 环境变量映射 ──────────────────────────────────────────────────────
API_KEY_ENV: Dict[LLMProvider, str] = {
    LLMProvider.GEMINI:   "GEMINI_API_KEY",
    LLMProvider.OPENAI:   "OPENAI_API_KEY",
    LLMProvider.CLAUDE:   "ANTHROPIC_API_KEY",
    LLMProvider.OLLAMA:   "",   # 不需要 Key
    LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
    LLMProvider.OPENAI_COMPAT: "",   # 从端点池读取，不落单一环境变量
}


# ─── OpenAI 兼容端点池（免费额度池） ─────────────────────────────────────────────
# 端点文件含密钥，**必须**保持 gitignore，不得提交。用 CLI 的 `llm-import` 从
# 本地 JSON 导入，用 `llm-status` 做真实连通性探测（不探测就不得宣称可用）。
ENDPOINT_POOL_FILE = Path(__file__).resolve().parent.parent / "config" / "llm_endpoints.json"


class LLMEndpoint:
    """一个 OpenAI 兼容的 LLM 端点。"""

    __slots__ = ("id", "name", "vendor", "url", "api_key",
                 "supports_tool_call", "supports_images", "supports_reasoning")

    def __init__(self, raw: Dict[str, Any]):
        self.id = str(raw.get("id", "")).strip()
        self.name = str(raw.get("name", self.id))
        self.vendor = str(raw.get("vendor", ""))
        self.url = str(raw.get("url", "")).rstrip("/")
        self.api_key = str(raw.get("apiKey", "") or raw.get("api_key", ""))
        self.supports_tool_call = bool(raw.get("supportsToolCall", False))
        self.supports_images = bool(raw.get("supportsImages", False))
        self.supports_reasoning = bool(raw.get("supportsReasoning", False))

    @property
    def chat_url(self) -> str:
        if self.url.endswith("/chat/completions"):
            return self.url
        return self.url + "/chat/completions"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "vendor": self.vendor,
            "url": self.chat_url, "supports_tool_call": self.supports_tool_call,
            "supports_images": self.supports_images, "supports_reasoning": self.supports_reasoning,
            # 不回显 api_key
        }


def load_endpoints(path: Path = ENDPOINT_POOL_FILE) -> List[LLMEndpoint]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, dict):
        raw = raw.get("endpoints", [])
    return [LLMEndpoint(x) for x in raw if isinstance(x, dict) and x.get("id")]


def probe_endpoint(ep: LLMEndpoint, timeout: int = 30) -> Dict[str, Any]:
    """真实连通性探测：发一条最小请求，只认真正拿回内容的端点为可用。"""
    import time as _t
    started = _t.time()
    body = {
        "model": ep.id,
        "messages": [{"role": "user", "content": "回复 OK"}],
        "max_tokens": 512,   # 推理类模型会先吃掉思考 token，给足额度
    }
    req = urllib.request.Request(
        ep.chat_url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {ep.api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = ""
            try:
                text = data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError):
                pass
            ok = bool(text.strip())
            return {
                "id": ep.id, "name": ep.name, "ok": ok,
                "latency_ms": int((_t.time() - started) * 1000),
                "error": "" if ok else "返回内容为空（可能是推理模型耗尽 token 或额度受限）",
                "sample": text[:60],
            }
    except urllib.error.HTTPError as e:
        return {"id": ep.id, "name": ep.name, "ok": False,
                "latency_ms": int((_t.time() - started) * 1000),
                "error": f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:160]}", "sample": ""}
    except Exception as e:
        return {"id": ep.id, "name": ep.name, "ok": False,
                "latency_ms": int((_t.time() - started) * 1000),
                "error": f"{type(e).__name__}: {str(e)[:160]}", "sample": ""}

# ─── 降级顺序 ──────────────────────────────────────────────────────────────────
FALLBACK_ORDER: List[LLMProvider] = [
    LLMProvider.OPENAI_COMPAT,   # 免费额度池优先，成本最低
    LLMProvider.GEMINI,
    LLMProvider.DEEPSEEK,
    LLMProvider.OLLAMA,
    LLMProvider.OPENAI,
    LLMProvider.CLAUDE,
]

# ─── 响应缓存与预算熔断防护 (V5-14) ──────────────────────────────────────────
_RESPONSE_CACHE: Dict[str, "LLMResponse"] = {}
_MAX_CACHE_ENTRIES: int = 256

class LLMBudgetTracker:
    """LLM 成本与预算熔断监控器"""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    budget_limit_usd: float = float(os.environ.get("LLM_BUDGET_LIMIT_USD", "100.0"))

    @classmethod
    def record_usage(cls, provider: str, in_tok: int, out_tok: int):
        cls.total_prompt_tokens += in_tok
        cls.total_completion_tokens += out_tok
        rates = {
            "gemini": (0.0001 / 1000, 0.0004 / 1000),
            "deepseek": (0.00014 / 1000, 0.00028 / 1000),
            "ollama": (0.0, 0.0),
            "openai": (0.00015 / 1000, 0.0006 / 1000),
            "claude": (0.003 / 1000, 0.015 / 1000),
        }
        in_r, out_r = rates.get(provider.lower(), (0.001 / 1000, 0.002 / 1000))
        cls.total_cost_usd += (in_tok * in_r + out_tok * out_r)

    @classmethod
    def is_budget_exceeded(cls) -> bool:
        return cls.total_cost_usd >= cls.budget_limit_usd


class LLMResponse:
    """统一响应格式"""
    def __init__(self, text: str, provider: str, model: str,
                 input_tokens: int = 0, output_tokens: int = 0,
                 success: bool = True, error: str = "", is_cached: bool = False):
        self.text = text
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.success = success
        self.error = error
        self.is_cached = is_cached

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
        use_cache: bool = True,
        max_retries: int = 2,
    ) -> LLMResponse:
        """调用 LLM，内置指数退避重试 (Exponential Backoff)、响应缓存与按成本梯度的 FALLBACK_ORDER 自动降级"""
        if LLMBudgetTracker.is_budget_exceeded():
            return LLMResponse("", str(self.provider), self.model, success=False,
                               error=f"预算熔断已触发: 当前预估消耗 ${LLMBudgetTracker.total_cost_usd:.4f} 超出上限 ${LLMBudgetTracker.budget_limit_usd:.2f}")

        max_tok = max_tokens or self.max_tokens
        temp = temperature if temperature is not None else self.temperature

        # 检查响应缓存 (Cache Lookup)
        cache_key = ""
        if use_cache:
            import hashlib
            raw_key = f"{self.provider.value}:{self.model}:{prompt}:{system}:{max_tok}:{temp}"
            cache_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            if cache_key in _RESPONSE_CACHE:
                cached = _RESPONSE_CACHE[cache_key]
                return LLMResponse(cached.text, cached.provider, cached.model,
                                   cached.input_tokens, cached.output_tokens,
                                   cached.success, cached.error, is_cached=True)

        providers_to_try = [self.provider]
        if self.auto_fallback:
            for p in FALLBACK_ORDER:
                if p != self.provider:
                    env_k = API_KEY_ENV.get(p, "")
                    if p == LLMProvider.OLLAMA or p == LLMProvider.OPENAI_COMPAT or os.environ.get(env_k, ""):
                        providers_to_try.append(p)

        last_error = ""
        for prov in providers_to_try:
            if self.verbose:
                print(f"[LLMGateway] 尝试 {prov.value}/{DEFAULT_MODELS[prov]} ...", flush=True)

            # 指数退避重试机制 (Retry with Exponential Backoff)
            for attempt in range(max_retries + 1):
                try:
                    resp = self._dispatch(prov, prompt, system, max_tok, temp)
                    if resp.success:
                        LLMBudgetTracker.record_usage(prov.value, resp.input_tokens, resp.output_tokens)
                        if use_cache and cache_key and len(_RESPONSE_CACHE) < _MAX_CACHE_ENTRIES:
                            _RESPONSE_CACHE[cache_key] = resp
                        return resp
                    last_error = resp.error
                except Exception as e:
                    last_error = str(e)
                    if self.verbose:
                        print(f"[LLMGateway] {prov.value} 尝试 {attempt+1}/{max_retries+1} 异常: {e}", flush=True)

                if attempt < max_retries:
                    import time
                    time.sleep(0.3 * (2 ** attempt))

        return LLMResponse(
            text="", provider=str(self.provider), model=self.model,
            success=False, error=f"所有 Provider 均失败 (已执行指数退避重试): {last_error}"
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
                api_key=self.api_key or os.environ.get("OPENAI_API_KEY", ""),
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
                api_key=self.api_key or os.environ.get("DEEPSEEK_API_KEY", ""),
                model=DEFAULT_MODELS[provider],
                provider_name="deepseek"
            )
        elif provider == LLMProvider.OPENAI_COMPAT:
            return self._call_endpoint_pool(prompt, system, max_tokens, temperature)
        else:
            return LLMResponse(text="", provider=str(provider), model="",
                               success=False, error=f"未知 Provider: {provider}")

    # ─── OpenAI 兼容端点池 ────────────────────────────────────────────────────
    def _resolve_endpoint(self) -> Optional[LLMEndpoint]:
        pool = load_endpoints()
        if not pool:
            return None
        if self.model:
            for ep in pool:
                if ep.id == self.model:
                    return ep
        preferred = os.environ.get("LLM_PREFERRED_ENDPOINT", "").strip()
        if preferred:
            for ep in pool:
                if ep.id == preferred:
                    return ep
        return pool[0]

    def _call_endpoint_pool(self, prompt: str, system: str,
                            max_tokens: int, temperature: float) -> LLMResponse:
        pool = load_endpoints()
        if not pool:
            return LLMResponse("", "openai_compat", "", success=False,
                               error="未配置端点池：请先执行 `game_agent.py llm-import --file <llm.json>`")
        ordered = list(pool)
        preferred = self._resolve_endpoint()
        if preferred:
            # 按 id 去重，不能用对象身份（两次 load 出来的实例不同）
            ordered = [e for e in ordered if e.id != preferred.id]
            ordered.insert(0, preferred)

        last_error = ""
        for ep in ordered:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            body = {"model": ep.id, "messages": messages,
                    "max_tokens": max_tokens, "temperature": temperature}
            resp = self._http_post_json(ep.chat_url, body, "openai_compat", ep.id,
                                        headers={"Authorization": f"Bearer {ep.api_key}"},
                                        response_extractor=self._extract_openai_text)
            if resp.success and (resp.text or "").strip():
                return resp
            last_error = f"{ep.id}: {resp.error or '空响应'}"
        return LLMResponse("", "openai_compat", preferred.id if preferred else "",
                           success=False, error=f"端点池全部失败 | {last_error}")

    # ─── Gemini ────────────────────────────────────────────────────────────────
    def _call_gemini(self, prompt: str, system: str, max_tokens: int,
                     temperature: float) -> LLMResponse:
        api_key = self.api_key or os.environ.get("GEMINI_API_KEY", "")
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
            in_tok = 0
            out_tok = 0
            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                in_tok = getattr(resp.usage_metadata, "prompt_token_count", 0) or 0
                out_tok = getattr(resp.usage_metadata, "candidates_token_count", 0) or 0
            return LLMResponse(text, "gemini", model, input_tokens=in_tok, output_tokens=out_tok, success=True)
        except ImportError:
            pass  # SDK 未安装，降级到 REST
        except Exception as e:
            return LLMResponse("", "gemini", model, success=False, error=str(e))

        # REST fallback
        return self._call_gemini_rest(prompt, system, max_tokens, temperature, api_key, model)

    def _call_gemini_rest(self, prompt: str, system: str, max_tokens: int,
                          temperature: float, api_key: str, model: str) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        parts = [{"text": prompt}]
        if system:
            parts.insert(0, {"text": f"[SYSTEM] {system}\n\n"})
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}
        }
        headers = {"x-goog-api-key": api_key}
        return self._http_post_json(url, body, "gemini", model, headers=headers)

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
        api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
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

                in_tok = 0
                out_tok = 0
                if "usageMetadata" in result:
                    in_tok = result["usageMetadata"].get("promptTokenCount", 0) or 0
                    out_tok = result["usageMetadata"].get("candidatesTokenCount", 0) or 0
                elif "usage" in result:
                    in_tok = result["usage"].get("prompt_tokens", result["usage"].get("input_tokens", 0)) or 0
                    out_tok = result["usage"].get("completion_tokens", result["usage"].get("output_tokens", 0)) or 0

                return LLMResponse(text, provider_name, model, input_tokens=in_tok, output_tokens=out_tok, success=True)
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
        if load_endpoints():
            available.append(LLMProvider.OPENAI_COMPAT.value)
        for prov, env_key in API_KEY_ENV.items():
            if prov == LLMProvider.OPENAI_COMPAT:
                continue
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
