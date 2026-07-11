from app.core.redis import redis

QUEUE_NAME = "submission_queue"

async def enqueu(submission_id: int) -> None:
    await redis.lpush(QUEUE_NAME, submission_id)


async def dequeue() -> int:
    _, submission_id = await redis.brpop(QUEUE_NAME)
    return int(submission_id)

