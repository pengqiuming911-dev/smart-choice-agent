"""Core domain - Git operations for wiki repo"""
import subprocess
from pathlib import Path
from loguru import logger


class GitManager:
    """Manages wiki repo Git operations"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._ensure_init()

    def _ensure_init(self):
        """Initialize git repo if not exists"""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=self.repo_path, check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=self.repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial wiki commit"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            logger.info("Git repo initialized")

    def commit(self, message: str):
        """Stage all changes and commit"""
        try:
            subprocess.run(["git", "add", "-A"], cwd=self.repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            logger.info(f"Git commit: {message}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed (may be no changes): {e.stderr}")

    def status(self) -> str:
        """Get git status"""
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout