"""저장소 상태 관리. CLI와 무관하게 기능을 호출하거나 테스트할 수 있다."""

from collections.abc import Callable
from datetime import datetime, timezone

from .algorithms import merge_sort
from .index import InvertedIndex
from .models import Commit, CommitGraph


class RepositoryError(ValueError):
    """사용자에게 그대로 표시할 수 있는 잘못된 저장소 조작 오류."""


class Repository:
    """커밋 저장소, 브랜치 포인터, HEAD, 사용자, 그래프, 색인을 분리한다."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, str | None] = {}
        self.current_branch: str | None = None
        self.current_user: str | None = None
        self.graph = CommitGraph()
        self.index = InvertedIndex()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._next_id = 1

    @property
    def head(self) -> str | None:
        """HEAD는 현재 브랜치가 가리키는 커밋이다. 빈 브랜치에서는 None이다."""
        return self.branches.get(self.current_branch)

    def _require_initialized(self) -> None:
        if self.current_branch is None:
            raise RepositoryError("Repository not initialized")

    @staticmethod
    def _require_text(value: str) -> None:
        if not value.strip():
            raise RepositoryError("Invalid args")

    def initialize(self, user_name: str) -> None:
        """저장소를 비우고 main/HEAD/사용자를 설정한다. 세션 hash 카운터는 유지한다."""
        self._require_text(user_name)
        self.commits.clear()
        self.branches = {"main": None}
        self.current_branch = "main"
        self.current_user = user_name
        self.graph = CommitGraph()
        self.index = InvertedIndex()

    def branch(self, name: str) -> None:
        """현재 HEAD를 가리키는 브랜치를 생성한다. 현재 브랜치는 바꾸지 않는다."""
        self._require_initialized()
        self._require_text(name)
        if name in self.branches:
            raise RepositoryError(f"Branch already exists: {name}")
        self.branches[name] = self.head

    def switch(self, name: str) -> None:
        """존재하는 브랜치로 HEAD를 이동한다."""
        self._require_initialized()
        if name not in self.branches:
            raise RepositoryError(f"Unknown branch: {name}")
        self.current_branch = name

    def set_user(self, name: str) -> None:
        """이후 커밋의 작성자만 바꾼다. 기존 커밋과 이력은 유지한다."""
        self._require_initialized()
        self._require_text(name)
        self.current_user = name

    def _create_commit(self, message: str, parents: tuple[str, ...]) -> Commit:
        """커밋 등록·색인 갱신·브랜치 이동을 일반/병합 커밋이 공유한다."""
        self._require_text(message)
        # 고정 길이 ID는 경로 문자열의 사전순 규칙을 단순하게 만든다.
        if self._next_id > 0xFFFFFFFF:
            raise RepositoryError("Commit hash space exhausted")
        commit = Commit(
            hash=f"c{self._next_id:08x}",
            message=message,
            author=self.current_user,
            timestamp=self._clock(),
            parents=parents,
        )
        self.graph.add(commit)
        self.commits[commit.hash] = commit
        self.index.add(commit)
        self.branches[self.current_branch] = commit.hash
        self._next_id += 1
        return commit

    def commit(self, message: str) -> Commit:
        """현재 HEAD를 부모로 하는 커밋을 추가하고 현재 브랜치만 이동한다."""
        self._require_initialized()
        parents = () if self.head is None else (self.head,)
        return self._create_commit(message, parents)

    def merge(self, branch_name: str) -> Commit:
        """현재·대상 브랜치의 HEAD를 부모로 하는 두 부모 커밋을 만든다."""
        self._require_initialized()
        if branch_name not in self.branches:
            raise RepositoryError(f"Unknown branch: {branch_name}")
        target = self.branches[branch_name]
        if self.head is None or target is None:
            raise RepositoryError("Cannot merge empty branch")
        if self.head == target:
            raise RepositoryError("Cannot merge identical heads")
        return self._create_commit(f"Merge branch '{branch_name}'", (self.head, target))

    def get_commit(self, commit_hash: str) -> Commit:
        """hash로 평균 O(1) 조회하고, 없는 커밋에는 표준 오류를 낸다."""
        self._require_initialized()
        if commit_hash not in self.commits:
            raise RepositoryError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]

    def log(self, sort_by: str | None = None) -> list[Commit]:
        """기본은 전체 저장소의 위상 순서, 옵션은 날짜/작성자의 오름차순이다."""
        self._require_initialized()
        if sort_by is None:
            return [self.commits[node] for node in self.graph.log_order()]
        if sort_by not in {"date", "author"}:
            raise RepositoryError("Invalid args")
        attribute = "timestamp" if sort_by == "date" else "author"
        return merge_sort(self.commits.values(), key=lambda item: getattr(item, attribute))

    def path(self, start: str, end: str) -> list[str] | None:
        """없는 hash와 연결되지 않은 유효한 두 커밋을 구별한다."""
        self.get_commit(start)
        self.get_commit(end)
        return self.graph.path(start, end)

    def ancestors(self, commit_hash: str) -> list[Commit]:
        """모든 조상을 찾은 뒤 hash 오름차순으로 표시한다. 시작 커밋은 제외한다."""
        self.get_commit(commit_hash)
        return merge_sort(
            (self.commits[node] for node in self.graph.ancestors(commit_hash)),
            key=lambda item: item.hash,
        )

    def search(self, query: str, *, author: bool = False) -> list[Commit]:
        """역색인 후보만 조회하고 hash 오름차순으로 반환한다."""
        self._require_initialized()
        self._require_text(query)
        hashes = self.index.by_author(query) if author else self.index.by_keywords(query)
        return merge_sort((self.commits[node] for node in hashes), key=lambda item: item.hash)
