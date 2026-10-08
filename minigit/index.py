"""작성자·메시지 토큰에서 커밋 hash를 바로 찾는 역색인."""

from .models import Commit


def tokenize(text: str) -> set[str]:
    """공백으로 분리하고 소문자로 통일한다. 문장부호는 제거하지 않는다."""
    return set(text.lower().split())


class InvertedIndex:
    """dict의 키 조회와 set의 교집합으로 전체 커밋 순회를 피한다."""

    def __init__(self) -> None:
        self.keywords: dict[str, set[str]] = {}
        self.authors: dict[str, set[str]] = {}

    def add(self, commit: Commit) -> None:
        """커밋 생성 직후 갱신한다. 반복 단어는 같은 hash를 중복 저장하지 않는다."""
        self.authors.setdefault(commit.author, set()).add(commit.hash)
        for keyword in tokenize(commit.message):
            self.keywords.setdefault(keyword, set()).add(commit.hash)

    def by_author(self, author: str) -> set[str]:
        """작성자 이름은 공백과 대소문자를 포함한 정확한 이름으로 찾는다."""
        return self.authors.get(author, set()).copy()

    def by_keywords(self, query: str) -> set[str]:
        """여러 검색 단어의 교집합. 가장 작은 후보 집합부터 계산한다."""
        words = tokenize(query)
        if not words:
            return set()
        buckets = [self.keywords.get(word, set()) for word in words]
        smallest = min(buckets, key=len)
        result = smallest.copy()
        for bucket in buckets:
            result.intersection_update(bucket)
            if not result:
                break
        return result
