+++
title = "读懂 Attention Is All You Need：从一次加权求和到完整 Transformer"
date = 2026-10-15T12:00:00+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "用四张可播放、可逐步查看的动态图，解释 Q、K、V、缩放点积注意力、多头、位置编码、因果掩码，以及原版 Transformer 的编码器、解码器与训练过程。"
summary = "从一组可以手算的注意力开始，逐步搭起 2017 年原版 Transformer。四张动态图对应注意力演算、多头合并、训练与生成、完整编码器和解码器，并解释维度、复杂度、实验结果与常见误读。"
ShowToc = true
math = true
tags = ["Transformer", "注意力机制", "论文解读"]
categories = ["ai"]
source_kind = "original"
article_type = "concept"
+++

Transformer 的一次注意力计算可以先记成一句话：**当前位置用一个查询向其他位置打分，把分数变成权重，再按这些权重取回信息。** 对整句话的所有位置一起做，每个位置就能得到混入其他位置信息的新向量，而且这一层的各个位置可以并行计算。

困难在于，这句话还没有回答几个关键问题：查询从哪里来？为什么要分成 Q、K、V？算出来的权重究竟乘到什么上？既然可以并行，翻译时为什么仍然逐词生成？

本文沿着这些问题，拆解 Vaswani 等人在 2017 年发表的《Attention Is All You Need》。阅读会用到向量、矩阵乘法，以及模型根据预测误差调整参数的基本概念。可以先把向量理解为按顺序排好的一组数，把矩阵理解为按行列排好的多组数；不熟悉公式时，先沿“猫、坐、垫”的数值例子跟踪每一步，再回看矩阵写法。文章先把一次注意力算清楚，再搭出完整的编码器与解码器，最后回到论文的实验和适用边界。这里讨论的是会议版中的原始 Transformer，模型结构和数字均可对照[原论文](https://papers.nips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf)。〔[1](#ref-transformer)〕

四张图都支持播放、暂停和逐步查看。第一次可以直接播放，遇到公式时暂停；关闭 JavaScript 或开启系统的“减少动态效果”后，会显示完整静态图。图中的小向量与数值是人为构造的教学示例，用来检验计算，不代表训练后的词义关系。

## 论文要去掉的，是序列里的循环依赖

机器翻译需要把一串源语言 token 变成另一串目标语言 token。token 是模型处理序列的基本单位，可能是词，也可能是子词；下文为了方便，会用一个汉字或一个词代表一个 token。

在循环神经网络（Recurrent Neural Network，RNN）中，位置 $t$ 的隐藏状态通常依赖位置 $t-1$：

<div class="math-display">
$$
h_t = f(h_{t-1}, x_t).
$$
</div>

这里的隐藏状态，是网络在当前位置保存、供后续位置继续使用的数值向量。这条依赖意味着，同一层里必须先得到 $h_{t-1}$，才能计算 $h_t$。两个距离较远的词之间，信息也需要经过多个序列位置传递。即使计算设备可以同时做很多乘法，隐藏状态的先后关系仍然存在。原论文用“串行操作数”和“最大路径长度”来讨论这一限制。〔[1，§1、§4](#ref-transformer)〕

注意力在 Transformer 之前已经用于翻译。Bahdanau 等人的工作允许解码器在每个输出位置，对源句的不同表示分配不同权重；它保留了循环结构，同时改善了把源句信息交给解码器的方式。〔[2](#ref-bahdanau)〕

Transformer 进一步把注意力用于构建序列表示本身。同一层内，每个位置都能直接读取允许访问的其他位置，而不必等待另一个位置刚算出的隐藏状态。计算上一层到下一层仍然有依赖，但一层内部的各个位置可以组织成矩阵运算。〔[1，§3、§4](#ref-transformer)〕

标题中的 “All You Need” 要放在这个问题里理解：论文用注意力搭建序列转换网络，去掉了循环和卷积。完整模型还需要前馈网络、位置编码、残差连接和归一化。这些部件会在后面逐个装回来。

## 先看一个位置如何读取整句话

假设输入只有三个 token：

```text
猫    坐    垫
```

我们希望为“坐”生成一个包含上下文的新表示。一个直接的办法是把三个位置的向量平均。但平均会让每个位置得到相同的混合比例，无法表达“这个位置现在更需要哪部分信息”。

注意力为每个查询位置单独计算一组权重。对“坐”计算时，模型可以给“猫”“坐”“垫”分配不同的比例；对“猫”计算时，又可以得到另一组比例。输入是同一句话，读取方式由当前位置决定。

### Q、K、V 是三种计算角色

设一层的输入为 $X \in \mathbb{R}^{n\times d_{\text{model}}}$。$n$ 是 token 数量，$d_{\text{model}}$ 是每个 token 的表示宽度。矩阵的每一行对应一个位置。

先只看一套打分和读取计算，称为一个注意力头。它把每个位置的输入向量分别乘以三组可学习的矩阵，将原来的各个分量重新组合成三种表示。这个操作叫线性投影：

<div class="math-display">
$$
Q = XW^Q,\qquad K = XW^K,\qquad V = XW^V.
$$
</div>

其中，$W^Q$、$W^K$ 的形状为 $d_{\text{model}}\times d_k$，$W^V$ 为 $d_{\text{model}}\times d_v$。于是 $Q$ 和 $K$ 的每行有 $d_k$ 个分量，$V$ 的每行有 $d_v$ 个分量。投影参数跟随模型一起训练。〔[1，§3.2](#ref-transformer)〕

三个名字可以按它们参与的运算记忆：

| 对象 | 参与什么计算 | 在这一步的作用 |
| --- | --- | --- |
| Query，查询 $q_i$ | 与各个 $k_j$ 做点积 | 让位置 $i$ 发起一次有条件的读取 |
| Key，键 $k_j$ | 接受查询打分 | 决定位置 $j$ 与当前查询有多匹配 |
| Value，值 $v_j$ | 被注意力权重加权求和 | 提供最后实际汇入输出的内容 |

“查询”“键”“值”可以借用检索的直觉，但这里得到的是连续的数值向量。计算并不要求某个键完全匹配，也通常不会只取出一个值。

把 Key 和 Value 分开，允许模型分别学习两件事：用什么特征判断相关性，以及被选中时传递什么内容。三个向量可以来自同一个 token，却使用不同的投影矩阵。它们也没有被预先规定成“主语向量”“动词向量”之类的语法标签。

### 六步算完一行注意力

只看“坐”的查询。为了方便手算，设：

<div class="math-display">
$$
q_{\text{坐}}=[1,0],\qquad
K=\begin{bmatrix}1&amp;0\\0&amp;1\\1&amp;1\end{bmatrix},\qquad
V=\begin{bmatrix}2&amp;0\\0&amp;2\\2&amp;2\end{bmatrix}.
$$
</div>

$K$、$V$ 的三行依次对应“猫”“坐”“垫”，并且 $d_k=d_v=2$。先不要给这些坐标附加词义，它们只是一组可以检查运算的数。

{{< interactive-diagram src="attention-calculation.html" title="注意力数值演算：观察查询如何经过打分、缩放、softmax 和值向量加权，得到一个新的表示" height="900" compact-height="1480" mobile-height="1560" >}}

第一步，用查询与每个键做点积，也就是对应分量相乘后相加，得到每个位置的匹配分数：

<div class="math-display">
$$
q_{\text{坐}}K^\top=[1,0,1].
$$
</div>

第二步，将分数除以 $\sqrt{d_k}=\sqrt{2}$：

<div class="math-display">
$$
s=\frac{[1,0,1]}{\sqrt{2}}
\approx[0.7071,0,0.7071].
$$
</div>

第三步，对这一行做 softmax。对任意分数向量 $s$，它的第 $j$ 个输出是：

<div class="math-display">
$$
\operatorname{softmax}(s)_j=\frac{e^{s_j}}{\sum_\ell e^{s_\ell}}.
$$
</div>

softmax 把分数变成非负、总和为 1 的权重。代入上面的数字：

<div class="math-display">
$$
a_{\text{坐}}\approx[0.4011,0.1978,0.4011].
$$
</div>

第四步，把权重乘到对应的 Value 上，再求和：

<div class="math-display">
$$
\begin{aligned}
z_{\text{坐}}
&amp;=0.4011[2,0]+0.1978[0,2]+0.4011[2,2]\\
&amp;\approx[1.6044,1.1978].
\end{aligned}
$$
</div>

输出的两个坐标由三个 Value 混合得到。“坐”保留了自己的部分信息，也读入了另外两个位置的信息。若更换查询，点积、权重和最终输出都可能改变。

权重归一化发生在每个查询自己的那一行。因此，“位置 $i$ 很关注位置 $j$”不意味着“位置 $j$ 也同样关注位置 $i$”。两个方向的查询不同，Q 与 K 的投影参数也不同。

按上面这个公式计算的加权和，是 Value 向量的凸组合：权重非负且和为 1。后面的多头拼接、输出投影与残差相加会继续变换它，完整子层的输出没有这个约束。

## 把所有位置合并，就是那条核心公式

对每个查询重复刚才的过程，可以写成一次矩阵计算：

<div class="math-display">
$$
\operatorname{Attention}(Q,K,V)
=
\operatorname{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)V.
$$
</div>

这是原论文的缩放点积注意力（Scaled Dot-Product Attention）。〔[1，§3.2.1](#ref-transformer)〕

把自注意力的形状沿着公式走一遍，就能看清每步在做什么：

| 计算结果 | 形状 | 含义 |
| --- | --- | --- |
| $Q$、$K$ | $n\times d_k$ | 每个位置的查询和键 |
| $QK^\top$ | $n\times n$ | 每个查询对每个键的分数 |
| $A=\operatorname{softmax}(QK^\top/\sqrt{d_k})$ | $n\times n$ | 每一行是一组读取权重 |
| $Z=AV$ | $n\times d_v$ | 每个位置读回的内容 |

$K^\top$ 是 K 的转置。第 $i$ 行与第 $j$ 列相乘，得到 $q_i\cdot k_j$。所以分数矩阵的行表示“谁在查”，列表示“查谁”；softmax 沿着列方向，对每一行单独归一化。

“所有位置可以并行”也可以从这个式子直接读出来：$Q$、$K$、$V$ 都来自这一层已经拿到的输入。计算 $z_i$ 时不需要先求出同层的 $z_{i-1}$。

### 为什么要按键的维度缩放？

若为了分析，假设 $q$、$k$ 的各分量相互独立，均值为 0、方差为 1，那么点积

<div class="math-display">
$$
q\cdot k=\sum_{r=1}^{d_k}q_rk_r
$$
</div>

的方差会随 $d_k$ 增长到 $d_k$，典型幅度约为 $\sqrt{d_k}$。除以 $\sqrt{d_k}$ 后，分数的尺度就不再仅仅因为维度增大而不断变大。这是论文给出的缩放理由。〔[1，§3.2.1、脚注 4](#ref-transformer)〕

它与 softmax 有直接关系。比如 $[1,2,3]$ 的 softmax 约为 $[0.090,0.245,0.665]$；把同样的分数放大十倍，$[10,20,30]$ 的最后一项权重会接近 1。分布过于尖锐时，小幅改变许多输入分数，权重也几乎不变；这种变化关系在训练中表现为较小的局部梯度，使参数更难通过误差信号得到调整。

这个推导依赖前面明确写出的统计假设。训练后的 Q、K 不必始终满足它；缩放也不保证注意力均匀。它控制的是分数尺度，模型仍然可以学出很集中的权重。

## 多头注意力让一次读取有多组投影

单个头为每个查询生成一组权重，然后把多个位置的 Value 压成一个向量。这样得到的读取方式只有一套。

多头注意力（Multi-Head Attention）使用多组独立投影。每个头都拿到输入，但使用自己的 $W_i^Q$、$W_i^K$、$W_i^V$：

<div class="math-display">
$$
\begin{aligned}
\operatorname{head}_i
&amp;=\operatorname{Attention}(XW_i^Q,XW_i^K,XW_i^V),\\
\operatorname{MultiHead}(X)
&amp;=\operatorname{Concat}(\operatorname{head}_1,\ldots,\operatorname{head}_h)W^O.
\end{aligned}
$$
</div>

各头先独立得到输出，再沿特征维拼接，最后用 $W^O$ 混合各头的信息。原论文 base 模型取 $d_{\text{model}}=512$、$h=8$、$d_k=d_v=64$，所以拼接后的宽度为 $8\times64=512$。〔[1，§3.2.2](#ref-transformer)〕

{{< interactive-diagram src="multi-head.html" title="多头注意力：沿着维度变化，观察八组独立投影如何计算、拼接并通过输出矩阵混合" height="1120" compact-height="1320" mobile-height="1360" >}}

可以把它理解成：模型有多组机会，用不同的特征组织一次上下文读取。某个头可能更关注局部搭配，另一个可能关联较远的位置；这些是可能学习到的行为，不能把头的编号当作固定职责。

从公式看，多头也不等于把一个已经算完的 512 维输出简单切成八段。各头在 softmax 之前就拥有不同的 Q 和 K，因此可以得到不同的注意力矩阵。另一方面，原论文把各头的内部维度相应缩小；八个头并非八套完整的 512 维注意力。〔[1，§3.2.2](#ref-transformer)〕

## 没有循环，模型怎样知道词序？

假设没有任何位置信息，只把 token 向量送入不带掩码的自注意力。将输入各行重新排列，输出也会按同样方式重排。

用排列矩阵 $P$ 表示这个操作。因为线性投影逐行使用同一组参数，重排后有 $Q'=PQ$、$K'=PK$、$V'=PV$，从而：

<div class="math-display">
$$
Q'K'^\top=P(QK^\top)P^\top.
$$
</div>

行 softmax 与这种行列重排相容，所以注意力输出满足：

<div class="math-display">
$$
\operatorname{Attention}(PQ,PK,PV)
=P\operatorname{Attention}(Q,K,V).
$$
</div>

这意味着，仅靠这些内容向量，运算没有引入“它原来处在第几个位置”的信息。我们必须把位置告诉模型，才能区分“猫追狗”和“狗追猫”中同一个词的不同排列。

原论文在编码器、解码器底部，把 token embedding 与位置编码（Positional Encoding，PE）相加：

<div class="math-display">
$$
X_{\text{input}}=\sqrt{d_{\text{model}}}\,E+PE.
$$
</div>

$E$ 是按 token ID 查表得到的 embedding（嵌入向量）：每个 token 编号对应一行可学习的数值，用这行数值表示该 token。论文将它乘以 $\sqrt{d_{\text{model}}}$。相加要求 PE 和 embedding 宽度一致。原论文使用：

<div class="math-display">
$$
\begin{aligned}
PE(pos,2i)&amp;=\sin\!\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right),\\
PE(pos,2i+1)&amp;=\cos\!\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right).
\end{aligned}
$$
</div>

这里 $pos$ 是位置，$i$ 表示一对相邻的偶数、奇数坐标。不同坐标对使用不同频率，让一个位置由多种尺度的波形共同表示。〔[1，§3.4、§3.5](#ref-transformer)〕

为什么选成对的正弦和余弦？设某对坐标的角频率为 $\omega$，对固定偏移 $k$ 有：

<div class="math-display">
$$
\begin{aligned}
\sin((pos+k)\omega)&amp;=\sin(pos\omega)\cos(k\omega)+\cos(pos\omega)\sin(k\omega),\\
\cos((pos+k)\omega)&amp;=\cos(pos\omega)\cos(k\omega)-\sin(pos\omega)\sin(k\omega).
\end{aligned}
$$
</div>

因此，同一频率下，偏移后的位置向量可由原来那对坐标通过一个只依赖 $k$ 的线性变换得到。这个关系为模型学习相对位置提供了可利用的结构。

论文还比较了可学习的位置 embedding，在所报告的实验里结果接近。作者选择正弦方案时，也希望它能外推到更长序列；这个动机本身不构成任意长度上的质量保证。〔[1，§3.5、表 3](#ref-transformer)〕

## 编码器：交互之后，还要逐位置处理信息

有了注意力和位置，编码器的一层就可以搭起来了。原版每层包含两个子层：多头自注意力，以及逐位置前馈网络。各子层外都有残差连接与 Layer Normalization。编码器堆叠六层。〔[1，§3.1](#ref-transformer)〕

### 前馈网络为什么放在注意力后面？

注意力负责跨位置收集信息。前馈网络（Feed-Forward Network，FFN）则对每个位置的特征做一次非线性变换：

<div class="math-display">
$$
\operatorname{FFN}(x)=\operatorname{ReLU}(xW_1+b_1)W_2+b_2.
$$
</div>

ReLU 将负数截成 0。base 模型先把宽度从 512 扩到 2048，再投影回 512。相同一层里的所有位置使用同一套 FFN 参数，不同层使用不同参数。〔[1，§3.3](#ref-transformer)〕

“逐位置”限定了 FFN 的信息来源：它处理某一行时，不直接读取另一行。上下文已经由前面的注意力写入这一行。两种操作于是承担不同工作：注意力改变位置之间如何交换信息，FFN 进一步变换交换后的特征。

### Add & Norm 里究竟发生了什么？

设某个子层是 $F$，输入是 $x$。原版采用：

<div class="math-display">
$$
\operatorname{LayerNorm}\bigl(x+\operatorname{Dropout}(F(x))\bigr).
$$
</div>

残差连接把输入 $x$ 加回来，让子层在已有表示上学习修改。dropout 在训练时随机将部分中间输出置零；运行训练好的模型时，也就是推理时，关闭这一操作。Layer Normalization，简称 LayerNorm，则对一个 token 的特征维进行归一化。论文把归一化放在残差相加之后，即常说的 **Post-LN**。〔[1，§3.1、§5.4](#ref-transformer)〕

略去批维度，对某个位置的 $d$ 维向量 $u$，LayerNorm 可以写成：

<div class="math-display">
$$
\operatorname{LN}(u)_r=\gamma_r\frac{u_r-\mu}{\sqrt{\sigma^2+\epsilon}}+\beta_r.
$$
</div>

$\mu$ 和 $\sigma^2$ 分别是该位置 $d$ 个特征的均值与方差，用来描述这一行数值的中心与波动；$\gamma$、$\beta$ 是可学习的缩放和平移参数，$\epsilon$ 是避免分母出现数值问题的小常数。它不需要用其他样本的统计量来归一化这个 token。〔[3](#ref-layernorm)〕

这样，一层编码器可表示为：

<div class="math-display">
$$
\begin{aligned}
U&amp;=\operatorname{LN}\!\left(X+\operatorname{Dropout}(\operatorname{MultiHead}(X))\right),\\
H&amp;=\operatorname{LN}\!\left(U+\operatorname{Dropout}(\operatorname{FFN}(U))\right).
\end{aligned}
$$
</div>

每层输入和输出都保持 $n\times512$ 的形状，但各行所包含的上下文会继续变化。把最后一层输出记为 $H$，它就是解码器接下来读取的源序列表示，也常被称为 memory。

## 解码器有两种读取：看前缀，以及看源句

翻译时，编码器拿到完整源句，解码器预测目标句。原版解码器也是六层，但每层有三个子层：掩码多头自注意力、编码器到解码器的多头注意力，以及 FFN。每个子层都有自己的 Add & Norm。〔[1，§3.1、§3.2.3](#ref-transformer)〕

先把三种注意力的输入来源分清：

| 用途 | Q 来自哪里 | K、V 来自哪里 | 可以读取哪些位置 |
| --- | --- | --- | --- |
| 编码器自注意力 | 编码器当前层输入 | 同一份输入 | 全部有效源位置 |
| 解码器掩码自注意力 | 解码器当前层输入 | 同一份输入 | 当前及更早的目标输入位置 |
| 编码器到解码器注意力，即交叉注意力 | 解码器前一个子层的输出 | 编码器最终输出 $H$ | 全部有效源位置 |

自注意力的“自”表示 Q、K、V 来自同一条表示序列。交叉注意力使用目标侧提出查询，再从源侧读取内容。

若目标输入长度为 $m$，源句长度为 $n$，一个交叉注意力头的分数矩阵形状为 $m\times n$。它的第 $t$ 行对应“预测目标位置 $t$ 时，应从源句各位置读多少信息”。矩阵可以是长方形，计算规则和前面的缩放点积注意力相同。

### 右移目标，是为了让输入与标签错开一位

设正确目标序列是：

```text
我    爱    猫    EOS
```

其中 EOS 表示结束符。训练时，用起始符 BOS 构造右移后的解码器输入：

```text
位置          1      2      3      4
解码器输入   BOS     我     爱     猫
预测标签      我     爱     猫    EOS
```

第 3 个位置读取的当前输入是“爱”，它要预测的是“猫”。这也解释了为什么掩码允许读取对角线：**当前位置的输入已经是前一个目标 token。** 右移与因果掩码共同保证预测不能读取尚未生成的目标内容。〔[1，§3.1、§3.2.3](#ref-transformer)〕

{{< interactive-diagram src="causal-mask.html" title="训练与生成：把右移输入和因果掩码放在一起，观察并行训练如何避免读取未来，以及生成前缀为何逐步增长" height="1040" compact-height="1440" mobile-height="1540" >}}

### 掩码必须在 softmax 之前生效

假设位置 $t$ 的输入正在预测 $y_t$。它可以读取第 $1$ 到第 $t$ 个输入位置，但不能读取 $j>t$ 的输入。定义加性掩码：

<div class="math-display">
$$
M_{tj}=\begin{cases}
0,&amp;j\le t,\\
-\infty,&amp;j&gt;t.
\end{cases}
$$
</div>

再计算：

<div class="math-display">
$$
A=\operatorname{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}+M\right).
$$
</div>

未来位置的分数变为 $-\infty$，指数变为 0，归一化后权重也就为 0。有限精度实现通常使用框架支持的屏蔽操作；数学上的 $-\infty$ 表达的是“完全不可参与这次读取”。

不能只把屏蔽位置的分数改成 0，因为 $e^0=1$，它仍会得到权重。也不能在 softmax 后随意把若干项清零就当作相同运算，那样剩余权重通常不再归一化。

批量训练还常需要 padding mask，遮住为了凑齐长度而补上的空位置。它与因果掩码处理不同问题：前者说明哪些位置不是有效内容，后者规定目标前缀的可见范围。

## 训练能并行，不意味着一次生成整句话

对于源序列 $x$ 和目标序列 $y_1,\ldots,y_m$，自回归模型把条件概率分解为：

<div class="math-display">
$$
p(y\mid x)=\prod_{t=1}^{m}p(y_t\mid y_{&lt;t},x).
$$
</div>

这里 $y_{<t}$ 表示已经出现的目标前缀。原论文采用的生成过程遵循这条依赖。〔[1，§3](#ref-transformer)〕

训练时，正确目标句已经在数据里。因此可以把右移后的整句一次送入解码器，由掩码约束每个位置只能看前缀。这种用正确前缀训练的方式通常称为 teacher forcing。不同位置的预测与损失可以一起计算，随后一起反向传播。

生成时，正确目标句并不存在。模型先根据 BOS 和源句预测第一个 token，再把选出的 token 放入前缀，继续预测下一个。选择结果可能改变后续条件，所以普通自回归生成仍然按目标步推进。原论文的翻译评测使用了 beam search，即在生成中保留若干候选前缀。〔[1，§6.1](#ref-transformer)〕

于是，“并行”需要注明发生在哪一部分：Transformer 去掉了一层内部沿 token 位置递推隐藏状态的要求；训练可以同时计算多个目标位置；自回归生成仍要等待前一步选出的 token。每一步内部的投影、注意力和 FFN 当然仍可以使用并行矩阵计算。

## 把整台 Transformer 接起来

到这里，源句和目标前缀的两条路径已经齐了。播放下图时，重点跟踪源句产生的 $H$：它先由编码器算出，再被目标侧的交叉注意力读取。

{{< interactive-diagram src="encoder-decoder.html" title="完整原版 Transformer：沿源句编码、目标前缀、掩码自注意力、交叉注意力和词表预测，跟踪数据从哪里来、流到哪里去" height="1180" compact-height="1380" mobile-height="1450" >}}

用公式把一个解码器层写出来，会比结构图中的三个相似方框更容易区分。设当前层的目标侧输入为 $Y$，编码器最终输出为 $H$：

<div class="math-display">
$$
\begin{aligned}
T&amp;=\operatorname{LN}\!\left(Y+\operatorname{Dropout}(\operatorname{MaskedMHA}(Y))\right),\\
C&amp;=\operatorname{LN}\!\left(T+\operatorname{Dropout}(\operatorname{CrossMHA}(Q=T,K=H,V=H))\right),\\
D&amp;=\operatorname{LN}\!\left(C+\operatorname{Dropout}(\operatorname{FFN}(C))\right).
\end{aligned}
$$
</div>

这里的 MHA 是多头注意力，CrossMHA 中仍包含各头自己的 Q、K、V 投影。$H$ 作为所有解码器层的源侧输入复用，每层的投影参数分别学习。〔[1，§3.2.3](#ref-transformer)〕

词表列出了模型可能输出的 token。最后一层解码器的每个位置仍是 $d_{\text{model}}$ 维。线性层把它映射到词表大小 $|\mathcal V|$：

<div class="math-display">
$$
\begin{aligned}
\operatorname{logits}_t&amp;=D_tW_{\text{vocab}}+b,\\
p(y_t\mid y_{&lt;t},x)&amp;=\operatorname{softmax}(\operatorname{logits}_t).
\end{aligned}
$$
</div>

线性层先为词表中的每个 token 产生一个分数，称为 logit；softmax 再把这些分数转换为概率。这里又出现了 softmax，但归一化的对象变了：注意力中的 softmax 沿源或目标的键位置归一化，决定从哪里取信息；输出层的 softmax 沿词表归一化，决定下一个 token 的概率。

论文还共享了源、目标 embedding 与输出层的相应权重矩阵，并在 embedding 查表后乘以 $\sqrt{d_{\text{model}}}$。这是原版模型的具体选择，阅读结构图时容易漏掉。〔[1，§3.4](#ref-transformer)〕

## 参数是怎样学出来的？

前面的 Q、K、V 投影并不靠人为填写相关词。训练先用损失函数把模型对正确目标句的预测误差变成一个数，再计算各参数怎样改变这个数。这个变化关系称为梯度；反向传播从输出端沿计算步骤往回传递，把调整参数所需的梯度传回各个部件。

若只写最基本的目标，可以用目标位置上的负对数概率之和表示：

<div class="math-display">
$$
\mathcal L=-\sum_{t=1}^{m}\log p(y_t^{\text{gold}}\mid y_{&lt;t}^{\text{gold}},x).
$$
</div>

$y_t^{\text{gold}}$ 是训练数据中的正确 token。只要模型给它的概率较低，这一项损失就较大。梯度会经过词表映射、FFN、注意力权重和各投影矩阵，更新参数。

原论文的实际训练还使用了 $\epsilon_{ls}=0.1$ 的标签平滑（label smoothing）：将目标分布做适度平滑，避免要求模型把全部概率都压在单一标签上。因此上式适合说明基本学习方向，不是论文训练目标的全部细节。〔[1，§5.4](#ref-transformer)〕

优化器是根据梯度更新参数的算法，原论文使用 Adam。学习率控制每次调整的幅度：先在 4000 个 warmup（预热）步中增长，随后按训练步数的平方根倒数衰减：

<div class="math-display">
$$
lrate=d_{\text{model}}^{-1/2}
\min\!\left(step^{-1/2},\;step\cdot warmup^{-3/2}\right).
$$
</div>

论文设置 Adam 的 $\beta_1=0.9$、$\beta_2=0.98$、$\epsilon=10^{-9}$，base 模型的残差 dropout 为 0.1。训练结果来自这些配置与模型结构的共同作用，不能只凭注意力公式复现表中的分数。〔[1，§5.3、§5.4](#ref-transformer)〕

如果只想抓住 base 模型的骨架，可以保留下面这张参数表：

| 项目 | 论文 base 配置 |
| --- | --- |
| 编码器、解码器层数 | 各 6 层 |
| 模型宽度 $d_{\text{model}}$ | 512 |
| 注意力头数 $h$ | 8 |
| 每头 $d_k$、$d_v$ | 64、64 |
| FFN 隐藏宽度 $d_{ff}$ | 2048 |
| FFN 激活 | ReLU |
| 位置编码 | 正弦与余弦 |
| 归一化位置 | 残差相加之后，即 Post-LN |

以上均来自论文 §3 与表 3；它们限定的是本文解释的原版配置。〔[1](#ref-transformer)〕

## 并行化的收益，与全连接注意力的代价

原论文表 1 比较了不同序列层的单层复杂度、串行操作数和最大路径长度。这里的复杂度比较输入规模增加时运算量怎样增长；最大路径长度则比较信息从一个位置传到另一个位置，最多要经过多少步。下表沿用论文的主要比较，省略批维度，并以 $n$ 表示序列长度、$d$ 表示表示宽度：〔[1，表 1](#ref-transformer)〕

| 层类型 | 表中的单层计算复杂度 | 沿序列的串行操作数 | 两个位置间的最大路径长度 |
| --- | --- | --- | --- |
| 自注意力 | $O(n^2d)$ | $O(1)$ | $O(1)$ |
| 循环层 | $O(nd^2)$ | $O(n)$ | $O(n)$ |

自注意力的任意两个位置能在一层中直接交互，路径较短；矩阵运算也更适合一次处理多个位置。但表中的“大 O”有特定抽象：实际多头注意力还包括 Q、K、V 和输出投影，其计算量包含 $O(nd^2)$ 项。FFN 同样需要计算。不能把 $O(n^2d)$ 直接当成整层 Transformer 的全部耗时。

从我们已经写出的形状可以进一步推得，常规显式存储注意力矩阵的实现，每个头需要 $n\times n$ 个分数或权重。带批大小 $B$、头数 $h$ 时，相关存储随 $Bhn^2$ 增长。序列长度翻倍，这部分矩阵的元素数量就会变成四倍。

这也说明为什么“去掉循环”与“长序列计算便宜”是两个需要分别判断的问题。若只看论文表中的两个主项，自注意力在 $n<d$ 时有较有利的复杂度比较；真实速度还取决于序列长度、设备、批量、数据类型和实现。本文没有进行现代硬件上的性能测量。

## 论文的实验支持了多大范围的结论？

2017 年会议版报告了 WMT 2014 英德、英法翻译实验。英德训练数据约 450 万句对，英法约 3600 万句对。作者在一台配有 8 张 NVIDIA P100 GPU 的机器上训练模型：base 训练 10 万步，约 12 小时；big 训练 30 万步，约 3.5 天。〔[1，§5.1、§5.2](#ref-transformer)〕

会议版表 2 中，Transformer big 在英德任务上报告 28.4 BLEU，在英法任务上报告 41.0 BLEU。BLEU 是根据模型输出与参考译文的 n-gram 重合等因素计算的翻译评测指标，n-gram 指连续的若干个文本单位组成的片段；这些分数应放在论文的数据、分词和解码设置下阅读，不宜脱离评测口径与其他实验直接比较。〔[1，§6.1、表 2](#ref-transformer)；[4](#ref-bleu)〕

这些实验说明，作者给出的纯注意力序列转换架构在所测翻译任务中取得了很强的质量和训练效率。论文还做了模型配置消融，也就是改变部分配置，再比较结果，以检查这些选择对所测任务的影响。这些结果为所测配置提供了实验证据，没有覆盖所有任务、长度和硬件下的表现。〔[1，§6](#ref-transformer)〕

注意力图的解释也要保持同样的尺度。论文 §4 讨论了注意力分布与句法、语义结构的关系。一张权重图只告诉我们某个头在某层如何混合 Value。后续还有其他头、输出投影、残差与 FFN。仅凭一个较大的权重，无法断定模型最终输出只由那个 token 决定。

## 用几十行代码核对刚才的数值

本文附带一个只使用 Python 标准库的[注意力计算示例](attention_example.py)。它不训练模型，只验证前面的单头计算和因果掩码。下载后在文件所在目录运行，使用 Python 3.10 或更新版本即可：

```sh
python3 attention_example.py
```

程序会打印“坐”的注意力权重与输出，并检查每行权重之和为 1、因果掩码下未来位置权重为 0。预期关键输出为：

```text
坐 attention: [0.4011, 0.1978, 0.4011]
坐 output:    [1.6044, 1.1978]
```

为了演示所有查询同时计算，代码补上了另外两行教学用 Q。K、V 以及“坐”的查询与正文一致。代码使用减去行最大值的稳定 softmax，数学结果与直接计算指数相同。

对照程序再看核心公式，可以给每个操作标上具体职责：$QK^\top$ 负责匹配，缩放控制分数尺度，掩码限定可见范围，行 softmax 分配比例，乘 V 取回内容。多头提供多组读取方式，位置编码提供顺序，FFN 变换特征，残差与归一化把这些计算组织成可以堆叠的层。

如果要从头画回原版 Transformer，可以先画源句的六层编码器，再画目标前缀的六层解码器。解码器每层先读取自己的可见前缀，再用这个表示向源句发起查询。最后落到词表上的概率，预测的是当前位置尚未看到的下一个目标 token。这样，从一次加权求和到整句翻译，所有数据的来源与去向都能对应起来。

## 参考资料

<span id="ref-transformer"></span>

1. Ashish Vaswani et al. [Attention Is All You Need，NeurIPS 2017 会议版 PDF](https://papers.nips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf)。本文模型结构、公式、配置与翻译结果以这一版本为准；另见 [arXiv 记录与版本历史](https://arxiv.org/abs/1706.03762)。

<span id="ref-bahdanau"></span>

2. Dzmitry Bahdanau, Kyunghyun Cho, Yoshua Bengio. [Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473)，2014 年首次提交。用于说明 Transformer 之前的翻译注意力与循环结构。

<span id="ref-layernorm"></span>

3. Jimmy Lei Ba, Jamie Ryan Kiros, Geoffrey E. Hinton. [Layer Normalization](https://arxiv.org/abs/1607.06450)，2016。用于说明 LayerNorm 的归一化维度与可学习参数。

<span id="ref-bleu"></span>

4. Kishore Papineni et al. [BLEU: a Method for Automatic Evaluation of Machine Translation](https://aclanthology.org/P02-1040/)，ACL 2002。用于说明 BLEU 指标。

论文与参考资料核对日期：2026 年 10 月 15 日。四张动态图为本文原创示意，没有复用论文原图；教学数值与实际训练实验已经分别标明。
