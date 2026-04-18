"""Step 2 自动化测试脚本

运行方式:
    python tests/run_step2.py

依赖:
    - demo.py 中的 get_tenant_token, fetch_doc_raw, ask 函数
    - tests/step2_test_cases.json 测试用例
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from demo import get_tenant_token, fetch_doc_raw, ask

DOC_ID = os.getenv("FEISHU_DOC_ID")
TEST_CASES_PATH = Path(__file__).parent / "step2_test_cases.json"
PASS_RATE_THRESHOLD = 0.7  # 70% 通过率门槛


def load_test_cases():
    with open(TEST_CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


def run_single_test(case, doc_content):
    question = case["question"]
    expected = case.get("expected_contains", [])

    answer = ask(doc_content, question)

    if case["type"] == "合规测试":
        # 合规测试:期望拒绝或提到相关内容
        passed = any(kw in answer for kw in expected) or "没有" in answer or "无法" in answer
    elif case["type"] == "边界测试":
        # 边界测试:期望说"没有"或"不知道"
        passed = any(kw in answer for kw in ["没有", "没有提到", "不确定", "不知道"])
    else:
        # 普通测试:期望包含关键词
        if not expected:
            passed = len(answer) > 10  # 开放式问题只要有回答即可
        else:
            passed = all(kw in answer for kw in expected)

    return {
        "id": case["id"],
        "question": question,
        "expected": expected,
        "answer": answer,
        "passed": passed,
        "type": case["type"],
        "difficulty": case["difficulty"],
    }


def run_tests():
    print("=" * 60)
    print("Step 2 自动化测试")
    print("=" * 60)

    # 加载测试用例
    cases = load_test_cases()
    print(f"加载 {len(cases)} 条测试用例\n")

    # 获取文档内容
    print("正在获取飞书文档...")
    token = get_tenant_token()
    doc_content = fetch_doc_raw(DOC_ID, token)
    print(f"文档长度: {len(doc_content)} 字\n")

    # 执行测试
    results = []
    for case in cases:
        result = run_single_test(case, doc_content)
        results.append(result)

        status_icon = "✓" if result["passed"] else "✗"
        print(f"{status_icon} Test {result['id']}: {result['question'][:40]}")

        if not result["passed"]:
            print(f"    期望包含: {result['expected']}")
            print(f"    回答: {result['answer'][:100]}...")

    # 统计结果
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    pass_rate = passed / total

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} ({pass_rate:.0%})")

    # 按类型统计
    type_stats = {}
    for r in results:
        t = r["type"]
        if t not in type_stats:
            type_stats[t] = {"total": 0, "passed": 0}
        type_stats[t]["total"] += 1
        if r["passed"]:
            type_stats[t]["passed"] += 1

    print("\n按类型统计:")
    for t, stats in type_stats.items():
        rate = stats["passed"] / stats["total"]
        print(f"  {t}: {stats['passed']}/{stats['total']} ({rate:.0%})")

    # 保存详细报告
    report = {
        "total": total,
        "passed": passed,
        "pass_rate": pass_rate,
        "threshold": PASS_RATE_THRESHOLD,
        "passed_flag": pass_rate >= PASS_RATE_THRESHOLD,
        "results": results,
        "type_stats": type_stats,
    }

    report_path = Path(__file__).parent / "step2_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存: {report_path}")

    # 断言通过率
    if pass_rate < PASS_RATE_THRESHOLD:
        print(f"\n❌ 通过率 {pass_rate:.0%} 低于门槛 {PASS_RATE_THRESHOLD:.0%}")
        sys.exit(1)
    else:
        print(f"\n✅ 通过率达标!")

    return report


if __name__ == "__main__":
    run_tests()
