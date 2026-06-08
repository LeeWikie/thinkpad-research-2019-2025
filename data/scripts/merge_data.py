#!/usr/bin/env python3
"""ThinkPad数据清洗与合并脚本 - Task 19.

读取所有原始数据文件，按型号合并数据，计算Linux兼容性评分，生成统一数据集。
"""

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")
EVIDENCE_DIR = Path(".sisyphus/evidence")


def normalize(name: str) -> str:
    name = name.strip()
    if name.lower().startswith("thinkpad "):
        name = name[9:].strip()
    return name


def normalize_price_key(key: str) -> str:
    name = key.replace("_", " ").strip()
    name = re.sub(r"\b(Gen)(\d)", r"\1 \2", name)
    return normalize(name)


def normalize_arch_name(name: str) -> str:
    name = re.sub(r"\s*\((?:Intel|AMD)\)\s*", " ", name).strip()
    return normalize(name)


def model_key(name: str, year=None):
    n = normalize(name).lower()
    return f"{n}::{year}" if year else n


def series_group(model_name: str, series_field: str) -> str:
    n = normalize(model_name).lower()
    s = series_field.lower()
    if "x1 carbon" in n or "x1 yoga" in n or "x1 nano" in n or "x1 fold" in n or "x1 titanium" in n or "x1 2-in-1" in n:
        return "x1_carbon"
    if "x1 extreme" in n:
        return "x1_extreme"
    if "x13" in n or "x12" in n or "x390" in n or "x395" in n:
        return "x13_series"
    if "t14" in n and "amd" in n:
        return "t14g_amd"
    if s.startswith("t "):
        return "t_series"
    if any(n.startswith(p) for p in ["t490", "t495", "t590", "t14", "t15", "t16"]):
        return "t_series"
    if s.startswith("p") or s.startswith("p1"):
        return "p_series"
    if s.startswith("e"):
        return "e_series"
    if s.startswith("l"):
        return "l_series"
    if s.startswith("z"):
        return "z_series"
    return "unknown"


# ─── Reader functions ────────────────────────────────────────────────────────


def read_master_models():
    files = [
        "models_t_series.json", "models_x_series.json",
        "models_p_series.json", "models_elz_series.json", "models_special.json",
    ]
    all_entries = []
    for fname in files:
        fpath = RAW_DIR / fname
        if not fpath.exists():
            continue
        with open(fpath) as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("models", [])
        all_entries.extend(items)
    seen = set()
    master = []
    for m in all_entries:
        key = model_key(m["model"], m.get("year"))
        if key not in seen:
            seen.add(key)
            master.append(m)
    return master


def read_specs_registry():
    files = ["specs_x_series.json", "specs_p_series.json",
             "specs_elz_series.json", "specs_special.json"]
    reg = {}
    for fname in files:
        fpath = RAW_DIR / fname
        if not fpath.exists():
            continue
        with open(fpath) as f:
            data = json.load(f)
        for item in data.get("specs", data.get("models", [])):
            name = item.get("model") or item.get("型号") or ""
            if name:
                reg[normalize(name).lower()] = item
    return reg


def read_ubuntu_registry():
    fpath = RAW_DIR / "ubuntu_cert.json"
    if not fpath.exists():
        return {}
    with open(fpath) as f:
        data = json.load(f)
    reg = {}
    for item in data.get("models", []):
        k = normalize(item.get("model", "")).lower()
        reg[k] = item
        full = item.get("full_name", "")
        if full:
            k2 = normalize(full).lower()
            if k2 != k:
                reg[k2] = item
    return reg


def read_fedora_registry():
    fpath = RAW_DIR / "fedora_compat.json"
    if not fpath.exists():
        return {}
    with open(fpath) as f:
        data = json.load(f)
    reg = {}
    for group in data.get("compatibility", []):
        for item in group.get("models", []):
            name = item.get("model", "")
            if name:
                reg[normalize(name).lower()] = item
    return reg


def read_arch_registry():
    fpath = RAW_DIR / "arch_compat.json"
    if not fpath.exists():
        return {}
    with open(fpath) as f:
        data = json.load(f)
    reg = {}
    for item in data.get("models", []):
        name = item.get("model", "")
        if not name:
            continue
        n = normalize_arch_name(name).lower()
        reg[n] = item
        if "/" in name:
            for part in re.split(r"\s*/\s*", name):
                reg[normalize_arch_name(part).lower()] = item
    return reg


def read_community_registry():
    fpath = RAW_DIR / "community_compat.json"
    if not fpath.exists():
        return {}
    with open(fpath) as f:
        data = json.load(f)
    result = {}
    for k, v in data.get("models", {}).items():
        if isinstance(v, dict):
            result[k] = v
    return result


def read_prices_registry():
    fpath = RAW_DIR / "prices_cn.json"
    if not fpath.exists():
        return {}
    with open(fpath) as f:
        data = json.load(f)
    reg = {}
    for sd in data.get("prices", {}).values():
        for mk, md in sd.get("models", {}).items():
            reg[normalize_price_key(mk).lower()] = md
    return reg


# ─── Lookup helpers ────────────────────────────────────────────────────────


def lookup(me, registry, name_modifier=None):
    model_name = me["model"]
    candidates = [normalize(model_name).lower()]
    year = me.get("year")
    if year:
        candidates.append(f"{normalize(model_name)} {year}".lower())
    for c in candidates:
        if c in registry:
            return registry[c]
    if name_modifier:
        mod = name_modifier(model_name).lower()
        if mod in registry:
            return registry[mod]
    for c in list(candidates):
        no_gen = re.sub(r"\s*gen\s*\d+", "", c, flags=re.IGNORECASE).strip()
        if no_gen and no_gen != c and no_gen in registry:
            return registry[no_gen]
    return None


# ─── Spec extraction ────────────────────────────────────────────────────────


def extract_spec_fields(spec):
    field_map = [
        ("screen_size", ["屏幕尺寸", "尺寸(英寸)", "screen_size"]),
        ("resolution", ["分辨率", "screen_resolution"]),
        ("refresh_rate", ["刷新率", "刷新率(Hz)", "screen_refresh_rate"]),
        ("touch_screen", ["触摸屏", "touch_screen"]),
        ("screen_type", ["屏幕类型"]),
        ("cpu", ["CPU型号", "cpu"]),
        ("cpu_architecture", ["CPU架构", "cpu_architecture"]),
        ("cpu_detail", ["CPU详情"]),
        ("igpu", ["集成显卡", "gpu_integrated"]),
        ("dgpu", ["独立显卡", "gpu_dedicated"]),
        ("ram_type", ["内存类型", "ram_type"]),
        ("ram_max", ["最大内存", "内存容量", "ram_max"]),
        ("storage", ["存储接口", "storage"]),
        ("storage_capacity", ["存储容量"]),
        ("ports", ["接口", "主要接口", "ports"]),
        ("wireless", ["WiFi", "无线", "wireless", "Wi-Fi"]),
        ("wwan", ["WWAN"]),
        ("fingerprint", ["指纹", "指纹识别", "fingerprint"]),
        ("camera", ["摄像头", "camera"]),
        ("battery_life", ["官方续航", "官方标称续航(小时)", "battery"]),
        ("bios", ["BIOS", "BIOS型号"]),
        ("audio", ["音频"]),
        ("dimensions", ["尺寸"]),
        ("weight", ["重量", "weight"]),
        ("materials", ["机身材料"]),
        ("security", ["安全"]),
        ("upgradeability", ["可升级性"]),
        ("special_features", ["特殊属性"]),
        ("isv_certified", ["isv_certified"]),
    ]
    fields = {}
    for ok, sks in field_map:
        for sk in sks:
            if sk in spec and spec[sk] is not None:
                v = spec[sk]
                if isinstance(v, list):
                    v = "; ".join(str(x) for x in v)
                fields[ok] = str(v) if not isinstance(v, str) else v
                break
    for ck in ["数据可信度", "data_reliability"]:
        if ck in spec:
            fields["spec_credibility"] = spec[ck]
            break
    for uk in ["来源URL", "数据来源URL", "source_urls"]:
        if uk in spec:
            vu = spec[uk]
            fields["spec_source_url"] = "; ".join(vu) if isinstance(vu, list) else str(vu)
            break
    for dk in ["更新日期", "data_collection_date"]:
        if dk in spec:
            fields["spec_update_date"] = spec[dk]
            break
    return fields


# ─── Scoring ────────────────────────────────────────────────────────────────


def compute_linux_score(u, f, a, c):
    bd = {}
    t = 0
    # Ubuntu
    if u:
        if u.get("ubuntu_certified") is True:   bd["ubuntu"] = "certified (+2)"; t += 2
        elif u.get("ubuntu_certified") is False: bd["ubuntu"] = "not_certified (+0)"; t += 0
        else:                                    bd["ubuntu"] = "unconfirmed (+1)"; t += 1
    else:
        bd["ubuntu"] = "no_data (+1)"; t += 1
    # Fedora
    if f:
        c0 = f.get("compatibility", "unknown").lower()
        if c0 in ("ships_fedora", "certified", "friendly"): bd["fedora"] = f"{c0} (+2)"; t += 2
        elif c0 in ("community_good",):                     bd["fedora"] = "community_good (+1)"; t += 1
        elif c0 in ("community_warning",):                  bd["fedora"] = "community_warning (+0)"; t += 0
        else:                                                bd["fedora"] = "unknown (+1)"; t += 1
    else:
        bd["fedora"] = "no_data (+1)"; t += 1
    # Arch
    if a:
        a0 = a.get("overall_compat", "").lower()
        if a0 in ("excellent", "good"):    bd["arch"] = f"{a0} (+2)"; t += 2
        elif a0 in ("fair", "ok"):         bd["arch"] = f"{a0} (+1)"; t += 1
        elif a0 in ("poor", "problematic"): bd["arch"] = f"{a0} (+0)"; t += 0
        else:                               bd["arch"] = "unknown (+1)"; t += 1
    else:
        bd["arch"] = "no_data (+1)"; t += 1
    # Community
    if c:
        r0 = str(c.get("overall_rating", "")).lower()
        if any(w in r0 for w in ["优秀", "excellent", "4.5", "5/5"]):
            bd["community"] = "positive (+2)"; t += 2
        elif any(w in r0 for w in ["良好", "good", "推荐", "4.3", "4.4", "4/5", "3.8"]):
            bd["community"] = "good (+2)"; t += 2
        elif any(w in r0 for w in ["一般", "mixed", "3.3", "3.5", "3.7", "3/5"]):
            bd["community"] = "mixed (+1)"; t += 1
        elif any(w in r0 for w in ["差", "poor", "1/5", "2/5"]):
            bd["community"] = "poor (+0)"; t += 0
        else:
            bd["community"] = "assessment_needed (+1)"; t += 1
    else:
        bd["community"] = "no_data (+1)"; t += 1

    if t <= 2:     stars = "★☆☆☆☆"
    elif t <= 4:   stars = "★★☆☆☆"
    elif t <= 6:   stars = "★★★☆☆"
    elif t <= 8:   stars = "★★★★☆"
    else:          stars = "★★★★★"
    return t, stars, bd


def compute_credibility(s, u, f, a, p):
    oscore = 0.0
    if s and "官方" in str(s.get("spec_credibility", "")):
        oscore += 1
    if u and u.get("ubuntu_certified") is not None:
        oscore += 0.5
    if f and f.get("compatibility") not in (None, "unknown", ""):
        oscore += 0.5
    if a and a.get("overall_compat"):
        oscore += 0.5
    if p and "可靠" in str(p.get("data_quality", "")):
        oscore += 0.5
    if oscore >= 3:    return "高 (>=3个官方/权威来源)"
    elif oscore >= 2:  return "中高 (2个官方/权威来源)"
    elif oscore >= 1:  return "中 (1个官方来源)"
    else:              return "低 (无官方来源)"


# ─── Merge ──────────────────────────────────────────────────────────────────


def merge_all():
    print("=" * 60)
    print("ThinkPad 数据清洗与合并 (Task 19)")
    print("=" * 60)

    print("\n[1/6] 读取型号清单...")
    master = read_master_models()
    print(f"  主清单: {len(master)} 个型号")

    print("\n[2/6] 读取硬件参数...")
    sr = read_specs_registry()
    print(f"  参数记录: {len(sr)} 个型号")

    print("\n[3/6] 读取兼容性数据...")
    ur = read_ubuntu_registry()
    fr = read_fedora_registry()
    ar = read_arch_registry()
    cr = read_community_registry()
    print(f"  Ubuntu: {len(ur)}  Fedora: {len(fr)}  Arch: {len(ar)}  社区: {len(cr)}系列")

    print("\n[4/6] 读取价格数据...")
    pr = read_prices_registry()
    print(f"  价格: {len(pr)} 个型号")

    print("\n[5/6] 合并数据...")
    merged = []
    st = {"s": 0, "u": 0, "f": 0, "a": 0, "c": 0, "p": 0, "n": len(master)}

    # Count how many times each model name appears
    name_counts = {}
    for me in master:
        n0 = normalize(me["model"])
        name_counts[n0] = name_counts.get(n0, 0) + 1

    for me in master:
        m_name = me["model"]
        s = lookup(me, sr)
        u = lookup(me, ur)
        f = lookup(me, fr)
        a = lookup(me, ar, normalize_arch_name)
        p = lookup(me, pr, normalize_price_key)
        gk = series_group(m_name, me.get("series", ""))
        c = cr.get(gk)

        if s: st["s"] += 1
        if u: st["u"] += 1
        if f: st["f"] += 1
        if a: st["a"] += 1
        if c: st["c"] += 1
        if p: st["p"] += 1

        sf = extract_spec_fields(s) if s else {}
        raw_score, stars, bd = compute_linux_score(u, f, a, c)
        cred = compute_credibility(s, u, f, a, p)

        rec = OrderedDict()
        rec["model"] = m_name
        # If duplicate model names exist, append year suffix for uniqueness
        if name_counts.get(normalize(m_name), 0) > 1 and me.get("year"):
            rec["model"] = f"{m_name} ({me['year']})"
        rec["series"] = me.get("series", "N/A")
        rec["year"] = me.get("year", "N/A")
        rec["generation"] = me.get("generation", "N/A")

        sd = (me.get("screen_sizes", ["N/A"]) or ["N/A"])[0]
        rec["screen_size"] = sf.get("screen_size", sd)
        rec["resolution"] = sf.get("resolution", "N/A")
        rec["refresh_rate"] = sf.get("refresh_rate", "N/A")
        rec["touch_screen"] = sf.get("touch_screen", "N/A")
        rec["cpu"] = sf.get("cpu", "N/A")
        rec["cpu_architecture"] = sf.get("cpu_architecture", "N/A")
        rec["igpu"] = sf.get("igpu", "N/A")
        rec["dgpu"] = sf.get("dgpu", "N/A")
        rec["ram_type"] = sf.get("ram_type", "N/A")
        rec["ram_max"] = sf.get("ram_max", "N/A")
        rec["storage"] = sf.get("storage", "N/A")
        rec["ports"] = sf.get("ports", "N/A")
        rec["wireless"] = sf.get("wireless", "N/A")
        rec["fingerprint"] = sf.get("fingerprint", "N/A")
        rec["camera"] = sf.get("camera", "N/A")
        rec["battery_life_official"] = sf.get("battery_life", "N/A")
        rec["weight"] = sf.get("weight", "N/A")

        rec["ubuntu_certified"] = u.get("ubuntu_certified", "N/A") if u else "N/A"
        rec["ubuntu_cert_status"] = u.get("certification_status", "N/A") if u else "N/A"
        rec["ubuntu_versions"] = u.get("ubuntu_versions", []) if u else []
        rec["ubuntu_source"] = u.get("sources", []) if u else []

        rec["fedora_compatibility"] = f.get("compatibility", "N/A") if f else "N/A"
        rec["fedora_versions"] = f.get("fedora_versions", []) if f else []
        rec["fedora_notes"] = f.get("notes", "N/A") if f else "N/A"
        rec["fedora_known_issues"] = f.get("known_issues", []) if f else []

        rec["arch_compatibility"] = a.get("overall_compat", "N/A") if a else "N/A"
        rec["arch_known_issues"] = a.get("known_issues", []) if a else []
        rec["arch_wiki_page"] = a.get("arch_wiki_page", "N/A") if a else "N/A"

        rec["community_rating"] = c.get("overall_rating", "N/A") if c else "N/A"
        rec["community_positive_feedback"] = (
            c.get("positive_feedback", [])[:3] if c and isinstance(c.get("positive_feedback"), list) else [])
        rec["community_negative_feedback"] = (
            c.get("negative_feedback", [])[:3] if c and isinstance(c.get("negative_feedback"), list) else [])

        if p:
            rec["price_range_cny"] = p.get("price_range_cny", "N/A")
            rec["price_typical_config"] = p.get("typical_config", "N/A")
            rec["price_condition"] = p.get("condition_range", "N/A")
            rec["price_data_quality"] = p.get("data_quality", "N/A")
        else:
            for k0 in ("price_range_cny", "price_typical_config", "price_condition", "price_data_quality"):
                rec[k0] = "N/A"

        rec["linux_compat_score_raw"] = raw_score
        rec["linux_compat_rating"] = stars
        rec["linux_compat_breakdown"] = bd
        rec["data_credibility"] = cred
        rec["data_source_urls"] = sf.get("spec_source_url", "N/A")
        rec["data_update_date"] = sf.get("spec_update_date", "2026-06-08")
        rec["merge_timestamp"] = "2026-06-08T00:00:00Z"
        merged.append(rec)

    print(f"\n  匹配统计:")
    print(f"    硬件参数: {st['s']}/{st['n']}")
    print(f"    Ubuntu:   {st['u']}/{st['n']}")
    print(f"    Fedora:   {st['f']}/{st['n']}")
    print(f"    Arch:     {st['a']}/{st['n']}")
    print(f"    社区反馈: {st['c']}/{st['n']}")
    print(f"    价格:     {st['p']}/{st['n']}")
    print(f"  合并完成: {len(merged)} 条记录")
    return merged, st


# ─── Validation ─────────────────────────────────────────────────────────────


def validate(merged, st):
    errs = []
    warns = []
    n = len(merged)
    if n != 162:
        errs.append(f"行数不匹配: 期望162, 实际{n}")
    for i, rec in enumerate(merged):
        if rec.get("model", "") in ("N/A", ""):
            errs.append(f"记录 #{i}: model 缺失")
    all_keys = set()
    for rec in merged:
        all_keys.update(rec.keys())
    fully_missing = [k for k in sorted(all_keys)
                     if all(r.get(k) in ("N/A", []) for r in merged)]
    if fully_missing:
        warns.append(f"全N/A字段: {', '.join(fully_missing)}")
    sd = {}
    for r in merged:
        s = r.get("linux_compat_rating", "N/A")
        sd[s] = sd.get(s, 0) + 1
    print(f"  评分分布: {dict(sorted(sd.items()))}")
    cd = {}
    for r in merged:
        c0 = r.get("data_credibility", "N/A")
        cd[c0] = cd.get(c0, 0) + 1
    print(f"  可信度分布: {cd}")
    names = [r["model"] for r in merged]
    dups = [m for m in set(names) if names.count(m) > 1]
    if dups:
        errs.append(f"重复型号: {dups}")
    return {"total": n, "expected": 162, "errors": errs, "warnings": warns,
            "fully_missing": fully_missing, "score_dist": sd, "cred_dist": cd, "stats": st}


# ─── Main ───────────────────────────────────────────────────────────────────


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    merged, st = merge_all()
    print("\n[6/6] 验证...")
    val = validate(merged, st)
    for e in val["errors"]:
        print(f"  ERROR: {e}")
    for w in val["warnings"]:
        print(f"  WARNING: {w}")

    op = OUT_DIR / "merged_data.json"
    out = {
        "meta": {
            "description": "ThinkPad型号综合数据集 (2019-2025)",
            "total_models": len(merged),
            "merge_date": "2026-06-08",
            "data_sources": [
                "Lenovo PSREF (官方参数)", "Ubuntu Certification",
                "Fedora HCL", "Arch Wiki",
                "社区反馈 (Reddit/V2EX/知乎等)",
                "中国二手市场 (专门网/ibmbjb/京东等)"
            ],
            "validation": {
                "errors": val["errors"], "warnings": val["warnings"],
                "score_distribution": {str(k): v for k, v in val["score_dist"].items()},
                "credibility_distribution": val["cred_dist"],
            }
        },
        "models": merged
    }
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 已保存: {op}")
    print(f"  文件大小: {op.stat().st_size:,} bytes")

    ep = EVIDENCE_DIR / "task-19-merge.txt"
    with open(ep, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("Task 19: 数据清洗与合并 - 验证报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"合并时间: 2026-06-08\n")
        f.write(f"总记录数: {val['total']}\n")
        f.write(f"期望记录数: {val['expected']}\n")
        f.write(f"记录数匹配: {'✓ 通过' if val['total'] == 162 else '✗ 失败'}\n\n")
        f.write("--- 匹配统计 ---\n")
        f.write(f"硬件参数: {st['s']}/{st['n']}\n")
        f.write(f"Ubuntu认证: {st['u']}/{st['n']}\n")
        f.write(f"Fedora兼容: {st['f']}/{st['n']}\n")
        f.write(f"Arch Wiki: {st['a']}/{st['n']}\n")
        f.write(f"社区反馈: {st['c']}/{st['n']}\n")
        f.write(f"价格数据: {st['p']}/{st['n']}\n\n")
        f.write("--- 评分分布 ---\n")
        for stars, cnt in sorted(val["score_dist"].items()):
            f.write(f"  {stars}: {cnt}\n")
        f.write("\n--- 可信度分布 ---\n")
        for cred, cnt in val["cred_dist"].items():
            f.write(f"  {cred}: {cnt}\n")
        f.write("\n--- 完全缺失列 ---\n")
        if val["fully_missing"]:
            for col in val["fully_missing"]:
                f.write(f"  - {col}\n")
        else:
            f.write("  无\n")
        f.write(f"\n--- 输出 ---\n{op.resolve()}\n")
    print(f"✓ 验证报告已保存: {ep}")
    return 0 if not val["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
