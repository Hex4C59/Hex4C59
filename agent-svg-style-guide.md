# Agent SVG Style Guide

这份规范用于统一 `content/agent/` 下所有 SVG 配图的字体、配色、布局和文案风格，让后续新图能够与现有 Agent 系列文章保持一致。

## 1. 目标

Agent 系列配图的目标不是做装饰，而是：

- 解释结构关系
- 帮助读者理解流程与分层
- 和正文形成互补，而不是替代正文

因此图的风格应该是：

- 克制
- 清晰
- 结构化
- 工程感强
- 低装饰噪音

---

## 2. 字体规范

全系列统一使用以下字体栈：

```svg
font-family="Inter, -apple-system, BlinkMacSystemFont, system-ui, Segoe UI, sans-serif"
```

如果是在 `<style>` 里定义类：

```css
font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
```

### 字重建议

- 图标题：`500` 或 `600`
- 卡片标题：`500` 或 `600`
- 正文说明：`400`
- 辅助标签：`400`

### 字号建议

- 整图标题：`14px` 或 `16px`
- 卡片标题：`14px` 或 `16px`
- 卡片正文：`12px` 或 `13px`
- 辅助说明：`12px`

不要在一张图里混入太多字号层级，通常控制在 3 档以内。

---

## 3. 画布规范

推荐使用这些常见尺寸：

- 横向对照图：`viewBox="0 0 680 230"`
- 四宫格框架图：`viewBox="0 0 680 320"`
- 闭环流程图：`viewBox="0 0 680 520"`
- 大型架构图：`viewBox="0 0 760 860"`

根节点建议：

```svg
<svg width="100%" viewBox="0 0 680 320" xmlns="http://www.w3.org/2000/svg">
```

如果图较复杂，建议加上语义信息：

```svg
<svg width="100%" viewBox="0 0 760 860" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">图标题</title>
  <desc id="desc">一句话描述图中表达的关系。</desc>
```

---

## 4. 组件规范

### 卡片

- 优先使用圆角矩形
- 常用圆角：`rx="8"`、`rx="10"`、`rx="12"`
- 边框：`stroke-width="0.5"` 到 `1.2`

### 连线

- 普通主流程线：`1.5` 左右
- 次级连接线：`1` 到 `1.2`
- 反馈/按需注入/回环：虚线

### 箭头

建议统一使用 `marker`：

```svg
<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
  <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</marker>
```

---

## 5. 配色规范

推荐延续当前 Agent 系列的语义配色。

### 中性 / 基础层

- fill: `rgb(241, 239, 232)`
- stroke: `rgb(95, 94, 90)`
- title: `rgb(68, 68, 65)`
- body: `rgb(95, 94, 90)`

适用：

- 输入
- 基础任务对象
- 中性容器
- 总结节点

### 紫色 / 推理与框架

- fill: `rgb(238, 237, 254)`
- stroke: `rgb(83, 74, 183)`
- title: `rgb(60, 52, 137)`
- body: `rgb(83, 74, 183)`

适用：

- 模型推理
- 框架层
- 规划层
- 中心结构

### 绿色 / 合理过程与成功路径

- fill: `rgb(225, 245, 238)`
- stroke: `rgb(15, 110, 86)`
- title: `rgb(8, 80, 65)`
- body: `rgb(15, 110, 86)`

适用：

- 合理流程
- 成功输出
- 正向状态

### 橙色 / 工具调用与中间动作

- fill: `rgb(250, 238, 218)`
- stroke: `rgb(133, 79, 11)`
- title: `rgb(99, 56, 6)`
- body: `rgb(133, 79, 11)`

适用：

- Tool Use
- 中间过程
- 调用层
- 检查点

### 红色 / 风险、错误、恢复

- fill: `rgb(252, 230, 227)` 或 `rgb(250, 236, 231)`
- stroke: `rgb(201, 77, 61)` 或 `rgb(153, 60, 29)`
- title: `rgb(140, 41, 29)` 或 `rgb(113, 43, 19)`
- body: `rgb(201, 77, 61)` 或 `rgb(153, 60, 29)`

适用：

- 错误恢复
- 外部执行
- 风险与波动

### 蓝色 / 检索与知识层

- fill: `#e6f1fb`
- stroke: `#185fa5`
- title: `#0c447c`
- body: `#185fa5`

适用：

- 语义记忆
- 检索系统
- 知识基座

---

## 6. 文案规范

SVG 内文案应保持短句化。

### 推荐

- 每个框 1 个标题 + 1~2 行说明
- 文案尽量是结构词、动作词、功能词
- 让图表达关系，不要在图里塞完整段落

### 不推荐

- 一整段解释性长文本
- 与正文重复的大段定义
- 口语化表达
- 营销化措辞

### 文案风格

延续正文的工程分析风格：

- 明确
- 克制
- 解释机制
- 少形容词，多结构词

示例：

- `模型推理`
- `结构化 JSON 参数输出`
- `结果结构化回传`
- `按需注入工作记忆`
- `任务完成率`

---

## 7. 推荐图型模板

### A. 双栏对照图

适合：

- 自动评测 vs 人工评测
- Chatbot vs Agent
- 短任务 vs 长任务

结构：

- 左右两个主卡片
- 每边 4~5 行短文案
- 画布常用 `680 x 230`

### B. 四宫格框架图

适合：

- 四维评测
- 四类能力
- 四类风险

结构：

- 2x2 卡片
- 每卡 1 个标题 + 2 行说明
- 画布常用 `680 x 320`

### C. 闭环流程图

适合：

- Tool Use Loop
- ReAct
- 观察-决策-执行-反馈

结构：

- 垂直主流程
- 可带一个判断菱形
- 右侧或左侧一条反馈虚线

### D. 分层/架构图

适合：

- 状态管理架构
- 记忆分层
- Planner / Executor / Memory / Tools

结构：

- 顶层入口
- 中间核心层
- 底部外部能力层或存储层

---

## 8. 最小 SVG 模板

下面这个模板适合快速起一张 Agent 系列新图：

```svg
<svg width="100%" viewBox="0 0 680 320" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">图标题</title>
  <desc id="desc">一句话描述这张图表达的结构关系。</desc>

  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <style>
      .label {
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
        text-anchor: middle;
      }
      .title {
        font-size: 16px;
        font-weight: 600;
      }
      .body {
        font-size: 12px;
        font-weight: 400;
      }
      .line {
        stroke: #73726c;
        stroke-width: 1.5;
        fill: none;
        marker-end: url(#arrow);
      }
      .muted {
        fill: #6b6a65;
      }
    </style>
  </defs>

  <rect x="44" y="44" width="272" height="100" rx="8" fill="rgb(238, 237, 254)" stroke="rgb(83, 74, 183)" stroke-width="0.5"/>
  <text class="label title" x="180" y="82" fill="rgb(60, 52, 137)">模块标题</text>
  <text class="label body" x="180" y="106" fill="rgb(83, 74, 183)">第一行说明</text>
  <text class="label body" x="180" y="124" fill="rgb(83, 74, 183)">第二行说明</text>
</svg>
```

---

## 9. 自查清单

每次新增 SVG 前，先检查：

- 是否使用统一字体栈 `Inter`
- 是否只有 3 档以内字号
- 是否颜色有明确语义
- 是否每个框文案足够短
- 是否留白充足
- 是否图的目标是解释结构，而不是装饰
- 是否图注放在正文里，而不是全部塞进 SVG

---

## 10. 当前约定

当前仓库内 `content/agent/` 下的 SVG 已统一到这套字体规范。后续新图建议继续沿用本文件中的规则，避免同一系列文章出现视觉风格漂移。
