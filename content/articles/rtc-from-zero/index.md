+++
title = "RTC 实时音视频入门：系列目录"
date = 2026-10-14
lastmod = 2026-10-14
draft = false
author = "Hex4C59"
description = "从一通语音电话开始，逐步理解实时音视频的时间约束、声音处理、网络传输和弱网恢复，再进入连接建立与实际通话实验。"
summary = "面向第一次接触 RTC 的读者，用完整案例、数据计算与可复现实验学习实时音视频。"
tags = ["RTC", "实时音视频"]
categories = ["engineering"]
source_kind = "original"
article_type = "concept"
series = ["rtc-from-zero"]
series_order = 0
series_index = true
series_title = "RTC 实时音视频入门"
series_status = "连载中"
series_intro = "先理解声音为什么要及时到达，再沿着采集、编码、传输和播放的路径，学习等待、恢复与网络变化。"
series_kind = "course"
layout = "series"
ShowToc = true
+++

这个系列面向第一次学习实时音视频的读者，不要求先掌握网络协议或编解码。每篇围绕一个完整问题，把相关机制、数据计算和处理过程放在一起，再用可复现实验检查结论。纯模型的结果与真实编解码输出会分别注明，避免把教学参数当作产品表现。

[阅读第一篇：实时通话为什么不能一直等](/articles/rtc-01-why-real-time/)

## 当前文章

- [01：实时通话为什么不能一直等](/articles/rtc-01-why-real-time/)：沿声音路径计算延迟预算，用时间图比较缓冲、迟到与恢复的取舍。
- [02：声音从麦克风到扬声器](/articles/rtc-02-audio-path/)：跟踪同一段声音的样本、字节和块长变化，用合成音运行真实 Opus 编解码实验。
- [03：从一段收包记录读懂 RTP](/articles/rtc-03-sequence-gap/)：读报头，将包序和媒体时间映射到播放计划，再比较统计口径与打包开销。

## 后续方向

接下来比较缺失声音的恢复方法：什么情况下重传仍来得及，冗余恢复增加多少数据成本，来不及恢复时怎样继续产生声音。各方法仍放回同一份播放时间预算中判断。

这条链路讲清后，再进入网络变化下的发送调整、连接建立和双端通话实验；随后讨论视频编码、音画同步与多人通信。篇章会按实际写作进展拆分，完成的文章再加入目录。
