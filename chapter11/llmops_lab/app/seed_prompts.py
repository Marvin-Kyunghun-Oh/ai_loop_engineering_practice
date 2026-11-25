# app/seed_prompts.py
# 프롬프트를 랭퓨즈에 등록하는 명령 

from pathlib import Path
from dotenv import load_dotenv

from .langfuse_ops import get_client

load_dotenv()


def main():
    # 랭퓨즈 클라이언트 가져오기
    client = get_client()
    template = Path("prompts/support_answer.md").read_text(encoding="utf-8")
    # 1. 이름, 본문, label을 함께 등록
    client.create_prompt(
        name="support-answer-v1",
        prompt=template,
        labels=["production"],
        type="text",
    )
    client.flush()
    print("등록 완료: support-answer-v1 (production)")


if __name__ == "__main__":
    main()