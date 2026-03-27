"""
F-07 验证脚本：增强Analyzer的金融分析边界控制
验证分析报告包含必需的结构化部分
"""
import asyncio
import sys
import os
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.agent.core.data_analyzer import DataAnalyzer


async def test_f07_financial_analysis_boundary():
    """测试金融分析边界控制"""
    print("\n" + "="*60)
    print("F-07 验证：金融分析边界控制")
    print("="*60)

    # 模拟股票数据
    stock_data = [
        {"date": "2024-03-20", "open": 170.5, "high": 172.3, "low": 169.8, "close": 171.2, "volume": 50000000, "pct_change": 0.41},
        {"date": "2024-03-21", "open": 171.5, "high": 173.1, "low": 170.9, "close": 172.8, "volume": 52000000, "pct_change": 0.93},
        {"date": "2024-03-22", "open": 172.9, "high": 174.5, "low": 172.1, "close": 173.6, "volume": 48000000, "pct_change": 0.46},
        {"date": "2024-03-25", "open": 173.8, "high": 175.2, "low": 173.0, "close": 174.9, "volume": 51000000, "pct_change": 0.75},
        {"date": "2024-03-26", "open": 175.0, "high": 176.8, "low": 174.5, "close": 176.2, "volume": 53000000, "pct_change": 0.74},
    ]

    analyzer = DataAnalyzer()

    print("\n[Step 1] 生成股票分析报告...")
    result = await analyzer.analyze(
        data=stock_data,
        user_query="分析苹果股票最近5个交易日的表现",
        analysis_type="summary"
    )

    analysis_report = result.get("analysis", "")
    print(f"✅ 报告生成成功，长度: {len(analysis_report)} 字符")

    print("\n[Step 2] 验证报告结构...")

    # 检查必需部分
    required_sections = {
        "事实总结": ["事实总结", "实际数据"],
        "可能原因": ["可能原因", "推测"],
        "风险提示": ["风险提示", "风险"],
        "非个性化建议": ["非个性化建议", "建议"]
    }

    all_passed = True
    for section_name, keywords in required_sections.items():
        found = any(keyword in analysis_report for keyword in keywords)
        if found:
            print(f"  ✅ 包含'{section_name}'部分")
        else:
            print(f"  ❌ 缺少'{section_name}'部分")
            all_passed = False

    print("\n[Step 3] 验证推测性内容标注...")
    speculation_markers = ["推测", "可能", "或许", "也许", "⚠️"]
    has_speculation_marker = any(marker in analysis_report for marker in speculation_markers)
    if has_speculation_marker:
        print("  ✅ 推测性内容已标注")
    else:
        print("  ❌ 推测性内容未明确标注")
        all_passed = False

    print("\n[Step 4] 验证风险提示...")
    risk_keywords = ["风险", "不确定", "波动", "谨慎"]
    has_risk_warning = any(keyword in analysis_report for keyword in risk_keywords)
    if has_risk_warning:
        print("  ✅ 包含风险提示")
    else:
        print("  ❌ 缺少风险提示")
        all_passed = False

    print("\n[Step 5] 验证免责声明...")
    disclaimer_keywords = ["不是", "非", "建议咨询", "专业"]
    has_disclaimer = any(keyword in analysis_report for keyword in disclaimer_keywords)
    if has_disclaimer:
        print("  ✅ 包含免责声明")
    else:
        print("  ❌ 缺少免责声明")
        all_passed = False

    print("\n[Step 6] 验证无伪造事件...")
    fake_event_keywords = ["发布财报", "CEO宣布", "公司宣布", "官方声明"]
    has_fake_events = any(keyword in analysis_report for keyword in fake_event_keywords)
    if not has_fake_events:
        print("  ✅ 未伪造具体事件")
    else:
        print("  ⚠️  可能包含伪造事件，需人工复核")

    print("\n" + "="*60)
    print("完整分析报告：")
    print("="*60)
    print(analysis_report)
    print("="*60)

    if all_passed:
        print("\n✅ F-07 验证通过：分析报告结构符合要求")
        return True
    else:
        print("\n❌ F-07 验证失败：分析报告结构不完整")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_f07_financial_analysis_boundary())
    sys.exit(0 if result else 1)
