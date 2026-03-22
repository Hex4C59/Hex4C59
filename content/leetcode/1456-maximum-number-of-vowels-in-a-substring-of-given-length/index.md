+++
title = "1456. 定长子串中元音的最大数目"
date = 2026-03-22T19:15:00+08:00
draft = false
author = "Hex4C59"
description = "LeetCode 1456 定长子串中元音的最大数目题解，使用定长滑动窗口统计子串中的最大元音数。"
summary = "LeetCode 1456 定长子串中元音的最大数目题解，包含暴力法、滑动窗口思路、复杂度分析，以及 Python 与 Rust 实现。"
tags = ["leetcode", "string", "sliding-window"]
categories = ["LeetCode"]
series = []
difficulty = "medium"
problem_id = 1456
source = "leetcode"
languages = ["Python", "Rust"]
ShowToc = true
+++

## 题目链接

- https://leetcode.cn/problems/maximum-number-of-vowels-in-a-substring-of-given-length/

## 题目描述

> 给你字符串 `s` 和整数 `k`，请返回字符串 `s` 中长度为 `k` 的单个子字符串中可能包含的最大元音字母数。
>
> 元音字母为 `a`、`e`、`i`、`o`、`u`。

## 示例

### 示例 1

```text
输入：s = "abciiidef", k = 3
输出：3
解释：子串 "iii" 包含 3 个元音字母
```

### 示例 2

```text
输入：s = "aeiou", k = 2
输出：2
```

### 示例 3

```text
输入：s = "leetcode", k = 3
输出：2
解释：子串 "lee"、"eet"、"ode" 都包含 2 个元音
```

## 提示

- `1 <= s.length <= 10^5`
- `s` 由小写英文字母组成
- `1 <= k <= s.length`

## 思路分析

### 暴力法

最直接的想法是枚举所有长度为 `k` 的子串，然后逐个统计每个子串里的元音个数，最后取最大值。

```text
s = "abciiidef", k = 3

"abc" -> 1
"bci" -> 1
"cii" -> 2
"iii" -> 3
"iid" -> 2
"ide" -> 2
"def" -> 1
```

这个思路容易理解，但存在明显的重复计算：

- 窗口从 `"abc"` 滑到 `"bci"` 时，`b` 和 `c` 又被重新统计了一遍
- 窗口从 `"bci"` 滑到 `"cii"` 时，`c` 和 `i` 还是会再次参与统计

时间复杂度是 `O(nk)`。当 `s.length` 和 `k` 都比较大时，这个复杂度会非常吃力。

> 根据我实际提交的结果，暴力解会超时。
>
> 因此下面的暴力代码只适合理解题意和对比思路，不适合作为最终提交方案。

### 定长滑动窗口

这题的关键在于：窗口长度 `k` 是固定的。

既然每次窗口只向右移动一格，那么窗口内部真正发生变化的只有两个字符：

- 右边新进入窗口的字符
- 左边离开窗口的字符

所以我们没必要每次都重新统计整个窗口，只需要：

1. 初始化第一个长度为 `k` 的窗口，统计其中的元音数
2. 每次向右滑动时：
   - 如果新进来的字符是元音，计数 `+1`
   - 如果移出去的字符是元音，计数 `-1`
3. 在滑动过程中维护最大值

```text
s = "abciiidef", k = 3

[a b c] i i i d e f   count = 1
 a[b c i] i i d e f   进 i，出 a，count = 1
 a b[c i i] i d e f   进 i，出 b，count = 2
 a b c[i i i] d e f   进 i，出 c，count = 3  <- 最大值
```

这样每个字符最多只会被处理两次：

- 一次进入窗口
- 一次离开窗口

因此总时间复杂度可以优化到 `O(n)`。

## 通用解法模板

> 只要题目满足“固定窗口长度 + 维护窗口内某种统计量”，就优先考虑定长滑动窗口。

这类题目的通用套路是：

1. 先统计第一个窗口
2. 然后不断执行“右进左出”
3. 用一个变量维护窗口状态，再用一个变量维护答案

## 代码实现

### 暴力法 Python

```python
class Solution:
    def maxVowels(self, s: str, k: int) -> int:
        vowels = set("aeiou")
        ans = 0

        for i in range(len(s) - k + 1):
            count = 0
            for j in range(i, i + k):
                if s[j] in vowels:
                    count += 1
            ans = max(ans, count)

        return ans
```

### 暴力法 Rust

```rust
impl Solution {
    pub fn max_vowels(s: String, k: i32) -> i32 {
        let bytes = s.as_bytes();
        let k = k as usize;
        let mut ans = 0;

        for i in 0..=bytes.len() - k {
            let mut count = 0;
            for j in i..i + k {
                if matches!(bytes[j], b'a' | b'e' | b'i' | b'o' | b'u') {
                    count += 1;
                }
            }
            ans = ans.max(count);
        }

        ans
    }
}
```

### 滑动窗口 Python

```python
class Solution:
    def maxVowels(self, s: str, k: int) -> int:
        vowels = set("aeiou")

        count = sum(1 for ch in s[:k] if ch in vowels)
        ans = count

        for i in range(k, len(s)):
            if s[i] in vowels:
                count += 1
            if s[i - k] in vowels:
                count -= 1
            ans = max(ans, count)

        return ans
```

### 滑动窗口 Rust

```rust
impl Solution {
    pub fn max_vowels(s: String, k: i32) -> i32 {
        let bytes = s.as_bytes();
        let k = k as usize;

        let mut count = 0;
        for i in 0..k {
            if matches!(bytes[i], b'a' | b'e' | b'i' | b'o' | b'u') {
                count += 1;
            }
        }

        let mut ans = count;

        for i in k..bytes.len() {
            if matches!(bytes[i], b'a' | b'e' | b'i' | b'o' | b'u') {
                count += 1;
            }
            if matches!(bytes[i - k], b'a' | b'e' | b'i' | b'o' | b'u') {
                count -= 1;
            }
            ans = ans.max(count);
        }

        ans
    }
}
```

## 复杂度分析

| 项目 | 复杂度 | 说明 |
| --- | --- | --- |
| 暴力法时间复杂度 | `O(nk)` | 每个窗口都重新统计 `k` 个字符 |
| 滑动窗口时间复杂度 | `O(n)` | 每个字符只参与有限次更新 |
| 空间复杂度 | `O(1)` | 只使用若干计数变量 |

如果把最坏情况代入，暴力法大致需要处理 `10^5 * 10^5` 级别的字符判断，显然无法在题目的时间限制内通过，这也是它实际提交会超时的根本原因。

## 易错点提醒

### 1. 不要每次都重新扫描整个窗口

这会把复杂度重新拉回 `O(nk)`，实际提交很容易超时。

### 2. 先初始化第一个窗口

很多人一上来就直接写滑动逻辑，结果忘了先统计前 `k` 个字符。

### 3. Rust 中优先按字节处理

这道题的数据只包含小写英文字母，用 `as_bytes()` 比先转成 `Vec<char>` 更直接，也更贴合下标访问的写法。

## 小结

| 方法 | 时间复杂度 | 空间复杂度 | 是否推荐提交 |
| --- | --- | --- | --- |
| 暴力法 | `O(nk)` | `O(1)` | 否，会超时 |
| 定长滑动窗口 | `O(n)` | `O(1)` | 是 |

这题是定长滑动窗口的经典入门题。真正需要记住的不是这一题本身，而是背后的模式：

**当窗口长度固定时，优先思考能否通过“右进左出”来增量维护窗口状态，而不是每次重新计算整个窗口。**
