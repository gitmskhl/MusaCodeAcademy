import asyncio

from app.core.redis import redis
from app.queue.submission import dequeue

async def main():
    await redis.ping()
    print('Worker started')

    while True:
        print('Waiting for submission...')
        submission_id = await dequeue()
        print(submission_id)

if __name__ == "__main__":
    asyncio.run(main())