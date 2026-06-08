"""ThinkPad 数据收集框架.

提供统一的数据收集、验证、合并与进度追踪基础设施。
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
DATA_DIR = Path("data/raw")
DEFAULT_TIMEOUT = 30  # 秒
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 2  # 秒
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# ProgressTracker
# ---------------------------------------------------------------------------
class CollectionStatus(str, Enum):
    """型号数据收集状态."""

    PENDING = "pending"
    COLLECTED = "collected"
    VALIDATING = "validating"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ProgressTracker:
    """记录每个型号的收集状态.

    状态文件保存为 JSON，路径: data/raw/_progress.json
    """

    progress_file: Path = field(default_factory=lambda: DATA_DIR / "_progress.json")
    _status: dict[str, CollectionStatus] = field(default_factory=dict, repr=False)

    # -- 持久化 ----------------------------------------------------------

    def load(self) -> None:
        """从磁盘加载进度."""
        if self.progress_file.exists():
            raw = json.loads(self.progress_file.read_text(encoding="utf-8"))
            self._status = {k: CollectionStatus(v) for k, v in raw.items()}
        else:
            self._status = {}

    def save(self) -> None:
        """将进度写入磁盘."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.value for k, v in self._status.items()}
        self.progress_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # -- 查询 -------------------------------------------------------------

    def get(self, model: str) -> CollectionStatus:
        """获取指定型号的状态，默认 PENDING."""
        return self._status.get(model, CollectionStatus.PENDING)

    def set(self, model: str, status: CollectionStatus) -> None:
        """设置指定型号的状态并持久化."""
        self._status[model] = status
        self.save()

    def summary(self) -> dict[str, int]:
        """返回各状态的数量统计."""
        counts: dict[str, int] = {s.value: 0 for s in CollectionStatus}
        for status in self._status.values():
            counts[status.value] += 1
        return counts

    @property
    def all_models(self) -> list[str]:
        """返回所有已记录的型号列表."""
        return list(self._status.keys())


# ---------------------------------------------------------------------------
# WebFetcher
# ---------------------------------------------------------------------------
@dataclass
class WebFetcher:
    """封装 requests，处理超时、重试、User-Agent、编码.

    用法::

        fetcher = WebFetcher(retries=3)
        html = fetcher.fetch("https://example.com")
    """

    timeout: int = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY
    user_agent: str = DEFAULT_USER_AGENT
    session: requests.Session = field(default_factory=requests.Session, repr=False)

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": self.user_agent})

    def fetch(self, url: str, **kwargs: Any) -> str:
        """请求 URL 并返回解码后的文本.

        自动重试，处理网络错误与编码问题。

        Raises:
            requests.RequestException: 所有重试均失败时抛出。
        """
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                # 优先使用响应头声明的编码，否则 fallback 到 utf-8
                if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "请求失败 (第 %d/%d 次): %s - %s",
                    attempt,
                    self.retries,
                    url,
                    exc,
                )
                if attempt < self.retries:
                    time.sleep(self.retry_delay * attempt)
        raise last_exc or requests.RequestException(f"所有重试均失败: {url}")


# ---------------------------------------------------------------------------
# DataValidator
# ---------------------------------------------------------------------------
@dataclass
class DataValidator:
    """验证 ThinkPad 数据格式.

    支持验证:
    - CPU 型号格式
    - 屏幕分辨率格式
    - 价格范围
    """

    # 常见 CPU 型号正则: "Intel Core i7-13700H", "AMD Ryzen 7 7840U"
    CPU_PATTERN = re.compile(
        r"^(Intel\s+Core\s+(?:i[3579]-\d{4,5}[A-Z]*|Ultra\s+\d+\s+\d+[A-Z]*)"
        r"|AMD\s+Ryzen\s+\d+\s+\d{4,5}[A-Z]*)$",
        re.IGNORECASE,
    )
    # 分辨率: "1920x1080", "2560x1440", "3840x2160"
    RESOLUTION_PATTERN = re.compile(r"^\d{3,5}x\d{3,5}$")
    # 价格: 正整数或浮点数，可选货币符号
    PRICE_PATTERN = re.compile(r"^[\$￥]?\d+([.,]\d{1,2})?$")

    @staticmethod
    def validate_cpu(cpu: str) -> bool:
        """验证 CPU 型号格式."""
        if not cpu or not isinstance(cpu, str):
            return False
        return bool(DataValidator.CPU_PATTERN.match(cpu.strip()))

    @staticmethod
    def validate_resolution(res: str) -> bool:
        """验证分辨率格式，如 '1920x1080'."""
        if not res or not isinstance(res, str):
            return False
        return bool(DataValidator.RESOLUTION_PATTERN.match(res.strip()))

    @staticmethod
    def validate_price(price: Any) -> bool:
        """验证价格格式."""
        if isinstance(price, (int, float)):
            return price >= 0
        if isinstance(price, str):
            return bool(DataValidator.PRICE_PATTERN.match(price.strip()))
        return False

    @staticmethod
    def validate_model_entry(entry: dict[str, Any]) -> list[str]:
        """验证一条型号数据，返回错误信息列表（空列表表示通过）."""
        errors: list[str] = []
        if not entry.get("model"):
            errors.append("缺少 model 字段")
        cpu = entry.get("cpu")
        if cpu and not DataValidator.validate_cpu(cpu):
            errors.append(f"CPU 格式无效: {cpu}")
        res = entry.get("resolution")
        if res and not DataValidator.validate_resolution(res):
            errors.append(f"分辨率格式无效: {res}")
        price = entry.get("price")
        if price is not None and not DataValidator.validate_price(price):
            errors.append(f"价格格式无效: {price}")
        return errors


# ---------------------------------------------------------------------------
# DataMerger
# ---------------------------------------------------------------------------
class MergeStrategy(str, Enum):
    """合并冲突策略."""

    OFFICIAL_FIRST = "official_first"  # 官方数据优先
    NEWEST_FIRST = "newest_first"  # 最新数据优先
    UNION = "union"  # 合并所有字段（不覆盖）


class DataMerger:
    """合并多个数据源，处理冲突.

    用法::

        merger = DataMerger(strategy=MergeStrategy.OFFICIAL_FIRST)
        result = merger.merge([official_data, wiki_data, benchmark_data])
    """

    def __init__(self, strategy: MergeStrategy = MergeStrategy.OFFICIAL_FIRST) -> None:
        self.strategy = strategy

    def merge(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        """合并多个数据源字典.

        按策略处理字段冲突:
        - OFFICIAL_FIRST: 列表顺序即优先级，前面的源优先
        - NEWEST_FIRST: 同 OFFICIAL_FIRST（调用方应按时间排序）
        - UNION: 保留所有源的字段，不覆盖已有值
        """
        if not sources:
            return {}
        if len(sources) == 1:
            return dict(sources[0])

        result: dict[str, Any] = {}
        if self.strategy == MergeStrategy.UNION:
            for src in sources:
                for key, value in src.items():
                    if key not in result:
                        result[key] = value
        else:
            # OFFICIAL_FIRST / NEWEST_FIRST: 后出现的源不覆盖已有值
            for src in reversed(sources):
                result.update(src)
        return result

    def merge_model_lists(
        self,
        source_lists: list[list[dict[str, Any]]],
        key: str = "model",
    ) -> list[dict[str, Any]]:
        """合并多个型号列表，按 key 去重.

        每个源列表中的条目通过 key 字段（默认 "model"）标识。
        同一型号的数据按策略合并。
        """
        model_map: dict[str, list[dict[str, Any]]] = {}
        for src_list in source_lists:
            for entry in src_list:
                model_key = entry.get(key, "")
                if not model_key:
                    continue
                model_map.setdefault(model_key, []).append(entry)

        merged: list[dict[str, Any]] = []
        for model_key, entries in model_map.items():
            merged_entry = self.merge(entries)
            merged.append(merged_entry)
        return merged


# ---------------------------------------------------------------------------
# BaseCollector
# ---------------------------------------------------------------------------
class BaseCollector(ABC):
    """统一的数据收集接口.

    子类需实现:
    - fetch(model): 获取原始数据
    - parse(raw): 解析原始数据为结构化字典
    - validate(parsed): 验证解析后的数据

    用法::

        class MyCollector(BaseCollector):
            def fetch(self, model): ...
            def parse(self, raw): ...
            def validate(self, parsed): ...

        collector = MyCollector()
        result = collector.collect("T14s Gen 4")
    """

    def __init__(
        self,
        source_name: str,
        fetcher: WebFetcher | None = None,
        validator: DataValidator | None = None,
        tracker: ProgressTracker | None = None,
    ) -> None:
        self.source_name = source_name
        self.fetcher = fetcher or WebFetcher()
        self.validator = validator or DataValidator()
        self.tracker = tracker or ProgressTracker()

    @abstractmethod
    def fetch(self, model: str) -> str:
        """获取指定型号的原始数据（HTML/JSON 等）."""

    @abstractmethod
    def parse(self, raw: str) -> dict[str, Any]:
        """将原始数据解析为结构化字典."""

    def validate(self, parsed: dict[str, Any]) -> list[str]:
        """验证解析后的数据，返回错误列表（空列表表示通过）."""
        return DataValidator.validate_model_entry(parsed)

    def save(self, data: dict[str, Any], series: str = "") -> Path:
        """将数据保存为 JSON 文件.

        路径格式: data/raw/{source_name}_{series}.json
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        suffix = f"_{series}" if series else ""
        path = DATA_DIR / f"{self.source_name}{suffix}.json"
        existing: list[dict[str, Any]] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("无法读取已有文件，将覆盖: %s", path)
        if isinstance(data, list):
            existing.extend(data)
        else:
            existing.append(data)
        path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("数据已保存: %s (%d 条)", path, len(existing))
        return path

    def collect(self, model: str) -> dict[str, Any]:
        """完整的收集流程: fetch → parse → validate → 更新进度.

        Returns:
            解析后的数据字典。如果验证有错误，会在数据中添加
            ``_validation_errors`` 字段。
        """
        self.tracker.load()
        self.tracker.set(model, CollectionStatus.PENDING)

        try:
            self.tracker.set(model, CollectionStatus.COLLECTED)
            raw = self.fetch(model)
            parsed = self.parse(raw)

            self.tracker.set(model, CollectionStatus.VALIDATING)
            errors = self.validate(parsed)
            if errors:
                parsed["_validation_errors"] = errors
                logger.warning("型号 %s 验证问题: %s", model, errors)

            self.tracker.set(model, CollectionStatus.DONE)
            return parsed

        except Exception:
            self.tracker.set(model, CollectionStatus.FAILED)
            raise