"""알고리즘의 정렬 안정성·경로 동률·사이클 검출 등을 검증한다."""

import unittest
from itertools import permutations

from minigit.algorithms import ancestor_ids, merge_sort, shortest_path, topological_order


class MergeSortTests(unittest.TestCase):
    def test_empty_and_single_item(self):
        self.assertEqual(merge_sort([], key=lambda item: item), [])
        self.assertEqual(merge_sort([7], key=lambda item: item), [7])

    def test_all_permutations_of_six_values(self):
        expected = list(range(6))
        for values in permutations(expected):
            self.assertEqual(merge_sort(values, key=lambda item: item), expected)

    def test_stability_and_input_unchanged(self):
        values = [("b", 1), ("a", 2), ("b", 3), ("a", 4), ("b", 5)]
        original = values.copy()
        self.assertEqual(
            merge_sort(values, key=lambda item: item[0]),
            [("a", 2), ("a", 4), ("b", 1), ("b", 3), ("b", 5)],
        )
        self.assertEqual(values, original)


class GraphAlgorithmTests(unittest.TestCase):
    def setUp(self):
        # 자식 인접 목록의 입력 순서는 사전순과 반대로 두어 동률 처리를 확인한다.
        self.parents = {"01": (), "02": ("01",), "03": ("01",), "04": ("03", "02")}
        self.children = {"01": ["03", "02"], "02": ["04"], "03": ["04"], "04": []}

    def test_topological_order_respects_every_parent(self):
        order = topological_order(self.parents, self.children)
        positions = {node: index for index, node in enumerate(order)}
        self.assertEqual(set(order), set(self.parents))
        for child, parents in self.parents.items():
            for parent in parents:
                self.assertLess(positions[parent], positions[child])

    def test_empty_topological_order(self):
        self.assertEqual(topological_order({}, {}), [])

    def test_cycle_detected(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            topological_order({"01": ("02",), "02": ("01",)}, {"01": ["02"], "02": ["01"]})

    def test_lexicographically_smallest_shortest_path(self):
        self.assertEqual(shortest_path(self.parents, self.children, "01", "04"), ["01", "02", "04"])

    def test_path_uses_edges_in_both_directions(self):
        self.assertEqual(shortest_path(self.parents, self.children, "02", "03"), ["02", "01", "03"])

    def test_identical_endpoints(self):
        self.assertEqual(shortest_path(self.parents, self.children, "02", "02"), ["02"])

    def test_disconnected_nodes(self):
        self.parents["05"] = ()
        self.children["05"] = []
        self.assertIsNone(shortest_path(self.parents, self.children, "01", "05"))

    def test_all_ancestors_without_duplicates_or_self(self):
        result = ancestor_ids(self.parents, "04")
        self.assertEqual(set(result), {"01", "02", "03"})
        self.assertEqual(len(result), 3)
        self.assertEqual(ancestor_ids(self.parents, "01"), [])

    def test_long_history_does_not_recurse(self):
        parents = {str(node): (() if node == 0 else (str(node - 1),)) for node in range(2000)}
        self.assertEqual(len(ancestor_ids(parents, "1999")), 1999)
