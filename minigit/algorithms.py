"""표준 정렬 API나 그래프 라이브러리 없이 구현한 정렬·탐색 알고리즘."""

from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TypeVar

T = TypeVar("T")


def merge_sort(items: Iterable[T], key: Callable[[T], object]) -> list[T]:
    """안정적인 반복형 병합 정렬. 시간 O(n log n), 추가 공간 O(n)."""
    source = list(items)
    size = len(source)
    target = source.copy()
    width = 1
    while width < size:
        for start in range(0, size, width * 2):
            middle = min(start + width, size)
            end = min(start + width * 2, size)
            left, right = start, middle
            for position in range(start, end):
                # 같을 때 왼쪽 원소를 먼저 선택해야 입력 순서가 유지된다.
                if left < middle and (
                    right >= end or key(source[left]) <= key(source[right])
                ):
                    target[position] = source[left]
                    left += 1
                else:
                    target[position] = source[right]
                    right += 1
        source, target = target, source
        width *= 2
    return source


def topological_order(
    parents: Mapping[str, Sequence[str]],
    children: Mapping[str, Sequence[str]],
) -> list[str]:
    """Kahn 알고리즘으로 모든 부모를 자식보다 먼저 반환한다. O(V + E)."""
    indegree = {node: len(links) for node, links in parents.items()}
    ready = deque(node for node, degree in indegree.items() if degree == 0)
    result = []
    while ready:
        node = ready.popleft()
        result.append(node)
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if len(result) != len(parents):
        raise ValueError("Commit graph contains a cycle")
    return result


def shortest_path(
    parents: Mapping[str, Sequence[str]],
    children: Mapping[str, Sequence[str]],
    start: str,
    end: str,
) -> list[str] | None:
    """무방향 BFS 거리와 탐욕 선택으로 사전순 최소 최단 경로를 구한다.

    Repository의 고정 길이 hash에서는 다음 hash의 사전순 비교가 전체
    'hash1->hash2->...' 문자열의 비교와 같다. 시간·공간 O(V + E).
    """
    if start == end:
        return [start]
    distance = {end: 0}
    pending = deque([end])
    while pending:
        node = pending.popleft()
        for neighbor in (*parents[node], *children[node]):
            if neighbor not in distance:
                distance[neighbor] = distance[node] + 1
                pending.append(neighbor)
    if start not in distance:
        return None

    path = [start]
    while path[-1] != end:
        node = path[-1]
        # 거리 1 감소 조건으로 최단성을, 최소 hash 선택으로 동률 규칙을 보장한다.
        next_node = min(
            neighbor
            for neighbor in (*parents[node], *children[node])
            if distance[neighbor] == distance[node] - 1
        )
        path.append(next_node)
    return path


def ancestor_ids(parents: Mapping[str, Sequence[str]], start: str) -> list[str]:
    """재귀 없는 DFS로 자기 자신을 제외한 모든 조상을 한 번씩 반환한다."""
    visited = {start}
    pending = list(parents[start])
    result = []
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        result.append(node)
        pending.extend(parents[node])
    return result
