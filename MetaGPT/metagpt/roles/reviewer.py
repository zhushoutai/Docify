from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.roles.researcher import Report,ConductResearch,CollectLinks,WebBrowseAndSummarize

class ReviewResearchReport(Action):
    name: str = "ReviewResearchReport"
    PROMPT_TEMPLATE: str = """
You are a strict research auditor. Carefully review the following research report.

Topic: "{topic}"

Sources:
{citations}

--- Report Content ---
{content}
--- End ---

Instructions:
- Check for factual errors, missing citations, vague or unsupported claims.
- Ensure the writing is clear, logically structured, and professional.
- Verify that at least {min_sources} different valid sources were used.
- If good, reply exactly: "APPROVED"
- If issues exist, reply exactly: "REJECTED: <feedback>"

Your Response:
"""

    async def run(self, report: Report):
        citations = "\n".join(f"- {s}" for s in (report.sources or [])) or "No citations provided"
        prompt = self.PROMPT_TEMPLATE.format(
            topic=report.topic,
            citations=citations,
            content=report.content,
            min_sources=report.research_parameters.get('min_sources', 3)
        )
        rsp = await self._aask(prompt)
        return rsp.strip()


class Reviewer(Role):
    name: str = "ReviewerGPT"
    profile: str = "Research Quality Inspector"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ReviewResearchReport])
        self._watch([ConductResearch])  # 注意这里要监听 ConductResearch 产生的最终报告

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: executing {self.rc.todo.name}")
        todo = self.rc.todo

        # 获取上一个阶段 Researcher 产出的 Report
        report_msg = self.rc.memory.get(k=1)[0]
        report: Report = report_msg.instruct_content

        review_result = await todo.run(report)

        review_msg = Message(
            content=review_result,
            instruct_content=report,
            role=self.profile,
            cause_by=type(todo).__name__,
        )
        return review_msg


from metagpt.team import Team
from metagpt.logs import logger
from metagpt.roles.researcher import Researcher
async def main(
    topic: str = "The impact of AI on scientific discovery",
    investment: float = 3.0,
    n_round: int = 2,
    add_human_reviewer: bool = False
):
    logger.info(f"🚀 Research Topic: {topic}")

    # 初始化团队
    team = Team()
    team.hire([
        Researcher(),
        Reviewer(is_human=add_human_reviewer),
    ])

    team.invest(investment=investment)
    team.run_project(topic)

    # 多轮迭代运行
    for i in range(n_round):
        logger.info(f"🌀 Round {i+1}/{n_round}")
        await team.run(n_round=1)

        # 检查最新 Reviewer 反馈
        latest_msgs = team.project.history[-2:]  # 取最后两步（Researcher + Reviewer）
        reviewer_msg = next((m for m in latest_msgs if m.role == "Research Quality Inspector"), None)

        if reviewer_msg:
            if reviewer_msg.content.strip().startswith("APPROVED"):
                logger.info("✅ Research report approved!")
                break
            else:
                logger.warning("❌ Research report rejected, requesting revision...")
                # 重新触发 Researcher 继续优化（你可以加修改提示作为补充）
                team.run_project(topic)  # 重新以 topic 触发改进
        else:
            logger.warning("⚠️ No reviewer feedback found, proceeding to next round.")
