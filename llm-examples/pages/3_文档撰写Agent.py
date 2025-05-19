import os
import streamlit as st
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
import nest_asyncio
nest_asyncio.apply()

# 定义各个文档生成的 Action 类
class ParseOutline(Action):
    async def run(self, outline: str):
        if not outline.strip():
            raise ValueError("大纲内容为空")
        return ""  # 不返回显示内容

class GenerateIntro(Action):
    async def run(self, outline: str):
        prompt = f"""请根据以下项目大纲，生成《引言》部分内容，严格遵循 GB/T 8567-2006 标准，内容需详尽、专业，适合正式的软件需求规格说明书。输出使用 Markdown 格式，直接写内容（无需 ```markdown```），每部分内容需清晰、逻辑严谨，总长度约 200-300 字。包括以下子章节：

1.1 标识
- 提供系统和软件的完整标识，包括：
  - 标识号（如 SRS-XXX-001）
  - 标题（系统全称）
  - 缩略词（如 ERP、CRM）
  - 版本号（如 V1.0.0）
  - 发行号（如 R1）
- 示例：标识号：SRS-ERP-001；标题：企业资源计划系统；缩略词：ERP；版本号：V1.0.0；发行号：R1。

1.2 系统概述
- 详细描述系统和软件的用途（如解决什么问题、提供什么功能）。
- 说明系统的一般性质（如实时性、分布式）。
- 概述开发、运行和维护历史（如开发起始时间、当前状态）。
- 列出相关方（如开发团队、客户、用户群体）。
- 描述运行现场（如部署环境：云端、本地服务器）。
- 提及相关文档（如用户手册、设计文档）。
- 示例： 企业资源计划系统旨在优化企业资源管理，支持库存、财务和人力资源管理。该系统采用模块化设计，运行于云端，开发始于2023年，当前为Beta版，计划于2025年正式发布。主要相关方包括开发团队（ABC公司）、客户（中小型企业）和最终用户（财务人员）。运行于AWS云端，相关文档包括《用户手册》和《API参考》。

1.3 文档概述
- 说明本文档的用途（如指导开发、测试和验证）。
- 描述文档内容结构（简要概述各章节）。
- 明确保密性与私密性要求（如仅限内部使用、需签署NDA）。
- 示例：本文档为企业资源计划系统的需求规格说明书，用于指导开发和测试团队，确保系统满足客户需求。内容包括总体描述、功能需求、非功能需求等。文档属机密，仅限项目相关方使用，未经授权不得外传。

要求：
- 深入分析大纲，提取关键信息（如系统名称、目标用户、功能范围）并融入输出。
- 使用正式、专业的语言，避免口语化表达。
- 确保内容逻辑清晰，层次分明，适合技术文档场景。

项目大纲如下：
{outline}
"""
        return await self._aask(prompt)

class GenerateOverallDesc(Action):
    async def run(self, outline: str):
        prompt = f"""请根据以下项目大纲，生成《总体描述》章节，严格遵循 GB/T 8567-2006 标准，内容需详尽、结构清晰，适合正式的软件需求规格说明书。输出使用 Markdown 格式，直接写内容（无需 ```markdown```），每部分内容约 150-200 字，总长度约 600-800 字。包括以下子章节：

2.1 产品视角
- 描述软件在整个系统中的位置和作用（如核心组件、与硬件的交互）。
- 说明软件与其他系统的关系（如集成第三方服务、数据交互）。
- 示例：企业资源计划系统是企业管理平台的核心，负责协调库存、财务和人力资源模块，与外部CRM系统通过API集成，运行于云端服务器，支持多租户架构。

2.2 产品功能概述
- 详细概述软件的主要功能（至少 5-7 个关键功能）。
- 使用简洁的描述，按优先级或模块分组。
- 示例：
  - 库存管理：实时跟踪库存水平，支持自动补货。
  - 财务管理：生成财务报表，支持多币种结算。
  - 人力资源管理：管理员工档案、薪资和考勤。

2.3 用户特征
- 详细描述目标用户的特征，包括：
  - 用户角色（如管理员、财务人员）。
  - 技术水平（如熟悉Excel、无编程经验）。
  - 使用场景（如办公室、移动端）。
- 示例：目标用户包括中小型企业的财务人员（熟悉基本办公软件）、仓库管理员（需简单界面）和高管（需报表分析）。主要在办公室使用，部分功能支持移动端。

2.4 假设与依赖关系
- 列出系统运行的假设（如稳定的网络连接、用户培训完成）。
- 描述外部依赖（如操作系统、数据库、第三方API）。
- 示例：假设用户完成系统培训，网络带宽不低于10Mbps。依赖MySQL数据库、AWS云服务和第三方支付网关（如Stripe）。

要求：
- 深入分析大纲，提取系统目标、功能和用户等信息，扩展为详细描述。
- 使用专业术语，保持技术文档的正式语气。
- 确保内容层次分明，适合开发和测试人员使用。

项目大纲如下：
{outline}
"""
        return await self._aask(prompt)

class GenerateFuncReq(Action):
    async def run(self, outline: str):
        prompt = f"""请根据以下项目大纲，生成《功能需求》章节，严格遵循 GB/T 8567-2006 标准，内容需详细、结构清晰，适合开发和测试人员使用。输出使用 Markdown 格式，直接写内容（无需 ```markdown```），总长度约 800-1000 字。结构如下：

- 每个功能点包括：
  - 功能描述：详细说明功能的作用和目的（约 50-70 字）。
  - 输入/输出说明：描述用户输入和系统输出（包括格式、范围）。
  - 验收标准：明确功能成功的标准（可量化或可测试）。
  - 优先级：高/中/低。
- 至少生成 5-7 个功能点，按模块或优先级分组。

示例：
### 功能 1：库存查询
- **功能描述**：允许用户查询指定仓库的库存水平，支持按产品类别或批次过滤。
- **输入/输出说明**：
  - 输入：产品类别（如“电子产品”）、批次号（如“2023-001”）。
  - 输出：库存列表（表格格式，包含产品ID、名称、数量、位置）。
- **验收标准**：查询响应时间小于2秒，列表准确反映数据库中的最新库存数据。
- **优先级**：高

要求：
- 深入分析大纲，提取关键功能并扩展为详细描述。
- 确保每个功能点的描述具体、可测试，输入/输出清晰。
- 使用专业语言，结构一致，适合技术文档。

项目大纲如下：
{outline}
"""
        return await self._aask(prompt)

class GenerateNonFuncReq(Action):
    async def run(self, outline: str):
        prompt = f"""请根据以下项目大纲，生成《非功能需求》章节，严格遵循 GB/T 8567-2006 标准，内容需详尽、专业，适合正式的软件需求规格说明书。输出使用 Markdown 格式，直接写内容（无需 ```markdown```），每部分约 100-150 字，总长度约 500-750 字。包括以下子章节：

- 性能需求
  - 描述系统性能要求（如响应时间、吞吐量、并发用户数）。
  - 示例：系统需支持1000并发用户，页面加载时间不超过2秒，批量数据处理每分钟1000条记录。

- 安全性
  - 说明数据保护、访问控制和认证要求。
  - 示例：支持SSO登录，所有数据传输使用TLS 1.3加密，敏感数据（如薪资）需字段级加密。

- 可用性
  - 定义系统可用性目标（如年可用性百分比、故障恢复时间）。
  - 示例：系统年可用性达99.9%，平均故障恢复时间（MTTR）小于1小时。

- 可维护性
  - 描述系统维护的便捷性（如日志记录、模块化设计）。
  - 示例：系统提供详细错误日志，支持热更新，模块化设计便于功能扩展。

- 可移植性
  - 说明系统在不同环境下的兼容性（如操作系统、云平台）。
  - 示例：系统兼容Windows和Linux服务器，支持AWS和Azure云部署。

要求：
- 深入分析大纲，提取系统特性并扩展为详细描述。
- 使用量化指标（如时间、百分比）增强可测试性。
- 保持专业语气，内容适合技术文档场景。

项目大纲如下：
{outline}
"""
        return await self._aask(prompt)

class GenerateInterfaces(Action):
    async def run(self, outline: str):
        prompt = f"""请根据以下项目大纲，生成《外部接口需求》章节，严格遵循 GB/T 8567-2006 标准，内容需详尽、结构清晰，适合正式的软件需求规格说明书。输出使用 Markdown 格式，直接写内容（无需 ```markdown```），每部分约 100-150 字，总长度约 400-600 字。包括以下子章节：

- 用户接口
  - 描述用户交互界面（如GUI、CLI、移动端）。
  - 示例：系统提供基于Web的GUI，支持响应式设计，兼容主流浏览器（Chrome、Firefox）。移动端支持iOS和Android原生应用。

- 硬件接口
  - 说明与硬件设备的交互（如传感器、打印机）。
  - 示例：系统通过USB接口与条码扫描器通信，支持Zebra系列设备，数据传输速率达480Mbps。

- 软件接口
  - 描述与外部软件的交互（如API、数据库）。
  - 示例：系统通过RESTful API与CRM系统集成，支持JSON格式，API响应时间小于500ms。

- 通讯接口
  - 说明网络通信协议和要求（如HTTP、MQTT）。
  - 示例：系统使用HTTPS协议与云服务器通信，支持WebSocket进行实时数据更新，带宽需求不低于10Mbps。

要求：
- 深入分析大纲，提取接口相关信息并扩展为详细描述。
- 使用技术术语，明确协议、格式和性能要求。
- 保持专业语气，内容适合技术文档场景。

项目大纲如下：
{outline}
"""
        return await self._aask(prompt)

# 定义需求文档生成的角色
class ReqDocAgent(Role):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([
            ParseOutline(),
            GenerateIntro(),
            GenerateOverallDesc(),
            GenerateFuncReq(),
            GenerateNonFuncReq(),
            GenerateInterfaces()
        ])

    async def _act(self) -> Message:
        msg = self.rc.memory.get()[-1]
        result = msg.content
        combined_result = ""

        for action in self.actions:
            if isinstance(action, ParseOutline):
                await action.run(result)  # 运行但不保存输出
                continue
            part = await action.run(result)
            combined_result += f"{part.strip()}\n\n"

        return Message(content=combined_result, role=self.profile)

# Streamlit 应用界面
st.title("📝 文档撰写Agent")

uploaded_file = st.file_uploader("上传项目大纲文件（.txt 或 .md）", type=("txt", "md"))
generate_button = st.button("生成需求文档")

if uploaded_file and generate_button:
    content = uploaded_file.read().decode('utf-8')
    if not content.strip():
        st.error("上传的文件内容为空，请上传有效的大纲文件。")
    else:
        try:
            agent = ReqDocAgent()
            result = asyncio.run(agent.run(Message(content=content)))
            st.success("✅ 成功生成需求文档")
            st.download_button(
                label="📥 下载需求文档",
                data=result.content,
                file_name="需求规格说明书.md",
                mime="text/markdown"
            )
            st.markdown("### 📄 生成的需求文档预览")
            st.markdown(result.content)
        except Exception as e:
            logger.error(f"执行失败: {str(e)}")
            st.error(f"执行失败: {str(e)}")