+++
title = "RTC 实时音视频入门：系列目录"
date = 2026-10-14
draft = false
author = "Hex4C59"
description = "从一通语音电话开始，逐步理解实时音视频的时间约束、声音处理、网络传输和弱网恢复，再进入连接建立与实际通话实验。"
summary = "面向第一次接触 RTC 的读者，用具体场景、分步计算和练习解释实时音视频。"
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

这个系列面向第一次学习实时音视频的读者。不要求先掌握网络协议或编解码，每篇从一个具体问题开始，解释相关对象和处理过程，再用例子检查理解。

[阅读第一篇：实时通话为什么不能一直等](/articles/rtc-01-why-real-time/)

## 当前文章

- [01：实时通话为什么不能一直等](/articles/rtc-01-why-real-time/)：从接话体验理解及时性，再判断缺失声音能否赶上播放。

## 后续方向

后续先沿着一条语音链路展开：声音从麦克风到扬声器怎样流动，数据如何表示先后，延迟怎样分段计算，接收端为何需要缓冲，以及重传什么时候还有价值。

这条链路讲清后，再进入网络变化下的发送调整、连接建立和双端通话实验；随后讨论视频编码、音画同步与多人通信。篇章会按实际写作进展拆分，完成的文章再加入目录。
