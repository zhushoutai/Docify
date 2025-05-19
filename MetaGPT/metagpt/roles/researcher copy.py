# #!/usr/bin/env python
# """
# @Modified By: mashenquan, 2023/8/22. A definition has been provided for the return value of _think: returning false indicates that further reasoning cannot continue.
# @Modified By: mashenquan, 2023-11-1. According to Chapter 2.2.1 and 2.2.2 of RFC 116, change the data type of
#         the `cause_by` value in the `Message` to a string to support the new message distribution feature.
# """

# import asyncio
# import re

# from pydantic import BaseModel

# from metagpt.actions import Action, CollectLinks, ConductResearch, WebBrowseAndSummarize
# from metagpt.actions.research import get_research_system_text
# from metagpt.const import RESEARCH_PATH
# from metagpt.logs import logger
# from metagpt.roles.role import Role, RoleReactMode
# from metagpt.schema import Message


# class Report(BaseModel):
#     topic: str
#     links: dict[str, list[str]] = None
#     summaries: list[tuple[str, str]] = None
#     content: str = ""


# class Researcher(Role):
#     name: str = "David"
#     profile: str = "Researcher"
#     goal: str = "Gather information and conduct research"
#     constraints: str = "Ensure accuracy and relevance of information"
#     language: str = "en-us"
#     enable_concurrency: bool = True

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.set_actions([CollectLinks, WebBrowseAndSummarize, ConductResearch])
#         self._set_react_mode(RoleReactMode.BY_ORDER.value, len(self.actions))
#         if self.language not in ("en-us", "zh-cn"):
#             logger.warning(f"The language `{self.language}` has not been tested, it may not work.")

#     async def _act(self) -> Message:
#         logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
#         todo = self.rc.todo
#         msg = self.rc.memory.get(k=1)[0]
#         if isinstance(msg.instruct_content, Report):
#             instruct_content = msg.instruct_content
#             topic = instruct_content.topic
#         else:
#             topic = msg.content

#         research_system_text = self.research_system_text(topic, todo)
#         if isinstance(todo, CollectLinks):
#             links = await todo.run(topic, 4, 4)
#             ret = Message(
#                 content="", instruct_content=Report(topic=topic, links=links), role=self.profile, cause_by=todo
#             )
#         elif isinstance(todo, WebBrowseAndSummarize):
#             links = instruct_content.links
#             todos = (
#                 todo.run(*url, query=query, system_text=research_system_text) for (query, url) in links.items() if url
#             )
#             if self.enable_concurrency:
#                 summaries = await asyncio.gather(*todos)
#             else:
#                 summaries = [await i for i in todos]
#             summaries = list((url, summary) for i in summaries for (url, summary) in i.items() if summary)
#             ret = Message(
#                 content="", instruct_content=Report(topic=topic, summaries=summaries), role=self.profile, cause_by=todo
#             )
#         else:
#             summaries = instruct_content.summaries
#             summary_text = "\n---\n".join(f"url: {url}\nsummary: {summary}" for (url, summary) in summaries)
#             content = await self.rc.todo.run(topic, summary_text, system_text=research_system_text)
#             ret = Message(
#                 content="",
#                 instruct_content=Report(topic=topic, content=content),
#                 role=self.profile,
#                 cause_by=self.rc.todo,
#             )
#         self.rc.memory.add(ret)
#         return ret

#     def research_system_text(self, topic, current_task: Action) -> str:
#         """BACKWARD compatible
#         This allows sub-class able to define its own system prompt based on topic.
#         return the previous implementation to have backward compatible
#         Args:
#             topic:
#             language:

#         Returns: str
#         """
#         return get_research_system_text(topic, self.language)

#     async def react(self) -> Message:
#         msg = await super().react()
#         report = msg.instruct_content
#         self.write_report(report.topic, report.content)
#         return msg

#     def write_report(self, topic: str, content: str):
#         filename = re.sub(r'[\\/:"*?<>|]+', " ", topic)
#         filename = filename.replace("\n", "")
#         if not RESEARCH_PATH.exists():
#             RESEARCH_PATH.mkdir(parents=True)
#         filepath = RESEARCH_PATH / f"{filename}.md"
#         filepath.write_text(content)


# if __name__ == "__main__":
#     import fire

#     async def main(topic: str, language: str = "en-us", enable_concurrency: bool = True):
#         role = Researcher(language=language, enable_concurrency=enable_concurrency)
#         await role.run(topic)

#     fire.Fire(main)



#!/usr/bin/env python
"""
Enhanced Researcher role with:
1. Better error handling
2. Improved concurrency control
3. Source tracking
4. RAG integration support
5. Enhanced reporting
"""

import asyncio
import re
from typing import Coroutine
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from metagpt.actions import Action, CollectLinks, ConductResearch, WebBrowseAndSummarize
from metagpt.actions.research import get_research_system_text
from metagpt.const import RESEARCH_PATH
from metagpt.logs import logger
from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message


class Report(BaseModel):
    topic: str
    links: dict[str, list[str]] = None
    summaries: list[tuple[str, str]] = None  # (url, summary)
    content: str = ""
    sources: list[str] = []  # Track all sources used
    generated_at: datetime = None
    research_parameters: dict = None


from metagpt.actions import Action, UserRequirement
class Researcher(Role):
    name: str = "ResearchGPT"
    profile: str = "Senior Research Assistant"
    goal: str = "Search for relevant materials on the given topic"#"Conduct thorough and verifiable research on given topics"
    constraints: str = """  1. Verify facts with multiple sources
                            2. Clearly cite all sources"""
    language: str = "en-us"
    enable_concurrency: bool = True
    max_concurrent_browsers: int = 5  # Control parallel browsing
    default_search_params: dict = {
        'decomposition_nums': 3,
        'url_per_query': 3,
        'min_sources': 3  # Minimum sources required
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._watch([UserRequirement])
        self.set_actions([CollectLinks, WebBrowseAndSummarize, ConductResearch])
        self._set_react_mode(RoleReactMode.BY_ORDER.value, len(self.actions))
        self._semaphore = asyncio.Semaphore(self.max_concurrent_browsers)
        if self.language not in ("en-us", "zh-cn"):
            logger.warning(f"The language `{self.language}` has not been tested, it may not work.")

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: executing {self.rc.todo.name}")
        todo = self.rc.todo
        msg = self.rc.memory.get(k=1)[0]
        
        # Initialize report structure
        if isinstance(msg.instruct_content, Report):
            report = msg.instruct_content
            topic = report.topic
            
            report.research_parameters = self.default_search_params
        else:
            topic = msg.content
            report = Report(
                topic=topic,
                research_parameters=self.default_search_params,
                generated_at=datetime.now()
            )
            report.research_parameters = self.default_search_params

        research_system_text = self.research_system_text(topic, todo)
        
        try:
            print(f"🛠️ 当前阶段：{type(todo).__name__}")
            if isinstance(todo, CollectLinks):
                # Phase 1: Link Collection
                print(f"🔍 开始收集相关链接，主题：{topic}")
                links = await todo.run(
                    topic=topic,
                    decomposition_nums=report.research_parameters['decomposition_nums'],
                    url_per_query=report.research_parameters['url_per_query'],
                    system_text=research_system_text
                )
                report.links = links
                ret = Message(
                    content="",
                    instruct_content=report,
                    role=self.profile,
                    cause_by=type(todo).__name__
                )
                print(f"✅ 链接收集完成，共找到 {sum(len(v) for v in links.values())} 个链接")
            
            elif isinstance(todo, WebBrowseAndSummarize):
                # Phase 2: Content Analysis
                print(f"📝 开始浏览并总结，链接数量：{len(report.links)}")
                if not report.links:
                    raise ValueError("No links available for browsing")
                
                # Process links with concurrency control
                summaries = await self._browse_and_summarize(
                    todo, report.links, research_system_text
                )
                
                if len(summaries) < report.research_parameters['min_sources']:
                    logger.warning(f"Only {len(summaries)} valid sources found")
                
                report.summaries = summaries
                report.sources = [url for url, _ in summaries]
                ret = Message(
                    content="",
                    instruct_content=report,
                    role=self.profile,
                    cause_by=type(todo).__name__
                )
                print(f"✅ 总结完成，共总结 {len(summaries)} 条信息")
            
            else:
                # Phase 3: Report Generation
                print(f"🧠 开始撰写调研报告...")
                if not report.summaries:
                    raise ValueError("No content available for research")
                
                research_text = self._prepare_research_text(report.summaries)
                content = await todo.run(
                    topic=topic,
                    content=research_text,
                    system_text=research_system_text
                )
                
                report.content = content
                report.generated_at = datetime.now()
                ret = Message(
                    content="",
                    instruct_content=report,
                    role=self.profile,
                    cause_by=type(todo).__name__
                )
                print(f"✅ 报告撰写完成")
            
            self.rc.memory.add(ret)
            return ret
        
        except Exception as e:
            logger.error(f"Error in {todo.name}: {str(e)}")
            # Store error in report
            report.content = f"Research failed at {todo.name} stage: {str(e)}"
            return Message(
                content=str(e),
                instruct_content=report,
                role=self.profile,
                cause_by=type(todo).__name__
            )

    async def _browse_and_summarize(
        self,
        action: Action,
        links: dict[str, list[str]],
        system_text: str
    ) -> list[tuple[str, str]]:
        """Process links with concurrency control and error handling"""
        tasks = []
        for query, urls in links.items():
            for url in urls[:4]:  # Process max 4 urls per query
                task = self._create_browse_task(action, url, query, system_text)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        valid_summaries = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Browsing task failed: {res}")
            elif res:
                valid_summaries.extend(res.items())
        
        return valid_summaries

    def _create_browse_task(
        self,
        action: Action,
        url: str,
        query: str,
        system_text: str
    ) -> Coroutine:
        """Create browsing task with semaphore control"""
        async def task():
            async with self._semaphore:
                try:
                    return await action.run(
                        url=url,
                        query=query,
                        system_text=system_text
                    )
                except Exception as e:
                    logger.warning(f"Failed to process {url}: {e}")
                    return None
        return task()

    def _prepare_research_text(self, summaries: list[tuple[str, str]]) -> str:
        """Format research material for RAG processing"""
        return "\n\n---\n".join(
            f"Source: {url}\nContent:\n{summary}"
            for url, summary in summaries
        )

    def research_system_text(self, topic: str, current_task: Action) -> str:
        """Generate task-specific system prompt"""
        base_prompt = get_research_system_text(topic, self.language)
        
        if isinstance(current_task, CollectLinks):
            return f"{base_prompt}\nFocus on finding authoritative sources."
        elif isinstance(current_task, WebBrowseAndSummarize):
            return f"{base_prompt}\nAnalyze content critically and summarize the content in detail and comprehensively."
        return base_prompt

    async def react(self) -> Message:
        """Override to add post-processing"""
        msg = await super().react()
        
        if hasattr(msg.instruct_content, 'content'):
            self.write_report(
                msg.instruct_content.topic,
                msg.instruct_content.content,
                sources=msg.instruct_content.sources
            )
        
        return msg

    def write_report(self, topic: str, content: str, sources: list = None):
        """Save report with metadata"""
        # Sanitize filename
        filename = re.sub(r'[\\/:"*?<>|]+', "_", topic)[:100]
        filename = filename.replace("\n", "_") + ".md"
        
        # Add sources if provided
        if sources:
            content += "\n\n## References\n" + "\n".join(f"- {url}" for url in sources)
        
        # Ensure research directory exists
        RESEARCH_PATH.mkdir(exist_ok=True, parents=True)
        
        # Write file
        filepath = RESEARCH_PATH / filename
        filepath.write_text(content)
        logger.info(f"Report saved to {filepath}")


if __name__ == "__main__":
    import fire

    async def main(
        topic: str,
        language: str = "en-us",
        enable_concurrency: bool = True,
        min_sources: int = 3
    ):
        role = Researcher(
            language=language,
            enable_concurrency=enable_concurrency,
        )
        await role.run(topic)

    fire.Fire(main)