import asyncio,sys
from app.agent.manus import Manus
async def main():
 agent=await Manus.create(max_steps=8)
 try:
  await agent.run(sys.argv[1])
 finally:
  await agent.cleanup()
asyncio.run(main())
