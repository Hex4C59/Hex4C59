+++
title = "构建多智能体系统：何时使用、如何使用"
date = 2026-03-25T12:00:00+08:00
lastmod = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "Anthropic 梳理多智能体架构的适用场景：上下文隔离、并行探索与工具/提示/领域专业化，并说明如何按上下文边界分解任务、采用验证子智能体模式，以及常见实现误区。"
summary = "从单智能体起步；在上下文污染、可并行子任务、需要专业化工具或提示时再引入多智能体；分解工作时应以「上下文」而非「工种」为界。"
tags = []
categories = ["Translations"]
topics = ["multi-agent", "agents", "claude", "orchestration", "context-engineering"]
translation_category = "AI 与工具"
original_title = "Building multi-agent systems: When and how to use them"
original_url = "https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them"
original_author = "Cara Phillips"
original_date = "2026-01-23"
original_site = "Claude Blog"
ShowToc = true
+++

> **译文信息**  
> - 原文：[Building multi-agent systems: When and how to use them](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)  
> - 作者：Cara Phillips（Paul Chen、Andy Schumeister、Brad Abrams、Theo Chu 亦有贡献）  
> - 原文发布：2026-01-23  
> - 翻译发布：2026-03-25（东八区）

虽然单智能体系统已能很好地覆盖多数企业工作流，多智能体架构仍可能为组织带来额外价值。本文讨论**何时、如何**采用它们。

多智能体系统（multi-agent system）指在代码协调下运行多个 LLM 实例、彼此拥有独立对话上下文的架构。协调方式有多种（智能体集群、基于能力的系统、消息总线等），本文聚焦 **orchestrator–subagent（编排器–子智能体）** 模式：由主导智能体为具体子任务派生并管理专职子智能体的层级结构。该模式协调关系清晰，适合刚接触多智能体的团队作为起点；其他模式将在后续文章中详述。

如今，多智能体常被用于「单智能体会更吃力」的场景，但随着模型能力提升，这一权衡也在变化。在 Anthropic，我们见过团队投入数月搭建复杂多智能体架构，最后却发现：**只要把单智能体的提示打磨好，效果相当**。

在搭建多智能体并与落地团队共事之后，我们总结出三类**多智能体稳定优于单智能体**的情形：**上下文被污染导致性能下降**、**任务可以并行**、**专业化能改善工具选择或任务聚焦**。除此之外，协调成本往往大于收益。

下文说明如何识别单智能体的边界、判断上述三类高回报场景，并避开常见实现陷阱。

## 为何应从单智能体开始

设计得当的单智能体，配上合适工具，能完成的工作往往超出许多开发者预期。

多智能体会带来开销。每多一个智能体，就多一个潜在故障点、多一套要维护的提示，也多一种意外行为来源。

我们见过团队搭建精细的多智能体系统：规划、执行、评审、迭代各由不同智能体负责，结果却在每次交接时丢失上下文，**协调所耗 token 甚至超过实际执行**。在测试中，对同等任务，多智能体实现通常比单智能体多消耗 **3～10 倍 token**。原因包括：上下文在多个智能体间重复、智能体之间要发协调消息、交接时还要对结果做摘要。

## 多智能体决策框架

多智能体架构应在**单智能体无法解决的明确约束**上创造价值，即：收益要配得上额外成本。下面几类是我们反复看到**投入能换来正回报**的情形。

### 上下文保护（Context protection）

大语言模型的上下文窗口有限，上下文变长后，回答质量可能下滑。当一个智能体的上下文里堆满了与后续子任务**无关**的信息，就会发生 **context pollution（上下文污染）**。子智能体彼此隔离，各自在干净、聚焦单一任务的上下文中工作。

例如客服智能体既要查订单历史，又要排查技术问题。若每次查单都把数千 token 的订单详情写进上下文，智能体推理技术问题的能力就会被拖累。

**单智能体做法：**

```python
# 单智能体把所有内容都堆进上下文
conversation_history = [
    {"role": "user", "content": "My order #12345 isn't working"},
    {"role": "assistant", "content": "Let me check your order..."},
    # 工具返回结果里塞了 2000+ token 的订单历史
    {"role": "user", "content": "... (order details, past purchases, shipping info) ..."},
    {"role": "assistant", "content": "Now let me diagnose the technical issue..."},
    # 上下文里现在充斥着与当前技术问题无关的订单细节
]
```

智能体必须在脑中同时扛着 2000+ token 的无关订单信息来推理技术问题，注意力被稀释，回答质量下降。

**多智能体做法：**

```python
from anthropic import Anthropic

client = Anthropic()

class OrderLookupAgent:
    def lookup_order(self, order_id: str) -> dict:
        # 独立智能体，自有上下文
        messages = [
            {"role": "user", "content": f"Get essential details for order {order_id}"}
        ]
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=messages,
            tools=[get_order_details_tool]
        )
        # 只返回必要信息
        return extract_summary(response)

class SupportAgent:
    def handle_issue(self, user_message: str):
        if needs_order_info(user_message):
            order_id = extract_order_id(user_message)
            # 只取需要的信息，而不是整段历史
            order_summary = OrderLookupAgent().lookup_order(order_id)
            # 注入紧凑摘要，而不是完整上下文
            context = f"Order {order_id}: {order_summary['status']}, purchased {order_summary['date']}"
        
        # 主智能体上下文保持干净
        messages = [
            {"role": "user", "content": f"{context}\n\nUser issue: {user_message}"}
        ]
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            messages=messages
        )
        return response
```

订单查询智能体处理完整订单历史并抽取摘要；主智能体只收到真正需要的约 50～100 token，上下文保持聚焦。

当子任务会产生**大量上下文**（例如超过 1000 token）、但其中大部分对主任务**无关紧要**，且子任务边界清晰、抽取标准明确，或属于需要先过滤再使用的查找/检索类操作时，**上下文隔离**最有效。

### 并行化（Parallelization）

多个智能体并行运行，可以探索比单个智能体更大的搜索空间，在**搜索与研究类任务**上尤其有用。

我们的 **Research** 功能采用这一思路：主导智能体分析查询，并派生多个子智能体**并行**调查不同侧面。每个子智能体独立搜索，再交回提炼后的结论。与单智能体相比，多智能体搜索允许在更大信息空间上探索，我们观察到**准确率有显著提升**。

核心实现是：把问题拆成彼此独立的研究维度，并发运行子智能体，再由主导智能体汇总。

```python
import asyncio
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

async def research_topic(query: str) -> dict:
    # 主导智能体将查询拆成研究维度
    facets = await lead_agent.decompose_query(query)
    
    # 为每个维度派生子智能体并行研究
    tasks = [
        research_subagent(facet) 
        for facet in facets
    ]
    results = await asyncio.gather(*tasks)
    
    # 主导智能体汇总结论
    return await lead_agent.synthesize(results)

async def research_subagent(facet: str) -> dict:
    """Each subagent has its own context window"""
    messages = [
        {"role": "user", "content": f"Research: {facet}"}
    ]
    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        messages=messages,
        tools=[web_search, read_document]
    )
    return extract_findings(response)
```

这种覆盖面的提升是有代价的。多智能体相对单智能体，对同等任务通常仍多耗 **3～10 倍 token**（每个智能体自有上下文、需要协调消息、交接要摘要）。并行能缩短**墙钟时间**，但总计算量更大，因此**整体耗时往往仍长于单智能体**。

并行化的主要收益是**更全面**，而不是更快。当你需要在庞大信息空间上搜索，或从多个角度审视复杂问题时，并行智能体比受上下文限制的单个智能体能覆盖更多地面。代价是更高的 token 消耗，以及通常更长的总执行时间，换取更完整的结果。

### 专业化（Specialization）

不同任务有时需要不同的工具集、system prompt 或专业领域。与其让一个智能体挂几十个工具，不如让**职责匹配、工具集聚焦**的专职智能体来干，可靠性往往更好。

#### 工具集专业化

工具过多会拖累表现。若出现下面三类信号，可考虑做工具专业化：

1. **数量**：工具太多（常见阈值约 **20+**）时，智能体难以稳定选对工具。  
2. **领域混杂**：工具横跨多个不相关领域（数据库、API、文件系统等）时，智能体容易搞混该用哪一类。  
3. **性能回退**：新增工具后，原有任务变差，说明智能体在「管理工具」上已接近上限。

#### System prompt 专业化

不同任务可能需要不同人设、约束或指令，合在一起会**互相打架**。客服要共情、耐心；代码评审要精确、挑剔；合规检查要死守规则；头脑风暴要灵活发散。若同一智能体要在这些**冲突的行为模式**间切换，拆成多个带定制 system prompt 的专职智能体，结果通常更一致。

#### 领域 expertise 专业化

有些任务需要很深的领域上下文，全塞进一个通才智能体会把上下文撑爆。例如法律分析可能需要大量判例与监管框架；医学研究可能需要临床试验方法论的专门知识。与其全部加载进一个智能体，不如让各子智能体只携带与其职责相关的聚焦知识。

**示例：多平台集成。** 某集成系统要同时对接 CRM、营销自动化与消息平台，每个平台各有约 10～15 个相关 API。单个智能体挂 **40+** 工具时，经常在相似操作间选错。拆成工具集与提示都聚焦的专职智能体，能显著减少选型错误。

```python
from anthropic import Anthropic

client = Anthropic()

# 工具集聚焦、提示定制的专职智能体
class CRMAgent:
    """Handles customer relationship management operations"""
    system_prompt = """You are a CRM specialist. You manage contacts, 
    opportunities, and account records. Always verify record ownership 
    before updates and maintain data integrity across related records."""
    tools = [
        crm_get_contacts,
        crm_create_opportunity,
        # 8-10 CRM-specific tools
    ]

class MarketingAgent:
    """Handles marketing automation operations"""
    system_prompt = """You are a marketing automation specialist. You 
    manage campaigns, lead scoring, and email sequences. Prioritize 
    data hygiene and respect contact preferences."""
    tools = [
        marketing_get_campaigns,
        marketing_create_lead,
        # 8-10 marketing-specific tools
    ]

class OrchestratorAgent:
    """Routes requests to specialized agents"""
    def execute(self, user_request: str):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system="""You coordinate platform integrations. Route requests to the appropriate specialist:
- CRM: Contact records, opportunities, accounts, sales pipeline
- Marketing: Campaigns, lead nurturing, email sequences, scoring
- Messaging: Notifications, alerts, team communication""",
            messages=[
                {"role": "user", "content": user_request}
            ],
            tools=[delegate_to_crm, delegate_to_marketing, delegate_to_messaging]
        )
        return response
```

这类似于现实里**专业分工**：各角色工具与职责匹配时，协作效率高于一人硬扛所有领域。但专业化会带来**路由复杂度**：编排器必须正确分类请求并委派；误派会得到很差的结果；维护多套提示也是负担。最适合的是**领域边界清晰、路由歧义少**的场景。

## 何时说明单智能体架构「不够用了」

在上述框架之外，还有一些**具体信号**表明该考虑超越单智能体：

**逼近上下文上限。** 若智能体频繁占用大量上下文且性能明显下滑，瓶颈可能在上下文压力。注意：近期上下文管理上的进展（例如 **compaction**）正在缓解这一限制，使单智能体能在更长跨度上保持有效记忆。

**工具数量很多。** 当智能体有 **15～20+** 工具时，模型会花大量上下文与注意力理解选项。在引入多智能体之前，可先考虑 **Tool Search Tool**：让 Claude **按需发现工具**，而不是一次性加载全部定义；据称最高可减少约 **85%** 的 token，并改善工具选择准确率。

**可并行的子任务。** 当任务自然拆成彼此独立的块（多源研究、多组件测试等）时，并行子智能体能带来实质性收益。

这些阈值会随模型能力演进；当前数字是**经验指引**，不是铁律。

## 以上下文为中心的分解方式

采用多智能体时，**如何在智能体之间切分工作**是最关键的设计决策之一。我们常见团队切错，导致协调开销抵消多智能体的好处。

要点是：分解时采用**上下文中心**视角，而不是**问题类型中心**视角。

**按问题类型分解（往往适得其反）。** 按工作种类切分（一个写功能、一个写测试、一个做评审）会带来持续协调成本。每次交接都丢上下文：写测试的智能体不知道某些实现决策为何如此；评审智能体缺少探索与迭代过程里的上下文。

**按上下文边界分解（通常更有效）。** 按「上下文能否真正隔离」来切分：负责某一功能的智能体**应同时负责该功能的测试**，因为它已经具备所需上下文。只有在上下文可以**真正隔离**时才拆分。

这一原则来自多智能体常见失败模式：按软件角色（规划、实现、测试、评审）拆智能体时，会像**传话游戏**一样来回传递信息，每传一手保真度就下降；在实验中，子智能体花在协调上的 token 甚至超过实际工作。

**较合理的分解边界包括：**

- **彼此独立的研究路径。** 例如「亚洲市场趋势」与「欧洲市场趋势」可并行，几乎不需共享上下文。  
- **接口清晰的不同组件。** API 契约明确时，前端与后端可并行。  
- **黑盒验证。** 验证者只需跑测试并汇报结果时，不需要实现过程的完整上下文。

**应避免的分解边界包括：**

- **同一工作的顺序阶段。** 同一功能的规划、实现、测试共享过多上下文。  
- **强耦合组件。** 需要频繁来回沟通的组件应放在同一智能体内。  
- **需要频繁对齐共享状态的工作。** 若两个智能体需要不断同步对状态的理解，应合并。

## 验证子智能体模式（Verification subagent）

跨领域都比较好用的一种模式是 **verification subagent（验证子智能体）**：专职负责测试或校验主导智能体产出。

也要说明：更强的编排模型（例如 **Claude Opus 4.5**）越来越能在**不单独设验证步骤**的情况下直接评估子智能体工作。但在编排模型能力较弱、验证需要**专用工具**，或你希望在工作流里**强制设置显式验证关卡**时，验证子智能体仍然有价值。

验证子智能体能避开传话问题：验证本身只需要**很少的上下文传递**——验证者可以黑盒测试系统，而不必了解「当初为何那样实现」。

### 实现方式

主导智能体完成一个工作单元后，在继续之前派生验证子智能体，传入待验证产物、明确的成功标准，以及执行验证所需的工具。

验证者不需要理解产物为何被做成那样，只需判断**是否满足既定标准**。

```python
from anthropic import Anthropic

client = Anthropic()

class CodingAgent:
    def implement_feature(self, requirements: str) -> dict:
        """Main agent implements the feature"""
        messages = [
            {"role": "user", "content": f"Implement: {requirements}"}
        ]
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=messages,
            tools=[read_file, write_file, list_directory]
        )
        return {
            "code": response.content,
            "files_changed": extract_files(response)
        }

class VerificationAgent:
    def verify_implementation(self, requirements: str, files_changed: list) -> dict:
        """Separate agent verifies the work"""
        messages = [
            {"role": "user", "content": f"""
Requirements: {requirements}
Files changed: {files_changed}

Run the test suite and verify:
1. All existing tests pass
2. New functionality works as specified
3. No obvious errors or security issues

You MUST run the complete test suite before marking as passed.
Do not mark as passing after only running a few tests.
Run: pytest --verbose
Only mark as PASSED if ALL tests pass with no failures.
"""}
        ]
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=messages,
            tools=[run_tests, execute_code, read_file]
        )
        return {
            "passed": extract_pass_fail(response),
            "issues": extract_issues(response)
        }

def implement_with_verification(requirements: str, max_attempts: int = 3):
    for attempt in range(max_attempts):
        result = CodingAgent().implement_feature(requirements)
        verification = VerificationAgent().verify_implementation(
            requirements,
            result['files_changed']
        )
        
        if verification['passed']:
            return result
        
        requirements += f"\n\nPrevious attempt failed: {verification['issues']}"
    
    raise Exception(f"Failed verification after {max_attempts} attempts")
```

### 适用场景

验证子智能体适合：

- **质量保证：** 跑测试套件、lint、按 schema 校验输出。  
- **合规检查：** 核对文档是否符合政策、输出是否符合规则。  
- **交付前输出校验：** 确认生成内容满足规格。  
- **事实核查：** 由单独智能体验证主张或引用是否成立。

### 「过早宣布胜利」问题

验证子智能体最大的失败模式是：**没测透就标通过**。验证者跑了一两个测试看见绿了，就宣告成功。

缓解思路：

- **标准要具体：** 写「跑**完整**测试套件并汇报所有失败」，而不是笼统的「确保能用」。  
- **检查要全面：** 要求覆盖多种场景与边界情况。  
- **负例测试：** 要求尝试**应当失败**的输入，并确认确实失败。  
- **指令要明确：** 「你必须在标为通过之前**跑完整个测试套件**」这类句子很关键；若不强制全面验证，验证智能体容易走捷径。

## 如何继续推进

多智能体很强，但并非放之四海而皆准。在引入多智能体协调的复杂度之前，请确认：

1. **确实存在**多智能体能解决的约束：上下文限制、并行机会，或专业化需求。  
2. **分解遵循上下文，而不是工种：** 按「需要什么上下文」分组，而不是按「干什么活」分组。  
3. **存在清晰的验证点**，子智能体能在**不必掌握完整实现上下文**的情况下完成校验。

我们的建议？**从最简单可行的方案开始**，只有有证据表明需要时，再增加复杂度。

*本文为多智能体系列第一篇。关于单智能体模式，见 [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)；关于上下文管理策略，见 [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；关于我们如何搭建多智能体研究系统，见 [How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system)。*

## 致谢

本文由 Cara Phillips 撰写，Paul Chen、Andy Schumeister、Brad Abrams、Theo Chu 亦有贡献。
