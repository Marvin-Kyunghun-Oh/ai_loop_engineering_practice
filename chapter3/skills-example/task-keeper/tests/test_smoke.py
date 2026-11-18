from sqlalchemy import event

from app.services.task_service import create_task, list_tasks


def test_create_and_list(client):
    res = client.post("/tasks", json={"title": "테스트 할 일", "tags": ["개인", "긴급"]})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "테스트 할 일"
    assert {t["name"] for t in body["tags"]} == {"개인", "긴급"}

    res = client.get("/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 1
    assert tasks[0]["tags"]


def test_list_tasks_query_count(db_session):
    # 할 일 개수와 무관하게 쿼리 수가 고정되어야 합니다(N+1 회귀 방지).
    for i in range(5):
        create_task(db_session, f"할 일 {i}", ["개인", f"태그{i}"])
    db_session.expire_all()  # create_task가 채워 둔 태그 캐시를 비웁니다.

    statements: list[str] = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count)
    try:
        tasks = list_tasks(db_session)
        assert all(task.tags for task in tasks)
    finally:
        event.remove(engine, "before_cursor_execute", count)

    # 할 일 조회 1회 + 태그 조회 1회
    assert len(statements) <= 2
