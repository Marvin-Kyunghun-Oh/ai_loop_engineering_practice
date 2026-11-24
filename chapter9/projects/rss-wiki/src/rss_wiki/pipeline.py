"""수집 파이프라인: 피드 1개를 가져와 글을 저장한다. feeds·repo만 사용한다."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from . import feeds, repo

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectResult:
    feed_id: int
    ok: bool
    not_modified: bool
    new_ids: tuple[int, ...]
    skipped_backfill: int
    skipped_unidentified: int
    error: str | None


def collect_feed(
    conn: sqlite3.Connection,
    feed_row: sqlite3.Row,
    fetcher: feeds.FeedFetcher,
    *,
    first_fetch_limit: int,
) -> CollectResult:
    """피드 1개를 수집해 새 글을 저장한다.

    쓰기는 repo 함수별 개별 트랜잭션이다. 중간에 중단되면 initial_fetch_done이 아직
    0이므로 다음 실행에서 첫 수집으로 다시 처리되고, 이미 저장된 글은 건너뛴다(멱등).
    FeedError는 던지지 않고 실패 결과로 돌려준다. 그 밖의 예외는 전파한다.

    Raises:
        ValueError: first_fetch_limit < 1 (DB·fetcher 접근 전).
    """
    if first_fetch_limit < 1:
        raise ValueError("first_fetch_limit은 1 이상이어야 합니다")
    feed_id = feed_row["id"]
    url = feed_row["url"]
    try:
        result = fetcher.fetch(
            url, etag=feed_row["etag"], last_modified=feed_row["last_modified"]
        )
    except feeds.FeedError as e:
        error = str(e).strip() or type(e).__name__
        repo.record_feed_failure(conn, feed_id, error)
        return CollectResult(feed_id, False, False, (), 0, 0, error)

    if result.not_modified or result.feed is None:
        repo.record_feed_success(
            conn, feed_id, etag=result.etag, last_modified=result.last_modified
        )
        return CollectResult(feed_id, True, True, (), 0, 0, None)

    first = feed_row["initial_fetch_done"] == 0
    identified: list[tuple[str, feeds.FeedEntry]] = []
    unidentified = 0
    for entry in result.feed.entries:
        key = feeds.entry_key(entry)
        if key is None:
            unidentified += 1
            log.warning("식별할 수 없는 항목을 건너뜀: feed=%s title=%r", url, entry.title)
            continue
        identified.append((key, entry))

    if first:
        # published 내림차순, None은 가장 오래된 것, 동률은 피드 순서 유지(stable sort)
        identified.sort(key=lambda ke: ke[1].published or "", reverse=True)
        # reverse=True도 stable이라 동률 순서가 유지된다.

    new_ids: list[int] = []
    backfill = 0
    for i, (key, entry) in enumerate(identified):
        skip = first and i >= first_fetch_limit
        aid = repo.insert_article_if_new(
            conn,
            feed_id,
            key,
            title=entry.title,
            url=entry.link,
            published=entry.published,
            status="skipped_backfill" if skip else "new",
        )
        if aid is None:
            continue
        if skip:
            backfill += 1
        else:
            new_ids.append(aid)

    repo.record_feed_success(
        conn, feed_id, etag=result.etag, last_modified=result.last_modified
    )
    if first:
        repo.mark_initial_fetch_done(conn, feed_id)
    return CollectResult(feed_id, True, False, tuple(new_ids), backfill, unidentified, None)
