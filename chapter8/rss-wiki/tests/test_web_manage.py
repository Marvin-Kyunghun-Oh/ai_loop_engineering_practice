import time

import pytest
from fakes import FakeLLM
from fastapi.testclient import TestClient

from rss_wiki.db import connect
from rss_wiki.main import create_app
from rss_wiki.pipeline.summarizer import resolve_category

PAGE = "# 대상\n\n## 한줄 요약\n병합 후\n\n## 핵심 내용\n내용"


@pytest.fixture
def llm():
    return FakeLLM(text_responses=[PAGE])


@pytest.fixture
def client(settings, llm):
    with TestClient(create_app(settings, llm=llm), follow_redirects=False) as c:
        yield c


@pytest.fixture
def db(client, settings):
    conn = connect(settings.db_path)
    conn.execute("INSERT INTO feeds(id, url) VALUES (1, 'http://f')")
    conn.commit()
    yield conn
    conn.close()


def cat(db, id, name, parent=None):
    db.execute("INSERT INTO categories(id, name, parent_id) VALUES (?,?,?)", (id, name, parent))
    db.commit()


def art(db, id, cat_id, title=None, status="ok"):
    db.execute("INSERT INTO articles(id, feed_id, url, title, llm_summary, primary_category_id, status) "
               "VALUES (?,1,?,?,'요약.',?,?)", (id, f"https://a.com/{id}", title or f"글{id}", cat_id, status))
    db.commit()


def one(db, sql, *a):
    return db.execute(sql, a).fetchone()


def wait_for(fn, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        time.sleep(0.05)
    return False


def test_manage_page_lists_active_only(client, db):
    cat(db, 1, "A"); cat(db, 2, "B")
    db.execute("UPDATE categories SET merged_into_id=1 WHERE id=2"); db.commit()
    html = client.get("/categories/manage").text
    assert r">A</a>" in html and r">B</a>" not in html


def test_rename_marks_user_edited(client, db):
    cat(db, 1, "A")
    assert client.post("/categories/1/rename", data={"name": " 새이름 "}).status_code == 303
    row = one(db, "SELECT name, is_user_edited FROM categories WHERE id=1")
    assert (row["name"], row["is_user_edited"]) == ("새이름", 1)


def test_rename_conflict_and_blank(client, db):
    cat(db, 1, "A"); cat(db, 2, "B")
    assert client.post("/categories/1/rename", data={"name": "B"}).status_code == 409
    assert client.post("/categories/1/rename", data={"name": "   "}).status_code == 400
    assert one(db, "SELECT name FROM categories WHERE id=1")[0] == "A"
    assert client.post("/categories/99/rename", data={"name": "x"}).status_code == 404


def test_merge_moves_articles_deletes_wiki_and_rebuilds_target(client, db, llm):
    cat(db, 1, "원본"); cat(db, 2, "대상")
    art(db, 1, 1, "원본글1"); art(db, 2, 1, "원본글2"); art(db, 3, 2, "대상글")
    db.execute("INSERT INTO wiki_pages(category_id, content_markdown) VALUES (1, '# 원본')")
    db.commit()
    assert client.post("/categories/1/merge", data={"target_id": 2}).status_code == 303
    assert {r[0] for r in db.execute("SELECT primary_category_id FROM articles")} == {2}
    assert one(db, "SELECT merged_into_id FROM categories WHERE id=1")[0] == 2
    assert one(db, "SELECT COUNT(*) FROM wiki_pages WHERE category_id=1")[0] == 0
    assert wait_for(lambda: one(db, "SELECT content_markdown FROM wiki_pages WHERE category_id=2"))
    w = one(db, "SELECT * FROM wiki_pages WHERE category_id=2")
    assert w["content_markdown"] == PAGE and w["has_unread_updates"] == 1 and w["articles_count_at_rebuild"] == 3
    prompt = llm.text_prompts[0]
    assert "원본글1" in prompt.split("[기존 글 중")[0] and "원본글2" in prompt.split("[기존 글 중")[0]  # 이번에 옮겨온 글이 new_articles


def test_old_name_resolves_to_target_after_merge(client, db):
    cat(db, 1, "원본"); cat(db, 2, "대상")
    client.post("/categories/1/merge", data={"target_id": 2})
    assert resolve_category(db, "원본") == 2


def test_merge_validation(client, db):
    cat(db, 1, "A"); cat(db, 2, "B")
    assert client.post("/categories/1/merge", data={"target_id": 1}).status_code == 400
    assert client.post("/categories/1/merge", data={"target_id": 99}).status_code == 404
    assert client.post("/categories/99/merge", data={"target_id": 1}).status_code == 404
    assert one(db, "SELECT merged_into_id FROM categories WHERE id=1")[0] is None


def test_merge_into_merged_target_follows_chain(client, db):
    cat(db, 1, "A"); cat(db, 2, "B"); cat(db, 3, "C")
    client.post("/categories/2/merge", data={"target_id": 3})
    client.post("/categories/1/merge", data={"target_id": 2})  # B는 C로 병합됨 → C로
    assert one(db, "SELECT merged_into_id FROM categories WHERE id=1")[0] == 3


def test_merge_root_with_children_into_root_reparents_children(client, db):
    cat(db, 1, "루트1"); cat(db, 2, "자식", 1); cat(db, 3, "루트2")
    client.post("/categories/1/merge", data={"target_id": 3})
    assert one(db, "SELECT parent_id FROM categories WHERE id=2")[0] == 3


def test_merge_root_into_child_of_other_root_keeps_two_levels(client, db):
    cat(db, 1, "루트1"); cat(db, 2, "자식1", 1); cat(db, 3, "루트2"); cat(db, 4, "자식2", 3)
    client.post("/categories/1/merge", data={"target_id": 4})
    assert one(db, "SELECT parent_id FROM categories WHERE id=2")[0] == 3  # 대상의 상위 아래로
    assert one(db, "SELECT parent_id FROM categories WHERE id=4")[0] == 3


def test_merge_root_into_its_own_child(client, db):
    cat(db, 1, "루트"); cat(db, 2, "자식", 1); cat(db, 3, "형제", 1)
    client.post("/categories/1/merge", data={"target_id": 2})
    assert one(db, "SELECT parent_id FROM categories WHERE id=2")[0] is None  # 대상이 최상위로 올라감
    assert one(db, "SELECT parent_id FROM categories WHERE id=3")[0] == 2     # 형제는 대상 아래로


def test_set_and_clear_parent(client, db):
    cat(db, 1, "루트"); cat(db, 2, "리프")
    assert client.post("/categories/2/parent", data={"parent_id": "1"}).status_code == 303
    assert one(db, "SELECT parent_id FROM categories WHERE id=2")[0] == 1
    assert client.post("/categories/2/parent", data={"parent_id": ""}).status_code == 303
    assert one(db, "SELECT parent_id FROM categories WHERE id=2")[0] is None


def test_parent_validation_two_level_limit(client, db):
    cat(db, 1, "루트"); cat(db, 2, "자식", 1); cat(db, 3, "손자후보"); cat(db, 4, "다른루트")
    assert client.post("/categories/3/parent", data={"parent_id": "2"}).status_code == 400  # 부모가 자식
    assert client.post("/categories/1/parent", data={"parent_id": "4"}).status_code == 400  # 하위가 있는 루트
    assert client.post("/categories/1/parent", data={"parent_id": "1"}).status_code == 400  # 자기 자신
    assert client.post("/categories/3/parent", data={"parent_id": "99"}).status_code == 404
    assert client.post("/categories/3/parent", data={"parent_id": "abc"}).status_code == 400
    assert one(db, "SELECT parent_id FROM categories WHERE id=3")[0] is None


def test_manage_route_not_shadowed_by_category_id(client):
    assert client.get("/categories/manage").status_code == 200
