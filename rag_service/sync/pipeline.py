"""Document sync pipeline: Feishu → Qdrant + PostgreSQL

Supports two sync modes:
1. Wiki space sync: Sync all documents in a wiki knowledge space
2. Shared folder sync: Sync all documents in a shared folder (云盘/共享文件夹)
"""
import os
import sys
import time
import uuid
import json
import httpx
from typing import Optional, List, Tuple
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rag_service.feishu.client import FeishuClient, get_client
from rag_service.feishu.block_parser import blocks_to_markdown, get_block_headings
from rag_service.rag.chunker import split_markdown
from rag_service.rag.embedder import embed_texts
from rag_service.rag.vector_store import get_client as get_qdrant, DEFAULT_COLLECTION
from rag_service.models.db import (
    upsert_document,
    set_document_permissions,
    get_document,
    set_document_status,
)

# Config
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION)


class SyncPipeline:
    """Pipeline for syncing documents from Feishu to Qdrant + PostgreSQL"""

    def __init__(self, feishu_client: FeishuClient = None, feishu_user_client=None):
        self.feishu = feishu_client or get_client()
        self.user_client = feishu_user_client  # User-level client for 云盘/共享文件夹
        self.qdrant = get_qdrant()
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

    # === Shared Folder Sync (云盘/共享文件夹) ===

    def sync_folder(
        self,
        folder_token: str = None,
        folder_name: str = "Shared Folder",
        dry_run: bool = False,
        recursive: bool = True,
    ) -> dict:
        """
        Sync all documents in a shared folder (云盘/共享文件夹).

        Args:
            folder_token: Folder token. If None, syncs My Drive root.
            folder_name: Display name for the folder
            dry_run: If True, don't actually write to Qdrant/PG
            recursive: If True, recursively sync subfolders

        Returns:
            Sync stats dict
        """
        print(f"\n{'='*60}")
        print(f"Starting sync for folder: {folder_name}")
        print(f"Folder token: {folder_token or 'My Drive root'}")
        print(f"Dry run: {dry_run}")
        print(f"Recursive: {recursive}")
        print(f"{'='*60}\n")

        # List all files in folder
        all_files = self._list_all_folder_contents(folder_token, recursive=recursive)

        # Filter to docx files only
        docx_files = [f for f in all_files if f.get("type") == "docx"]
        print(f"Found {len(all_files)} total files, {len(docx_files)} docx documents")

        self.stats["total"] = len(docx_files)

        # Process each document
        for i, file_info in enumerate(docx_files, 1):
            doc_token = file_info.get("token") or file_info.get("file_token")
            title = file_info.get("name", f"Document {doc_token}")

            if not doc_token:
                print(f"[{i}/{len(docx_files)}] Skipping: no token")
                self.stats["skipped"] += 1
                continue

            try:
                print(f"\n[{i}/{len(docx_files)}] Syncing: {title[:40]}...")
                print(f"  Token: {doc_token}")

                if not dry_run:
                    self._sync_docx(doc_token, title, folder_name)
                    self.stats["success"] += 1
                else:
                    print(f"  [DRY RUN] Would sync document {doc_token}")

            except Exception as e:
                print(f"  [ERROR] {e}")
                self.stats["failed"] += 1
                self.stats["errors"].append({
                    "document_token": doc_token,
                    "title": title,
                    "error": str(e),
                })

        return self._report_stats()

    def _list_all_folder_contents(self, folder_token: str = None, recursive: bool = True) -> list:
        """List all files in folder, optionally recursively"""
        all_files = []
        files_to_process = [{"token": folder_token, "is_folder": folder_token is not None, "name": "root"}]

        while files_to_process:
            current = files_to_process.pop(0)
            token = current.get("token")
            is_folder = current.get("is_folder", False)

            if is_folder:
                # List folder contents
                folder_files = self._list_single_folder(token)
                print(f"  Folder {current.get('name', token)[:30]}: {len(folder_files)} items")

                for f in folder_files:
                    f_type = f.get("type")
                    f_token = f.get("token")
                    f_name = f.get("name", "unknown")

                    if f_type == "folder" and recursive:
                        # Add subfolder to process queue
                        files_to_process.append({
                            "token": f_token,
                            "is_folder": True,
                            "name": f_name,
                        })
                    elif f_type == "docx":
                        # Add document to list
                        all_files.append(f)

            # Rate limit protection
            time.sleep(0.1)

        return all_files

    def _list_single_folder(self, folder_token: str) -> list:
        """List files in a single folder"""
        # Use user_client if available (for 云盘/共享文件夹), otherwise use app client
        client = self.user_client or self.feishu

        all_items = []
        page_token = None

        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            # Use user_client's list_my_drive_files which handles wiki folders correctly
            if self.user_client:
                try:
                    data = client.list_my_drive_files(folder_token=folder_token, page_token=page_token)
                    items = data.get("files", [])
                    all_items.extend(items)
                    page_token = data.get("page_token")
                    if not page_token:
                        break
                except Exception as e:
                    print(f"  [WARN] Failed to list folder {folder_token}: {e}")
                    break
            else:
                # Use app-level API
                url = f"{self.feishu.BASE_URL}/drive/v1/files/{folder_token}/children"
                resp = httpx.get(url, headers=self.feishu._headers(), timeout=30, params=params)
                data = resp.json()

                if data.get("code") != 0:
                    print(f"  [WARN] Failed to list folder {folder_token}: {data.get('msg')}")
                    break

                items = data.get("data", {}).get("files", [])
                all_items.extend(items)

                page_token = data.get("data", {}).get("page_token")
                if not page_token:
                    break

        return all_items

    # === Wiki Space Sync ===

    def sync_space(self, space_id: str, dry_run: bool = False) -> dict:
        """
        Sync all documents in a wiki space.

        Args:
            space_id: Feishu wiki space ID
            dry_run: If True, don't actually write to Qdrant/PG

        Returns:
            Sync stats dict
        """
        print(f"\n{'='*60}")
        print(f"Starting sync for wiki space: {space_id}")
        print(f"Dry run: {dry_run}")
        print(f"{'='*60}\n")

        # List wiki spaces first to verify access
        spaces = self.feishu.list_wiki_spaces()
        space = next((s for s in spaces if s.get("space_id") == space_id), None)
        if not space:
            raise ValueError(f"Space {space_id} not found or not accessible")

        print(f"Space name: {space.get('name', 'Unknown')}")

        # Walk the wiki tree
        all_nodes = self._walk_wiki_tree(space_id)
        print(f"Found {len(all_nodes)} nodes in wiki tree")

        # Filter to docx documents only
        doc_nodes = [
            n for n in all_nodes
            if n.get("node_type") == "docx" or n.get("obj_type") == "docx"
        ]
        print(f"Found {len(doc_nodes)} docx documents")

        self.stats["total"] = len(doc_nodes)

        # Process each document
        for i, node in enumerate(doc_nodes, 1):
            node_token = node.get("node_token")
            doc_id = node.get("document", {}).get("document_id") or node.get("document_id")

            if not doc_id:
                print(f"[{i}/{len(doc_nodes)}] Skipping node {node_token}: no document_id")
                self.stats["skipped"] += 1
                continue

            try:
                title = node.get("title", f"Document {doc_id}")
                print(f"\n[{i}/{len(doc_nodes)}] Syncing: {title[:40]}...")

                if not dry_run:
                    self._sync_docx(doc_id, title, "wiki")
                    self.stats["success"] += 1
                else:
                    print(f"  [DRY RUN] Would sync document {doc_id}")

            except Exception as e:
                print(f"  [ERROR] {e}")
                self.stats["failed"] += 1
                self.stats["errors"].append({
                    "document_id": doc_id,
                    "error": str(e),
                })

        return self._report_stats()

    def _walk_wiki_tree(self, space_id: str) -> List[dict]:
        """Recursively walk wiki tree and collect all nodes"""
        all_nodes = []

        def walk(parent_token: str = None):
            nodes = self.feishu.walk_wiki_tree(space_id, parent_token)
            for node in nodes:
                all_nodes.append(node)
                # Recurse into child nodes
                if node.get("has_children"):
                    walk(node.get("node_token"))

        walk()
        return all_nodes

    # === Core Sync Logic ===

    def _sync_docx(
        self,
        doc_token: str,
        title: str = None,
        source: str = "unknown",
    ) -> Tuple[int, int]:
        """
        Sync a single docx document.

        Args:
            doc_token: Document token (document_id)
            title: Document title
            source: Source description (folder name or "wiki")

        Returns:
            (chunk_count, permission_count)
        """
        start_time = time.time()

        # Use user_client for user folders, app client for wiki spaces
        client = self.user_client or self.feishu

        # 1. Get document content - prefer raw_content (more reliable)
        try:
            content_md = client.get_docx_raw_content(doc_token)
        except Exception:
            # Fallback to blocks
            blocks_data = self._get_doc_blocks(doc_token)
            blocks = blocks_data.get("items", [])
            if blocks:
                content_md = blocks_to_markdown(blocks)
            else:
                content_md = ""

        title = title or f"Document {doc_token}"
        print(f"  Title: {title[:50]}...")
        print(f"  Content: {len(content_md)} chars")

        # Skip heading extraction when using raw_content
        heading_breadcrumb = []

        # Chunk the markdown
        chunks = split_markdown(content_md)
        chunk_count = len(chunks)
        print(f"  Chunks: {chunk_count}")

        if chunk_count == 0:
            print(f"  [SKIP] No content after chunking")
            self.stats["skipped"] += 1
            return 0, 0

        # 4. Generate embeddings
        print(f"  Generating embeddings...")
        try:
            embeddings = embed_texts(chunks)
        except Exception as e:
            print(f"  [ERROR] Embedding failed: {e}")
            raise

        # 5. Build Qdrant points
        import hashlib
        points = []
        for seq, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Use hash of doc_token + seq as point ID
            point_id = int(hashlib.md5(f"{doc_token}_{seq}".encode()).hexdigest()[:8], 16)
            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "document_id": doc_token,
                    "seq": seq,
                    "content": chunk,
                    "headings": heading_breadcrumb,
                    "title": title,
                    "space_id": source,
                    "path": source,
                }
            })

        # 6. Delete old chunks for this document
        self._delete_document_chunks(doc_token)

        # 7. Upsert new chunks to Qdrant
        if points:
            self.qdrant.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points,
            )

        # 8. Upsert document metadata to PostgreSQL
        upsert_document(
            document_id=doc_token,
            space_id=source,
            obj_type="docx",
            title=title,
            path=source,
            content_md=content_md[:50000] if content_md else "",
            owner_id="",
            last_edit_time=datetime.now(),
            chunk_count=chunk_count,
            status="active",
        )

        # 9. Sync permissions
        perm_count = self._sync_permissions(doc_token)

        elapsed = time.time() - start_time
        print(f"  Done in {elapsed:.1f}s ({chunk_count} chunks, {perm_count} permissions)")

        return chunk_count, perm_count

    def _get_doc_blocks(self, doc_token: str) -> dict:
        """Get all blocks for a document with pagination"""
        all_items = []
        page_token = None

        while True:
            data = self.feishu.get_docx_blocks(doc_token, page_token)
            items = data.get("items", [])
            all_items.extend(items)

            page_token = data.get("page_token")
            if not page_token:
                break

            # Rate limit protection
            time.sleep(0.1)

        return {"items": all_items}

    def _sync_permissions(self, doc_token: str) -> int:
        """Sync document permissions to PostgreSQL"""
        try:
            members = self.feishu.get_document_permissions(doc_token)
        except Exception as e:
            print(f"  [WARN] Could not fetch permissions: {e}")
            # Fallback: make document public
            members = [{"member_type": "tenant", "member_id": "all"}]

        permissions = []
        for m in members:
            member_type = m.get("member_type", "user")
            # Map Feishu types to our types
            if member_type == "user":
                ptype = "user"
            elif member_type in ("department", "open_department"):
                ptype = "dept"
            else:
                ptype = "tenant"

            permissions.append({
                "principal_type": ptype,
                "principal_id": m.get("member_id", ""),
                "perm": m.get("perm", "read"),
            })

        if not permissions:
            # Fallback to public
            permissions = [{"principal_type": "tenant", "principal_id": "all", "perm": "read"}]

        set_document_permissions(doc_token, permissions)
        return len(permissions)

    def _delete_document_chunks(self, doc_token: str):
        """Delete all chunks for a document from Qdrant"""
        try:
            results = self.qdrant.scroll(
                collection_name=QDRANT_COLLECTION,
                scroll_filter={
                    "must": [
                        {
                            "key": "document_id",
                            "match": {"value": doc_token}
                        }
                    ]
                },
                limit=1000,
            )

            if results and results[0]:
                point_ids = [p["id"] for p in results[0]]
                self.qdrant.delete(
                    collection_name=QDRANT_COLLECTION,
                    points_selector=point_ids,
                )
        except Exception as e:
            print(f"  [WARN] Error deleting old chunks: {e}")

    def _report_stats(self) -> dict:
        """Print and return sync stats"""
        print(f"\n{'='*60}")
        print("Sync Summary")
        print(f"{'='*60}")
        print(f"Total documents: {self.stats['total']}")
        print(f"Success: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped: {self.stats['skipped']}")

        if self.stats["errors"]:
            print(f"\nErrors:")
            for err in self.stats["errors"][:10]:
                print(f"  - {err.get('title', err.get('document_id', 'unknown'))}: {err['error']}")

        return self.stats


# === CLI Commands ===

def full_sync(space_id: str = None, dry_run: bool = False):
    """Run full sync for a wiki space"""
    if not space_id:
        print("ERROR: space_id required for wiki sync")
        print("Usage: python -m sync.pipeline full_sync --space_id <SPACE_ID>")
        sys.exit(1)

    pipeline = SyncPipeline()
    stats = pipeline.sync_space(space_id, dry_run=dry_run)
    return stats


def sync_folder_cmd(folder_token: str = None, folder_name: str = None, dry_run: bool = False, recursive: bool = True):
    """Sync all documents in a shared folder"""
    if not folder_token:
        print("ERROR: folder_token required")
        print("Usage: python -m sync.pipeline sync_folder --folder_token <TOKEN> [--name 'Folder Name']")
        sys.exit(1)

    # Set up user_client for shared folder access
    from rag_service.feishu.auth_tool import load_saved_token
    from rag_service.feishu.user_client import get_user_client, set_user_token

    token_data = load_saved_token()
    if not token_data:
        print("ERROR: No saved user token. Run: python -m feishu.auth_tool")
        sys.exit(1)

    set_user_token(token_data.get("access_token"), token_data.get("refresh_token"))
    user_client = get_user_client()

    pipeline = SyncPipeline(feishu_user_client=user_client)
    stats = pipeline.sync_folder(
        folder_token=folder_token,
        folder_name=folder_name or "Shared Folder",
        dry_run=dry_run,
        recursive=recursive,
    )
    return stats


if __name__ == "__main__":
    import argparse
    import httpx

    parser = argparse.ArgumentParser(description="Document sync pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # full_sync command (wiki)
    fs_parser = subparsers.add_parser("full_sync", help="Sync entire wiki space")
    fs_parser.add_argument("--space_id", type=str, help="Wiki space ID")
    fs_parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")

    # sync_folder command (云盘)
    sf_parser = subparsers.add_parser("sync_folder", help="Sync shared folder")
    sf_parser.add_argument("--folder_token", type=str, help="Folder token")
    sf_parser.add_argument("--name", type=str, default=None, help="Folder display name")
    sf_parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    sf_parser.add_argument("--no-recursive", action="store_true", help="Don't recurse into subfolders")

    # sync_doc command
    sd_parser = subparsers.add_parser("sync_doc", help="Sync single document")
    sd_parser.add_argument("--doc_token", type=str, required=True, help="Document token")
    sd_parser.add_argument("--title", type=str, default=None, help="Document title")

    args = parser.parse_args()

    if args.command == "full_sync":
        full_sync(args.space_id, args.dry_run)
    elif args.command == "sync_folder":
        sync_folder_cmd(
            args.folder_token,
            args.name,
            args.dry_run,
            not args.no_recursive,
        )
    elif args.command == "sync_doc":
        pipeline = SyncPipeline()
        pipeline._sync_docx(args.doc_token, args.title or "Unknown")
    else:
        parser.print_help()
