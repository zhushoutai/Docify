# write.py 最终方案
#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
import sys
import os

# 获取当前脚本的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 计算父目录路径（即包含llm-examples和MetaGPT的目录）
parent_dir = os.path.dirname(current_dir)
# 拼接MetaGPT的完整路径
metagpt_path = os.path.join(parent_dir, 'MetaGPT')
# 将路径插入到sys.path的最前面
sys.path.insert(0, metagpt_path)

import asyncio
from typing import Optional
from typing import Dict

from metagpt.roles.tutorial_assistant import TutorialAssistant
from metagpt.schema import Message

async def generate_content(topic: str) -> Optional[str]:
    try:
        # 初始化角色实例
        assistant = TutorialAssistant(language="Chinese")
        
        # 手动注入用户消息
        assistant.rc.memory.add(Message(content=topic, role="user"))
        
        # 执行完整反应链
        await assistant.react()
        
        # 直接返回内存中的生成内容
        return assistant.total_content
    except Exception as e:
        return f"生成失败：{str(e)}"

def generate_markdown(topic: str) -> str:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(generate_content(topic + "No detailed code is required.")) or "空响应"
    finally:
        loop.close()

if __name__ == "__main__":
    print(generate_markdown("测试主题"))