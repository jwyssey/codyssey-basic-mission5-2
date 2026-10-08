"""따옴표를 이해하는 명령 파서와 mini-git> REPL."""

import shlex
import sys
from collections.abc import Sequence
from typing import TextIO

from .models import Commit
from .repository import Repository, RepositoryError

HELP = """INIT <user_name>                저장소 초기화 (기존 메모리 이력 삭제)
BRANCH <branch_name>            현재 HEAD에서 브랜치 생성
SWITCH <branch_name>            브랜치 전환
COMMIT <message>               메타데이터 커밋 생성
LOG                            모든 브랜치의 커밋을 부모 먼저 출력
LOG --sort-by=date|author       날짜/작성자 오름차순 (안정 병합 정렬)
PATH <commit1> <commit2>        무방향 최단 경로 (동률은 사전순)
ANCESTORS <commit_hash>         자기 자신을 제외한 모든 조상
SEARCH <keyword>               단어 검색 (여러 단어는 AND)
SEARCH --author=<name>         정확한 작성자 이름으로 검색
USER <name>                    이후 커밋의 작성자 변경
MERGE <branch_name>            두 부모를 갖는 병합 커밋 생성
HELP                           도움말
exit / quit                    종료
공백이 있는 인자는 따옴표로 감싸세요. 예: COMMIT "Add login feature"
"""


class MiniGitCLI:
    """입력을 검증한 후 Repository를 호출한다. 실행 결과는 문자열로 반환한다."""

    def __init__(self, repository: Repository | None = None) -> None:
        self.repository = repository if repository is not None else Repository()
        self.running = True

    @staticmethod
    def _one_argument(args: Sequence[str]) -> str:
        if len(args) != 1 or not args[0].strip():
            raise RepositoryError("Invalid args")
        return args[0]

    def _format_commits(self, commits: Sequence[Commit], empty: str) -> str:
        """브랜치 표시를 한 번 계산해 커밋마다 전체 브랜치를 훑지 않는다."""
        if not commits:
            return empty
        references: dict[str, list[str]] = {}
        for branch, head in self.repository.branches.items():
            if head is not None:
                label = f"HEAD -> {branch}" if branch == self.repository.current_branch else branch
                references.setdefault(head, []).append(label)
        rows = []
        for commit in commits:
            labels = references.get(commit.hash, [])
            suffix = f" [{', '.join(labels)}]" if labels else ""
            rows.append(
                f"commit {commit.hash} ({commit.author}, "
                f"{commit.timestamp.isoformat(timespec='microseconds')}){suffix}\n"
                f"{commit.message}"
            )
        return "\n\n".join(rows)

    def execute(self, line: str) -> str:
        """문법·사용자 오류를 표준 메시지로 바꿔 REPL이 계속 실행되게 한다."""
        try:
            tokens = shlex.split(line, comments=False)
        except ValueError:
            return "Invalid args"
        if not tokens:
            return ""
        command = tokens[0].lower()
        args = tokens[1:]
        try:
            return self._dispatch(command, args)
        except RepositoryError as error:
            return str(error)

    def _dispatch(self, command: str, args: Sequence[str]) -> str:
        """명령별 인자를 검증하고 저장소 작업과 표시 문자열을 조합한다."""
        repo = self.repository
        if command in {"exit", "quit", "help"}:
            if args:
                raise RepositoryError("Invalid args")
            if command == "help":
                return HELP
            self.running = False
            return "Bye."
        if command == "init":
            user = self._one_argument(args)
            repo.initialize(user)
            return f"Initialized repository.\nCurrent branch: main\nCurrent user: {user}"
        if command == "branch":
            name = self._one_argument(args)
            repo.branch(name)
            return f"Created branch: {name}"
        if command == "switch":
            name = self._one_argument(args)
            repo.switch(name)
            return f"Switched to branch: {name}"
        if command == "user":
            name = self._one_argument(args)
            repo.set_user(name)
            return f"Current user: {name}"
        if command in {"commit", "merge"}:
            value = self._one_argument(args)
            commit = repo.commit(value) if command == "commit" else repo.merge(value)
            return f"[{repo.current_branch} {commit.hash}] {commit.message}"
        if command == "log":
            sort_by = None
            if args:
                option = self._one_argument(args)
                if not option.startswith("--sort-by="):
                    raise RepositoryError("Invalid args")
                sort_by = option.partition("=")[2]
                if sort_by not in {"date", "author"}:
                    raise RepositoryError("Invalid args")
            return self._format_commits(repo.log(sort_by), "No commits")
        if command == "path":
            if len(args) != 2 or any(not value.strip() for value in args):
                raise RepositoryError("Invalid args")
            path = repo.path(args[0], args[1])
            return "No path" if path is None else "Path: " + "->".join(path)
        if command == "ancestors":
            commit_hash = self._one_argument(args)
            return self._format_commits(repo.ancestors(commit_hash), "No ancestors")
        if command == "search":
            value = self._one_argument(args)
            by_author = value.startswith("--author=")
            if value.startswith("--") and not by_author:
                raise RepositoryError("Invalid args")
            query = value.partition("=")[2] if by_author else value
            matches = repo.search(query, author=by_author)
            if not matches:
                return "No matches"
            noun = "commit" if len(matches) == 1 else "commits"
            return f"Found {len(matches)} {noun}:\n\n" + self._format_commits(matches, "No matches")
        return f"Unknown command: {command}"


def run_repl(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    """EOF·Ctrl+C·exit·quit로 종료한다. 테스트에서는 입출력 스트림을 바꿀 수 있다."""
    source = input_stream if input_stream is not None else sys.stdin
    target = output_stream if output_stream is not None else sys.stdout
    cli = MiniGitCLI()
    print("Mini Git — HELP로 명령어를 확인하세요.", file=target)
    while cli.running:
        print("mini-git> ", end="", flush=True, file=target)
        try:
            line = source.readline()
            if not line:
                print("\nBye.", file=target)
                break
            result = cli.execute(line)
        except KeyboardInterrupt:
            print("\nBye.", file=target)
            break
        if result:
            print(result, file=target)
