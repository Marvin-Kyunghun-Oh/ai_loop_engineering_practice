# llmops_lab/conftest.py
# pytest 공용 설정 파일: 프로젝트 루트를 sys.path에 추가해 `from app...` import 경로 에러를 방지한다.
import sys
from pathlib import Path

# 이 파일이 있는 디렉터리(프로젝트 루트)를 import 탐색 경로 맨 앞에 등록
sys.path.insert(0, str(Path(__file__).parent))
