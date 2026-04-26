"""Core domain - wiki repo structure and paths"""
from pathlib import Path
from dataclasses import dataclass


@dataclass
class WikiRepo:
    """Wiki repository structure as defined in ARCHITECTURE.md"""

    root: Path

    @property
    def claude_md_path(self) -> Path:
        return self.root / "CLAUDE.md"

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    @property
    def index_md_path(self) -> Path:
        return self.wiki_dir / "index.md"

    @property
    def log_md_path(self) -> Path:
        return self.wiki_dir / "log.md"

    # Raw subdirectories
    @property
    def raw_articles_dir(self) -> Path:
        return self.raw_dir / "articles"

    @property
    def raw_pdfs_dir(self) -> Path:
        return self.raw_dir / "pdfs"

    @property
    def raw_meeting_notes_dir(self) -> Path:
        return self.raw_dir / "meeting-notes"

    @property
    def raw_tables_dir(self) -> Path:
        return self.raw_dir / "tables"

    # Wiki subdirectories
    @property
    def wiki_entities_dir(self) -> Path:
        return self.wiki_dir / "entities"

    @property
    def wiki_concepts_dir(self) -> Path:
        return self.wiki_dir / "concepts"

    @property
    def wiki_overviews_dir(self) -> Path:
        return self.wiki_dir / "overviews"

    def ensure_structure(self):
        """Create directory structure if not exists"""
        for d in [
            self.raw_articles_dir,
            self.raw_pdfs_dir,
            self.raw_meeting_notes_dir,
            self.raw_tables_dir,
            self.wiki_entities_dir,
            self.wiki_concepts_dir,
            self.wiki_overviews_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)