# 博客文章为什么难读，怎样改

调研日期：2026-10-17。

本次回应用户对文章术语太多、普通读者难以理解的反馈。抽查了 8 篇文章的开头、标题及部分正文，对照技术写作指南和相关研究，给出修改建议与示例。本次没有进行真实读者测试，也没有逐篇审计全文。

## 主要判断

问题集中在部分源码解析文章：读者还没弄清楚具体场景，就要记住多个内部对象；解释一个术语时，又出现另外几个术语。有些句子已经写得简短，却把理解所需的前提删掉了。另一些段落在机制尚未讲清时，就插入大量版本、实验和例外说明，打断了阅读。

博客已有的 humanizer 与技术写作规范，已经要求解释陌生术语、交代具体主体和动作。这次需要补充的，是如何实际检查这些要求有没有做到。

建议将普通解释文章的默认读者设为：会写简单代码，但没有读过当前项目源码、不熟悉这个框架的人。开头与主要结论要让非专业读者也能抓住意思。深入源码的章节可以要求更多前置知识，但需要在当地补足理解关键结论所必需的背景。

## 抽查中看到了什么

以下是对片段的编辑判断，不是经过读者实验得到的难度排名。

| 文章 | 抽查中看到的情况 | 修改方向 |
| --- | --- | --- |
| [DeepSeek Harness 开篇](../../content/agent/deepseek-harness-agent-engineering/index.md) | 从取消导出后仍生成文件的故障开始，读者能看到要解决什么 | 保留贯穿案例，后续章节也沿具体操作引出新概念 |
| [Context 与服务](../../content/articles/deepseek-harness-cordis-context-services/index.md) | 缺少文件系统服务的场景明确，但随后一段同时引入服务域、Context、Service、inject | 先讲工具为什么等待、等什么准备好，再解释框架怎样实现 |
| [类型声明与服务注册](../../content/articles/deepseek-harness-types-service-registration/index.md) | 编辑器能补全字段与运行时能取得服务的区别有用；开头叠加 Program、Host/Client、包边界和多层验证说明 | 先用一个能补全却不能调用的最小例子建立区别，再展开发布与验证细节 |
| [effect、Fiber 与 Scope](../../content/articles/deepseek-harness-effect-fiber-scope/index.md) | 第二段已包含 effect、Fiber、disposer、组合 effect、持有关系；后面的定义表又依赖注册表、路由和可见性 | 先讲几项清理工作如何安排，再给管理这些工作的对象命名 |
| [Agent 与销毁责任](../../content/articles/deepseek-harness-agent-handle-ownership/index.md) | get/create 的区别清楚；解释清理责任时，Context、Fiber、effect、owner 与会话来源记录连续出现 | 先沿“插件创建 Agent，随后插件退出”的例子讲清楚，再拆分几种关系 |
| [Preset 与默认模型](../../content/articles/deepseek-harness-presets-persona-model-selection/index.md) | 开头有配置切换的现象，但“能力组合”“状态链”“重放投影”没有先变成读者能观察的动作 | 先说明换配置具体换了什么，再解释模型为什么保持原选择 |
| [抽象的收益与代价](../../content/articles/software-design-01-abstraction/index.md) | 同一份版本数据与两个调用者，让抽象问题有了可追踪的对象；部分限定出现偏早 | 保留运行前后的比较，把不影响当前步骤的实验背景集中说明 |
| [RTC 两端建立连接](../../content/articles/rtc-07-connection-setup/index.md) | 从接听后没有声音开始，再解释地址、端口与路径检查 | 可作为解释顺序的参考；继续检查正式定义是否需要配一个更直观的例子 |

## 外部资料支持什么

1. Google 的技术写作课程要求先判断读者已有的知识，再补上理解目标所需的知识差距。专业程度相近，也不代表读者熟悉同一个项目。[S1]
2. Google 的文风指南区分有用的技术术语与可以用普通话表达的行话；术语是否要解释，取决于目标读者。必要的新术语应说明含义，避免自行制造没有必要的新名称。[S2][S3]
3. Microsoft 建议使用常见、明确的词和动词；同一件事保持同一个名称，删除不增加信息的表达。[S4]
4. GOV.UK 的指南明确允许在通俗说明中保留必要技术词，同时要求在需要时解释。它也提醒不要把比喻用成读者还要解码的另一套行话。[S5]
5. W3C 建议用熟悉的词、在附近解释不熟悉的词，例子和图示可以帮助理解专业表达。[S6]
6. 美国 Digital.gov 的复述测试要求目标读者用自己的话讲出一段内容，再由作者核对理解是否准确。它区分了理解与记忆，强调阅读问题来自文本时应修改文本。[S7]
7. 一项 2025 年的科学解释研究报告，在相关实验中，术语可能提高解释满意度，同时降低可理解性；让参与者自己生成解释，可以改善这种判断偏差。本次核对到摘要，没有核对全文。这不能当作中文编程博客已测得的效果，但支持在修改中增加实际复述检查。[S8]

这些指南大多用英语写成，适合借鉴读者定位、解释顺序和测试方法。英文单词数量、阅读年级与词频阈值不能直接作为中文博客的验收分数。De-Jargonizer 论文的工具以 BBC 网站英文词频为基础，也不适合直接拿来给中文源码文章判分。[S9]

## 用博客原句试着改

以下改写依据原文所描述的行为，用于示范表达。它们没有重新核验当前 dsh 版本的实现，也不是整篇文章的替换稿。

### 例一：把清理责任讲成一个过程

来自 [Agent 与销毁责任](../../content/articles/deepseek-harness-agent-handle-ownership/index.md)的原句：

> 从哪个 Context 调用工厂，生命周期 effect 就登记到哪个 owner。这决定该调用方退出时会收回哪些资源。

建议展开为：

> 假设插件 A 通过自己的 Context 创建了一个 Agent。创建过程中，框架会登记一项清理工作：插件 A 卸载时，关闭这个 Agent。
>
> Context 是调用创建方法的入口。这项清理工作实际记在 A 对应的插件运行实例上，源码把这个实例叫 Fiber。后面判断“谁退出时会触发清理”，就要看这项工作登记在哪里。

这个版本增加了字数，但交代了创建、登记与清理之间的关系。后文讨论业务上的父子关系、会话来源和工厂提供者的清理责任时，再逐项加入；保留原文关于其他清理入口的条件。

### 例二：先说工作怎样执行，再给工作组命名

来自 [effect、Fiber 与 Scope](../../content/articles/deepseek-harness-effect-fiber-scope/index.md)的原句：

> 同一个 effect 内的清理函数按逆序串行等待，Fiber 上多个兄弟 effect 的清理却会并行推进。

建议展开为：

> 清理资源时，需要区分同一组里的工作，以及不同组之间的工作。这里，一组初始化与清理工作由 effect 管理；插件的运行实例 Fiber 会保存这些组。
>
> 同一组内部，后登记的清理先执行，并且要等它结束，才开始下一项。如果插件登记了多个这样的组，各组会并行开始清理；不能据此认为前一组做完后才会开始后一组。

接下来可以用原文已有的执行日志说明先后关系，再解释组合清理、函数身份和失败情况。

### 例三：把抽象描述换成明确对象

这些建议只适用于对应段落，不能作为全站自动替换表。

| 原文中的表达 | 在对应语境中说明什么 |
| --- | --- |
| “Preset 管能力组合” | 这份预设配置决定给 Agent 安装哪些插件，以及由这些插件提供的工具、提示词等功能 |
| “Session 的持久谱系” | 保存这段会话是从哪段会话派生出来的；这份来源记录不决定当前进程由谁执行清理 |
| “服务域标签决定同名能力从哪里取得” | 有多个同名服务时，用标签区分这个插件该使用哪一个 |
| “Context 负责承载和解析这些关系” | 在当前案例中，具体说明插件通过 Context 声明需要哪些服务、怎样取得可用的实现 |

`Context`、`Fiber`、`effect` 等源码名仍要保留，方便查代码。只把它们译成“上下文”“纤程”“副作用”，读者仍可能不知道它们在当前框架里做什么；需要解释实际职责。

### 例四：标题先说读者遇到的问题

可以把《Preset、Persona 与默认模型怎样生效》的标题方向改成《换了工具配置，为什么模型没有跟着换？》。原有源码名可以放在副标题、导语或正文首次解释处。

涉及多个知识点的文章不必都改成问句。标题只要能让读者判断“我能从这里解决什么疑问”，就比单列几个内部对象更有帮助。

## 对这个博客的具体建议

### 写作前

- 说明读者已会什么，尤其不要把“会 TypeScript”直接当成“熟悉 Cordis 的对象与运行方式”。
- 用普通话写出文章要回答的问题，并选择一个可以贯穿解释的小场景。
- 列出理解结论确实需要的概念。与当前问题无关的内部名称，放到后续相关段落。

### 写作时

- 先说明谁在什么情况下，对什么做了什么，以及结果是什么；读者知道对象后，再介绍源码名。
- 第一次解释术语时，说明它在当前场景里做什么。英文全称、中文译名与术语表不能代替这种解释。
- 一句话需要读者同时理解多个新概念时，拆开解释。把清楚的动词写出来，检查“承载、映射、收敛、编排、归属”等词是否隐藏了实际操作。
- 允许为了补充前提而增加篇幅。删掉重复铺垫，保留帮助读者接上因果关系的说明。
- 先走通一个最小过程，再进入异常分支、多个调用方或包发布等扩展问题。会改变当前结论的条件，要留在对应说明附近。
- 开头保留必要的版本范围。完整 commit、机器环境、依赖版本和验证命令集中到来源与复现说明中，相关判断仍链接到对应依据。
- 图中的名称和箭头也说明具体职责与动作。需要查源码时，在次要说明中保留对应标识符。

### 初稿之后

先做一次专门的理解检查，再处理修辞和套话。检查者按目标读者的知识背景，指出第一处跟不上的地方，并回答：

1. 这一节在解决什么具体问题？
2. 谁做了什么，为什么会得到这个结果？
3. 换一个输入或调用方式，结果会怎样？文章给出的条件够不够判断？

作者核对答案时，重点找漏掉的前提、指代不清和例子不足。能复述几个术语，不等于能解释过程。真实目标读者的反馈比作者自行检查更有说服力；模型模拟读者可以帮助发现缺口，但不能作为已经通过读者测试的证据。

自动检查适合找候选问题，例如缩写未解释、同一句堆叠多个新标识符、同一对象换了多个叫法。它不能单凭词频决定一个词必须删除，也不能证明文章已经容易理解。

## 建议先改哪些内容

优先处理 effect/Fiber/Scope、Agent 创建与清理责任、Context 与服务这三篇的开头及首次概念解释。它们所需的新概念多，前置知识又集中出现，适合先选一小节验证改法。

修改时先检查读者能不能解释具体过程，再处理全文。RTC 的场景引入和软件设计文章中的可运行小例子，可以提供站内参考；仍需按具体题目安排，不要把所有文章写成同一套标题。

## 来源

以下页面核对于 2026-10-17。指南提供编辑原则，研究提供特定材料与实验条件下的观察；两者不能替代本站真实读者的反馈。

- [S1：Google，Audience](https://developers.google.com/tech-writing/one/audience)
- [S2：Google，Jargon](https://developers.google.com/style/jargon)
- [S3：Google，Words](https://developers.google.com/tech-writing/one/words)
- [S4：Microsoft，Use simple words, concise sentences](https://learn.microsoft.com/en-us/style-guide/word-choice/use-simple-words-concise-sentences)
- [S5：GOV.UK，Clear language](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/)
- [S6：W3C，Use Clear Words](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o3p01-clear-words/)
- [S7：Digital.gov，Paraphrase testing](https://digital.gov/guides/plain-language/test/paraphrase-testing)
- [S8：Cruz、Lombrozo，When jargon makes the explanation: the layperson paradox of jargon quality，Nature Human Behaviour（2025）；本次依据摘要](https://pubmed.ncbi.nlm.nih.gov/40506550/)
- [S9：Rakedzon 等，Automatic jargon identifier for scientists engaging with the public and science communication educators，PLOS ONE（2017）](https://pubmed.ncbi.nlm.nih.gov/28792938/)

## 本次执行记录

使用 research-explainer 组织问题、核对资料与结论范围；使用项目 humanizer 检查改写示例和报告表达。核对了本地引用片段、相对文件链接与 Markdown 差异。没有开展真实读者测试，研究记录不作为博客已经通过易读性验收的证明。
