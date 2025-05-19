import os
import streamlit as st
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
import nest_asyncio
nest_asyncio.apply()

# 新增：文档对比与标准化功能类 [8,6](@ref)
class DocumentStandardizer(Action):
    async def run(self, original_content: str, standard_content: str):
        """
        实现文档对比与格式标准化
        参数：
        original_content: 需要修改的文档内容
        standard_content: 标准格式文档内容
        """
        prompt = f"""请根据以下标准格式文档，对需要修改的文档进行格式标准化处理。要求：
1. 保留原始文档的核心内容
2. 完全应用标准文档的格式规范（包括但不限于）：
   - 章节结构
   - 标题层级
   - 段落格式
   - 列表样式
   - 专业术语
3. 输出使用Markdown格式
4. 保持技术文档的专业性

标准格式文档内容：
{standard_content}

需要修改的原始文档内容：
{original_content}

处理后的文档应体现以下改进：
- 标题采用## 二级标题格式（如标准文档所示）
- 功能描述使用编号列表
- 参数说明使用表格形式
- 代码块用```python包裹
- 关键术语加粗显示

原文档的所有内容一定不能删除，标准格式文档相较于原文档多的部分应尽量补充
"""
        return await self._aask(prompt)

# 简化后的角色类 [2](@ref)
class DocStandardizerAgent(Role):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([DocumentStandardizer()])  # 仅保留一个核心功能类

    async def _act(self) -> Message:
        # 获取两个文档内容 [7](@ref)
        msg = self.rc.memory.get()[-1]
        original_content, standard_content = msg.content.split("|||")  # 用分隔符区分两个文档
        
        # 执行标准化处理
        action = self.rc.todo
        result = await action.run(original_content, standard_content)
        
        return Message(content=result, role=self.profile)

# 修改后的Streamlit界面（保持布局基本不变）[2](@ref)
st.title("📄 文档格式标准化工具")

# 新增：双文档上传功能 [7](@ref)
col1, col2 = st.columns(2)
with col1:
    original_file = st.file_uploader("上传待修改文档", type=("txt", "md"))
with col2:
    standard_file = st.file_uploader("上传标准格式文档", type=("txt", "md"))

process_button = st.button("执行标准化处理")

if original_file and standard_file and process_button:
    try:
        # 读取双文档内容 [6](@ref)
        original_content = original_file.read().decode('utf-8')
        standard_content = standard_file.read().decode('utf-8')
        
        if not original_content.strip() or not standard_content.strip():
            st.error("文档内容不能为空")
        else:
            # 通过分隔符传递双文档内容
            combined_content = f"{original_content}|||{standard_content}"
            
            agent = DocStandardizerAgent()
            result = asyncio.run(agent.run(Message(content=combined_content)))
            
            st.success("✅ 文档标准化处理完成")
            st.download_button(
                label="📥 下载标准化文档",
                data=result.content,
                file_name="标准化文档.md",
                mime="text/markdown"
            )
            st.markdown("### 处理结果预览")
            st.markdown(result.content)
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        st.error(f"处理失败: {str(e)}")