# ThinkPad 调研数据集 (2019-2025)

系统整理 2019-2025 年 ThinkPad 全系列（含 7 款中国市场特供机型）的硬件规格、Linux 发行版兼容性与中国二手市场参考价格，供选购 ThinkPad（尤其是 Linux 开发环境与二手选购）的用户和开发者查阅与筛选。

> English summary: A structured dataset and Python processing pipeline covering 169 ThinkPad models (2019-2025, plus 7 China-exclusive models including 1 announced 2026 model) across 44 fields, including hardware specs, Ubuntu/Fedora/Arch Linux compatibility, community feedback, and China used-market price references.

## 数据概览

数据快照日期：2026-06-08，主交付文件为 `thinkpad_complete_research.xlsx`（44 列 × 169 行）及结构化数据 `data/processed/merged_data.json`。

| 指标 | 数值 |
|------|------|
| 覆盖型号总数 | 169（162 款全球型号 + 7 款中国市场特供型号） |
| 发布年份范围 | 2019-2025（含 1 款 2026 年中国特供预告机型 X14 Gen 1） |
| 数据字段数 | 44 列（2 个工作表：`ThinkPad调研数据`、`数据说明`） |
| Ubuntu 官方认证 | 138 是 / 31 否 |
| Linux 兼容性评分分布 | 4 星 81 款 (47.9%) / 3 星 68 款 (40.2%) / 2 星 20 款 (11.8%) |
| 二手价格覆盖 | 135 / 169 (79.9%) |
| 数据来源 URL 覆盖 | 141 / 169 (83.4%) |

按系列分布：X/X1 系列 48 款、P 系列 39 款、T 系列 31 款、L 系列 26 款、E 系列 21 款、Z 系列 4 款。

### 主要字段分类（44 列）

- **基础信息**：型号、系列、发布年份、代际
- **显示与计算**：尺寸(英寸)、分辨率、刷新率(Hz)、触摸屏、CPU 型号、CPU 架构、集成显卡、独立显卡
- **内存与存储**：内存类型、最大内存、存储接口
- **连接与外设**：接口、无线、指纹识别、摄像头、官方标称续航(h)、重量
- **Linux 兼容性**：Ubuntu 认证/版本/来源、Fedora 兼容性/版本/说明/已知问题、Arch 兼容性/已知问题/Wiki 页面、Linux 兼容性原始分数/星级评分/评分细分
- **社区与价格**：社区评分、社区正面反馈、社区负面反馈、二手价格区间(CNY)、典型配置、成色、价格数据质量
- **元数据**：数据可信度、数据来源 URL、数据更新日期

部分二手价格参考样例（2026-06-08 社区参考区间，非实时行情）：
- ThinkPad T490：`1100-1700` 元
- X1 Carbon Gen 10：`3000-5500` 元
- ThinkPad P1 Gen 6：`10000-16000` 元

## 使用方式

### 直接查阅数据

- 用 Excel / LibreOffice 打开 `thinkpad_complete_research.xlsx`，通过首行自动筛选按系列、年份、Ubuntu 认证或 Linux 评分筛选，字段定义与评分标准见“数据说明”工作表。
- 程序化读取可直接解析 `data/processed/merged_data.json`。

### 本地复现 Excel 生成与校验

环境要求：Python 3，依赖见 `requirements.txt`（`pandas`、`openpyxl`、`requests`、`beautifulsoup4`、`lxml`）。

```bash
pip install -r requirements.txt

# 基于 data/processed/merged_data.json 重新生成 thinkpad_complete_research.xlsx
python3 scripts/generate_final_excel.py

# 校验生成的 Excel 结构、44 列完整性、条件格式、冻结窗格与无宏状态
python3 scripts/validate_excel_final.py

# 可选：生成 29 列空白模板 thinkpad_template.xlsx
python3 scripts/excel_template.py
```

## 项目结构与技术要点

```text
.
├── thinkpad_complete_research.xlsx         # 最终交付表格（169 行 × 44 列，含条件格式与数据说明）
├── thinkpad_template.xlsx                  # 初始 29 列空白字段模板
├── RESEARCH_SUMMARY.md                     # 调研交付总结
├── requirements.txt                        # Python 依赖清单
├── data/
│   ├── processed/merged_data.json          # 清洗合并后的完整数据集（169 款型号）
│   ├── raw/models_china_exclusive.json     # 7 款中国市场特供机型数据
│   └── scripts/merge_data.py               # 多源数据归一化合并与评分脚本
└── scripts/
    ├── data_collector.py                   # 采集基础设施（ProgressTracker、WebFetcher、校验与基类）
    ├── excel_template.py                   # 空白模板生成脚本
    ├── generate_final_excel.py             # 最终 Excel 渲染脚本
    ├── validate_excel_final.py             # Excel 结构与格式验证脚本
    ├── fix_t_series_merge.py               # T 系列官方参数补合并脚本
    ├── fix_feedback_format.py              # 社区反馈格式修复（中国特供机型）
    ├── fix_feedback_v2.py                  # 社区反馈 URL 与条目数统一脚本（v1.1.1）
    ├── fix_community_feedback_real_data.py # 基于真实来源重写社区反馈去重脚本（v1.2.0）
    ├── audit_integrity.py                  # 数据完整性审计脚本（初版）
    └── audit_integrity_v2.py               # 数据完整性审计脚本（名称匹配优化版）
```

关键工程实现：

- **采集框架（`scripts/data_collector.py`）**：封装 `ProgressTracker` 将各型号状态持久化到 JSON 以便断点续跑；封装 `WebFetcher` 统一处理超时、重试、User-Agent 与编码检测。
- **多源合并与评分（`data/scripts/merge_data.py`）**：对 PSREF、Ubuntu、Fedora、Arch Wiki、社区评价与二手价格进行型号名归一化与去代际回退匹配；按 Ubuntu/Fedora/Arch/社区四个维度（各 0-2 分）计算 Linux 兼容性原始分、星级与来源可信度。
- **跨平台 Excel 生成（`scripts/generate_final_excel.py`）**：基于 `openpyxl` 生成双工作表文件，配置 19 条 `CellIsRule` 条件格式（Linux 评分、Ubuntu 认证、Fedora 兼容性、数据可信度）、三档列宽自适应、首行冻结与自动筛选，不使用 VBA 宏，兼容 Windows/macOS/Linux。
- **社区反馈去重与溯源（`scripts/fix_community_feedback_real_data.py`）**：针对 v1.2.0 将 169 款型号的 1014 条正/负面反馈替换为型号专属内容，并通过词边界正则检查避免跨型号误引用。

## 验证

本仓库未配置 CI 或单元测试套件，数据交付物通过 `scripts/validate_excel_final.py` 进行 7 项自动化校验（文件可读性、字段完整性、数据说明工作表、条件格式、冻结首行、自动筛选、无 VBA 宏）。

运行命令：

```bash
python3 scripts/validate_excel_final.py
```

当前对 `thinkpad_complete_research.xlsx` 的实测结果：

```text
Fields [44/44] | Format [PASS] | Functionality [PASS] | VERDICT: APPROVE
```

## 当前状态与已知限制

- **静态快照**：数据采集于 2026-06-08，价格区间和 Linux 认证状态不随时间自动更新。
- **部分字段缺失**：重量字段 129/169 (76.3%) 缺失（仅 P 系列相对完整）；独立显卡列中 60 款为“无”、30 款为 `N/A`（反映轻薄本无独显或未采集）；34 款型号缺少二手价格（主要为 2024-2025 新款）。
- **已知数据条目瑕疵**：`X13 Gen 5 (AMD)` 在实际产品线中不存在（Gen 5 仅 Intel），其硬件参数为 `N/A`；`ThinkPad P16 Gen 3` 存在 2024/2025 两条记录尚未合并。
- **评分上限设定**：`data/scripts/merge_data.py` 中 4 个评分维度每项最高 2 分（满分 8 分），而星级映射将 `> 8` 定义为 5 星，导致当前数据集中无 5 星型号（最高为 4 星，原始分 8 分共 15 款）。
- **原始中间文件未全量入库**：`.gitignore` 排除了 `data/raw/` 下除 `models_china_exclusive.json` 外的原始中间 JSON，因此依赖全量原始文件的 `data/scripts/merge_data.py`、`scripts/fix_t_series_merge.py` 与 `scripts/audit_integrity*.py` 无法直接基于当前仓库从零重跑；基于 `data/processed/merged_data.json` 重新生成和校验 Excel 可直接复现。

## 数据来源

- [Lenovo PSREF](https://psref.lenovo.com/) — 官方硬件规格
- [Ubuntu Certified](https://ubuntu.com/certified) — Ubuntu 硬件认证状态
- [Fedora Discussion](https://discussion.fedoraproject.org/) / [Lenovo Linux Support](https://support.lenovo.com/solutions/pd031426) — Fedora 与官方 Linux 支持信息
- [Arch Wiki (Laptop/Lenovo)](https://wiki.archlinux.org/title/Laptop/Lenovo) — Arch Linux 兼容性与已知问题
- Reddit r/thinkpad、r/linuxonthinkpad、V2EX、知乎 — 社区反馈
- 专门网论坛、ibmbjb.com、Lenovo China / 电商平台 — 二手价格与中国市场特供机型信息

## License & Contact

- License: MIT License，详见 [LICENSE](LICENSE)。
- Contact: me@neryc.net
