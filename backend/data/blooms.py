import datetime

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from data.connection import db_cursor
from data.users import User


@dataclass
class Bloom:
    id: int
    sender: str
    content: str
    sent_timestamp: datetime.datetime
    original_bloom_id: Optional[int] = None
    original_sender: Optional[str] = None
    original_sent_timestamp: Optional[datetime.datetime] = None
    rebloom_count: int = 0


def add_bloom(
    *,
    sender: User,
    content: str,
    original_bloom_id: Optional[int] = None,
) -> Bloom:
    hashtags = [word[1:] for word in content.split(" ") if word.startswith("#")]

    now = datetime.datetime.now(tz=datetime.UTC)
    bloom_id = int(now.timestamp() * 1000000)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO blooms (id, sender_id, content, send_timestamp, original_bloom_id) VALUES (%(bloom_id)s, %(sender_id)s, %(content)s, %(timestamp)s, %(original_bloom_id)s)",
            dict(
                bloom_id=bloom_id,
                sender_id=sender.id,
                content=content,
                timestamp=now,
                original_bloom_id=original_bloom_id,
            ),
        )
        for hashtag in hashtags:
            cur.execute(
                "INSERT INTO hashtags (hashtag, bloom_id) VALUES (%(hashtag)s, %(bloom_id)s)",
                dict(hashtag=hashtag, bloom_id=bloom_id),
            )
    return Bloom(
        id=bloom_id,
        sender=sender.username,
        content=content,
        sent_timestamp=now,
        original_bloom_id=original_bloom_id,
    )


def _row_to_bloom(row):
    (
        bloom_id,
        sender_username,
        content,
        timestamp,
        original_bloom_id,
        original_send_timestamp,
        original_sender_username,
        rebloom_count,
    ) = row
    return Bloom(
        id=bloom_id,
        sender=sender_username,
        content=content,
        sent_timestamp=timestamp,
        original_bloom_id=original_bloom_id,
        original_sent_timestamp=original_send_timestamp,
        original_sender=original_sender_username,
        rebloom_count=rebloom_count,
    )


def get_blooms_for_user(
    username: str, *, before: Optional[int] = None, limit: Optional[int] = None
) -> List[Bloom]:
    with db_cursor() as cur:
        kwargs = {
            "sender_username": username,
        }
        if before is not None:
            before_clause = "AND b.send_timestamp < %(before_limit)s"
            kwargs["before_limit"] = before
        else:
            before_clause = ""

        limit_clause = make_limit_clause(limit, kwargs)

        cur.execute(
            f"""SELECT
              b.id,
              sender.username,
              b.content,
              b.send_timestamp,
              b.original_bloom_id,
              original_bloom.send_timestamp AS original_send_timestamp,
              original_sender.username AS original_sender_username,
              COUNT(rebloom_child.id) AS rebloom_count
            FROM blooms b
              INNER JOIN users sender ON sender.id = b.sender_id
              LEFT JOIN blooms original_bloom ON original_bloom.id = b.original_bloom_id
              LEFT JOIN users original_sender ON original_sender.id = original_bloom.sender_id
              LEFT JOIN blooms rebloom_child ON rebloom_child.original_bloom_id = b.id
            WHERE sender.username = %(sender_username)s
              {before_clause}
            GROUP BY b.id, sender.username, b.content, b.send_timestamp, b.original_bloom_id, original_bloom.send_timestamp, original_sender.username
            ORDER BY b.send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        return [_row_to_bloom(row) for row in rows]


def get_bloom(bloom_id: int) -> Optional[Bloom]:
    with db_cursor() as cur:
        cur.execute(
            """SELECT
              b.id,
              sender.username,
              b.content,
              b.send_timestamp,
              b.original_bloom_id,
              original_bloom.send_timestamp AS original_send_timestamp,
              original_sender.username AS original_sender_username,
              COUNT(rebloom_child.id) AS rebloom_count
            FROM blooms b
              INNER JOIN users sender ON sender.id = b.sender_id
              LEFT JOIN blooms original_bloom ON original_bloom.id = b.original_bloom_id
              LEFT JOIN users original_sender ON original_sender.id = original_bloom.sender_id
              LEFT JOIN blooms rebloom_child ON rebloom_child.original_bloom_id = b.id
            WHERE b.id = %s
            GROUP BY b.id, sender.username, b.content, b.send_timestamp, b.original_bloom_id, original_bloom.send_timestamp, original_sender.username
            """,
            (bloom_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_bloom(row)


def get_blooms_with_hashtag(
    hashtag_without_leading_hash: str, *, limit: int = None
) -> List[Bloom]:
    kwargs = {
        "hashtag_without_leading_hash": hashtag_without_leading_hash,
    }
    limit_clause = make_limit_clause(limit, kwargs)
    with db_cursor() as cur:
        cur.execute(
            f"""SELECT
              b.id,
              sender.username,
              b.content,
              b.send_timestamp,
              b.original_bloom_id,
              original_bloom.send_timestamp AS original_send_timestamp,
              original_sender.username AS original_sender_username,
              COUNT(rebloom_child.id) AS rebloom_count
            FROM blooms b
              INNER JOIN hashtags ON b.id = hashtags.bloom_id
              INNER JOIN users sender ON b.sender_id = sender.id
              LEFT JOIN blooms original_bloom ON original_bloom.id = b.original_bloom_id
              LEFT JOIN users original_sender ON original_sender.id = original_bloom.sender_id
              LEFT JOIN blooms rebloom_child ON rebloom_child.original_bloom_id = b.id
            WHERE hashtag = %(hashtag_without_leading_hash)s
            GROUP BY b.id, sender.username, b.content, b.send_timestamp, b.original_bloom_id, original_bloom.send_timestamp, original_sender.username
            ORDER BY b.send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        return [_row_to_bloom(row) for row in rows]


def make_limit_clause(limit: Optional[int], kwargs: Dict[Any, Any]) -> str:
    if limit is not None:
        limit_clause = "LIMIT %(limit)s"
        kwargs["limit"] = limit
    else:
        limit_clause = ""
    return limit_clause
