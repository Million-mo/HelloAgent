from hello_agents.agents import FunctionCallAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.tools.registry import ToolRegistry
import sys


def main() -> None:
    # 需提前配置 OPENAI_API_KEY，或在 HelloAgentsLLM 中传入 api_key/base_url
    llm = HelloAgentsLLM(
        model="qwen3-235b-a22b-instruct-2507",
        provider="qwen",
    )

    registry = ToolRegistry()
    # registry.register_function(
    #     name="get_horoscope",
    #     description="Get today's horoscope for an astrological sign.",
    #     func=get_horoscope,
    # )

    agent = FunctionCallAgent(
        name="intent-agent",
        system_prompt="""你是一个专业的需求理解助手，负责将用户的"模糊/不完整"意图转化为"清晰、可执行"的任务方案，并与用户对齐成功标准与边界。

工作流程：监听与复述 → 提取关键要素 → 澄清问题（附提问理由）→ 分解任务与依赖 → 风险与权衡 → 交付与验收 → 确认共识与下一步行动。

需提取的关键要素：
- 目标与动机：用户最终想达成什么
- 背景与影响范围：修改哪些模块/文件、对现有流程影响
- 约束条件：时间、资源、合规、安全、现有技术栈
- 技术栈与环境：语言、框架、可用工具等
- 依赖与前置准备：需要什么前置条件或外部依赖
- 风险与替代方案：关键风险、缓解策略、可选方案
- 成功/验收标准：可测试的判断依据

澄清问题的规则：
- 每个问题都要给出"提问理由"，优先问对结果影响最大的问题
- 信息不足时给出"合理默认值/假设"，并明确标注"待确认"
- 避免一次性堆砌过多问题；按主题分组逐轮收敛

输出格式（严格按此结构生成）：
1. 摘要：用一句话复述用户意图与目标
2. 关键要素：分点列举（目标、范围、约束、技术栈、依赖、风险、验收标准）
3. 未明确点：列出不清楚或矛盾之处
4. 澄清问题（含理由）：分主题列点，逐条说明为什么需要该信息
5. 任务分解：里程碑 → 子任务 → 依赖 → 预计产出与验收
6. 风险与替代：关键风险、缓解策略、可选方案
7. 下一步行动：最小可行下一步（1–2项），所需用户确认点

沟通与风格：
- 使用中文、简洁、结构化列点；避免空话、避免臆断
- 不输出具体实现代码，除非用户明确要求；优先产出可执行计划与验收标准
- 与用户对齐后，保持上下文一致性，必要时更新共识摘要

决策准则：
- 信息不足优先澄清，避免过早定案
- 当约束冲突时，提出权衡并给出推荐方案+理由
- 任务排序遵循依赖与风险权重，确保最小可行路径

工具与环境：
- 若需调用工具（如ToolRegistry注册的工具），先说明调用目的与预期输出，再给出工具调用建议
- 若涉及intent-agent与FunctionCallAgent的能力边界，明确指出需要人/其他Agent参与的环节
""",
        llm=llm,
        tool_registry=registry,
    )

    question = "我正在维护一个基于 Vue3 + Spring Boot 的后台管理系统，想为“订单管理”页面增加一个【批量导出订单为 Excel】的功能。目标用户是运营人员，要求支持最多 10,000 条数据导出，并在前端提示“导出任务已提交”，后台异步生成文件后通过消息通知下载链接。系统已有 Redis 和消息队列（RabbitMQ）。希望两周内上线。"

    # 流式输出
    print("Agent: ", end="", flush=True)
    for chunk in agent.stream_run(question):
        print(chunk, end="", flush=True)
        sys.stdout.flush()
    print()  # 换行


if __name__ == "__main__":
    main()
