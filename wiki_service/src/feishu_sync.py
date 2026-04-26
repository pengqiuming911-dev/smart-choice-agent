"""
飞书文档定时同步脚本

使用方式:
    python -m src.feishu_sync high-freq   # 高频空间每天同步
    python -m src.feishu_sync low-freq    # 低频空间每周同步

Crontab 配置示例:
    0 2 * * * /usr/bin/python3 /opt/wiki/src/feishu_sync.py high-freq >> /var/log/wiki-sync-high.log 2>&1
    0 3 * * 1 /usr/bin/python3 /opt/wiki/src/feishu_sync.py low-freq >> /var/log/wiki-sync-low.log 2>&1
"""
import hashlib
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")

from src.config import settings
from src.feishu_client import FeishuClient
from src.wiki_agent import WikiAgent


class SyncState:
    """管理同步状态（本地文件）"""

    def __init__(self, state_file: Path = None):
        self.state_file = state_file or Path(settings.wiki_repo_path) / ".sync_state.json"
        self.state = self._load()

    def _load(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        return {}

    def save(self):
        self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_hash(self, node_token: str) -> str:
        return self.state.get("hashes", {}).get(node_token, "")

    def set_hash(self, node_token: str, content_hash: str):
        self.state.setdefault("hashes", {})[node_token] = content_hash

    def set_last_sync(self, space_id: str, ts: str):
        self.state["last_sync"] = {"space": space_id, "at": ts}


def content_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def sync_folder(folder_id: str, dry_run: bool = False) -> dict:
    """同步一个云文档文件夹（共享文档）"""
    client = FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
    agent = WikiAgent()
    state = SyncState()

    stats = {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    logger.info(f"Syncing folder: {folder_id}")
    files = client.list_folder_files(folder_id)
    docx_files = [f for f in files if f["type"] == "docx"]
    logger.info(f"Found {len(docx_files)} docx documents in folder")

    for f in docx_files:
        try:
            md_content = client.get_docx_markdown(f["token"])
            new_hash = content_hash(md_content)
            old_hash = state.get_hash(f["token"])

            if new_hash == old_hash:
                logger.debug(f"Skipped (unchanged): {f['name']}")
                stats["skipped"] += 1
                continue

            if dry_run:
                logger.info(f"[DRY] Would update: {f['name']}")
                continue

            safe_name = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", f["name"])
            raw_path = settings.raw_dir / "articles" / f"{safe_name}.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(md_content, encoding="utf-8")

            state.set_hash(f["token"], new_hash)

            rel_path = str(raw_path.relative_to(settings.wiki_repo_path))
            result = agent.ingest(rel_path)

            if result["success"]:
                if old_hash:
                    stats["updated"] += 1
                    logger.info(f"Updated: {f['name']} (+{result['pages_created']}/~{result['pages_updated']})")
                else:
                    stats["new"] += 1
                    logger.info(f"New: {f['name']} (+{result['pages_created']})")
            else:
                stats["failed"] += 1
                stats["errors"].append(f"{f['name']}: ingest failed")

            time.sleep(0.5)

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"{f['name']}: {e}")
            logger.error(f"Failed to sync {f['name']}: {e}")

    state.set_last_sync(folder_id, datetime.now().isoformat())
    state.save()

    logger.info(f"Sync complete: {stats}")
    return stats


def sync_space(space_id: str, dry_run: bool = False) -> dict:
    """同步一个知识空间"""
    client = FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
    agent = WikiAgent()
    state = SyncState()

    stats = {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    logger.info(f"Syncing space: {space_id}")
    nodes = client.list_wiki_nodes(space_id)
    docx_nodes = [n for n in nodes if n.obj_type == "docx"]
    logger.info(f"Found {len(docx_nodes)} docx documents")

    for node in docx_nodes:
        try:
            # Fetch content
            md_content = client.get_docx_markdown(node.node_token)
            new_hash = content_hash(md_content)
            old_hash = state.get_hash(node.node_token)

            if new_hash == old_hash:
                logger.debug(f"Skipped (unchanged): {node.title}")
                stats["skipped"] += 1
                continue

            if dry_run:
                logger.info(f"[DRY] Would update: {node.title}")
                continue

            # Save to raw/
            safe_name = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", node.title)
            raw_path = settings.raw_dir / "articles" / f"{safe_name}.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(md_content, encoding="utf-8")

            # Update state
            state.set_hash(node.node_token, new_hash)

            # Trigger ingest
            rel_path = str(raw_path.relative_to(settings.wiki_repo_path))
            result = agent.ingest(rel_path)

            if result["success"]:
                if old_hash:
                    stats["updated"] += 1
                    logger.info(f"Updated: {node.title} (+{result['pages_created']}/~{result['pages_updated']})")
                else:
                    stats["new"] += 1
                    logger.info(f"New: {node.title} (+{result['pages_created']})")
            else:
                stats["failed"] += 1
                stats["errors"].append(f"{node.title}: ingest failed")

            # Rate limit: sleep between docs
            time.sleep(0.5)

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"{node.title}: {e}")
            logger.error(f"Failed to sync {node.title}: {e}")

    state.set_last_sync(space_id, datetime.now().isoformat())
    state.save()

    logger.info(f"Sync complete: {stats}")
    return stats


if __name__ == "__main__":
    import re

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    dry_run = "--dry-run" in sys.argv

    if not settings.feishu_app_id or not settings.feishu_app_secret:
        logger.error("FEISHU_APP_ID / FEISHU_APP_SECRET not set")
        sys.exit(1)

    # 三个重要文件夹配置
    folder_ids = [
        settings.feishu_folder_fanfei,
        settings.feishu_folder_chanpin,
        settings.feishu_folder_zhuanhuan,
    ]
    folder_ids = [f for f in folder_ids if f]

    if not folder_ids:
        logger.error("No folder IDs configured. Set FEISHU_FOLDER_FANFEI / FEISHU_FOLDER_CHANPIN / FEISHU_FOLDER_ZHUANHUAN in .env")
        sys.exit(1)

    # 如果传了文件夹 ID 参数，就只同步那个文件夹
    if mode not in ("all", "high-freq", "low-freq"):
        logger.info(f"Starting sync for folder: {mode}")
        stats = sync_folder(mode, dry_run=dry_run)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 全量同步：遍历所有配置的文件夹
    for fid in folder_ids:
        logger.info(f"=== Syncing folder: {fid} ===")
        stats = sync_folder(fid, dry_run=dry_run)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
