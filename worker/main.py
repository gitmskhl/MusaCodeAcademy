import asyncio

from app.core.redis import redis


async def main():
    pong = await redis.ping()
    print(pong)


if __name__ == "__main__":
    asyncio.run(main())