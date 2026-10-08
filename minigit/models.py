"""커밋과 커밋 간 연결을 표현하는 자료구조."""

from dataclasses import dataclass
from datetime import datetime

from .algorithms import ancestor_ids, shortest_path, topological_order


@dataclass(frozen=True)
class Commit:
    """생성 후 바뀌지 않는 커밋 메타데이터. parents는 0개 이상의 부모 hash다."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: tuple[str, ...]


class CommitGraph:
    """부모·자식 인접 목록을 함께 보관해 양방향 탐색을 지원한다."""

    def __init__(self) -> None:
        self.parents: dict[str, tuple[str, ...]] = {}
        self.children: dict[str, list[str]] = {}

    def add(self, commit: Commit) -> None:
        """이미 있는 부모만 새 노드에 연결한다. 기존 간선을 바꾸지 않아 DAG다."""
        if commit.hash in self.parents:
            raise ValueError(f"Duplicate commit: {commit.hash}")
        if len(set(commit.parents)) != len(commit.parents):
            raise ValueError("Duplicate parents")
        for parent in commit.parents:
            if parent not in self.parents:
                raise ValueError(f"Unknown parent: {parent}")
        self.parents[commit.hash] = commit.parents
        self.children[commit.hash] = []
        for parent in commit.parents:
            self.children[parent].append(commit.hash)

    def log_order(self) -> list[str]:
        """전체 커밋을 부모가 자식보다 먼저 나오는 순서로 반환한다."""
        return topological_order(self.parents, self.children)

    def path(self, start: str, end: str) -> list[str] | None:
        """최단 경로 탐색을 독립 알고리즘 함수에 위임한다."""
        return shortest_path(self.parents, self.children, start, end)

    def ancestors(self, start: str) -> list[str]:
        """조상 탐색을 독립 알고리즘 함수에 위임한다."""
        return ancestor_ids(self.parents, start)
