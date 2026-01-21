"""GitHub adapter for syncing repositories."""

import fnmatch
from datetime import datetime, timezone
from typing import Iterator
import requests
from schema.rag import RemoteFile
from rag.adapters import BaseAdapter, register_adapter


@register_adapter("github")
class GitHubAdapter(BaseAdapter):
    """Sync files từ GitHub repo"""

    source_type = "github"

    def __init__(self, config: dict):
        """
        Config:
            - repo: "owner/repo"
            - branch: "main" (optional)
            - token: GitHub token (optional, for private repos)
        """
        super().__init__(config)
        self.repo = config["repo"]
        self.branch = config.get("branch", "main")
        self.token = config.get("token")

    def list_files(self, include_patterns: list[str], exclude_patterns: list[str]) -> Iterator[RemoteFile]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        url = f"https://api.github.com/repos/{self.repo}/git/trees/{self.branch}?recursive=1"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()

        for item in resp.json().get("tree", []):
            if item["type"] != "blob":
                continue

            path = item["path"]
            if not self._match(path, include_patterns, exclude_patterns):
                continue

            yield RemoteFile(
                path=path,
                filename=path.split("/")[-1],
                size=item.get("size", 0),
                modified_at=datetime.now(timezone.utc),
                content_type=self._guess_type(path)
            )

    def download_file(self, remote_file: RemoteFile) -> bytes:
        url = f"https://raw.githubusercontent.com/{self.repo}/{self.branch}/{remote_file.path}"
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.content

    def _match(self, path: str, includes: list[str], excludes: list[str]) -> bool:
        included = any(fnmatch.fnmatch(path, p) for p in includes)
        excluded = any(fnmatch.fnmatch(path, p) for p in excludes)
        return included and not excluded

    def _guess_type(self, path: str) -> str:
        types = {
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".html": "text/html",
            ".csv": "text/csv",
        }
        return next((t for ext, t in types.items() if path.endswith(ext)), "application/octet-stream")
