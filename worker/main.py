import asyncio

from app.core.redis import redis
from app.queue.submission import dequeue
from worker.processor import process_submission

async def main():
    await redis.ping()
    print('Worker started')

    while True:
        print('Waiting for submission...')
        submission_id = await dequeue()
        print(f'Received submission: {submission_id}')
        await process_submission(submission_id=submission_id)

if __name__ == "__main__":
    asyncio.run(main())