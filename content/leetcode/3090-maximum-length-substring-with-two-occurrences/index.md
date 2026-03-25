+++
title = "3090. 每个字符最多出现两次的最长子字符串"
date = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "LeetCode 3090 每个字符最多出现两次的最长子字符串题解，不定长滑动窗口的变体，限制窗口内每个字符出现次数不超过 2。"
summary = "LeetCode 3090 题解：与第 3 题同构的不定长滑动窗口，将「每个字符至多 1 次」改为至多 2 次；含 Python / Rust 实现、复杂度与易错点。"
tags = ["leetcode", "string", "hash-table", "sliding-window"]
categories = ["LeetCode"]
series = []
difficulty = "easy"
problem_id = 3090
source = "leetcode"
languages = ["Python", "Rust"]
ShowToc = true
+++

## 题目链接

- https://leetcode.cn/problems/maximum-length-substring-with-two-occurrences/

## 题目描述

> 给你一个字符串 `s`，请找出满足每个字符最多出现两次的最长子字符串，并返回该最长子字符串的长度。

## 示例

### 示例 1

```text
输入：s = "bcbbbcba"
输出：4
解释：满足条件的最长子字符串是 "bcbb"，每个字符最多出现两次，长度为 4
```

### 示例 2

```text
输入：s = "aaaa"
输出：2
解释：满足条件的最长子字符串是 "aa"，长度为 2
```

## 提示

- `2 <= s.length <= 100`
- `s` 仅由小写英文字母组成

## 思路分析

### 与第 3 题的关系

这道题是 LeetCode 3（无重复字符的最长子串）的直接变体：

- 第 3 题：每个字符最多出现 **1** 次
- 本题：每个字符最多出现 **2** 次

本质上只需把"窗口不合法"的判定条件从 `count > 1` 改为 `count > 2`，其余框架完全一致。

### 不定长滑动窗口

同样使用双指针维护一个滑动窗口：

- `right` 向右扩展，将新字符加入窗口
- 若某个字符在窗口内出现超过 2 次，从 `left` 开始收缩，直到不再超限
- 每次窗口合法时更新最大长度

```text
s = "bcbbbcba"

right = 0, 进入 b：{b:1}，合法，ans = 1
right = 1, 进入 c：{b:1, c:1}，合法，ans = 2
right = 2, 进入 b：{b:2, c:1}，合法，ans = 3
right = 3, 进入 b：{b:3, c:1}，b 超过 2！
  移出 s[0]=b：{b:2, c:1}，合法，left = 1，ans = 3
right = 4, 进入 b：{b:3, c:1}，b 超过 2！
  移出 s[1]=c：{b:3}，还是不合法
  移出 s[2]=b：{b:2}，合法，left = 3，ans = max(3, 4-3+1) = 3
  等等，此时窗口是 s[3..4] = "bb"，长度 2
right = 5, 进入 c：{b:2, c:1}，合法，ans = max(3, 5-3+1) = 3
right = 6, 进入 b：{b:3, c:1}，b 超过 2！
  移出 s[3]=b：{b:2, c:1}，合法，left = 4
right = 7, 进入 a：{b:2, c:1, a:1}，合法，ans = max(3, 7-4+1) = 4
```

最终答案为 4，对应子串 `"bcba"` 或其等价窗口。

## 通用解法模板

对比两道题的模板，差异只有一行：

```python
# 第 3 题：每个字符最多出现 1 次
while count[ch] > 1:
    ...

# 第 3090 题：每个字符最多出现 2 次
while count[ch] > 2:
    ...
```

这也体现了不定长滑动窗口框架的扩展性：只要能清晰定义"窗口合法性"，框架本身无需修改。

## 代码实现

### Python

```python
class Solution:
    def maximumLengthSubstring(self, s: str) -> int:
        count = {}
        left = 0
        ans = 0

        for right, ch in enumerate(s):
            count[ch] = count.get(ch, 0) + 1

            while count[ch] > 2:
                left_ch = s[left]
                count[left_ch] -= 1
                left += 1

            ans = max(ans, right - left + 1)

        return ans
```

### Rust

```rust
impl Solution {
    pub fn maximum_length_substring(s: String) -> i32 {
        let bytes = s.as_bytes();
        let mut count = [0u32; 26];
        let mut left = 0;
        let mut ans = 0;

        for right in 0..bytes.len() {
            let ch = (bytes[right] - b'a') as usize;
            count[ch] += 1;

            while count[ch] > 2 {
                count[(bytes[left] - b'a') as usize] -= 1;
                left += 1;
            }

            ans = ans.max(right - left + 1);
        }

        ans as i32
    }
}
```

> 因为题目限定输入只含小写英文字母，Rust 实现中可以用长度 26 的数组替代哈希表，通过 `bytes[i] - b'a'` 直接映射到下标，更简洁高效。

## 复杂度分析

| 项目 | 复杂度 | 说明 |
| --- | --- | --- |
| 时间复杂度 | `O(n)` | 每个字符至多入窗、出窗各一次 |
| 空间复杂度 | `O(∣Σ∣)` | 字符集大小，小写字母时为 `O(26)` |

## 易错点提醒

### 1. 收缩条件是 `> 2` 而不是 `>= 2`

每个字符允许出现 **最多** 2 次，所以 `count == 2` 仍然合法，只有 `count == 3` 时才需要收缩。写成 `>= 2` 会把合法窗口误判为非法。

### 2. while 而不是 if

和第 3 题一样，收缩时必须用 `while`。加入一个新字符后，可能需要连续移出多个字符才能恢复合法状态。

### 3. 答案在 while 之后更新

`ans` 要在窗口恢复合法后才更新，确保统计的是合法子串的长度。

## 小结

| 方法 | 时间复杂度 | 空间复杂度 | 是否推荐提交 |
| --- | --- | --- | --- |
| 不定长滑动窗口 | `O(n)` | `O(∣Σ∣)` | 是 |

这道题是第 3 题的一键变体，核心逻辑完全相同，只有合法性阈值从 1 改成了 2。

**当题目从"不重复"变成"最多出现 k 次"时，滑动窗口框架不变，只需调整窗口的合法性判断条件。**

这种"参数化合法性"的思路，是不定长滑动窗口框架最有价值的地方。
