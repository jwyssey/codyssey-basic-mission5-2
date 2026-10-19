# Mini Git 평가표 답변

평가표의 4개 항목, 20개 질문의 문구와 순서를 그대로 유지했습니다. 각 질문의 답변은 평가 때 설명할 핵심이고, 이어지는 예시와 코드는 그 원리를 이해하기 위한 내용입니다.

이 프로그램은 커밋의 메시지·작성자·시간·부모 관계를 메모리에 저장하는 학습용 Mini Git입니다. 실제 파일 내용, 스테이징 영역, 디스크 저장, 네트워크 통신은 구현하지 않았습니다. 종료하면 이력이 사라집니다.

필요한 부분으로 바로 이동할 수 있습니다.

- [항목 1 — 기능 동작](#항목-1--기능-동작)
- [항목 2 — 구조와 설계](#항목-2--구조와-설계)
- [항목 3 — 알고리즘 이해](#항목-3--알고리즘-이해)
- [항목 4 — 확장과 변경 대응](#항목-4--확장과-변경-대응)
- [부록 A — Python 표현](#부록-a--코드에서-낯설-수-있는-python-표현)
- [부록 B — 테스트 실행](#부록-b--테스트로-확인하기)

## 먼저 실행하고 예제 이해하기

이 문서와 `main.py`가 있는 프로젝트 폴더에서 실행합니다. Python 3.10 이상이면 외부 패키지 설치 없이 사용할 수 있습니다.

```bash
python3 main.py
```

`mini-git>`가 나오면 아래 명령을 한 줄씩 입력합니다. 공백이 있는 인자는 따옴표로 감쌉니다.

```text
INIT "Alice Smith"
COMMIT "Initial commit"
BRANCH feature
SWITCH feature
USER "Bob Lee"
COMMIT "Add login feature"
SWITCH main
USER "Alice Smith"
COMMIT "Add payment feature"
MERGE feature
```

이후 `LOG`, `PATH`, `ANCESTORS`, `SEARCH`를 실행할 수 있습니다. `HELP`는 도움말, `exit` 또는 `quit`는 종료 명령입니다.

이 예제의 커밋을 설명할 때는 A·B·C·D로 줄여 부릅니다. 실제 CLI에는 전체 ID를 입력해야 합니다. 코드의 `hash`는 이 커밋 ID를 뜻합니다.

| 설명용 이름 | 실제 커밋 ID | 작성자 | 메시지 | 부모 |
| --- | --- | --- | --- | --- |
| A | `c00000001` | Alice Smith | Initial commit | 없음 |
| B | `c00000002` | Bob Lee | Add login feature | A |
| C | `c00000003` | Alice Smith | Add payment feature | A |
| D | `c00000004` | Alice Smith | Merge branch 'feature' | C, B |

아래 그림의 연결은 왼쪽 부모에서 오른쪽 자식으로 이어집니다. A는 부모가 없는 루트 커밋, D는 부모가 둘인 병합 커밋입니다.

```text
                  c00000002 (B / feature / Bob Lee)
                 /         \
c00000001 (A) ---           --- c00000004 (D / main / 병합)
                 \         /
                  c00000003 (C / Alice Smith)

HEAD → main → c00000004
```

브랜치는 커밋을 가리키는 이름이고, **HEAD는 현재 브랜치가 가리키는 커밋**입니다. 이 구분이 아래 설명의 기준입니다.

예제 전체를 자동 입력하려면 다음 명령을 사용합니다.

```bash
python3 main.py < examples/demo.commands
python3 main.py < examples/no-path.commands
```

첫 예제는 분기·병합·검색·정렬을, 두 번째는 연결되지 않은 커밋 사이의 경로를 보여 줍니다. 테스트 실행법과 검증 내용은 [부록 B](#부록-b--테스트로-확인하기)에 모았습니다.

## 항목 1 — 기능 동작

### 1.1 INIT <user_name> 실행 후 main 브랜치/HEAD/현재 사용자 설정이 정상적으로 초기화되어 있는가?

답변: 네. `INIT`은 **빈 `main` 브랜치와 현재 사용자**를 설정합니다. 아직 커밋이 없으므로 HEAD는 `None`이고, 첫 커밋을 만들면 그 커밋을 가리킵니다.

`INIT "Alice Smith"` 직후의 상태는 다음과 같습니다.

```python
branches = {"main": None}
current_branch = "main"
current_user = "Alice Smith"
# head는 branches[current_branch]를 조회하므로 None
```

`INIT`을 다시 실행하면 커밋·브랜치·부모/자식 관계·검색 색인을 비웁니다. 다만 같은 실행 세션에서 커밋 ID가 재사용되지 않도록 ID 카운터는 유지합니다. 빈 사용자명은 상태를 바꾸기 전에 거부합니다. 작성자만 바꾸려면 이력을 지우는 `INIT` 대신 `USER`를 사용합니다.

코드 위치: [repository.py](minigit/repository.py)의 `Repository.initialize()`, `head`, `set_user()`.

### 1.2 BRANCH <name> 생성 후 SWITCH <name> 로 전환되며, 이후 COMMIT 이 해당 브랜치에 반영되는가?

답변: 네. `BRANCH`는 **현재 HEAD와 같은 커밋을 가리키는 새 브랜치 이름**을 등록합니다. `SWITCH`로 전환한 뒤 커밋하면 현재 브랜치만 새 커밋으로 이동합니다.

`main`이 A를 가리키는 상태에서 진행하면 다음과 같습니다.

| 명령 | 현재 브랜치 | main이 가리키는 커밋 | feature가 가리키는 커밋 |
| --- | --- | --- | --- |
| `BRANCH feature` | main | A | A |
| `SWITCH feature` | feature | A | A |
| `COMMIT "Add login feature"` | feature | A | 새 커밋 B |

그림에서 브랜치 이름 옆 화살표는 브랜치가 가리키는 위치이고, A와 B 사이의 선은 부모·자식 관계입니다.

```text
BRANCH feature 직후          feature에서 새 커밋 B를 만든 뒤

A ← main ← HEAD              A ← main
↑                             \
feature                        B ← feature ← HEAD
```

핵심 코드는 `self.branches[name] = self.head`입니다. 브랜치를 만들 때 새 커밋은 생기지 않습니다. 기존 커밋을 가리키는 이름만 추가하며, 현재 브랜치도 자동으로 바뀌지 않습니다. 미커밋 파일 변경이나 스테이징 내용을 복사하는 기능도 아닙니다.

커밋을 만들기 전에 빈 브랜치를 두 개 만들면 둘 다 `None`을 가리킵니다. 이후 각 브랜치에서 첫 커밋을 만들면 서로 연결되지 않은 루트 커밋이 생길 수 있습니다.

코드 위치: [repository.py](minigit/repository.py)의 `branch()`, `switch()`, `commit()`, `_create_commit()`.

### 1.3 LOG 가 "부모 커밋이 자식 커밋보다 먼저" 출력되도록 동작하는가?

답변: 네. 기본 `LOG`는 **모든 부모가 처리된 커밋만 결과에 추가**하는 Kahn 위상 정렬을 사용합니다. 병합 커밋도 두 부모 뒤에 나옵니다.

기본 예제에서는 `A, B, C, D` 순서로 출력합니다. D는 B와 C가 모두 처리되어야 출력할 수 있습니다. B와 C 사이에는 부모·자식 관계가 없으므로, 일반적으로는 둘의 순서가 바뀌어도 부모 우선 조건을 만족합니다.

`LOG`는 현재 브랜치뿐 아니라 **저장소의 모든 커밋**을 보여 줍니다. 각 커밋의 ID·작성자·시간·메시지를 표시하고, 브랜치가 가리키는 커밋에는 브랜치명과 HEAD 표시를 붙입니다.

부모 우선 순서는 timestamp가 아니라 연결 관계로 결정합니다. 따라서 시계가 뒤로 움직여도 유지됩니다. 다만 `LOG --sort-by=date`와 `LOG --sort-by=author`는 별도 정렬이므로 **부모 우선 조건을 보장하지 않습니다.**

코드 위치: [repository.py](minigit/repository.py)의 `log()` → [models.py](minigit/models.py)의 `log_order()` → [algorithms.py](minigit/algorithms.py)의 `topological_order()`. 표시 문자열은 [cli.py](minigit/cli.py)의 `_format_commits()`가 만듭니다. 알고리즘 과정은 3.2에서 설명합니다.

### 1.4 PATH <a> <b> 가 경로가 있으면 최단 경로를, 없으면 No path 를 출력하는가?

답변: 네. **부모와 자식 양쪽으로 이동**할 수 있다고 보고, 연결을 가장 적게 건너는 경로를 구합니다. 같은 길이의 경로가 여러 개면 경로 문자열의 사전순이 가장 앞선 것을 선택합니다.

기본 예제에서 B와 C 사이에는 두 최단 경로가 있습니다. 아래 선은 양방향으로 이동할 수 있는 연결입니다.

```text
    B (출발)
   / \
  A   D
   \ /
    C (도착)

B → A → C   # 공통 부모를 거침
B → D → C   # 병합 커밋을 거침
```

둘 다 두 번 이동합니다. A의 ID가 D의 ID보다 사전순으로 앞서므로 다음 결과를 선택합니다.

```text
mini-git> PATH c00000002 c00000003
Path: c00000002->c00000001->c00000003
```

| 상황 | 결과 |
| --- | --- |
| 두 커밋은 존재하지만 서로 연결되지 않음 | `No path` |
| 입력한 ID의 커밋이 존재하지 않음 | `Unknown commit: <hash>` |
| 시작과 끝이 같은 커밋 | 해당 ID 하나만 반환, 이동 횟수 0 |

코드 위치: [repository.py](minigit/repository.py)의 `path()`, [algorithms.py](minigit/algorithms.py)의 `shortest_path()`. BFS가 목적지에서 시작하는 이유와 경로 선택 과정은 3.3에서 설명합니다.

### 1.5 ANCESTORS <hash> 가 모든 조상을 빠짐없이 출력하는가?

답변: 네. **부모 방향으로 계속 올라가 모든 조상**을 찾습니다. 방문한 ID를 집합으로 기록해 공통 조상을 한 번만 포함하고, 시작 커밋 자신은 제외합니다.

기본 예제에서 D의 부모는 C와 B이고, 둘의 부모는 A입니다. 따라서 `ANCESTORS c00000004`의 출력 대상은 A·B·C입니다. 표시할 때는 ID 오름차순으로 정렬합니다. A처럼 부모가 없는 커밋에는 `No ancestors`를 출력합니다.

아래는 커밋 생성 방향이 아니라, D에서 부모를 찾아 올라가는 탐색을 위에서 아래로 그린 것입니다. 두 갈래가 같은 A에 도달합니다.

```text
    D (시작 커밋, 결과에서 제외)
   / \
  C   B
   \ /
    A (공통 조상, 한 번만 포함)
```

```python
ancestor_ids(parents, start)
# parents: 전체 커밋의 부모 관계 딕셔너리
# start:   조상을 찾을 커밋 ID 하나
```

`start`만으로는 부모가 누구인지 알 수 없습니다. `parents[start]`로 부모를 찾고, 그 부모의 부모도 같은 딕셔너리에서 조회합니다. 자식 방향으로는 이동하지 않으므로 `children`은 필요 없습니다.

탐색은 재귀 대신 리스트를 스택으로 사용하는 DFS입니다.

1. 시작 커밋을 방문 집합에 넣어 결과에서 제외합니다.
2. 시작 커밋의 부모들을 스택에 넣습니다.
3. 맨 뒤에서 ID 하나를 꺼내, 처음 방문했다면 결과에 추가합니다.
4. 그 커밋의 부모들을 스택에 넣고 반복합니다.

기본 예제의 D는 부모가 `(C, B)`이므로 스택에서 B → A → C 순서로 처리합니다. C에서 A를 다시 만나도 이미 방문했으므로 건너뜁니다. `ancestor_ids()`가 찾은 순서는 B·A·C이고, `Repository.ancestors()`가 정렬한 출력 순서는 A·B·C입니다.

커밋 2,000개를 일렬로 연결하고 마지막 커밋의 조상 1,999개를 찾는 테스트도 있습니다. 반복문을 사용하므로 재귀 깊이 제한에 걸리지 않습니다.

코드 위치: [algorithms.py](minigit/algorithms.py)의 `ancestor_ids()`, [repository.py](minigit/repository.py)의 `ancestors()`.

### 1.6 SEARCH <keyword> / SEARCH --author=<name> / LOG --sort-by=date|author 가 요구사항대로 동작하는가?

답변: 네. 검색에는 **미리 만든 검색 색인**을 사용하고, 날짜·작성자 로그에는 **직접 구현한 병합 정렬**을 사용합니다.

| 명령 | 동작 | 기본 예제의 결과 |
| --- | --- | --- |
| `SEARCH LOGIN` | 메시지에 `login` 단어가 있는 커밋 검색 | B |
| `SEARCH "login feature"` | 두 단어가 모두 있는 커밋 검색 | B |
| `SEARCH --author="Bob Lee"` | 작성자 이름이 정확히 일치하는 커밋 검색 | B |
| `LOG --sort-by=date` | 시간 오름차순 | 시각도 생성 순으로 증가했다면 A·B·C·D |
| `LOG --sort-by=author` | 작성자 이름 오름차순 | A·C·D·B |

키워드는 `lower().split()`으로 처리하므로 대소문자는 구분하지 않지만, 부분 문자열 검색은 아닙니다. `log`로 `login`을 찾을 수 없고, `login,`도 `login`과 다른 단어입니다. 작성자 검색은 공백과 대소문자까지 정확히 일치해야 합니다.

검색 결과는 ID 오름차순입니다. 날짜·작성자 로그는 비교 값이 같으면 생성 순서를 유지합니다. 단, 이 옵션 로그는 부모보다 자식이 먼저 나올 수 있습니다.

코드 위치: [index.py](minigit/index.py)의 `tokenize()`, `by_keywords()`, `by_author()`; [repository.py](minigit/repository.py)의 `search()`, `log()`; [algorithms.py](minigit/algorithms.py)의 `merge_sort()`.

## 항목 2 — 구조와 설계

### 2.1 커밋 저장소/브랜치/HEAD/사용자 정보를 어떤 구조로 분리했고, 각 책임을 설명할 수 있는가?

답변: `Repository`는 저장소 전체 상태를 관리하고, **커밋 객체·연결 관계·검색 색인의 책임을 분리**했습니다. CLI는 입력과 출력만 담당합니다.

| 저장하는 정보 | 실제 자료구조 또는 값 | 역할 |
| --- | --- | --- |
| `commits` | `dict[str, Commit]` | ID로 실제 커밋 객체 조회 |
| `branches` | 브랜치 이름 → 커밋 ID 또는 `None`인 딕셔너리 | 각 브랜치의 마지막 커밋 관리 |
| `current_branch` | 문자열, 초기화 전에는 `None` | 현재 작업 중인 브랜치 이름 |
| `head` | `branches.get(current_branch)`의 결과 | 현재 브랜치가 가리키는 커밋 ID |
| `current_user` | 문자열, 초기화 전에는 `None` | 이후 커밋의 작성자 |
| `graph.parents` | `dict[str, tuple[str, ...]]` | 커밋별 부모 ID들 |
| `graph.children` | `dict[str, list[str]]` | 커밋별 자식 ID들 |
| `index` | 단어/작성자 → ID 집합인 딕셔너리들 | 검색 후보 조회 |

HEAD는 별도로 저장하지 않고 현재 브랜치에서 계산합니다.

```python
@property
def head(self) -> str | None:
    return self.branches.get(self.current_branch)
```

따라서 `SWITCH`가 `current_branch`를 바꾸면 HEAD도 바뀝니다. `@property`이므로 호출할 때는 `repo.head()`가 아니라 `repo.head`라고 씁니다.

커밋 객체는 `Commit(hash, message, author, timestamp, parents)` 형태입니다. `@dataclass`가 생성자를 자동으로 만들고, `frozen=True`가 생성 후 필드 재할당을 막습니다. 부모는 생성 시 결정되므로 튜플로 보관하고, 자식은 새 커밋이 생길 때 추가하므로 리스트로 보관합니다.

`dict[...]` 같은 **타입 힌트는 실행 중 자료형을 강제하지 않습니다.** 타입 힌트와 `frozen=True`의 동작은 구분해야 합니다. 자세한 표기와 부모·자식 딕셔너리 예시는 [부록 A](#부록-a--코드에서-낯설-수-있는-python-표현)에 정리했습니다.

코드 위치: [repository.py](minigit/repository.py)의 `Repository.__init__()`, `head`; [models.py](minigit/models.py)의 `Commit`, `CommitGraph.__init__()`.

### 2.2 커밋 hash로 빠르게 조회하기 위해 어떤 키-값 구조를 사용했고, 중복/충돌을 어떻게 방지했는지 설명할 수 있는가?

답변: `commits[hash] = commit` 형태의 **딕셔너리에 저장해 ID로 평균 `O(1)`에 조회**합니다. ID는 증가하는 카운터로 만들고, 같은 `Repository`를 사용하는 세션에서 재사용하지 않습니다.

실제 객체 생성은 `_create_commit()`에서 수행합니다.

```python
commit = Commit(
    hash=f"c{self._next_id:08x}",
    message=message,
    author=self.current_user,
    timestamp=self._clock(),
    parents=parents,
)
```

`08x`는 카운터를 16진수로 표현하고 앞을 0으로 채워 최소 8자리로 만드는 형식입니다.

```text
카운터 1  → c00000001
카운터 2  → c00000002
카운터 10 → c0000000a
```

객체를 등록한 뒤 카운터를 1 늘립니다. `INIT`에서도 카운터를 유지하며, 8자리 16진수의 최대값 `0xFFFFFFFF`를 넘으면 오류를 내서 ID 길이와 유일성을 지킵니다. `CommitGraph.add()`도 중복 ID 등록을 거부합니다.

이 ID는 실제 Git처럼 파일 내용으로 계산한 해시가 아닙니다. 현재 프로그램에서 커밋을 구분하기 위한 식별자입니다. 시간은 `_clock()`이 반환한 UTC `datetime` 객체로 저장하며, 출력할 때 문자열로 바꿉니다.

코드 위치: [repository.py](minigit/repository.py)의 `_create_commit()`, `get_commit()`; [models.py](minigit/models.py)의 `CommitGraph.add()`.

### 2.3 커밋이 추가될 때 역색인(author/keyword)을 어떤 시점에, 어떤 방식으로 갱신하도록 설계했는지 설명할 수 있는가?

답변: 일반 커밋과 병합 커밋 모두 `_create_commit()`에서 생성하며, **커밋 생성 시 검색 색인을 갱신**합니다. 작성자와 메시지 단어별로 새 ID를 등록하므로 다음 검색에서 바로 찾을 수 있습니다.

커밋 생성과 등록 순서는 다음과 같습니다.

```text
Commit 객체 생성
    → graph.add(commit): 부모·자식 연결 등록
    → commits[commit.hash] = commit: 객체 보관
    → index.add(commit): 검색 색인 갱신
    → 현재 브랜치를 새 커밋으로 이동
    → ID 카운터 증가
```

역색인은 **검색어로 해당 커밋 ID들을 찾아가는 표**입니다. ID가 B, 작성자가 Bob Lee, 메시지가 `Login LOGIN feature`라면 다음 정보를 등록합니다.

```python
authors["Bob Lee"] = {"B"}
keywords["login"] = {"B"}
keywords["feature"] = {"B"}
```

메시지는 소문자로 바꾸고 공백으로 나눈 뒤 집합으로 변환합니다. 같은 단어가 반복되어도 한 번만 처리하고, ID 집합에도 중복으로 저장하지 않습니다.

실제 등록 코드는 다음과 같습니다.

```python
self.authors.setdefault(commit.author, set()).add(commit.hash)
```

`setdefault()`는 작성자 키가 있으면 기존 집합을 반환하고, 없으면 빈 집합을 저장한 뒤 반환합니다. 이어지는 `add()`가 그 집합에 새 ID를 넣습니다. 키워드 등록도 같은 방식입니다. 이 표는 커밋 생성 시 갱신하며 검색할 때마다 다시 만들지 않습니다.

코드 위치: [repository.py](minigit/repository.py)의 `_create_commit()`; [index.py](minigit/index.py)의 `tokenize()`, `InvertedIndex.add()`.

### 2.4 LOG, PATH, ANCESTORS 에서 사용하는 그래프 탐색 로직을 어떻게 재사용 가능하게 구성했는지 설명할 수 있는가?

답변: 계산을 수행하는 알고리즘을 **입력·출력과 분리된 함수**로 만들었습니다. 필요한 연결 정보와 시작 ID만 전달하면 CLI 없이도 사용할 수 있습니다.

| 기능 | 독립 함수 | 반환값 |
| --- | --- | --- |
| LOG | `topological_order(parents, children)` | 부모 우선 순서의 ID 리스트 |
| PATH | `shortest_path(parents, children, start, end)` | 경로 ID 리스트 또는 `None` |
| ANCESTORS | `ancestor_ids(parents, start)` | 정렬 전 조상 ID 리스트 |

각 파일이 맡는 일은 다음처럼 연결됩니다.

```text
cli.py         입력 해석, 결과를 문자열로 변환하고 출력
    ↓
repository.py  저장소 상태와 ID 유효성 확인, 필요한 객체 조회·정렬
    ↓
models.py      보관 중인 부모·자식 딕셔너리를 알고리즘에 전달
    ↓
algorithms.py  정렬·탐색 결과를 반환
```

예를 들어 `LOG`의 알고리즘은 ID 목록을 반환하고, `Repository.log()`가 ID를 `Commit` 객체로 바꿉니다. CLI의 `_format_commits()`가 객체들을 표시용 문자열로 바꾼 뒤 `run_repl()`이 출력합니다.

이렇게 분리하면 작은 그래프만 준비해서 알고리즘을 테스트하거나, 같은 저장소 기능에 다른 화면을 연결할 수 있습니다.

코드 위치: [algorithms.py](minigit/algorithms.py), [models.py](minigit/models.py)의 `CommitGraph`, [repository.py](minigit/repository.py), [cli.py](minigit/cli.py).

### 2.5 주요 함수/클래스에 docstring/주석을 어떤 기준으로 작성했는지 설명할 수 있는가?

답변: **역할과 동작 규칙은 docstring에, 선택 이유는 주석에** 적었습니다.

docstring은 `def`나 `class` 바로 아래의 설명 문자열입니다. 이 코드에서는 다음처럼 사용합니다.

| 위치 | 설명한 내용 | 필요한 이유 |
| --- | --- | --- |
| `Commit` | 생성 후 바뀌지 않는 커밋 정보 | 객체의 사용 규칙을 알 수 있음 |
| `initialize()` | 이력은 지우지만 ID 카운터는 유지 | 초기화 후에도 ID가 재사용되지 않는 이유를 알 수 있음 |
| `merge_sort()` | 동률이면 왼쪽을 먼저 선택 | 안정 정렬이 유지되는 이유를 알 수 있음 |
| `shortest_path()` | 거리를 1씩 줄이며 작은 ID 선택 | 최단 거리와 사전순 동률 처리를 함께 이해할 수 있음 |

단순히 대입문을 읽어주는 설명보다, 왜 이렇게 구현했고 어떤 조건을 지키는지를 기록했습니다.

코드 위치: [models.py](minigit/models.py), [repository.py](minigit/repository.py)의 `initialize()`, [algorithms.py](minigit/algorithms.py)의 각 함수와 내부 주석.

## 항목 3 — 알고리즘 이해

### 3.1 커밋 그래프가 왜 DAG여야 하는지, 사이클이 생기면 어떤 문제가 발생하는지 설명할 수 있는가?

답변: 커밋은 이미 존재하는 커밋을 부모로 연결합니다. 부모를 따라갔을 때 자기 자신으로 돌아오면 이력의 선후 관계가 모순되므로, **방향이 있고 순환이 없는 그래프인 DAG**여야 합니다.

`A → B`는 A가 부모이고 B가 자식이라는 뜻입니다. 여기에 `B → A`까지 있다면 A와 B가 서로의 조상이 되어, 둘 다 상대보다 먼저 나와야 하는 문제가 생깁니다. 이런 방향성 순환을 사이클이라고 합니다.

병합 자체는 사이클이 아닙니다. 아래 연결은 왼쪽 부모에서 오른쪽 자식으로 향합니다.

```text
    B
   / \
  A   D
   \ /
    C
```

그림이 두 갈래로 갈라졌다 합쳐져도, 화살표를 따라 D에서 A로 돌아올 수는 없습니다. `PATH`가 연결을 양방향으로 해석하는 것과 커밋 그래프의 방향성은 구분해야 합니다.

`CommitGraph.add()`는 새 ID와 이미 존재하는 부모만 연결하고, 기존 커밋의 부모를 바꾸지 않습니다. 이 추가 방식으로 DAG를 유지합니다. 위상 정렬도 모든 노드를 처리하지 못하면 사이클 오류를 냅니다. 방문 검사가 없는 조상 탐색이라면 사이클에서 무한 반복할 수도 있습니다.

코드 위치: [models.py](minigit/models.py)의 `CommitGraph.add()`; [algorithms.py](minigit/algorithms.py)의 `topological_order()`.

### 3.2 LOG 에서 "부모가 먼저" 조건을 만족시키기 위해 어떤 접근(예: 위상 정렬 성격의 출력)을 적용했는지 설명할 수 있는가?

답변: Kahn 위상 정렬을 사용했습니다. **아직 처리하지 않은 부모 수가 0인 커밋만 큐에 넣고**, 하나를 처리할 때마다 자식들의 남은 부모 수를 줄입니다.

위상 정렬은 그래프의 선후 관계를 지키도록 노드를 나열하는 것입니다. 여기서는 부모 → 자식 관계를 지킵니다.

부모 수는 생성 시 기록한 부모 튜플의 길이로 바로 알 수 있습니다.

```python
indegree = {node: len(links) for node, links in parents.items()}
# 기본 예제: {"A": 0, "B": 1, "C": 1, "D": 2}
```

`indegree`는 처음에는 전체 부모 수이고, 처리 중에는 아직 처리하지 않은 부모 수입니다. 원본 `parents`는 바꾸지 않습니다.

```python
ready = deque(node for node, degree in indegree.items() if degree == 0)
```

이 한 줄은 길게 쓰면 다음과 같습니다.

```python
ready = deque()
for node, degree in indegree.items():
    if degree == 0:
        ready.append(node)
```

`deque`를 큐로 사용해 `append()`로 뒤에 넣고 `popleft()`로 앞에서 꺼냅니다. 먼저 들어간 커밋이 먼저 처리됩니다.

| 꺼낸 커밋 | 자식의 미처리 부모 수 변경 | 처리 후 큐 | 결과 |
| --- | --- | --- | --- |
| 초기 상태 | A만 부모 수 0 | `[A]` | `[]` |
| A | B: 1→0, C: 1→0 | `[B, C]` | `[A]` |
| B | D: 2→1 | `[C]` | `[A, B]` |
| C | D: 1→0 | `[D]` | `[A, B, C]` |
| D | 자식 없음 | `[]` | `[A, B, C, D]` |

루트가 여러 개면 처음부터 여러 커밋이 큐에 들어갑니다. 전체 커밋 수를 `V`, 부모 연결 수를 `E`라고 하면 각각을 한 번씩 처리하므로 시간은 `O(V + E)`, 기존 그래프를 제외한 추가 공간은 `O(V)`입니다.

코드 위치: [algorithms.py](minigit/algorithms.py)의 `topological_order()`.

### 3.3 PATH 에서 최단 경로를 찾기 위해 어떤 알고리즘(예: BFS)을 선택했고, 간선을 무방향으로 정의한 이유를 설명할 수 있는가?

답변: 연결 하나를 건너는 비용이 모두 같으므로 **가까운 노드부터 탐색하는 BFS**를 사용했습니다. 경로에서 부모·자식 양쪽 이동을 허용하므로 서로 다른 브랜치의 커밋 사이도 이동할 수 있습니다.

예를 들어 B에서 C로 가려면 `B → A → C`처럼 부모로 올라갔다가 자식으로 내려갈 수 있어야 합니다. 목적지가 부모인지 자식인지 모르는 상황 때문만이 아니라, 이 기능의 이동 규칙 자체가 양방향이기 때문입니다.

부모와 자식을 합쳐 이웃으로 사용합니다.

```python
for neighbor in (*parents[node], *children[node]):
```

`*`는 내부 원소를 펼칩니다. B의 부모가 `(A,)`, 자식이 `[D]`이면 이웃은 `(A, D)`입니다.

실제 알고리즘은 두 단계입니다.

1. **목적지 `end`부터 BFS:** 각 커밋에서 목적지까지의 최소 이동 횟수를 기록합니다.
2. **출발점 `start`에서 경로 만들기:** 거리가 1 작은 이웃으로 이동하고, 후보가 여러 개면 가장 작은 ID를 고릅니다.

B에서 C로 가는 예에서, C부터 BFS하면 다음 거리를 얻습니다. 대괄호의 숫자는 목적지 C까지의 최소 이동 횟수입니다. 선은 양방향 연결입니다.

```text
      B[2] (출발)
     /    \
  A[1]    D[1]
     \    /
      C[0] (도착)

BFS 발견 순서: C → {A, D} → B
경로 만들기:  B → A → C
남은 거리:    2 → 1 → 0
```

B에서는 거리 1인 A와 D가 후보입니다. 더 작은 ID인 A를 선택하고, A에서는 거리 0인 C를 선택해 `B → A → C`를 만듭니다. BFS 큐는 한 단계 가까운 노드를 먼저 처리하므로 처음 기록한 거리가 최단 거리입니다.

거리를 1씩 줄여 최단 경로를 지키고, 같은 거리 후보에서 작은 ID를 골라 동률을 처리합니다. 현재 ID는 길이가 고정되어 있으므로 이 선택이 전체 경로 문자열의 사전순 비교와 맞습니다. 출발점이 거리 표에 없으면 목적지와 연결되지 않았으므로 `None`을 반환합니다.

시간은 `O(V + E)`, 추가 공간은 `O(V)`입니다. 실제 탐색 범위는 목적지와 연결된 부분입니다.

코드 위치: [algorithms.py](minigit/algorithms.py)의 `shortest_path()`.

### 3.4 정렬 알고리즘의 평균/최악 시간복잡도와 안정 정렬 여부를 설명할 수 있는가?

답변: 직접 구현한 반복형 병합 정렬을 사용합니다. 평균·최악 시간은 모두 **`O(n log n)`**이고, 비교 값이 같은 원소의 기존 순서를 유지하는 **안정 정렬**입니다.

1부터 8까지의 숫자를 섞은 `[8, 3, 7, 1, 6, 2, 5, 4]`를 정렬한다고 해보겠습니다. 원소 하나짜리 구간은 이미 정렬되었다고 보고, 두 구간씩 합칩니다. `width`는 이번 단계에서 합칠 구간 하나의 길이입니다.

```text
입력
[8] [3]   [7] [1]   [6] [2]   [5] [4]
   ↓         ↓         ↓         ↓
 [3,8]     [1,7]     [2,6]     [4,5]     width = 1
     \     /             \     /
    [1,3,7,8]           [2,4,5,6]        width = 2
            \           /
          [1,2,3,4,5,6,7,8]             width = 4
```

`width = 1`에서는 길이 1인 구간 둘을 합쳐 길이 2를 만들고, `width = 2`에서는 길이 2인 구간 둘을 합쳐 길이 4를 만듭니다. `width = 4`에서는 두 구간을 합쳐 원소 8개 전체의 정렬을 마칩니다.

마지막 단계에서 `[1, 3, 7, 8]`과 `[2, 4, 5, 6]`을 합칠 때는 각 구간의 맨 앞에 남은 값끼리 비교합니다.

```text
1과 2 비교 → 1 선택
3과 2 비교 → 2 선택
3과 4 비교 → 3 선택
7과 4 비교 → 4 선택
7과 5 비교 → 5 선택
7과 6 비교 → 6 선택
오른쪽이 비었으므로 왼쪽에 남은 7, 8을 순서대로 추가

결과: [1, 2, 3, 4, 5, 6, 7, 8]
```

`source`는 읽을 리스트, `target`은 결과를 쓸 리스트, `width`는 구간 길이입니다. 한 단계가 끝나면 두 리스트의 역할을 바꾸고 `width`를 2배로 늘립니다. 입력을 새 리스트로 복사하므로 원본 입력은 변경하지 않습니다.

핵심 비교는 `key(source[left]) <= key(source[right])`입니다. `key`는 비교할 값을 얻는 함수입니다. `lambda commit: commit.author`라면 작성자를 비교합니다. `<=`이므로 값이 같을 때 왼쪽 원소를 먼저 선택해 기존 순서를 유지합니다. 날짜·작성자 로그에서는 생성 순서대로 입력하므로 동률일 때 생성 순서도 유지됩니다.

| 성질 | 현재 구현 |
| --- | --- |
| 평균·최악·최선 시간 | `O(n log n)` |
| 추가 공간 | `O(n)` |
| 안정성 | 같은 비교 값이면 입력 순서 유지 |
| 정렬 API | `sorted()`와 `list.sort()`를 사용하지 않음 |

위 예제는 단계마다 원소 8개를 결과 리스트에 쓰고, 총 3단계를 거칩니다. 일반적으로 구간 길이가 2배씩 커지므로 단계 수는 약 `log₂ n`입니다. 단계마다 원소 `n`개를 처리하므로 전체 시간은 `O(n log n)`입니다.

코드 위치: [algorithms.py](minigit/algorithms.py)의 `merge_sort()`; [repository.py](minigit/repository.py)의 `log()`, `ancestors()`, `search()`.

### 3.5 역색인이 순회 검색보다 빠른 이유를, 자료구조/시간복잡도 관점에서 설명할 수 있는가?

답변: 전체 커밋을 검색할 때마다 읽는 대신, **커밋 생성 시 단어·작성자별 ID 집합을 미리 만들어 둡니다.** 검색할 때는 해당 후보만 가져오므로, 결과가 적을수록 전체 순회보다 유리합니다.

커밋 10,000개 중 `login`이 있는 커밋이 3개라면, 색인에서 그 3개의 ID를 찾아 해당 커밋만 조회합니다. 다만 결과 복사와 정렬도 필요하므로 검색 전체가 `O(1)`은 아닙니다.

여러 단어를 검색할 때는 모든 단어가 있는 커밋을 찾기 위해 집합의 교집합을 구합니다.

```python
login = {"A", "B", "C"}
feature = {"A", "C"}

result = feature.copy()
result.intersection_update(login)
# result: {"A", "C"}
```

`intersection_update()`는 상대 집합에도 있는 원소만 남기도록 현재 집합을 수정합니다. 상대 집합은 바꾸지 않고, **반환값은 `None`**입니다. 따라서 `result = result.intersection_update(...)`라고 쓰면 안 됩니다.

실제 코드에서는 가장 작은 집합을 복사해 시작합니다.

```python
smallest = min(buckets, key=len)
result = smallest.copy()
```

검색 단어별 후보 수가 100,000개·90,000개·2개라면 최종 결과는 반드시 마지막 2개 안에 있습니다. 작은 집합부터 시작하면 2개만 복사하고 중간 후보도 최대 2개로 유지합니다. 어느 집합부터 시작해도 교집합 결과는 같지만, 복사량과 중간 후보 크기를 줄일 수 있습니다. 결과가 비면 더 계산해도 비어 있으므로 반복을 멈춥니다.

전체 커밋 수를 `V`, 최종 결과 수를 `k`라고 할 때 평균적인 비용은 다음과 같습니다. 검색 문자열을 읽고 토큰으로 나누는 비용은 별도입니다.

| 방식 | 후보 찾기와 가져오기 | 결과 정렬까지 포함 |
| --- | --- | --- |
| 작성자 전체 순회 | `O(V)` | `O(V + k log k)` |
| 메시지 전체 순회 | 전체 메시지 길이에 비례 | 전체 순회 비용 + `O(k log k)` |
| 단일 단어·작성자 역색인 | 딕셔너리 조회 평균 `O(1)`, 결과 복사·조회 `O(k)` | `O(k + k log k)` |

여러 단어는 단어 수가 `m`, 가장 작은 집합 크기가 `s`라면 집합 조회·최소 집합 선택에 `O(m)`, 평균적인 교집합 작업에 최대 `O(m × s)`가 필요하고, 이후 결과를 정렬합니다. 집합 연산과 딕셔너리 조회의 일반적인 평균 비용을 전제로 한 설명입니다.

색인은 추가 메모리와 생성 시 갱신 비용을 사용합니다. 결과가 전체 커밋만큼 많으면 이득이 줄며, 작은 집합을 고른다고 모든 검색이 반드시 더 빨라지는 것은 아닙니다.

코드 위치: [index.py](minigit/index.py)의 `InvertedIndex`, [repository.py](minigit/repository.py)의 `search()`.

## 항목 4 — 확장과 변경 대응

이 항목은 현재 동작과 **요구사항이 바뀌었을 때의 개선 제안**을 구분합니다. 아래 제안은 아직 구현한 기능이 아닙니다.

### 4.1 커밋 수가 10배 늘어났을 때 병목이 될 지점을 예측하고, 개선 방향(자료구조/알고리즘)을 설명할 수 있는가?

답변: 전체 커밋을 탐색·정렬·출력하는 작업과 메모리 사용량이 커집니다. 먼저 **측정으로 병목을 찾고**, 출력 제한·캐시·탐색 범위 축소를 적용하겠습니다.

현재 CLI로 만드는 커밋은 부모가 최대 2개이므로 연결 수도 커밋 수에 비례합니다. 메시지 길이가 비슷하다면 다음을 예상할 수 있습니다.

| 작업 | 증가할 수 있는 비용 | 개선 방향 |
| --- | --- | --- |
| 기본 LOG | `O(V + E)` 탐색과 전체 결과 출력 | 결과를 나눠 보여 주거나 순차 출력 |
| PATH | 연결된 그래프 전체의 `O(V + E)` 탐색 | 거리 계산 조기 종료, 반복 질의 캐시, 양방향 BFS 검토 |
| 날짜·작성자 LOG | `O(V log V)` 정렬 | 변경이 없으면 정렬 결과 재사용 |
| ANCESTORS | 조상 탐색과 조상 ID 정렬 | 결과 제한, 자주 조회하는 결과 캐시 |
| SEARCH | 흔한 단어의 큰 후보 집합과 결과 정렬 | 결과를 나눠 보여 주기, 큰 집합 저장 방식 개선 |
| 메모리 | 커밋 객체·연결·색인 모두 저장 | 내부 정수 ID, 압축된 ID 목록, 디스크 저장 검토 |

커밋이 10배가 되어도 메시지 길이와 연결 수 비율이 비슷하다면, 선형 탐색 비용과 메모리 사용량은 대략 10배가 됩니다. 전체 정렬 비용은 보통 10배보다 더 증가합니다. 반면 희귀 단어 검색은 결과 수가 그대로라면 영향이 작을 수 있습니다. 출력할 결과 자체가 많아지는 비용은 탐색 개선만으로 없앨 수 없습니다.

캐시를 넣으면 커밋 추가·`INIT` 시 갱신하거나 무효화해야 합니다. 양방향 BFS도 처음 만난 경로만 반환하면 기존 사전순 동률 규칙을 놓칠 수 있어, 필요한 거리 정보와 경로 복원 규칙을 함께 검토해야 합니다.

관련 코드: [repository.py](minigit/repository.py)의 `log()`, `path()`, `ancestors()`, `search()`; [algorithms.py](minigit/algorithms.py); [index.py](minigit/index.py).

### 4.2 PATH 의 간선 정의를 "부모 방향만 허용"으로 바꾸면 결과가 어떻게 달라지고, 구현은 무엇을 바꿔야 하는지 설명할 수 있는가?

답변: 출발 커밋에서 **조상 쪽으로만 이동**할 수 있게 됩니다. 현재의 양방향 탐색을 바꾸되, 목적지에서 거리를 구하는 단계와 출발점에서 경로를 만드는 단계의 방향을 다르게 적용해야 합니다.

기본 예제에서는 다음과 같이 달라집니다.

아래 화살표는 부모 방향만 허용했을 때의 실제 이동 방향입니다. D에서는 A로 갈 수 있지만 A에서 D로 내려갈 수는 없습니다.

```text
    D
   ↙ ↘
  B   C
   ↘ ↙
    A
```

| 경로 | 부모 방향만 허용할 때 | 이유 |
| --- | --- | --- |
| B → C | `No path` | A로 올라간 뒤 다른 자식 C로 내려갈 수 없음 |
| D → A | 경로 있음 | 부모를 따라 D → B → A 또는 D → C → A |
| A → D | `No path` | 자식 방향으로 내려가야 함 |

현재 코드는 목적지에서 BFS하므로 수정 위치를 구분해야 합니다.

| 단계 | 현재 코드의 이웃 | 변경 후 이웃 |
| --- | --- | --- |
| 목적지에서 거리 계산 | 부모 + 자식 | `children`만 사용 |
| 출발점에서 경로 생성 | 부모 + 자식 | `parents`만 사용 |

예를 들어 D에서 A로 올라가는 거리를 계산하려면, 목적지 A에서 역으로 자식 B·C·D를 찾아야 합니다. 이후 출발점 D에서는 실제 허용 방향인 부모 쪽으로 이동합니다.

두 곳을 모두 `parents`로 바꾸면 원하는 방향의 거리가 계산되지 않습니다. 대안으로 출발점에서 부모만 따라 BFS하도록 전체 경로 탐색을 다시 구성할 수 있지만, 사전순 동률 처리도 함께 유지해야 합니다.

변경 위치: [algorithms.py](minigit/algorithms.py)의 `shortest_path()` 안 BFS 이웃 선택과 경로 복원 후보 선택.

### 4.3 LOG --sort-by=author 요구사항이 "부모-자식 선후도 유지"로 강화된다면, 어떤 전략으로 해결할지 설명할 수 있는가?

답변: **부모가 모두 처리된 커밋 중 작성자 이름이 가장 앞선 커밋을 선택**하는 위상 정렬로 바꾸겠습니다.

단순히 작성자로 전체 정렬하면 부모보다 자식이 먼저 나올 수 있습니다. 예를 들어 부모 작성자가 Zoe이고 자식 작성자가 Alice라면, 작성자 오름차순과 부모 우선 조건을 동시에 전역적으로 지킬 수는 없습니다.

따라서 규칙을 부모 우선 조건을 먼저 지키고, 동시에 출력 가능한 후보 사이에서 작성자 순서를 적용한다고 정해야 합니다.

1. Kahn 알고리즘처럼 미처리 부모 수를 계산합니다.
2. 부모 수가 0인 커밋을 후보에 넣습니다.
3. 후보 중 `(author, hash)`가 가장 작은 커밋을 선택합니다.
4. 자식의 남은 부모 수를 줄이고, 0이 된 자식을 후보에 추가합니다.

작성자가 같으면 ID로 동률을 처리합니다. 현재 카운터 ID에서는 생성 순서와도 일치합니다.

후보의 최솟값을 빠르게 꺼내기 위해 최소 힙을 직접 구현할 수 있습니다. 시간은 `O(E + V log V)`입니다. 후보 리스트를 매번 순회해 최솟값을 고르는 방법도 있지만, 최악에는 `O(V² + E)`로 커집니다.

변경 위치: [repository.py](minigit/repository.py)의 `log()`에서 author 분기를 새 작성자 우선 위상 정렬 함수로 연결하고, [algorithms.py](minigit/algorithms.py)에 후보 관리 로직을 추가합니다.

### 4.4 해시 생성 방식을 카운터 기반 ↔ 난수 기반으로 바꿀 때 테스트/재현성/디버깅에 미치는 영향을 설명할 수 있는가?

답변: 카운터는 같은 명령 순서에서 같은 ID를 만들어 재현과 디버깅이 쉽습니다. 난수는 ID가 실행마다 달라질 수 있으므로 **충돌 처리와 테스트용 생성기 제어**가 필요합니다.

| 관점 | 현재 카운터 방식 | 난수 방식으로 바꿀 경우 |
| --- | --- | --- |
| 중복 방지 | 카운터 유지와 최대값 검사 | 사용한 ID인지 검사하고 충돌 시 재시도 |
| 테스트 | 예상 ID를 직접 작성 가능 | 고정된 ID 시퀀스를 반환하는 생성기 주입 |
| 재현성 | 같은 명령 순서면 같은 ID | 생성 조건을 제어하지 않으면 달라짐 |
| 디버깅 | ID로 생성 순서를 파악하기 쉬움 | ID와 작업 순서를 별도로 기록하는 편이 좋음 |
| PATH 동률 | 현재 ID는 생성 순서대로 증가 | 그래프 구조가 같아도 ID에 따라 선택 경로가 달라질 수 있음 |

생성기는 현재의 `_clock`처럼 함수로 주입할 수 있습니다. 테스트에서는 의도적으로 중복 ID를 반환하게 해서 충돌 시 재시도와 상태 유지도 확인할 수 있습니다.

`INIT` 이후에도 같은 세션의 ID를 재사용하지 않으려면, 현재 커밋 딕셔너리뿐 아니라 세션 전체에서 사용한 ID 집합을 유지해야 합니다. 현재 PATH의 사전순 선택 규칙을 그대로 쓰려면 난수 ID도 고정 길이로 만들겠습니다.

반대로 카운터 방식으로 돌아오면 시작값·증가·최대값·재초기화 후 비재사용을 다시 검증합니다. ID를 고정해도 시각은 바뀔 수 있으므로, 완전히 같은 출력이 필요한 테스트에서는 시계 함수도 고정해야 합니다.

변경 위치: [repository.py](minigit/repository.py)의 `__init__()`, `_create_commit()`, `initialize()`; ID를 직접 기대하는 테스트와 예제 명령 파일.

## 부록 A — 코드에서 낯설 수 있는 Python 표현

### 타입 힌트와 실제 부모·자식 자료구조

```python
self.parents: dict[str, tuple[str, ...]] = {}
self.children: dict[str, list[str]] = {}
```

실제로는 둘 다 딕셔너리입니다. 부모 값은 튜플, 자식 값은 리스트입니다. 기본 예제를 A·B·C·D로 표현하면 다음과 같습니다.

```python
parents = {"A": (), "B": ("A",), "C": ("A",), "D": ("C", "B")}
children = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
```

각 노드에 연결된 노드 목록을 저장하는 방식을 인접 목록이라고 합니다. 새 커밋을 추가하면 그 커밋의 부모를 등록하고, 각 부모의 자식 리스트에도 새 ID를 추가합니다.

알고리즘의 `Mapping[str, Sequence[str]]`는 이 구조를 더 일반적으로 표현한 타입 힌트입니다.

| 표현 | 뜻 | 우리 코드의 실제 값 |
| --- | --- | --- |
| `Mapping` | 키로 값을 조회할 수 있는 구조 | `dict` |
| `Sequence[str]` | 문자열 원소들이 순서대로 들어 있는 구조 | 부모는 `tuple`, 자식은 `list` |
| `tuple[str, ...]` | 문자열이 0개 이상인 튜플 | `()`, `("A",)`, `("C", "B")` |

타입 힌트가 전달된 딕셔너리를 변환하거나 실행 중 자료형을 강제하지는 않습니다. 반면 `@dataclass(frozen=True)`의 필드 재할당 금지는 실행 중에도 적용됩니다. 연결 딕셔너리는 외부에서 수정할 수 있으므로, DAG 유지는 정상적인 `add()` 경로로 등록한다는 사용 규칙을 전제로 합니다.

### `get()`과 `setdefault()`, 집합 메서드

`set()`은 빈 집합을 만듭니다. `{}`는 빈 딕셔너리이므로 구분해야 합니다.

| 표현 | 키가 있을 때 | 키가 없을 때 |
| --- | --- | --- |
| `d.get(key, set())` | 기존 값 반환 | 빈 집합 반환. 딕셔너리는 그대로 |
| `d.setdefault(key, set())` | 기존 값 반환 | 빈 집합을 딕셔너리에 저장하고 반환 |

등록은 다음처럼 풀어 읽을 수 있습니다.

```python
# 원래 코드
self.authors.setdefault(commit.author, set()).add(commit.hash)

# 같은 동작을 길게 표현
if commit.author not in self.authors:
    self.authors[commit.author] = set()
self.authors[commit.author].add(commit.hash)
```

조회 시의 `return self.authors.get(author, set()).copy()`는 해당 작성자의 집합 또는 빈 집합을 **복사해서 반환**합니다. 호출자가 결과를 지워도 원본 색인은 유지됩니다.

| 집합 연산 | 기존 `result` 변경 여부 | 반환값 |
| --- | --- | --- |
| `result.intersection_update(other)` | 변경 | `None` |
| `result.intersection(other)` | 변경하지 않음 | 새 교집합 |
| `result & other` | 변경하지 않음 | 새 교집합 |

모두 Python이 기본으로 제공하는 `set`의 메서드 또는 연산자입니다.

### 시계 함수를 저장했다가 호출하기

```python
self._clock = clock or (lambda: datetime.now(timezone.utc))
```

`clock`을 전달하지 않으면 현재 UTC 시각을 반환하는 **함수 객체**를 저장합니다. 이 대입 시점에 시각을 구하는 것이 아닙니다.

```python
self._clock     # 저장된 함수 객체
self._clock()   # 함수를 실행해 datetime 객체를 얻음
```

`_clock`은 클래스에 정의한 일반 메서드가 아니라 함수를 담은 인스턴스 속성입니다. 커밋을 만들 때 호출하므로 그때의 시각이 저장됩니다. 테스트에서는 `Repository(clock=lambda: fixed_time)`처럼 고정된 시각을 반환하는 함수를 전달할 수 있습니다.

## 부록 B — 테스트로 확인하기

테스트는 실제 결과와 예상 결과를 비교하는 Python 코드입니다. 예를 들어 `assertEqual(실제값, 예상값)`은 두 값이 다르면 실패합니다. 아래 함수명은 구현 근거를 찾기 위한 안내이며, 통과 여부는 명령을 실행해서 확인합니다.

### 전체 테스트 실행

프로젝트 최상위 폴더에서 실행합니다.

```bash
python3 -m unittest discover -s tests -v
```

현재 Python 3.11.13 환경에서 44개 테스트가 통과하는 것을 확인했습니다. `ok`는 개별 테스트 통과, `FAIL`은 결과 불일치, `ERROR`는 실행 중 오류를 뜻합니다. 마지막에 `OK`가 나오면 실행한 테스트가 모두 통과한 것입니다.

| 테스트 파일 | 검증하는 내용 |
| --- | --- |
| [test_repository.py](tests/test_repository.py) | 초기화, 브랜치·커밋·병합 상태, 검색·정렬 결과, 잘못된 조작 시 상태 유지 |
| [test_algorithms.py](tests/test_algorithms.py) | 위상 정렬, 경로 동률, 조상 중복 제거, 긴 이력, 병합 정렬 |
| [test_cli.py](tests/test_cli.py) | 명령 해석, 출력 형식, 오류 후 계속 실행, 종료 처리, 표준 정렬 API 미사용 |

### 테스트 하나만 실행

병합 커밋의 조상을 검사하는 테스트 하나는 다음 명령으로 실행합니다.

```bash
python3 -m unittest tests.test_repository.RepositoryTests.test_merge_ancestors_include_both_branches_once -v
```

명령의 구조는 `모듈.클래스.메서드`입니다.

```text
tests.test_repository → tests/test_repository.py
RepositoryTests → 그 파일 안의 테스트 클래스
test_merge_ancestors_include_both_branches_once → 실행할 테스트 메서드
```

코드 위치를 안내하는 `파일명:157`의 숫자는 줄 번호입니다. 테스트 실행 명령에 줄 번호를 넣는 것은 아닙니다.

긴 이력 테스트 하나만 실행하려면 다음과 같습니다.

```bash
python3 -m unittest tests.test_algorithms.GraphAlgorithmTests.test_long_history_does_not_recurse -v
```

이 테스트는 커밋 ID `0 → 1 → … → 1999`를 연결하고 마지막 커밋의 조상이 1,999개인지 확인합니다. 즉, 커밋 2,000개와 연결 1,999개인 이력입니다.

### 평가 항목별 대표 테스트 찾기

아래는 대표 테스트이며, 전체 검증 목록은 각 테스트 파일에 있습니다.

| 평가 항목 | 테스트 위치 | 대표 메서드 | 확인하는 내용 |
| --- | --- | --- | --- |
| 1.1 초기화 | `test_repository.py / RepositoryTests` | `test_initialization` | 빈 main·HEAD·사용자 설정 |
| 1.2 브랜치 | `test_repository.py / RepositoryTests` | `test_branch_switch_and_commit_update_only_current_branch` | 현재 브랜치만 새 커밋으로 이동 |
| 1.3 LOG | `test_repository.py / RepositoryTests` | `test_log_includes_all_branches_and_parent_first_after_merge` | 전체 커밋과 부모 우선 순서 |
| 1.4 PATH | `test_repository.py / RepositoryTests` | `test_path_lexicographic_tie_in_both_directions` | 최단 경로와 사전순 동률 |
| 1.5 조상 | `test_repository.py / RepositoryTests` | `test_merge_ancestors_include_both_branches_once` | 병합 양쪽 조상을 각각 한 번 포함 |
| 1.5 조상 | `test_algorithms.py / GraphAlgorithmTests` | `test_all_ancestors_without_duplicates_or_self` | 중복과 자기 자신 제외 |
| 1.5 조상 | `test_algorithms.py / GraphAlgorithmTests` | `test_long_history_does_not_recurse` | 커밋 2,000개의 이력 탐색 |
| 1.6 검색 | `test_repository.py / RepositoryTests` | `test_multiple_keywords_use_and` | 여러 검색 단어의 교집합 |
| 2.2 ID | `test_repository.py / RepositoryTests` | `test_hash_unique_across_reinitialization` | 재초기화 후 ID 비재사용 |
| 2.3 색인 갱신 | `test_repository.py / RepositoryTests` | `test_merge_has_two_parents_and_updates_index` | 병합 커밋도 검색 색인에 등록 |
| 3.1 DAG | `test_algorithms.py / GraphAlgorithmTests` | `test_cycle_detected` | 순환 그래프에서 위상 정렬 오류 |
| 3.2 위상 정렬 | `test_algorithms.py / GraphAlgorithmTests` | `test_topological_order_respects_every_parent` | 모든 부모가 자식보다 앞서는지 검사 |
| 3.4 정렬 | `test_algorithms.py / MergeSortTests` | `test_stability_and_input_unchanged` | 안정 정렬과 원본 입력 보존 |
| 3.5 검색 비용 | `test_repository.py / RepositoryTests` | `test_search_does_not_scan_all_commits` | 전체 커밋 순회 없이 검색 |
