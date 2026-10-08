# Mini Git 평가표 답변

평가표의 **4개 항목, 20개 질문을 원래 순서대로** 정리했습니다. 각 답변은 실제 구현 방식, 확인 방법, 필요한 알고리즘 설명을 함께 제공합니다.

## 먼저 실행해 보기

이 문서가 있는 저장소 폴더에서 실행합니다. 외부 패키지는 필요하지 않습니다.

```bash
python main.py
python main.py < examples/demo.commands
python main.py < examples/no-path.commands
python -m unittest discover -s tests -v
```

`demo.commands`는 분기·병합·검색·정렬을, `no-path.commands`는 연결되지 않은 커밋을 확인하는 예제입니다. Python 3.13.5에서 **44개 테스트가 모두 통과**했습니다.

설명을 위한 기본 예제의 커밋은 다음과 같습니다. 그림의 화살표는 부모에서 자식 방향입니다.

```text
                    c00000002
                   /          \
       c00000001 --             c00000004
                   \          /
                    c00000003
```

| hash | 작성자 | 메시지 | 부모 |
| --- | --- | --- | --- |
| `c00000001` | Alice Smith | Initial commit | 없음 |
| `c00000002` | Bob Lee | Add login feature | `c00000001` |
| `c00000003` | Alice Smith | Add payment feature | `c00000001` |
| `c00000004` | Alice Smith | Merge branch 'feature' | `c00000003`, `c00000002` |

## 항목 1 — 기능 동작

### 1.1 INIT <user_name> 실행 후 main 브랜치/HEAD/현재 사용자 설정이 정상적으로 초기화되어 있는가?

**답변:** 정상적으로 초기화됩니다. `INIT "Alice Smith"`를 실행하면 브랜치 목록은 `{"main": None}`, 현재 브랜치는 `main`, 현재 사용자는 `Alice Smith`가 됩니다. 아직 커밋이 없으므로 HEAD는 `None`입니다. 첫 `COMMIT`을 생성하면 HEAD가 그 커밋의 hash를 가리킵니다.

`INIT`을 다시 실행하면 기존 커밋·브랜치·그래프·역색인을 비웁니다. 다만 같은 세션에서 hash가 재사용되지 않도록 카운터는 유지합니다. 이름이 비어 있는 잘못된 입력은 상태를 바꾸기 전에 거부합니다.

**코드:** [repository.py](minigit/repository.py)의 `Repository.initialize`, `head`.

**확인:** [test_repository.py](tests/test_repository.py)의 `test_initialization`, `test_hash_unique_across_reinitialization`, `test_invalid_reinitialize_preserves_state`.

### 1.2 BRANCH <name> 생성 후 SWITCH <name> 로 전환되며, 이후 COMMIT 이 해당 브랜치에 반영되는가?

**답변:** 새 브랜치는 현재 HEAD를 복사해 가리킵니다. `BRANCH feature` 자체는 현재 브랜치를 바꾸지 않습니다. `SWITCH feature`로 전환한 뒤 커밋하면 `feature`의 포인터만 새 커밋으로 이동하며 `main`은 기존 커밋을 유지합니다.

예를 들어 `main`의 첫 커밋이 `c00000001`이라면, feature에서 만든 `c00000002`의 부모는 `c00000001`입니다. 이때 `main`은 여전히 `c00000001`을 가리킵니다.

**코드:** [repository.py](minigit/repository.py)의 `branch`, `switch`, `commit`, `_create_commit`.

**확인:** `test_branch_switch_and_commit_update_only_current_branch`. 중복 브랜치와 없는 브랜치도 `test_bad_branch_operations_leave_state_unchanged`에서 검사합니다.

### 1.3 LOG 가 "부모 커밋이 자식 커밋보다 먼저" 출력되도록 동작하는가?

**답변:** 기본 `LOG`는 Kahn 위상 정렬을 사용하므로 모든 부모가 출력된 뒤에 자식을 출력합니다. 현재 브랜치뿐 아니라 저장소의 모든 커밋을 보여 줍니다.

예제의 출력 순서는 `c00000001 → c00000002 → c00000003 → c00000004`입니다. 병합 커밋 `c00000004`도 두 부모가 모두 출력된 뒤에 나옵니다. 커밋의 hash·작성자·timestamp·메시지를 표시하며, 브랜치 끝에는 브랜치명과 HEAD도 표시합니다.

시계가 뒤로 움직여 자식의 timestamp가 부모보다 작아져도 기본 LOG는 관계를 기준으로 출력하므로 부모가 먼저 나옵니다. `LOG --sort-by=...`는 명세의 별도 정렬 기준을 적용합니다.

**코드:** [algorithms.py](minigit/algorithms.py)의 `topological_order`, [cli.py](minigit/cli.py)의 `_format_commits`.

**확인:** `test_log_includes_all_branches_and_parent_first_after_merge`, `test_date_sort_is_ascending_and_stable`, `test_log_includes_identifiable_fields_and_head`.

### 1.4 PATH <a> <b> 가 경로가 있으면 최단 경로를, 없으면 No path 를 출력하는가?

**답변:** 부모 연결을 무방향 간선으로 보고 BFS로 최단 거리를 구합니다. 같은 최단 길이의 경로가 여럿이면 전체 `hash1->hash2->...` 문자열의 사전순이 가장 작은 경로를 선택합니다.

예제에서 `PATH c00000002 c00000003`에는 공통 부모와 병합 커밋을 각각 거치는 두 경로가 있습니다. 둘 다 간선이 2개지만, `c00000001`이 `c00000004`보다 사전순으로 작으므로 결과는 다음과 같습니다.

```text
Path: c00000002->c00000001->c00000003
```

연결되지 않은 유효한 두 커밋에는 `No path`를 출력합니다. 없는 hash에는 `Unknown commit: <hash>`를 출력합니다. 시작과 끝이 같으면 그 커밋 하나를 출력하며 간선 수는 0입니다.

**코드:** [algorithms.py](minigit/algorithms.py)의 `shortest_path`, [repository.py](minigit/repository.py)의 `path`.

**확인:** `test_path_lexicographic_tie_in_both_directions`, `test_disconnected_nodes`, `test_identical_endpoints`, `test_unknown_commit_differs_from_no_path`. CLI의 `No path` 출력은 `test_no_path_and_same_commit_output`과 [no-path.commands](examples/no-path.commands)로 확인합니다.

### 1.5 ANCESTORS <hash> 가 모든 조상을 빠짐없이 출력하는가?

**답변:** 부모 방향으로 반복형 DFS를 수행해 도달 가능한 모든 조상을 찾습니다. 방문 집합으로 공통 조상의 중복을 막고, 시작 커밋은 결과에서 제외합니다. 출력은 hash 오름차순입니다.

`ANCESTORS c00000004`는 두 부모인 `c00000002`·`c00000003`과 그 공통 부모인 `c00000001`을 각각 한 번씩 출력합니다. 루트 커밋에는 `No ancestors`를 출력합니다.

재귀 대신 리스트 스택을 사용하므로 이력이 깊어져도 Python의 재귀 깊이 제한에 걸리지 않습니다.

**코드:** [algorithms.py](minigit/algorithms.py)의 `ancestor_ids`, [repository.py](minigit/repository.py)의 `ancestors`.

**확인:** `test_merge_ancestors_include_both_branches_once`, `test_all_ancestors_without_duplicates_or_self`, `test_long_history_does_not_recurse`. 마지막 테스트는 깊이 2,000의 이력을 검사합니다.

### 1.6 SEARCH <keyword> / SEARCH --author=<name> / LOG --sort-by=date|author 가 요구사항대로 동작하는가?

**답변:** 두 검색은 역색인을 사용하고, 두 정렬은 직접 구현한 안정 병합 정렬을 사용합니다.

| 명령 | 적용 규칙 | 예제 결과 |
| --- | --- | --- |
| `SEARCH LOGIN` | 메시지를 공백 분리·소문자 정규화한 토큰 검색 | `c00000002` |
| `SEARCH "login feature"` | 모든 검색 토큰이 존재하는 AND 검색 | `c00000002` |
| `SEARCH --author="Bob Lee"` | 작성자 이름의 정확한 일치 | `c00000002` |
| `LOG --sort-by=date` | timestamp 오름차순, 동률은 생성 순서 유지 | 통상적인 시계에서는 생성 순서 |
| `LOG --sort-by=author` | 작성자 이름 오름차순, 동률은 생성 순서 유지 | `c00000001`, `c00000003`, `c00000004`, `c00000002` |

키워드는 부분 문자열이 아닌 토큰 단위로 비교합니다. 따라서 `log`는 `login`을 찾지 않으며, 문장부호가 있는 `login,`도 `login`과 다릅니다. 작성자 검색은 대소문자를 구분합니다. 정렬 옵션에는 부모-자식 선후 유지 조건을 추가하지 않았습니다.

**코드:** [index.py](minigit/index.py)의 `tokenize`, `InvertedIndex`; [repository.py](minigit/repository.py)의 `search`, `log`; [algorithms.py](minigit/algorithms.py)의 `merge_sort`.

**확인:** `test_keyword_normalization_duplicates_and_punctuation`, `test_multiple_keywords_use_and`, `test_author_search_exact_and_user_change_preserves_history`, `test_date_sort_is_ascending_and_stable`, `test_author_sort_is_ascending_and_stable`.

## 항목 2 — 구조와 설계

### 2.1 커밋 저장소/브랜치/HEAD/사용자 정보를 어떤 구조로 분리했고, 각 책임을 설명할 수 있는가?

**답변:** `Repository`가 상태를 조합하되 각 정보의 책임은 나누었습니다.

| 구조 | 예시 | 책임 |
| --- | --- | --- |
| `commits: dict[str, Commit]` | `hash → Commit` | 커밋 메타데이터 저장·조회 |
| `branches: dict[str, str \| None]` | `main → c00000004` | 브랜치가 가리키는 커밋 관리 |
| `current_branch` | `main` | HEAD가 따라가는 현재 브랜치 |
| `head` 프로퍼티 | `branches[current_branch]` | 현재 커밋 조회; 별도 값 중복 저장을 피함 |
| `current_user` | `Alice Smith` | 이후 커밋의 작성자 |
| `CommitGraph` | 부모·자식 인접 목록 | 그래프 관계와 탐색 |
| `InvertedIndex` | 토큰/작성자 → hash 집합 | 검색 후보 조회 |

`Commit`은 `hash`, `message`, `author`, `timestamp`, `parents`를 가진 frozen dataclass입니다. 부모는 tuple이므로 생성된 커밋의 부모 관계를 바꾸지 않습니다. CLI는 입력과 출력을 맡고, Repository는 상태 변경을 맡습니다. `USER`는 이후 커밋의 사용자만 바꾸므로 기존 작성자와 이력은 유지됩니다.

**코드:** [models.py](minigit/models.py), [repository.py](minigit/repository.py), [cli.py](minigit/cli.py).

### 2.2 커밋 hash로 빠르게 조회하기 위해 어떤 키-값 구조를 사용했고, 중복/충돌을 어떻게 방지했는지 설명할 수 있는가?

**답변:** Python `dict`에 `commits[hash] = Commit` 형태로 저장합니다. 키 하나로 조회하므로 평균 시간복잡도는 `O(1)`입니다.

hash는 `c` 뒤에 8자리 16진수 카운터를 붙인 `c00000001`, `c00000002`, … 형태입니다. 생성 성공 후 카운터를 증가시키고, `INIT`에서도 카운터를 초기화하지 않습니다. 따라서 한 REPL 세션에서 기존에 사용한 ID를 재사용하지 않습니다. 8자리 최대값을 넘으면 오류를 내며, 더 긴 ID나 중복 ID를 만들지 않습니다.

`CommitGraph.add`에서도 동일한 hash의 재등록을 검사합니다. 이 식별자는 실제 Git의 콘텐츠 기반 해시와 목적이 다르지만, 세션 내 유일성과 빠른 조회라는 명세는 충족합니다.

**코드:** `_next_id`, `_create_commit`, `get_commit`, `CommitGraph.add`.

**확인:** `test_hash_unique_across_reinitialization`, `test_hash_exhaustion_does_not_change_state`, `test_graph_rejects_invalid_links_before_mutating`.

### 2.3 커밋이 추가될 때 역색인(author/keyword)을 어떤 시점에, 어떤 방식으로 갱신하도록 설계했는지 설명할 수 있는가?

**답변:** 일반 커밋과 병합 커밋이 모두 `_create_commit`을 거칩니다. 커밋을 그래프와 커밋 저장소에 등록한 직후 `index.add(commit)`을 호출하고, 이어서 현재 브랜치의 HEAD를 이동합니다.

역색인 갱신 과정은 다음과 같습니다.

1. `authors[commit.author]` 집합에 새 hash를 추가합니다.
2. 메시지에 `lower().split()`을 적용합니다.
3. 같은 메시지의 중복 단어를 set으로 제거합니다.
4. 각 토큰의 `keywords[token]` 집합에 새 hash를 추가합니다.

예를 들어 `Login LOGIN feature`는 `login`과 `feature` 두 토큰으로 색인됩니다. `login`의 목록에 같은 hash가 두 번 들어가지 않습니다. 다음 검색부터 갱신된 인덱스를 바로 사용하며, 검색할 때 인덱스를 다시 만들지 않습니다.

**코드:** [repository.py](minigit/repository.py)의 `_create_commit`, [index.py](minigit/index.py)의 `InvertedIndex.add`.

**확인:** `test_keyword_normalization_duplicates_and_punctuation`, `test_merge_has_two_parents_and_updates_index`.

### 2.4 LOG, PATH, ANCESTORS 에서 사용하는 그래프 탐색 로직을 어떻게 재사용 가능하게 구성했는지 설명할 수 있는가?

**답변:** 그래프 알고리즘은 입출력이나 CLI 상태를 모르는 독립 함수로 분리했습니다. 모두 `CommitGraph`의 부모·자식 인접 목록을 받아 동작합니다.

| 기능 | 독립 함수 | 반환값 |
| --- | --- | --- |
| LOG | `topological_order(parents, children)` | 부모가 먼저인 hash 목록 |
| PATH | `shortest_path(parents, children, start, end)` | 최단 경로 hash 목록 또는 `None` |
| ANCESTORS | `ancestor_ids(parents, start)` | 중복 없는 조상 hash 목록 |

`CommitGraph`는 이 함수들을 호출하고, `Repository`는 hash를 커밋 정보로 바꾸거나 유효성을 검사합니다. CLI는 반환된 결과를 출력합니다. 따라서 CLI 없이도 작은 그래프를 만들어 알고리즘을 직접 테스트할 수 있습니다.

**코드:** [algorithms.py](minigit/algorithms.py), [models.py](minigit/models.py)의 `CommitGraph`.

**확인:** [test_algorithms.py](tests/test_algorithms.py)는 Repository나 REPL 없이 탐색 함수를 검증합니다.

### 2.5 주요 함수/클래스에 docstring/주석을 어떤 기준으로 작성했는지 설명할 수 있는가?

**답변:** 함수와 클래스의 역할, 반환값과 중요한 규칙을 docstring으로 설명했습니다. 알고리즘에는 시간·공간복잡도와 선택 이유를 덧붙였습니다. 코드만 읽으면 놓치기 쉬운 불변 조건은 해당 위치에 주석으로 남겼습니다.

예를 들어 병합 정렬에서는 **동률이면 왼쪽 원소를 먼저 선택해야 안정성이 유지된다**고 설명합니다. PATH에는 **남은 거리가 1씩 감소해야 최단 경로를 유지한다**는 조건을 남겼습니다. 초기화에는 **세션 내 ID 중복을 막기 위해 카운터를 유지한다**고 적었습니다.

단순 대입을 다시 설명하기보다는, 왜 그 선택을 했는지와 어떤 동작을 보장하는지를 기록했습니다.

**코드:** [algorithms.py](minigit/algorithms.py)의 각 함수, [models.py](minigit/models.py)의 `CommitGraph.add`, [repository.py](minigit/repository.py)의 `initialize`.

## 항목 3 — 알고리즘 이해

### 3.1 커밋 그래프가 왜 DAG여야 하는지, 사이클이 생기면 어떤 문제가 발생하는지 설명할 수 있는가?

**답변:** 커밋의 부모는 그 커밋보다 먼저 존재한 이력입니다. 새 커밋은 이미 등록된 부모만 참조하고 기존 커밋의 부모를 바꾸지 않으므로, 부모를 계속 따라가며 자기 자신으로 돌아올 수 없습니다. 이처럼 방향이 있고 순환이 없는 그래프가 DAG입니다.

브랜치가 나뉘고 병합되어도 부모는 항상 과거의 커밋이므로 DAG를 유지합니다. 병합이 만드는 마름모 모양은 무방향으로 보면 순환 경로가 있지만, 부모 방향을 따라 돌아오는 **방향성 사이클**은 없습니다.

사이클이 있다면 A가 B보다 먼저, 동시에 B가 A보다 먼저 출력되어야 하는 모순이 생겨 위상 정렬을 완성할 수 없습니다. 방문 검사가 없는 조상 탐색은 무한 반복할 수도 있습니다. 방문 검사가 있어도 잘못된 이력 관계 자체는 해결되지 않습니다.

구현에서는 새 노드의 부모가 모두 기존 노드인지 검사합니다. Kahn 알고리즘도 출력한 노드 수가 전체보다 작으면 사이클 오류를 냅니다.

**코드·확인:** `CommitGraph.add`, `topological_order`, `test_cycle_detected`, `test_graph_rejects_invalid_links_before_mutating`.

### 3.2 LOG 에서 "부모가 먼저" 조건을 만족시키기 위해 어떤 접근(예: 위상 정렬 성격의 출력)을 적용했는지 설명할 수 있는가?

**답변:** Kahn 위상 정렬을 적용했습니다. 부모에서 자식으로 향하는 관계를 기준으로, 각 커밋의 아직 처리되지 않은 부모 수를 진입 차수로 사용합니다.

1. 각 커밋의 진입 차수를 부모 수로 설정합니다.
2. 부모가 없는 커밋을 deque에 넣습니다.
3. 큐에서 커밋 하나를 꺼내 출력 순서에 추가합니다.
4. 그 커밋의 자식들에게 남은 부모 수를 1씩 줄입니다.
5. 남은 부모 수가 0이 된 자식을 큐에 넣습니다.

두 부모를 가진 병합 커밋은 두 부모가 모두 처리돼야 큐에 들어갑니다. 그래서 timestamp나 브랜치 이름에 의존하지 않고 부모 선행 조건을 보장합니다.

커밋 수를 `V`, 부모 연결 수를 `E`라고 하면 각 노드와 간선을 한 번씩 처리하므로 시간은 **`O(V + E)`**, 그래프를 제외한 추가 공간은 **`O(V)`**입니다.

**코드·확인:** `topological_order`, `test_topological_order_respects_every_parent`.

### 3.3 PATH 에서 최단 경로를 찾기 위해 어떤 알고리즘(예: BFS)을 선택했고, 간선을 무방향으로 정의한 이유를 설명할 수 있는가?

**답변:** 모든 간선의 비용이 1이므로 BFS를 선택했습니다. BFS는 가까운 노드부터 층별로 방문해 최소 간선 수를 계산합니다. 간선을 무방향으로 보는 것은 명세의 정의이며, 부모와 자식 양쪽으로 이동해 서로 다른 브랜치의 커밋도 연결할 수 있습니다.

동률 규칙까지 보장하기 위해 다음 두 단계를 사용합니다.

1. **목적지에서 BFS:** 각 커밋에서 목적지까지의 최단 거리를 기록합니다.
2. **시작점에서 경로 복원:** 이웃 중 거리가 정확히 1 작은 노드만 후보로 삼고, 그중 hash가 가장 작은 노드를 선택합니다.

거리를 1씩 줄이므로 경로 길이는 항상 최단입니다. 모든 hash가 같은 길이이므로, 경로가 처음 갈라지는 위치에서 작은 hash를 고르면 전체 `hash1->hash2->...` 문자열도 가장 작습니다. 방문 순서나 set의 순서에 결과가 좌우되지 않습니다.

부모와 자식 인접 목록을 함께 보관하기 때문에 이웃을 찾기 위해 전체 커밋을 순회하지 않습니다. 시간복잡도는 **`O(V + E)`**, 추가 공간은 **`O(V)`**입니다. 실제로는 목적지와 연결된 부분을 탐색합니다.

**코드·확인:** `shortest_path`, `test_lexicographically_smallest_shortest_path`, `test_path_uses_edges_in_both_directions`, `test_path_lexicographic_tie_in_both_directions`.

### 3.4 정렬 알고리즘의 평균/최악 시간복잡도와 안정 정렬 여부를 설명할 수 있는가?

**답변:** 반복형 병합 정렬을 직접 구현했습니다. 길이 1인 구간부터 시작해 정렬된 두 구간을 병합하고, 구간 크기를 2·4·8·…로 늘립니다. 재귀나 표준 정렬 API는 사용하지 않습니다.

| 성질 | 내용 |
| --- | --- |
| 평균 시간 | `O(n log n)` |
| 최악 시간 | `O(n log n)` |
| 최선 시간 | 현재 구현에서도 `O(n log n)` |
| 추가 공간 | `O(n)` |
| 안정성 | 안정 정렬 |
| 입력 변경 | 원본 입력을 변경하지 않음 |

각 단계에서 전체 원소를 한 번씩 처리하며 단계 수는 약 `log₂ n`입니다. 같은 키를 비교할 때 왼쪽 구간의 원소를 먼저 선택하므로 원래 순서를 유지합니다. Repository는 커밋 생성 순서대로 정렬 입력을 구성하므로 날짜나 작성자가 같으면 생성 순서가 유지됩니다.

`key` 함수만 바꿔 timestamp·author·hash 정렬에 같은 알고리즘을 재사용합니다.

**코드·확인:** `merge_sort`, `test_stability_and_input_unchanged`, `test_all_permutations_of_six_values`, `test_no_standard_sort_api_used_in_implementation`.

### 3.5 역색인이 순회 검색보다 빠른 이유를, 자료구조/시간복잡도 관점에서 설명할 수 있는가?

**답변:** 순회 검색은 검색할 때마다 모든 커밋의 메시지나 작성자를 확인합니다. 역색인은 커밋을 만들 때 미리 **검색어 → 그 검색어가 있는 커밋 hash 집합**을 기록합니다. 검색할 때는 dict에서 해당 집합을 바로 찾고, 결과에 해당하는 커밋만 조회합니다.

예를 들어 커밋 10,000개 중 `login`이 3개에만 있다면, 검색 결과를 만들기 위해 10,000개를 훑지 않고 그 3개만 가져옵니다.

전체 커밋 수를 `V`, 결과 수를 `k`라고 할 때 일반적인 평균 복잡도는 다음과 같습니다. 문자열을 읽고 정규화하는 비용은 별도로 필요합니다.

| 방식 | 후보 찾기·가져오기 | 현재 구현의 결과 정렬까지 포함 |
| --- | --- | --- |
| 전체 작성자 순회 | `O(V)` | 결과 정렬 시 `O(V + k log k)` |
| 전체 메시지 순회 | 모든 메시지의 총 길이에 비례 | 전체 순회 비용 + `O(k log k)` |
| 단일 토큰/작성자 역색인 | dict 조회 평균 `O(1)`, 집합 복사·커밋 조회 `O(k)` | `O(k + k log k)` |

여러 단어는 각 토큰의 집합을 가져와 가장 작은 집합부터 교집합을 계산합니다. 단어 수가 `m`, 가장 작은 후보 집합의 크기가 `s`라면 평균적인 교집합 작업의 상한은 `O(m × s)`이며, 이후 결과를 정렬합니다.

결과가 전체 커밋에 가까우면 역색인의 이득도 작아집니다. 빠른 검색을 위해 인덱스를 저장하는 메모리와 커밋 생성 시 토큰화 비용을 지불하는 구조입니다. 검색 전체를 무조건 `O(1)`이라고 부를 수는 없습니다.

**코드·확인:** `InvertedIndex`, `Repository.search`. `test_search_does_not_scan_all_commits`는 커밋 dict의 전체 순회 메서드가 호출되면 실패하도록 만들어 실제 순회 여부를 검증합니다.

## 항목 4 — 확장과 변경 대응

### 4.1 커밋 수가 10배 늘어났을 때 병목이 될 지점을 예측하고, 개선 방향(자료구조/알고리즘)을 설명할 수 있는가?

**답변:** 현재 CLI는 커밋당 부모가 최대 2개이므로 간선 수도 커밋 수에 비례합니다. 메시지 길이가 비슷하다는 가정에서는 다음 지점이 커집니다.

| 작업 | 현재 비용 | 10배 증가 시 예상 | 개선 방향 |
| --- | --- | --- | --- |
| 기본 LOG | `O(V + E)` + 출력 | 탐색·출력량 약 10배 | 결과 스트리밍, 출력 페이지 나누기 |
| PATH | `O(V + E)` | 연결된 그래프가 커지면 약 10배 | 거리 계산 조기 종료, 반복 질의 캐시, 양방향 BFS |
| 날짜/작성자 LOG | `O(V log V)` | 보통 10배보다 더 증가 | 변경 없을 때 정렬 결과 재사용 |
| ANCESTORS | `O(A + Eₐ)` + `O(A log A)` 정렬 | 조상 수에 따라 증가 | 필요한 출력량 제한, 자주 조회하는 조상 결과 캐시 |
| SEARCH | 후보 크기·결과 수에 비례 | 희귀 토큰은 영향 작고 흔한 토큰은 큼 | 결과 페이지 나누기, 큰 posting 집합 표현 개선 |
| 메모리 | 그래프·커밋·인덱스 전체 | 비슷한 데이터면 약 10배 | 내부 정수 ID, 압축된 posting 목록, 영속 저장 구조 검토 |

여기서 `A`는 해당 커밋의 조상 수, `Eₐ`는 그 조상 탐색에서 방문한 간선 수입니다. 출력해야 할 결과 자체가 10배면 출력 시간은 알고리즘만으로 없앨 수 없습니다.

양방향 BFS로 PATH를 개선할 경우 첫 만남에서 무조건 종료하면 사전순 동률 규칙을 놓칠 수 있습니다. 필요한 거리 정보를 확보한 뒤 같은 규칙으로 경로를 복원해야 합니다. 캐시는 커밋 추가·INIT 시 갱신하거나 무효화해야 합니다.

개선 우선순위는 먼저 실제 크기의 데이터로 시간·메모리를 측정하고, 병목이 출력인지 탐색인지 정렬인지 확인한 뒤 정합니다. 위 내용은 확장 설계 제안이며 현재 구현에 추가한 기능은 아닙니다.

### 4.2 PATH 의 간선 정의를 "부모 방향만 허용"으로 바꾸면 결과가 어떻게 달라지고, 구현은 무엇을 바꿔야 하는지 설명할 수 있는가?

**답변:** 출발 커밋에서 조상 쪽으로만 이동할 수 있습니다. 예제의 `c00000002 → c00000003`은 공통 부모에서 다른 자식으로 내려가야 하므로 `No path`가 됩니다. 반대로 `c00000004 → c00000001`은 부모를 따라갈 수 있어 경로가 있습니다. 부모에서 자식으로 향하는 `c00000001 → c00000004`는 경로가 없습니다.

현재 구현은 **목적지에서 BFS**를 하기 때문에 두 부분을 구분해서 바꿔야 합니다.

- 목적지에서 거리 계산을 할 때는 허용된 간선의 역방향인 **children**만 따라갑니다. 그래야 어떤 노드가 부모 방향으로 목적지에 도달할 수 있는지 알 수 있습니다.
- 시작점에서 경로를 복원할 때는 허용된 정방향인 **parents**만 후보로 선택합니다. 거리가 1 감소하는 후보 중 가장 작은 hash를 고릅니다.

목적지에서 시작하는 BFS까지 parents로 바꾸면 출발점에서 도달 가능한 조상을 찾는 문제와 방향이 뒤집힙니다. 이 부분이 변경 시 주의할 점입니다. 대안으로 출발점에서 parents만 따라 BFS하는 방식으로 다시 구성할 수도 있습니다.

**변경 위치:** [algorithms.py](minigit/algorithms.py)의 `shortest_path` 안에 있는 BFS 이웃 선택과 경로 복원 후보 선택.

### 4.3 LOG --sort-by=author 요구사항이 "부모-자식 선후도 유지"로 강화된다면, 어떤 전략으로 해결할지 설명할 수 있는가?

**답변:** 위상 정렬에서 **현재 출력 가능한 커밋 중 작성자가 가장 앞선 커밋**을 선택하도록 바꿉니다. 부모가 전부 처리된 커밋만 후보에 넣고, 후보 선택 기준을 `(author, hash)`로 두면 부모 선행 조건과 결정적인 동률 처리를 함께 만족시킬 수 있습니다.

1. Kahn 알고리즘처럼 부모 수를 계산합니다.
2. 부모 수가 0인 커밋을 후보 집합에 넣습니다.
3. 후보 중 작성자 이름이 가장 작은 커밋을 출력합니다.
4. 자식의 남은 부모 수를 줄이고, 0이 되면 후보에 넣습니다.

표준 정렬 API 금지 조건을 유지한다면 **최소 힙을 직접 구현**해 후보를 관리할 수 있습니다. 각 노드는 힙에 한 번 들어갔다가 나오므로 시간은 `O(E + V log V)`입니다. 학습용으로 후보 목록에서 매번 최솟값을 찾는 방법도 가능하지만, 최악에는 `O(V² + E)`이므로 규모가 커질 때 불리합니다.

전역 작성자 오름차순을 항상 만족시키는 것은 불가능합니다. 예를 들어 부모가 `Zoe`, 자식이 `Alice`라면 부모 선행 조건상 Zoe가 먼저 나와야 합니다. 따라서 강화된 규칙은 **부모 제약을 우선하고, 동시에 출력 가능한 커밋 사이에서 작성자 순서를 적용한다**고 정의해야 합니다.

현재의 author 로그는 전체 커밋을 병합 정렬합니다. 위 전략을 적용하려면 `Repository.log`의 author 분기를 작성자 우선 위상 정렬 함수 호출로 바꿉니다.

### 4.4 해시 생성 방식을 카운터 기반 ↔ 난수 기반으로 바꿀 때 테스트/재현성/디버깅에 미치는 영향을 설명할 수 있는가?

**답변:** 카운터는 같은 명령 순서에서 같은 ID가 나오므로 테스트와 예제 재현이 쉽습니다. 난수는 ID 생성 순서가 드러나지 않는 장점이 있지만, 충돌 검사와 테스트 제어가 추가로 필요합니다.

| 관점 | 카운터 기반 | 난수 기반 |
| --- | --- | --- |
| 유일성 | 카운터 유지·최대값 검사로 보장 | 이미 사용한 ID인지 검사하고 충돌 시 다시 생성 |
| 테스트 | 예상 hash를 직접 쓸 수 있음 | 생성기를 주입하거나 테스트용 고정 시퀀스 사용 |
| 재현성 | 명령 순서가 같으면 hash도 같음 | 고정된 생성 조건 없이는 hash가 달라짐 |
| 디버깅 | ID로 생성 순서 파악이 쉬움 | ID와 사건을 연결해 별도 기록하는 편이 좋음 |
| PATH 동률 | 생성 순서와 hash 사전순이 함께 증가 | 그래프가 같아도 새 ID에 따라 선택 경로가 달라질 수 있음 |

난수로 바꿀 때는 hash 생성기를 Repository에 주입하고, **세션 전체에서 사용한 ID 집합**을 유지하겠습니다. `INIT`으로 커밋 저장소가 비워져도 이전 ID와 중복되지 않아야 하기 때문입니다. 테스트용 생성기는 의도적으로 충돌하는 값을 반환하게 해 재시도와 상태 유지도 검증할 수 있습니다.

현재 PATH의 사전순 선택 증명을 유지하려면 난수 ID도 같은 길이로 만듭니다. 길이가 달라지는 ID를 허용하면 다음 hash 비교와 전체 경로 문자열 비교가 항상 같지는 않으므로 동률 처리도 다시 검토해야 합니다.

난수 구현에서 카운터로 돌아오면 hash의 고정 길이·증가·최대값 동작을 다시 테스트합니다. 두 방식 모두 시간은 별도 문제이므로, 완전히 같은 출력이 필요한 테스트에서는 현재처럼 시계도 주입해 timestamp를 고정합니다.
