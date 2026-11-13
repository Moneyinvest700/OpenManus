import asyncio,sys
from app.agent.manus import Manus
from app.schema import Message
async def main():
 agent=await Manus.create(max_steps=8)
 try:
  result=await agent.run(sys.argv[1])
  answer=await agent.llm.ask(messages=[Message.user_message('Give the user a concise final answer in the language of their task. Use only the execution results below. State any failures or limits honestly. Do not claim actions that are not in the results.\nTask: '+sys.argv[1]+'\nExecution results:\n'+result[-18000:])],stream=False)
  print('\nFINAL ANSWER\n'+str(answer),flush=True)
 finally:
  await agent.cleanup()
asyncio.run(main())
