# PRD: 문자열 뒤집기 함수

스모크 테스트용 아주 작은 프로젝트다. 하네스의 배관을 확인하는 것이 목적이다.

## 요구

1. `src/string_utils.py`에 함수 `reverse(text: str) -> str`를 만든다.
   - 문자열을 뒤집어서 돌려준다. 예: `reverse("abc")`는 `"cba"`.
   - 빈 문자열은 빈 문자열을 돌려준다.
2. `tests/test_string_utils.py`에 `unittest`로 테스트를 만든다.
   - 일반 문자열, 빈 문자열, 한 글자, 한글 문자열(`"가나다"` → `"다나가"`)을 확인한다.

## 제약

- 표준 라이브러리만 쓴다. 외부 패키지를 설치하지 않는다.
- 패키지 구성: `src/__init__.py`, `tests/__init__.py`를 두고 테스트에서 `from src.string_utils import reverse`로 가져온다.
- 테스트 실행: `python3 -m unittest discover -s tests -t .`

## 미해결 의사결정

없음
