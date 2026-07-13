import asyncio
import logging
import app.core.logging

from app.core.redis import redis
from app.queue.submission import dequeue
from worker.processor import process_submission

logger = logging.getLogger(__name__)

async def connect_to_redis():
    delay = 1
    while True:
        try:
            await redis.ping()
            logger.info("Connected to Redis")
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Failed to connect to Redis. Retrying in %s seconds",
                delay
            )
            await asyncio.sleep(delay)
            delay = min(2 * delay, 8)

async def main():
    await connect_to_redis()
    logger.info("Worker started")
    delay = 1
    submission_id = None
    while True:
        try:
            logger.debug('Waiting for submission...')
            submission_id = await dequeue()
            logger.debug('Received submission: %s', submission_id)
            await process_submission(submission_id=submission_id)
            delay = 1
        except asyncio.CancelledError:
            logger.info(
                "Processing submission %s was cancelled",
                submission_id
            )
            raise
        except Exception:
            logger.exception(
                "Worker iteration failed"
            )
            await asyncio.sleep(delay)
            delay = min(2 * delay, 8)

if __name__ == "__main__":
    asyncio.run(main())