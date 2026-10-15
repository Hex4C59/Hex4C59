+++
title = "实时通信与网络"
description = "从一通语音电话理解采集、播放和网络传输，再观察丢包、发送排队与连接建立。"
date = 2026-10-15
weight = 40
topic_key = "rtc"
topic_label = "音频链路 · 弱网恢复 · 连接建立"
topic_start = "/articles/rtc-01-why-real-time/"
include_series = ["rtc-from-zero"]

[[reading_routes]]
title = "先走通一条声音链路"
description = "认识实时通话的时间约束，沿麦克风、处理、编码与扬声器追踪声音。"
series = "rtc-from-zero"
pages = ["/articles/rtc-01-why-real-time/", "/articles/rtc-02-audio-path/"]

[[reading_routes]]
title = "从收发记录理解弱网"
description = "区分迟到与丢失，比较恢复方式，再观察发送队列和延迟怎样增长。"
series = "rtc-from-zero"
pages = ["/articles/rtc-03-sequence-gap/", "/articles/rtc-04-loss-recovery/", "/articles/rtc-05-send-queue/", "/articles/rtc-06-delay-trend/"]

[[reading_routes]]
title = "让两端找到可以通信的路径"
description = "从地址和 NAT 进入信令、ICE 与中继，用浏览器观察候选路径和数据回传。"
series = "rtc-from-zero"
pages = ["/articles/rtc-07-connection-setup/"]
+++
