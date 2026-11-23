"""가짜 `claude -p` CLI. stdin 프롬프트를 읽어 요약 JSON 또는 위키 Markdown을 stdout으로 낸다.

제목 마커로 동작을 제어한다: LLMFAIL → 종료코드 1, FENCE → JSON을 코드펜스로 감싼다.
환경변수 FAKE_CLAUDE_LOG(호출 기록 파일), FAKE_CLAUDE_DELAY(초) 지원.
"""
import json
import os
import re
import sys
import time

prompt = sys.stdin.read()
log = os.environ.get("FAKE_CLAUDE_LOG")
delay = float(os.environ.get("FAKE_CLAUDE_DELAY", "0"))
if delay:
    time.sleep(delay)


def record(kind, detail):
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, "detail": detail}, ensure_ascii=False) + "\n")


if "[입력 글]" in prompt:
    title = re.search(r"^제목: (.*)$", prompt, re.M).group(1)
    record("summarize", title)
    if "LLMFAIL" in title:
        print("simulated failure", file=sys.stderr)
        sys.exit(1)
    cat = "LLM 에이전트" if "AI" in title else "데이터베이스" if "DB" in title else "기타"
    out = json.dumps({"summary": f"{title}에 대한 요약입니다. 핵심만 정리했습니다.", "category_name": cat,
                      "is_new_category": True, "language_detected": "ko"}, ensure_ascii=False)
    print(f"```json\n{out}\n```" if "FENCE" in title else out)
else:
    name = re.search(r"^카테고리명: (.*)$", prompt, re.M).group(1)
    new = re.findall(r"^- 제목: (.*)$", prompt, re.M)
    record("rebuild", {"category": name, "new": new})
    urls = re.findall(r"^  URL: (.*)$", prompt, re.M)
    prev_links = re.findall(r"^- \[.*$", prompt, re.M)
    refs = "\n".join(f"- [{t}]({u}) — 2026-01-01 — 요약" for t, u in zip(new, urls))
    print(f"# {name}\n\n## 한줄 요약\n{name} 주제 정리 (신규 {len(new)}건)\n\n## 핵심 내용\n"
          f"- 핵심 포인트\n\n## 최근 동향\n" + "\n".join(f"- {t}" for t in new) +
          "\n\n## 참고한 글\n" + "\n".join(prev_links) + ("\n" if prev_links else "") + refs)
