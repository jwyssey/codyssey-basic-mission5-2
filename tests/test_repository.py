"""평가표의 저장소 기능과 자료구조 불변 조건을 검증한다."""

import unittest
from datetime import datetime, timedelta, timezone

from minigit import Repository, RepositoryError
from minigit.models import Commit, CommitGraph


class LookupOnlyDict(dict):
    """검색 중 전체 저장소를 순회하면 실패하게 하는 테스트용 dict."""

    def __iter__(self):
        raise AssertionError("Full commit scan is forbidden during search")

    def values(self):
        raise AssertionError("Full commit scan is forbidden during search")

    def items(self):
        raise AssertionError("Full commit scan is forbidden during search")


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
        self.repo = Repository(clock=lambda: self.now)
        self.repo.initialize("Alice Smith")

    def test_initialization(self):
        self.assertEqual(self.repo.branches, {"main": None})
        self.assertEqual(self.repo.current_branch, "main")
        self.assertEqual(self.repo.current_user, "Alice Smith")
        self.assertIsNone(self.repo.head)
        self.assertEqual(self.repo.log(), [])

    def test_branch_switch_and_commit_update_only_current_branch(self):
        root = self.repo.commit("Initial commit")
        self.repo.branch("feature")
        self.assertEqual(self.repo.current_branch, "main")
        self.assertEqual(self.repo.branches["feature"], root.hash)
        self.repo.switch("feature")
        child = self.repo.commit("Add login feature")
        self.assertEqual(child.parents, (root.hash,))
        self.assertEqual(self.repo.head, child.hash)
        self.assertEqual(self.repo.branches["main"], root.hash)

    def test_empty_branch_can_have_a_separate_root(self):
        self.repo.branch("orphan")
        first = self.repo.commit("First root")
        self.repo.switch("orphan")
        second = self.repo.commit("Second root")
        self.assertEqual(first.parents, ())
        self.assertEqual(second.parents, ())
        self.assertIsNone(self.repo.path(first.hash, second.hash))

    def test_hash_unique_across_reinitialization(self):
        first = self.repo.commit("Before reset")
        self.repo.initialize("Bob")
        self.assertEqual(self.repo.commits, {})
        self.assertEqual(self.repo.graph.parents, {})
        self.assertEqual(self.repo.index.keywords, {})
        second = self.repo.commit("After reset")
        self.assertNotEqual(first.hash, second.hash)
        self.assertEqual(len(first.hash), len(second.hash))
        self.assertEqual(self.repo.search("before"), [])

    def test_invalid_reinitialize_preserves_state(self):
        commit = self.repo.commit("Keep me")
        with self.assertRaisesRegex(RepositoryError, "Invalid args"):
            self.repo.initialize("  ")
        self.assertEqual(self.repo.head, commit.hash)

    def test_hash_exhaustion_does_not_change_state(self):
        self.repo._next_id = 0xFFFFFFFF
        last = self.repo.commit("Last available identifier")
        with self.assertRaisesRegex(RepositoryError, "exhausted"):
            self.repo.commit("Cannot create")
        self.assertEqual(self.repo.head, last.hash)
        self.assertEqual(len(self.repo.commits), 1)

    def test_keyword_normalization_duplicates_and_punctuation(self):
        first = self.repo.commit("Login LOGIN feature")
        second = self.repo.commit("login, bugfix")
        self.assertEqual(self.repo.search("LOGIN"), [first])
        self.assertEqual(self.repo.search("login,"), [second])
        self.assertEqual(self.repo.index.keywords["login"], {first.hash})

    def test_multiple_keywords_use_and(self):
        first = self.repo.commit("Add login feature")
        self.repo.commit("Add login tests")
        self.assertEqual(self.repo.search("FEATURE login login"), [first])
        self.assertEqual(self.repo.search("login missing"), [])

    def test_author_search_exact_and_user_change_preserves_history(self):
        first = self.repo.commit("Alice work")
        self.repo.set_user("Bob")
        second = self.repo.commit("Bob work")
        self.assertEqual(second.parents, (first.hash,))
        self.assertEqual(first.author, "Alice Smith")
        self.assertEqual(self.repo.search("Alice Smith", author=True), [first])
        self.assertEqual(self.repo.search("Bob", author=True), [second])
        self.assertEqual(self.repo.search("bob", author=True), [])

    def test_search_does_not_scan_all_commits(self):
        match = self.repo.commit("Needle")
        self.repo.set_user("Bob")
        self.repo.commit("Other message")
        self.repo.commits = LookupOnlyDict(self.repo.commits)
        self.assertEqual(self.repo.search("needle"), [match])
        self.assertEqual(self.repo.search("Alice Smith", author=True), [match])
        self.assertEqual(self.repo.search("missing"), [])

    def test_date_sort_is_ascending_and_stable(self):
        first = self.repo.commit("First")
        self.now -= timedelta(days=1)
        second = self.repo.commit("Clock went backwards")
        third = self.repo.commit("Same time")
        self.assertEqual(self.repo.log("date"), [second, third, first])
        # 기본 LOG는 시계가 거꾸로 가도 부모-자식 순서를 유지한다.
        self.assertEqual(self.repo.log(), [first, second, third])

    def test_author_sort_is_ascending_and_stable(self):
        self.repo.set_user("Zoe")
        first = self.repo.commit("First")
        self.repo.set_user("Alice")
        second = self.repo.commit("Second")
        third = self.repo.commit("Third")
        self.assertEqual(self.repo.log("author"), [second, third, first])

    def _make_merge(self):
        root = self.repo.commit("Root")
        self.repo.branch("feature")
        self.repo.switch("feature")
        left = self.repo.commit("Left")
        self.repo.switch("main")
        right = self.repo.commit("Right")
        merge = self.repo.merge("feature")
        return root, left, right, merge

    def test_merge_has_two_parents_and_updates_index(self):
        root, left, right, merge = self._make_merge()
        self.assertEqual(merge.parents, (right.hash, left.hash))
        self.assertEqual(self.repo.head, merge.hash)
        self.assertEqual(self.repo.branches["feature"], left.hash)
        self.assertEqual(self.repo.search("merge"), [merge])
        self.assertEqual(self.repo.graph.children[root.hash], [left.hash, right.hash])

    def test_log_includes_all_branches_and_parent_first_after_merge(self):
        root, left, right, merge = self._make_merge()
        log = self.repo.log()
        positions = {commit.hash: index for index, commit in enumerate(log)}
        self.assertEqual(len(log), 4)
        for commit in log:
            for parent in commit.parents:
                self.assertLess(positions[parent], positions[commit.hash])

    def test_merge_ancestors_include_both_branches_once(self):
        root, left, right, merge = self._make_merge()
        self.assertEqual(self.repo.ancestors(merge.hash), [root, left, right])

    def test_path_lexicographic_tie_in_both_directions(self):
        root, left, right, merge = self._make_merge()
        self.assertEqual(self.repo.path(left.hash, right.hash), [left.hash, root.hash, right.hash])
        self.assertEqual(self.repo.path(root.hash, merge.hash), [root.hash, left.hash, merge.hash])
        self.assertEqual(self.repo.path(merge.hash, root.hash), [merge.hash, left.hash, root.hash])

    def test_unknown_commit_differs_from_no_path(self):
        commit = self.repo.commit("Root")
        with self.assertRaisesRegex(RepositoryError, "Unknown commit: missing"):
            self.repo.path(commit.hash, "missing")
        with self.assertRaisesRegex(RepositoryError, "Unknown commit: missing"):
            self.repo.ancestors("missing")

    def test_bad_branch_operations_leave_state_unchanged(self):
        root = self.repo.commit("Root")
        for operation, error in (
            (lambda: self.repo.branch("main"), "Branch already exists"),
            (lambda: self.repo.switch("missing"), "Unknown branch"),
            (lambda: self.repo.branch(" "), "Invalid args"),
        ):
            with self.assertRaisesRegex(RepositoryError, error):
                operation()
        self.assertEqual(self.repo.current_branch, "main")
        self.assertEqual(self.repo.head, root.hash)
        self.assertEqual(self.repo.branches, {"main": root.hash})

    def test_invalid_merge_preserves_state(self):
        for branch, error in (("missing", "Unknown branch"), ("main", "empty branch")):
            with self.assertRaisesRegex(RepositoryError, error):
                self.repo.merge(branch)
        root = self.repo.commit("Root")
        self.repo.branch("same")
        for branch in ("main", "same"):
            with self.assertRaisesRegex(RepositoryError, "identical heads"):
                self.repo.merge(branch)
        self.assertEqual(self.repo.head, root.hash)
        self.assertEqual(len(self.repo.commits), 1)

    def test_commands_require_initialization(self):
        repo = Repository()
        operations = (
            lambda: repo.branch("feature"), lambda: repo.switch("main"),
            lambda: repo.commit("Message"), lambda: repo.log(),
            lambda: repo.path("a", "b"), lambda: repo.ancestors("a"),
            lambda: repo.search("word"), lambda: repo.set_user("Bob"),
            lambda: repo.merge("main"),
        )
        for operation in operations:
            with self.assertRaisesRegex(RepositoryError, "Repository not initialized"):
                operation()

    def test_invalid_search_and_sort_options(self):
        for operation in (lambda: self.repo.search(" "), lambda: self.repo.log("unknown")):
            with self.assertRaisesRegex(RepositoryError, "Invalid args"):
                operation()


class CommitGraphTests(unittest.TestCase):
    def test_graph_rejects_invalid_links_before_mutating(self):
        graph = CommitGraph()
        stamp = datetime(2026, 10, 8, tzinfo=timezone.utc)
        root = Commit("01", "Root", "Alice", stamp, ())
        graph.add(root)
        invalid = (
            root,
            Commit("02", "Self", "Alice", stamp, ("02",)),
            Commit("02", "Missing", "Alice", stamp, ("missing",)),
            Commit("02", "Repeated", "Alice", stamp, ("01", "01")),
        )
        for commit in invalid:
            with self.assertRaises(ValueError):
                graph.add(commit)
        self.assertEqual(graph.parents, {"01": ()})
        self.assertEqual(graph.children, {"01": []})
