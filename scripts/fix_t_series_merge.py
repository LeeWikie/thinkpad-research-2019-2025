#!/usr/bin/env python3
"""修复 T 系列数据合并 — 将 specs_t_series.json 的官方参数合并到 merged_data.json"""

import json
import sys
from pathlib import Path

SPECS_PATH = Path("data/raw/specs_t_series.json")
MERGED_PATH = Path("data/processed/merged_data.json")


def build_cpu_string(cpu: dict) -> str:
    """Build CPU string from specs CPU dict."""
    family = cpu.get("family", "")
    # Check for dual-architecture format (models_intel/models_amd)
    if "models_intel" in cpu or "models_amd" in cpu:
        intel_models = cpu.get("models_intel", [])
        amd_models = cpu.get("models_amd", [])
        parts = []
        if intel_models:
            parts.append(f"Intel: {', '.join(intel_models)}")
        if amd_models:
            parts.append(f"AMD: {', '.join(amd_models)}")
        return f"{family} ({'; '.join(parts)})"

    # Single architecture
    models = cpu.get("models", [])
    if models:
        return f"{family} ({', '.join(models)})"
    return family


def build_cpu_architecture(cpu: dict) -> str:
    """Determine CPU architecture."""
    family = cpu.get("family", "")
    has_intel = "Intel" in family or "intel" in str(cpu).lower() or "models_intel" in cpu
    has_amd = "AMD" in family or "Ryzen" in family or "amd" in str(cpu).lower() or "models_amd" in cpu
    if has_intel and has_amd:
        return "Intel / AMD"
    if has_intel:
        return "Intel"
    if has_amd:
        return "AMD"
    return "N/A"


def build_dgpu_string(dgpu_val: str) -> str:
    """Translate discrete GPU string."""
    if dgpu_val in ("None", "无", ""):
        return "无"
    return dgpu_val


def build_fingerprint(val: str) -> str:
    """Translate fingerprint string."""
    m = {
        "Optional": "可选",
        "Yes": "是",
        "No": "否",
        "yes": "是",
        "no": "否",
        "optional": "可选",
    }
    return m.get(val, val)


def build_touch_string(val: str) -> str:
    """Translate touch support string."""
    if "Optional" in val:
        return "可选"
    if "Yes" in val or "yes" in val:
        return "是"
    if "No" in val or "no" in val:
        return "否"
    return val


def build_camera(webcam: dict) -> str:
    """Build camera string from webcam dict."""
    res = webcam.get("resolution", "")
    ir = webcam.get("ir", "")
    shutter = webcam.get("shutter", "")
    parts = [res]
    if shutter:
        parts.append(f"with {shutter}")
    if ir and "Optional" in ir:
        parts.append("(可选 IR)")
    elif ir:
        parts.append(f"({ir})")
    return " ".join(parts)


def build_battery(battery: dict) -> str:
    """Build battery_life_official string."""
    hours = battery.get("hours", "N/A")
    capacity = battery.get("capacity", "")
    if hours == "N/A" or hours is None:
        if capacity:
            return f"N/A ({capacity})"
        return "N/A"
    if capacity:
        return f"{hours} ({capacity})"
    return hours


def build_storage(storage: dict) -> str:
    """Build storage string."""
    interface = storage.get("interface", "")
    max_val = storage.get("max", "")
    slots = storage.get("slots", "")
    parts = [interface]
    if max_val:
        parts.append(max_val)
    if slots:
        parts.append(slots)
    return ", ".join(parts)


def merge_t_series():
    """Main merge function."""
    # Load specs
    with open(SPECS_PATH) as f:
        specs_data = json.load(f)
    specs_models = specs_data["models"]

    # Load merged data
    with open(MERGED_PATH) as f:
        merged = json.load(f)

    # Build lookup by model name
    specs_by_model = {}
    for sm in specs_models:
        key = sm["model"].strip()
        specs_by_model[key] = sm

    # Track stats
    updated = 0
    not_found = []

    # Update T-series models in merged data
    for m in merged["models"]:
        model_name = m.get("model", "").strip()
        if model_name not in specs_by_model:
            continue

        spec = specs_by_model[model_name]
        updated += 1

        # Screen fields
        screen = spec.get("screen", {})
        m["screen_size"] = screen.get("size", m.get("screen_size", "N/A"))
        m["resolution"] = " / ".join(screen.get("resolution_options", [])) or m.get("resolution", "N/A")
        m["refresh_rate"] = screen.get("refresh_rate", m.get("refresh_rate", "N/A"))
        m["touch_screen"] = build_touch_string(screen.get("touch_support", m.get("touch_screen", "N/A")))

        # CPU fields
        cpu = spec.get("cpu", {})
        m["cpu"] = build_cpu_string(cpu) or m.get("cpu", "N/A")
        m["cpu_architecture"] = build_cpu_architecture(cpu)

        # GPU fields
        gpu = spec.get("gpu", {})
        m["igpu"] = gpu.get("integrated", m.get("igpu", "N/A"))
        m["dgpu"] = build_dgpu_string(gpu.get("discrete", m.get("dgpu", "N/A")))

        # RAM fields
        ram = spec.get("ram", {})
        m["ram_type"] = ram.get("type", m.get("ram_type", "N/A"))
        m["ram_max"] = ram.get("max", m.get("ram_max", "N/A"))

        # Storage
        storage = spec.get("storage", {})
        m["storage"] = build_storage(storage)

        # Ports / Wireless / Fingerprint / Camera / Battery
        m["ports"] = spec.get("ports", m.get("ports", "N/A"))
        m["wireless"] = spec.get("wireless", m.get("wireless", "N/A"))
        m["fingerprint"] = build_fingerprint(spec.get("fingerprint", m.get("fingerprint", "N/A")))

        webcam = spec.get("webcam", {})
        m["camera"] = build_camera(webcam)

        battery = spec.get("battery", {})
        m["battery_life_official"] = build_battery(battery)

        # Preserve year if spec has it
        if "year" in spec and m.get("year") in (None, "N/A"):
            m["year"] = spec["year"]

    print(f"Models updated: {updated}")
    if not_found:
        print(f"Models in specs but not in merged: {not_found}")

    # Update meta
    merged["meta"]["merge_date"] = "2026-06-08 (T-series fix)"

    # Save
    with open(MERGED_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"Saved to {MERGED_PATH}")
    return updated


if __name__ == "__main__":
    updated = merge_t_series()
    if updated == 28:
        print("\n✓ All 28 T-series models successfully merged!")
        sys.exit(0)
    else:
        print(f"\n⚠ Expected 28, got {updated}")
        sys.exit(1)
