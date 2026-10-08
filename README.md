# Mini Git

Python으로 구현한 CLI 버전 관리 학습 프로그램입니다. 커밋의 메시지·작성자·시간·부모 관계를 메모리에 기록하고, 브랜치와 커밋 그래프를 탐색합니다.

## 실행

Python **3.10 이상**이면 외부 패키지 설치 없이 실행할 수 있습니다. 이 README가 있는 저장소 폴더에서 실행하세요.

```bash
python main.py
```

`mini-git>`에 명령을 입력하고 `exit` 또는 `quit`로 종료합니다. EOF와 Ctrl+C로도 종료할 수 있습니다. 일부 환경에서는 `python` 대신 `python3`를 사용하세요.

## 명령어

명령어 이름은 대소문자를 구분하지 않습니다. 공백이 있는 인자는 따옴표로 감쌉니다. 사용자명·브랜치명·hash는 입력한 대소문자를 그대로 사용합니다.

| 명령 | 동작 |
| --- | --- |
| `INIT "Alice Smith"` | 저장소를 초기화하고 빈 `main` 브랜치와 현재 사용자를 설정 |
| `BRANCH feature` | 현재 HEAD를 가리키는 브랜치 생성 |
| `SWITCH feature` | 현재 브랜치를 변경 |
| `COMMIT "Add login feature"` | 현재 HEAD를 부모로 하는 커밋 생성 |
| `LOG` | 저장소의 모든 커밋을 부모가 자식보다 먼저 나오도록 출력 |
| `LOG --sort-by=date` | timestamp 오름차순으로 출력 |
| `LOG --sort-by=author` | 작성자 이름 오름차순으로 출력 |
| `PATH c00000002 c00000003` | 부모 연결을 양방향으로 이동하는 최단 경로 출력 |
| `ANCESTORS c00000004` | 지정한 커밋의 모든 조상 출력 |
| `SEARCH login` | 메시지의 `login` 토큰을 역색인으로 검색 |
| `SEARCH "login feature"` | 두 토큰이 모두 들어 있는 메시지 검색 |
| `SEARCH --author="Alice Smith"` | 작성자 이름이 정확히 일치하는 커밋 검색 |
| `USER "Bob Lee"` | 이후 생성할 커밋의 작성자 변경 |
| `MERGE feature` | 현재 HEAD와 feature의 HEAD를 부모로 하는 병합 커밋 생성 |
| `HELP` | 명령어 도움말 |
| `exit` / `quit` | 종료 |

## 사용 예시

아래 명령을 새 REPL 세션에 순서대로 입력합니다. hash는 `c00000001`부터 증가합니다.

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

커밋 관계는 다음과 같습니다. 화살표는 부모에서 자식으로 표시했습니다.

```text
                c00000002 (feature / Bob Lee)
               /          \
c00000001 ----             c00000004 (main / 병합)
               \          /
                c00000003 (Alice Smith)
```

| 입력 | 핵심 결과 |
| --- | --- |
| `LOG` | `c00000001`, `c00000002`, `c00000003`, `c00000004` 순서 |
| `PATH c00000002 c00000003` | `Path: c00000002->c00000001->c00000003` |
| `ANCESTORS c00000004` | `c00000001`, `c00000002`, `c00000003` |
| `SEARCH LOGIN` | `c00000002` |
| `SEARCH "login feature"` | `c00000002` |
| `SEARCH --author="Bob Lee"` | `c00000002` |
| `LOG --sort-by=author` | `c00000001`, `c00000003`, `c00000004`, `c00000002` 순서 |

`PATH`에는 공통 부모를 거치는 경로와 병합 커밋을 거치는 경로가 있습니다. 두 경로 모두 간선 수가 2이지만, 전체 경로 문자열을 비교하면 `c00000001`을 거치는 경로가 사전순으로 앞섭니다.

예제를 파일로도 실행할 수 있습니다.

```bash
python main.py < examples/demo.commands
python main.py < examples/no-path.commands
```

두 번째 예제는 커밋을 만들기 전에 빈 브랜치를 생성해 서로 연결되지 않은 두 루트를 만듭니다. 유효한 두 hash 사이에 연결이 없으면 `No path`, 존재하지 않는 hash를 입력하면 `Unknown commit: missing`이 출력됩니다.

## 세부 동작 규칙

- `INIT`을 다시 실행하면 메모리의 커밋·브랜치·색인을 비웁니다. hash 카운터는 유지해 같은 REPL 세션에서 ID가 재사용되지 않습니다. 작성자만 바꾸려면 `USER`를 사용합니다.
- HEAD는 **현재 브랜치가 가리키는 커밋**입니다. 커밋이 없는 브랜치의 HEAD는 `None`이며, 그 브랜치의 첫 커밋은 부모가 없습니다.
- `LOG`는 현재 브랜치뿐 아니라 저장소의 모든 커밋을 보여 줍니다. 기본 출력은 Kahn 위상 정렬, 옵션 출력은 직접 구현한 안정 병합 정렬입니다.
- 정렬 옵션은 오름차순입니다. 동률이면 생성 순서를 유지합니다. 작성자 비교는 Python 문자열 비교 규칙을 따릅니다. 옵션을 준 로그는 지정한 정렬 기준을 적용하므로 부모가 먼저라는 조건을 항상 유지하지는 않습니다.
- 메시지는 `lower().split()`으로 토큰화합니다. `LOGIN`과 `login`은 같은 키워드지만 `login,`은 별개입니다. 부분 문자열 검색은 하지 않으며, 여러 단어는 AND로 검색합니다.
- 검색 결과와 조상 목록은 hash 오름차순입니다. 조상 목록에 자기 자신은 포함하지 않고, 공통 조상은 한 번만 출력합니다.
- timestamp는 UTC의 시간대 정보를 포함합니다. hash는 `c` + 8자리 16진수 카운터로, 실제 Git의 콘텐츠 해시와는 다른 학습용 식별자입니다. 최대값 이후에는 오류를 내고 중복을 만들지 않습니다.
- `MERGE`는 항상 두 부모를 가진 새 커밋을 만듭니다. 대상 브랜치는 유지하고 현재 브랜치만 이동합니다. 빈 브랜치나 동일한 HEAD는 오류로 처리합니다.
- 파일 내용 추적·데이터 영속성·네트워크 통신은 구현 범위에 포함하지 않습니다. 종료하면 메모리 이력은 사라집니다. 보너스 중 Merge를 구현했습니다.

입력이 잘못되면 `Invalid args`, 없는 브랜치에는 `Unknown branch: <name>`, 없는 커밋에는 `Unknown commit: <hash>`를 출력하고 다음 입력을 받습니다. 초기화 전 저장소 명령에는 `Repository not initialized`를 출력합니다.

## 코드 구조

| 파일 | 책임 |
| --- | --- |
| [main.py](main.py) | REPL 실행 진입점 |
| [minigit/cli.py](minigit/cli.py) | 따옴표 처리, 명령 검증, 결과 출력, REPL |
| [minigit/repository.py](minigit/repository.py) | 커밋·브랜치·HEAD·사용자 관리와 기능 조합 |
| [minigit/models.py](minigit/models.py) | 변경 불가능한 Commit과 부모·자식 인접 목록 |
| [minigit/index.py](minigit/index.py) | 키워드·작성자 역색인 |
| [minigit/algorithms.py](minigit/algorithms.py) | Kahn 위상 정렬, BFS 최단 경로, DFS 조상 탐색, 안정 병합 정렬 |
| [tests/](tests/) | 기능·알고리즘·입력 오류 검증 |
| [EVALUATION.md](EVALUATION.md) | 평가표 20개 질문에 대한 순서별 답변 |

## 검증

```bash
python -m unittest discover -s tests -v
```

44개 테스트로 초기화·브랜치·커밋·검색·정렬·탐색·병합·CLI 오류 복구를 검증합니다. 검색 시 전체 커밋 순회를 금지하는 테스트, 깊이 2,000의 이력에서 재귀 없이 조상을 찾는 테스트, 표준 정렬 API 사용을 검사하는 테스트를 포함합니다.

검증 환경은 Python 3.13.5입니다. 구현은 Python 3.10 이상에서 제공하는 표준 라이브러리와 문법만 사용합니다.
