import os
import streamlit as st
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
import nest_asyncio
nest_asyncio.apply()

# 定义生成用例图的 Action 类
class ParseDocument(Action):
    async def run(self, document: str):
        if not document.strip():
            raise ValueError("需求文档内容为空")
        return ""  # 不返回显示内容

class GenerateUseCaseDiagram(Action):
    async def run(self, document: str):
        prompt = f"""请根据以下完整的软件需求规格说明书（SRS），生成用例图的 PlantUML 脚本，遵循 UML 2.0 标准，适合软件工程需求分析。输出使用 PlantUML 格式，直接写内容（无需 ```plantuml```），内容需清晰、结构化，适合技术文档。总长度约 100-300 行，包含以下内容：

1. **参与者（Actors）**：
   - 从文档的“用户特征”或“相关方”部分提取所有参与者（如用户角色、外部系统）。
   - 包括主要和次要参与者（如管理员、普通用户、第三方API）。
   - 示例：actor "管理员" as Admin

2. **用例（Use Cases）**：
   - 从“功能需求”或“产品功能概述”部分提取系统的主要功能作为用例（至少 7-10 个）。
   - 用例名称应简洁、动词开头（如 "管理库存"），反映具体功能。
   - 示例：(管理库存)

3. **关系（Relationships）**：
   - 定义参与者与用例的关联（使用 -->）。
   - 识别 <<include>> 和 <<extend>> 关系，基于功能之间的依赖或扩展（如“登录”包含“验证身份”）。
   - 示例：Admin --> (管理库存)
   - 示例：(登录) .> (重置密码) : <<extend>>

4. **注释（Notes）**：
   - 添加注释说明用例的目的、上下文或特殊条件，基于“功能描述”或“非功能需求”。
   - 示例：note right of (管理库存) : 允许管理员实时查看和更新库存水平

要求：
- 深入分析 SRS 文档，重点从“用户特征”、“功能需求”和“总体描述”部分提取信息。
- 确保提取的参与者和用例准确反映文档内容，避免假设未提及的功能。
- 使用专业术语，确保用例名称和关系符合 UML 规范。
- 确保 PlantUML 脚本语法正确，可直接渲染为用例图。
- 按模块或功能分组，保持逻辑清晰。
- 示例输出：
@startuml
actor "管理员" as Admin
actor "用户" as User
actor "CRM系统" as CRM
Admin --> (登录)
Admin --> (管理库存)
User --> (查看报表)
CRM --> (同步数据)
(登录) .> (重置密码) : <<extend>>
(管理库存) .> (更新库存) : <<include>>
note right of (管理库存) : 允许管理员查看和更新库存水平
@enduml

软件需求规格说明书如下：
{document}
"""
        return await self._aask(prompt)

# 定义用例图生成的角色
class UseCaseDiagramAgent(Role):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([
            ParseDocument(),
            GenerateUseCaseDiagram()
        ])

    async def _act(self) -> Message:
        msg = self.rc.memory.get()[-1]
        result = msg.content
        combined_result = ""

        for action in self.actions:
            if isinstance(action, ParseDocument):
                await action.run(result)  # 解析文档但不保存输出
                continue
            part = await action.run(result)
            combined_result += f"{part.strip()}\n\n"

        return Message(content=combined_result, role=self.profile)

# Streamlit 应用界面
st.title("📊 用例图生成 Agent")

uploaded_file = st.file_uploader("上传需求规格说明书（.txt 或 .md）", type=("txt", "md"))
generate_button = st.button("生成用例图")

if uploaded_file and generate_button:
    content = uploaded_file.read().decode('utf-8')
    if not content.strip():
        st.error("上传的文档内容为空，请上传有效的需求规格说明书。")
    else:
        try:
            agent = UseCaseDiagramAgent()
            result = asyncio.run(agent.run(Message(content=content)))
            st.success("✅ 成功生成用例图")
            st.download_button(
                label="📥 下载用例图 PlantUML 脚本",
                data=result.content,
                file_name="use_case_diagram.puml",
                mime="text/plain"
            )
            st.markdown("### 📄 生成的用例图 PlantUML 脚本预览")
            st.code(result.content, language="plantuml")
        except Exception as e:
            logger.error(f"执行失败: {str(e)}")
            st.error(f"执行失败: {str(e)}")