"""Internal helpers for scripts/restore-server.sh; run with app and worker stopped."""

import argparse
import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import make_url, select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.enums import SubmissionStatus
from app.models import Base, Submission


async def check_schema() -> None:
    engine = create_async_engine(settings.sqlalchemy_database_url)
    try:
        async with engine.connect() as connection:
            # Check all mapped columns, including empty tables, before switching databases.
            for table in Base.metadata.sorted_tables:
                await connection.execute(select(table).limit(0))
    finally:
        await engine.dispose()


async def rebuild_submission_queue() -> None:
    from app.core.redis import redis
    from app.queue.submission import QUEUE_NAME

    engine = create_async_engine(settings.sqlalchemy_database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            await session.execute(
                update(Submission)
                .where(Submission.status == SubmissionStatus.RUNNING)
                .values(status=SubmissionStatus.PENDING, passed_tests=0, total_tests=None,
                        failed_test_id=None, actual_output=None)
            )
            ids = (await session.scalars(
                select(Submission.id).where(Submission.status == SubmissionStatus.PENDING)
                .order_by(Submission.submitted_at, Submission.id)
            )).all()
            await session.commit()

        async with redis.pipeline(transaction=True) as pipeline:
            pipeline.delete(QUEUE_NAME)
            for offset in range(0, len(ids), 1000):
                pipeline.lpush(QUEUE_NAME, *ids[offset:offset + 1000])
            await pipeline.execute()
        print(f"Очередь проверок восстановлена: {len(ids)} заданий.")
    finally:
        await engine.dispose()
        await redis.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("database")
    subparsers.add_parser("rebuild-queue")
    args = parser.parse_args()

    if args.action == "prepare":
        url = make_url(settings.sqlalchemy_database_url)
        settings.sqlalchemy_database_url = url.set(database=args.database).render_as_string(hide_password=False)
        command.upgrade(Config("alembic.ini"), "head")
        asyncio.run(check_schema())
    else:
        asyncio.run(rebuild_submission_queue())


if __name__ == "__main__":
    main()
