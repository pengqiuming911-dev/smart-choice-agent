"""Step 9: Daily Metrics Dashboard Script

Usage:
    python tests/step9_metrics_dashboard.py              # Today's metrics
    python tests/step9_metrics_dashboard.py --date 2026-04-18  # Specific date
    python tests/step9_metrics_dashboard.py --days 7          # Last 7 days
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_service.models.db import get_cursor


def get_daily_metrics(date: str) -> dict:
    """Get metrics for a specific date"""
    with get_cursor() as cur:
        # Total conversations
        cur.execute("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT user_open_id) as unique_users
            FROM chat_logs
            WHERE DATE(created_at) = %s
        """, (date,))
        row = cur.fetchone()

        total_conversations = row[0] or 0
        unique_users = row[1] or 0

        # Blocked rate (compliance blocks)
        cur.execute("""
            SELECT COUNT(*) * 1.0 / NULLIF(%s, 0)
            FROM chat_logs
            WHERE DATE(created_at) = %s AND blocked = true
        """, (total_conversations, date))
        blocked_rate = cur.fetchone()[0] or 0

        # Average latency
        cur.execute("""
            SELECT AVG(latency_ms)
            FROM chat_logs
            WHERE DATE(created_at) = %s AND latency_ms IS NOT NULL
        """, (date,))
        avg_latency = cur.fetchone()[0] or 0

        # Feedback stats (if feedback field exists, otherwise estimate)
        # For now, estimate from chat logs presence
        cur.execute("""
            SELECT COUNT(*)
            FROM chat_logs
            WHERE DATE(created_at) = %s
        """, (date,))
        conversations_with_feedback = 0  # Placeholder - needs feedback field

        # Error rate (5xx would be logged as errors in app)
        cur.execute("""
            SELECT COUNT(*)
            FROM chat_logs
            WHERE DATE(created_at) = %s
              AND (answer LIKE '%服务暂时不可用%' OR answer LIKE '%error%')
        """, (date,))
        error_count = cur.fetchone()[0] or 0

        return {
            "date": date,
            "total_conversations": total_conversations,
            "unique_users": unique_users,
            "blocked_rate": round(blocked_rate * 100, 1),
            "avg_latency_ms": round(avg_latency, 0),
            "error_count": error_count,
            "error_rate": round(error_count / total_conversations * 100, 1) if total_conversations > 0 else 0,
        }


def get_trend_metrics(days: int) -> list:
    """Get metrics trend for last N days"""
    results = []
    today = datetime.now().date()

    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        metrics = get_daily_metrics(date)
        results.append(metrics)

    return results


def print_metrics(metrics: dict):
    """Print metrics in a formatted way"""
    print(f"\n📊 {metrics['date']} Metrics")
    print("=" * 40)
    print(f"  Total Conversations: {metrics['total_conversations']}")
    print(f"  Unique Users: {metrics['unique_users']}")
    print(f"  Compliance Block Rate: {metrics['blocked_rate']}%")
    print(f"  Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"  Error Count: {metrics['error_count']}")
    print(f"  Error Rate: {metrics['error_rate']}%")


def print_trend_report(trend: list):
    """Print trend report"""
    print(f"\n📈 Metrics Trend (Last {len(trend)} days)")
    print("=" * 60)
    print(f"{'Date':<12} {'Conv':>6} {'Users':>6} {'Block%':>7} {'Latency':>8} {'Err%':>5}")
    print("-" * 60)

    total_conv = sum(m["total_conversations"] for m in trend)
    total_users = sum(m["unique_users"] for m in trend)
    avg_blocked = sum(m["blocked_rate"] for m in trend) / len(trend)
    avg_latency = sum(m["avg_latency_ms"] for m in trend) / len(trend)
    avg_error = sum(m["error_rate"] for m in trend) / len(trend)

    for m in reversed(trend):
        print(f"{m['date']:<12} {m['total_conversations']:>6} {m['unique_users']:>6} "
              f"{m['blocked_rate']:>6.1f}% {m['avg_latency_ms']:>7.0f}ms {m['error_rate']:>5.1f}%")

    print("-" * 60)
    print(f"{'TOTAL/AVG':<12} {total_conv:>6} {total_users:>6} "
          f"{avg_blocked:>6.1f}% {avg_latency:>7.0f}ms {avg_error:>5.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Step 9 Metrics Dashboard")
    parser.add_argument("--date", type=str, help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=7, help="Number of days for trend (default: 7)")
    parser.add_argument("--output", type=str, help="Output file (Markdown)")

    args = parser.parse_args()

    if args.date:
        # Single day
        metrics = get_daily_metrics(args.date)
        print_metrics(metrics)
    else:
        # Trend report
        trend = get_trend_metrics(args.days)
        print_trend_report(trend)

        if args.output:
            # Write to Markdown file
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(f"# Step 9 Daily Metrics Report\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write(f"## Trend (Last {args.days} days)\n\n")
                f.write(f"| Date | Conversations | Unique Users | Block Rate | Avg Latency | Error Rate |\n")
                f.write(f"|------|---------------|--------------|------------|--------------|------------|\n")
                for m in reversed(trend):
                    f.write(f"| {m['date']} | {m['total_conversations']} | {m['unique_users']} | "
                            f"{m['blocked_rate']}% | {m['avg_latency_ms']:.0f}ms | {m['error_rate']}% |\n")
            print(f"\n📁 Report saved to {args.output}")


if __name__ == "__main__":
    main()
