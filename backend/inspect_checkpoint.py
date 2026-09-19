import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import json
import pickle

async def main():
    engine = create_async_engine("postgresql+asyncpg://aarushisharma:@localhost:5432/quikhire_bgv")
    async with AsyncPostgresSaver(engine) as saver:
        # Get the latest checkpoint for the specific thread or any thread
        # We can just list the last few checkpoints
        async with engine.connect() as conn:
            result = await conn.execute("SELECT thread_id, checkpoint FROM checkpoints ORDER BY thread_id DESC LIMIT 5")
            for row in result.fetchall():
                thread_id = row[0]
                chkpt = pickle.loads(row[1]) if isinstance(row[1], bytes) else row[1]
                print(f"--- Thread: {thread_id} ---")
                # Look into the channel values
                if hasattr(chkpt, 'channel_values'):
                    cv = chkpt.channel_values
                    print("PII Map:", cv.get("pii_map"))
                    print("Extracted Data:", cv.get("extracted_data"))
                    print("Evaluation Result:", cv.get("evaluation_result"))

if __name__ == "__main__":
    asyncio.run(main())
