"""Market data fetcher using AKShare"""
import akshare as ak
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from datetime import datetime

# Index code map loaded dynamically from Bitable on first use
_INDEX_CODE_MAP: Optional[Dict[str, str]] = None


def _get_index_code_map() -> Dict[str, str]:
    """Lazy-load index code map from Bitable"""
    global _INDEX_CODE_MAP
    if _INDEX_CODE_MAP is None:
        try:
            from src.feishu_bitable import build_index_code_map
            _INDEX_CODE_MAP = build_index_code_map()
            if not _INDEX_CODE_MAP:
                raise ValueError("empty map")
            print(f"[INFO] Loaded {len(_INDEX_CODE_MAP)} index codes from Bitable")
        except Exception as e:
            print(f"[ERROR] Failed to load index codes from Bitable ({e})")
            _INDEX_CODE_MAP = {}
    return _INDEX_CODE_MAP


def get_index_realtime(index_name: str) -> Optional[Dict]:
    """
    Get single index realtime quote

    Args:
        index_name: Index name, e.g. "上证指数"

    Returns:
        dict with keys: name, code, current, change, change_pct, volume, date, time
    """
    code = _get_index_code_map().get(index_name)
    if not code:
        print(f"[WARN] Unknown index: {index_name}")
        return None

    try:
        # Use stock_zh_index_spot_em for newer akshare versions
        df = ak.stock_zh_index_spot_em()

        # Filter by code
        row = df[df["代码"] == code]
        if row.empty:
            print(f"[WARN] Index {index_name}({code}) not found in data")
            return None

        row = row.iloc[0]
        current = float(row["最新价"]) if pd.notna(row["最新价"]) else 0
        change = float(row["涨跌额"]) if pd.notna(row["涨跌额"]) else 0
        change_pct = float(row["涨跌幅"]) if pd.notna(row["涨跌幅"]) else 0
        volume = row["成交量"] if pd.notna(row["成交量"]) else 0
        amount = row["成交额"] if pd.notna(row["成交额"]) else 0

        return {
            "name": index_name,
            "code": code,
            "current": current,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "amount": amount,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
        }
    except Exception as e:
        print(f"[ERROR] Failed to get realtime data for {index_name}: {e}")
        return None


def get_indices_batch(index_names: List[str]) -> List[Dict]:
    """
    Batch get multiple index realtime quotes in parallel

    Args:
        index_names: List of index names

    Returns:
        List of valid index quote dicts
    """
    results = []
    with ThreadPoolExecutor(max_workers=min(len(index_names), 4)) as executor:
        futures = {executor.submit(get_index_realtime, name): name for name in index_names}
        for future in as_completed(futures):
            data = future.result()
            if data:
                results.append(data)
    return results


def get_index_zh_hist(
    index_name: str,
    period: str = "daily",
    start_date: str = None,
    end_date: str = None,
) -> Optional[pd.DataFrame]:
    """
    Get index historical quotes

    Args:
        index_name: Index name
        period: daily / weekly / monthly
        start_date: YYYYMMDD
        end_date: YYYYMMDD
    """
    code = _get_index_code_map().get(index_name)
    if not code:
        return None

    try:
        symbol = f"sh{code}" if code.startswith("0") else f"sz{code}"
        df = ak.index_zh_a_hist(symbol=symbol, period=period, start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        print(f"[ERROR] Failed to get history for {index_name}: {e}")
        return None
