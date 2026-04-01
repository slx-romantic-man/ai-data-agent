"""
F-25 快速验证 - 直接测试分析模板输出
不依赖完整Agent流程，直接测试Analyzer模块
"""
from app.agent.core.data_analyzer import DataAnalyzer
from app.config.llm_config import get_llm
import asyncio
import sys

# 设置stdout编码为utf-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def safe_print(text: str):
    """安全打印"""
    safe_text = text.encode('ascii', errors='ignore').decode('ascii')
    print(safe_text)


async def test_weather_analysis():
    """测试天气数据分析"""
    print("\n========================================")
    print("测试1: 天气数据分析")
    print("========================================")

    weather_data = [
        {
            "location": "上海",
            "temp_c": 21.1,
            "condition": "Patchy rain nearby",
            "humidity": 78,
            "wind_kph": 18.0,
            "last_updated": "2026-03-30 17:15"
        }
    ]

    analyzer = DataAnalyzer()
    result = await analyzer.analyze(
        data=weather_data,
        user_query="上海今天天气怎么样",
        analysis_type="summary"
    )

    analysis_text = result["analysis"]
    print(f"\n分析结果长度: {len(analysis_text)} 字符")
    safe_print(f"\n分析结果预览（前500字符）:")
    safe_print(analysis_text[:500])

    # 验证通用模板结构
    has_data_overview = "数据概览" in analysis_text
    has_core_metrics = "核心指标" in analysis_text
    has_findings = "主要发现" in analysis_text

    # 验证不包含金融术语
    has_financial_terms = any(term in analysis_text for term in ["开盘价", "收盘价", "涨跌幅", "成交量"])

    print(f"\n模板验证:")
    print(f"  数据概览: {'✓' if has_data_overview else '✗'}")
    print(f"  核心指标: {'✓' if has_core_metrics else '✗'}")
    print(f"  主要发现: {'✓' if has_findings else '✗'}")
    print(f"  无金融术语: {'✓' if not has_financial_terms else '✗'}")

    passed = has_data_overview and has_core_metrics and has_findings and not has_financial_terms
    print(f"\n结果: {'PASS' if passed else 'FAIL'}")
    return passed


async def test_stock_analysis():
    """测试股票数据分析"""
    print("\n========================================")
    print("测试2: 股票数据分析")
    print("========================================")

    stock_data = [
        {
            "date": "2026-03-29",
            "symbol": "AAPL",
            "open": 189.50,
            "close": 190.32,
            "high": 191.20,
            "low": 188.90,
            "volume": 50000000
        }
    ]

    analyzer = DataAnalyzer()
    result = await analyzer.analyze(
        data=stock_data,
        user_query="查询AAPL股票最近的价格",
        analysis_type="summary"
    )

    analysis_text = result["analysis"]
    print(f"\n分析结果长度: {len(analysis_text)} 字符")
    safe_print(f"\n分析结果预览（前500字符）:")
    safe_print(analysis_text[:500])

    # 验证通用模板结构
    has_data_overview = "数据概览" in analysis_text
    has_core_metrics = "核心指标" in analysis_text
    has_findings = "主要发现" in analysis_text

    # 对于股票数据，可以有金融术语（自然适配）
    print(f"\n模板验证:")
    print(f"  数据概览: {'✓' if has_data_overview else '✗'}")
    print(f"  核心指标: {'✓' if has_core_metrics else '✗'}")
    print(f"  主要发现: {'✓' if has_findings else '✗'}")
    print(f"  自然适配股票数据: {'✓' if ('价格' in analysis_text or '股价' in analysis_text) else '✗'}")

    passed = has_data_overview and has_core_metrics and has_findings
    print(f"\n结果: {'PASS' if passed else 'FAIL'}")
    return passed


async def test_ip_analysis():
    """测试IP定位数据分析"""
    print("\n========================================")
    print("测试3: IP定位数据分析")
    print("========================================")

    ip_data = [
        {
            "ip": "8.8.8.8",
            "country": "United States",
            "region": "California",
            "city": "Mountain View",
            "isp": "Google LLC",
            "lat": 37.386,
            "lon": -122.0838
        }
    ]

    analyzer = DataAnalyzer()
    result = await analyzer.analyze(
        data=ip_data,
        user_query="查询IP 8.8.8.8的位置",
        analysis_type="summary"
    )

    analysis_text = result["analysis"]
    print(f"\n分析结果长度: {len(analysis_text)} 字符")
    safe_print(f"\n分析结果预览（前500字符）:")
    safe_print(analysis_text[:500])

    # 验证通用模板结构
    has_data_overview = "数据概览" in analysis_text
    has_core_metrics = "核心指标" in analysis_text
    has_findings = "主要发现" in analysis_text

    # 验证不包含金融术语
    has_financial_terms = any(term in analysis_text for term in ["开盘价", "收盘价", "涨跌幅", "成交量"])

    print(f"\n模板验证:")
    print(f"  数据概览: {'✓' if has_data_overview else '✗'}")
    print(f"  核心指标: {'✓' if has_core_metrics else '✗'}")
    print(f"  主要发现: {'✓' if has_findings else '✗'}")
    print(f"  无金融术语: {'✓' if not has_financial_terms else '✗'}")
    print(f"  自然适配地理数据: {'✓' if ('地理位置' in analysis_text or '坐标' in analysis_text or '位置' in analysis_text) else '✗'}")

    passed = has_data_overview and has_core_metrics and has_findings and not has_financial_terms
    print(f"\n结果: {'PASS' if passed else 'FAIL'}")
    return passed


async def main():
    """运行所有验证测试"""
    print("========================================")
    print("F-25 通用分析模板快速验证")
    print("========================================")

    results = []

    # 测试天气数据分析
    results.append(("天气API", await test_weather_analysis()))

    # 测试股票数据分析
    results.append(("股票API", await test_stock_analysis()))

    # 测试IP数据分析
    results.append(("IP定位API", await test_ip_analysis()))

    # 输出总结
    print("\n========================================")
    print("测试总结")
    print("========================================")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"[{status}] {name}")

    print(f"\n通过率: {passed}/{total} ({100*passed/total:.1f}%)")

    if passed == total:
        print("\n✅ F-25验收通过：通用模板成功适配所有API类型")
        return 0
    else:
        print("\n❌ F-25验收失败：部分验证未通过")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)