+++
title = "相关系数详解与应用"
date = 2025-09-15T19:48:36+08:00
draft = false
Toc = true
author = "Hex4C59"
tags = ["数学", "深度学习"]
math = true
+++

我最近在复现一篇论文的实验:[Speech Emotion: Investigating Model Representations, Multi-Task Learning and Knowledge Distillation（Mitra et al. 2022）](https://arxiv.org/abs/2207.03334), 这是在[MSP-Podcast（Busso et al. 2025）](https://www.arxiv.org/pdf/2509.09791)这个语音情感数据集上做Arousal，Valence, Dominace三个维度的回归任务。论文模型结构图如下

![模型结构图](model.png)

我复现的是左边这个模型，它是先用预训练模型对数据进行特征提取，然后把特征送到 **two GRU Layer**——**Embedding Layer(其实就是Linear Layer)**——**Linear Layer** 这个网络结构里，这个模型用到的损失函数并不是MSE，而是自己定义的加权CCC，公式如下所示

$$
L_{ccc} := 1 - (\alpha CCC_v + \beta CCC_a + (1 - \alpha - \beta) CCC_d)
$$

$$
CCC = \frac{2\rho \sigma_x \sigma_y}{\sigma_x^2 + \sigma_y^2 + (\mu_x - \mu_y)^2}
$$