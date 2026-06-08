# ThinkPad 深度调研 (2019-2025)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 系统性收集 ThinkPad 2019-2025 全系列型号的详细硬件参数、Ubuntu 认证状态、Linux 兼容性评价及中国二手市场价格。

## 📊 数据概览

- **覆盖型号**: 162 个 ThinkPad 型号
- **时间范围**: 2019 - 2025
- **数据字段**: 44 个维度（屏幕/CPU/内存/存储/显卡/接口/指纹/摄像头/续航/BIOS/价格/Ubuntu认证/Linux评分等）
- **数据来源**: Lenovo PSREF、Ubuntu 认证中心、Fedora HCL、Arch Wiki、社区反馈、中国二手市场

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `thinkpad_complete_research.xlsx` | 主数据文件（162行×44列，含条件格式） |
| `RESEARCH_SUMMARY.md` | 项目总结与使用说明 |
| `scripts/` | 数据收集与处理脚本 |
| `requirements.txt` | Python 依赖 |

## 🐧 Linux 兼容性亮点

- **最佳兼容性**: X1 Carbon Gen 12/13、T14/T14s Gen 5（4.5/5星）
- **性价比推荐**: T14/T14s AMD 系列（4.3-4.4/5星）
- **常见问题**: 指纹识别(fprintd)、休眠唤醒、NVIDIA 混合显卡
- **社区共识**: AMD > Intel（Linux 兼容性）、选较成熟型号

## 💰 二手价格参考

- T490: 1199-1689 元
- X1 Carbon Gen 10: 3400-5200 元
- P1 Gen 6: 15300 元（高端工作站）

> 价格为社区参考区间，非实时市场数据。采集日期：2026-06-08

## 📈 数据统计

| 指标 | 数值 |
|------|------|
| 型号总数 | 162 |
| Ubuntu 认证 | 138 是 / 24 否 |
| Linux 4星+ | 80 个型号 (49.4%) |
| Linux 3星 | 62 个型号 (38.3%) |
| 二手价格覆盖 | 128/162 (79%) |

## 🚀 使用方式

1. 下载 `thinkpad_complete_research.xlsx`
2. 使用 Excel/LibreOffice 打开
3. 利用筛选功能按系列、年份、Linux 评分等维度筛选
4. 查看"数据说明"Sheet 了解字段定义

## 📝 字段示例

- **基础**: 系列、型号、发布年份、代际
- **屏幕**: 尺寸、分辨率、刷新率、触摸屏
- **CPU**: 型号、架构（Intel/AMD/Qualcomm）
- **内存/存储**: 类型、最大容量、接口
- **显卡**: 集成显卡、独立显卡
- **连接**: USB/Thunderbolt/HDMI/RJ45、WiFi 标准
- **生物识别**: 指纹、摄像头（分辨率/IR/物理遮挡）
- **电池**: 官方标称续航、实测续航
- **固件**: BIOS 型号、可升级性
- **价格**: 二手价格区间（人民币）
- **Linux**: Ubuntu 认证、兼容性评分（1-5星）、已知问题
- **元数据**: 数据可信度、数据来源 URL、更新日期

## ⚠️ 已知限制

1. 重量字段 75% 缺失（仅 P 系列完整）
2. 独立显卡 52% 为 N/A（轻薄本 iGPU-only 的真实情况）
3. 2024-2025 新型号二手价格数据较少
4. 数据为一次性快照，非实时更新

## 📚 数据来源

- [Lenovo PSREF](https://psref.lenovo.com/) — 官方规格
- [Ubuntu Certified](https://certification.ubuntu.com/) — 认证状态
- [Fedora HCL](https://docs.fedoraproject.org/) — Fedora 兼容性
- [Arch Wiki](https://wiki.archlinux.org/) — Arch Linux 兼容性
- Reddit r/thinkpad、V2EX、知乎 — 社区反馈
- 专门网论坛、ibmbjb.com — 二手价格

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)

## 🤝 贡献

欢迎提交 Issue 或 PR 补充数据、修正错误。

---

*数据更新日期: 2026-06-08*
