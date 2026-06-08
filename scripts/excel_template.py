#!/usr/bin/env python3
"""ThinkPad调研项目 - Excel模板生成脚本

生成包含所有字段定义的空Excel模板，用于后续数据填充。
"""

import pandas as pd
from pathlib import Path

# ── 字段定义 ──────────────────────────────────────────────
# 每个字段: (列名, 数据类型/约束说明, 示例值)
FIELDS = [
    # 基础信息
    ("系列", "文本", "ThinkPad X1 Carbon"),
    ("型号", "文本", "21HM000QCD"),
    ("发布年份", "整数", 2024),
    ("代际", "文本", "Gen 12"),
    # 屏幕
    ("尺寸(英寸)", "浮点数", 14.0),
    ("分辨率", "文本", "1920x1200"),
    ("刷新率(Hz)", "整数", 60),
    ("触摸屏", "是/否/选配", "否"),
    # CPU
    ("CPU型号", "文本", "Intel Core Ultra 7 165H"),
    ("CPU架构", "Intel/AMD", "Intel"),
    # 内存/存储
    ("内存类型", "DDR4/DDR5/LPDDR4x/LPDDR5x", "LPDDR5x"),
    ("存储接口", "NVMe/SATA", "NVMe"),
    # 显卡
    ("集成显卡", "文本", "Intel Arc Graphics"),
    ("独立显卡", "文本/无", "无"),
    # 连接
    ("接口", "文本(逗号分隔)", "USB-C, Thunderbolt 4, HDMI 2.1, RJ45"),
    ("无线", "文本", "WiFi 6E"),
    # 生物识别
    ("指纹", "是/否", "是"),
    ("摄像头", "720p/1080p/IR/物理遮挡", "1080p IR"),
    # 电池
    ("官方标称续航(小时)", "浮点数", 15.0),
    ("实测续航(小时)", "浮点数", 10.5),
    # 固件
    ("BIOS型号", "文本", "N3AET"),
    ("可升级性", "文本(内存/硬盘/网卡)", "硬盘"),
    # 价格
    ("二手价格区间(CNY)", "文本", "3000-5000"),
    # Linux
    ("Ubuntu认证", "是/否/未确认", "是"),
    ("Linux兼容性评分", "1-5星", 4),
    ("已知问题", "文本", "指纹识别需额外配置"),
    # 元数据
    ("数据可信度", "官方确认/社区共识/单一来源/推测", "官方确认"),
    ("数据来源URL", "文本(URL)", "https://psref.lenovo.com/"),
    ("数据更新日期", "日期(YYYY-MM-DD)", "2024-01-15"),
]


def build_template() -> pd.DataFrame:
    """构建空模板DataFrame，列名与字段定义一致。"""
    columns = [name for name, _, _ in FIELDS]
    # 空模板：无数据行，仅列头
    df = pd.DataFrame(columns=columns)
    return df


def add_data_validation_hints(df: pd.DataFrame) -> dict:
    """返回字段约束信息，供后续数据验证使用。"""
    constraints = {}
    for name, dtype, example in FIELDS:
        constraints[name] = {"dtype": dtype, "example": example}
    return constraints


def main():
    output_path = Path(__file__).resolve().parent.parent / "thinkpad_template.xlsx"

    df = build_template()
    constraints = add_data_validation_hints(df)

    # 写入Excel，首行为列头
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="ThinkPad调研")

        # 在第二个sheet写入字段定义参考
        ref_df = pd.DataFrame(
            [
                {"字段名": name, "数据类型": dtype, "示例值": example}
                for name, dtype, example in FIELDS
            ]
        )
        ref_df.to_excel(writer, index=False, sheet_name="字段定义")

    print(f"模板已生成: {output_path}")
    print(f"列数: {len(df.columns)}")
    print(f"字段列表: {list(df.columns)}")

    return output_path


if __name__ == "__main__":
    main()