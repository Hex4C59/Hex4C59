+++
title = "3. 无重复字符的最长子串"
date = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "LeetCode 3 无重复字符的最长子串题解，使用不定长滑动窗口 + 哈希表维护窗口内字符状态。"
summary = "LeetCode 3 无重复字符的最长子串题解，包含暴力法、不定长滑动窗口、通用模板、复杂度分析，以及 Python / Rust 实现。"
tags = ["leetcode", "hot-100", "string", "hash-table", "sliding-window"]
categories = ["LeetCode"]
series = ["hot-100"]
difficulty = "medium"
problem_id = 3
source = "leetcode"
languages = ["Python", "Rust"]
ShowToc = true
+++

## 题目链接

- https://leetcode.cn/problems/longest-substring-without-repeating-characters/

## 题目描述

> 给定一个字符串 `s`，请你找出其中不含有重复字符的**最长子串**的长度。

## 示例

### 示例 1

```text
输入：s = "abcabcbb"
输出：3
解释：最长不重复子串是 "abc"，长度为 3
```

### 示例 2

```text
输入：s = "bbbbb"
输出：1
解释：最长不重复子串是 "b"，长度为 1
```

### 示例 3

```text
输入：s = "pwwkew"
输出：3
解释：最长不重复子串是 "wke"，长度为 3
```

## 提示

- `0 <= s.length <= 5 * 10^4`
- `s` 由英文字母、数字、符号和空格组成

## 思路分析

### 暴力法

最直接的思路是枚举所有子串，逐一判断是否存在重复字符，最后取最长的那个。

```text
s = "abcabcbb"

"a"     -> 不重复，长度 1
"ab"    -> 不重复，长度 2
"abc"   -> 不重复，长度 3
"abca"  -> 有重复 a，停止
"b"     -> 不重复，长度 1
"bc"    -> 不重复，长度 2
"bca"   -> 不重复，长度 3
"bcab"  -> 有重复 b，停止
...
```

每个起点最多向右扩展 `n` 次，总时间复杂度为 `O(n^2)`（若用哈希集合判断重复）或 `O(n^3)`（若每次遍历子串）。当字符串较长时，这个复杂度难以承受。

> 暴力代码仅用于理解题意，实际提交会超时。

### 不定长滑动窗口

这道题与定长滑动窗口最大的区别在于：**窗口的长度不是固定的**，而是根据当前窗口内部的状态来动态伸缩。

核心思路：

- 用两个指针 `left` 和 `right` 分别表示窗口的左右边界（左闭右开）
- 用一个哈希表（或数组）记录窗口内每个字符出现的次数
- `right` 不断向右扩展，将新字符加入窗口
- 一旦发现窗口内出现了重复字符（某字符计数 > 1），就从左边收缩窗口，直到不再重复为止
- 在每次合法状态下更新最大长度

```text
s = "abcabcbb"

初始：left = 0, right = 0, window = {}

right = 0, 进入 a：window = {a:1}，合法，ans = 1
right = 1, 进入 b：window = {a:1, b:1}，合法，ans = 2
right = 2, 进入 c：window = {a:1, b:1, c:1}，合法，ans = 3
right = 3, 进入 a：window = {a:2, b:1, c:1}，重复！
  left = 0, 移出 a：window = {a:1, b:1, c:1}，不再重复，left = 1
right = 4, 进入 b：window = {a:1, b:2, c:1}，重复！
  left = 1, 移出 b：window = {a:1, b:1, c:1}，不再重复，left = 2
...
```

每个字符最多进入和离开窗口各一次，因此总时间复杂度为 `O(n)`。

## 通用解法模板

不定长滑动窗口与定长窗口最大的区别就在于"窗口何时收缩"：

- 定长窗口：窗口大小达到 `k` 时，强制移出左边一个元素
- **不定长窗口：窗口状态不合法时，持续从左边收缩，直到状态重新合法**

通用套路：

```python
left = 0
window = {}  # 或其他数据结构，维护窗口状态

for right in range(len(s)):
    # 1. 将 s[right] 加入窗口
    window[s[right]] = window.get(s[right], 0) + 1

    # 2. 若窗口状态不合法，从左边收缩
    while window_is_invalid():
        window[s[left]] -= 1
        left += 1

    # 3. 此时窗口合法，更新答案
    ans = max(ans, right - left + 1)
```

这个框架对一大类"最长合法子串/子数组"问题都适用。

## 代码实现

### 暴力法 Python

```python
class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        ans = 0
        n = len(s)
        for i in range(n):
            seen = set()
            for j in range(i, n):
                if s[j] in seen:
                    break
                seen.add(s[j])
                ans = max(ans, j - i + 1)
        return ans
```

### 暴力法 Rust

```rust
impl Solution {
    pub fn length_of_longest_substring(s: String) -> i32 {
        let bytes = s.as_bytes();
        let n = bytes.len();
        let mut ans = 0;

        for i in 0..n {
            let mut seen = std::collections::HashSet::new();
            for j in i..n {
                if !seen.insert(bytes[j]) {
                    break;
                }
                ans = ans.max(j - i + 1);
            }
        }

        ans as i32
    }
}
```

### 滑动窗口 Python

```python
class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        count = {}
        left = 0
        ans = 0

        for right, ch in enumerate(s):
            count[ch] = count.get(ch, 0) + 1

            while count[ch] > 1:
                left_ch = s[left]
                count[left_ch] -= 1
                left += 1

            ans = max(ans, right - left + 1)

        return ans
```

### 滑动窗口 Rust

```rust
impl Solution {
    pub fn length_of_longest_substring(s: String) -> i32 {
        let bytes = s.as_bytes();
        let mut count = [0u32; 128];
        let mut left = 0;
        let mut ans = 0;

        for right in 0..bytes.len() {
            let ch = bytes[right] as usize;
            count[ch] += 1;

            while count[ch] > 1 {
                count[bytes[left] as usize] -= 1;
                left += 1;
            }

            ans = ans.max(right - left + 1);
        }

        ans as i32
    }
}
```

> Rust 实现中，由于题目保证输入为 ASCII 字符，可以直接用长度 128 的数组代替哈希表，省去哈希开销，访问更快。

## 复杂度分析

| 项目 | 复杂度 | 说明 |
| --- | --- | --- |
| 暴力法时间复杂度 | `O(n^2)` | 枚举起点 × 向右扩展 |
| 滑动窗口时间复杂度 | `O(n)` | 每个字符至多入窗、出窗各一次 |
| 空间复杂度 | `O(∣Σ∣)` | 字符集大小，通常为常数（ASCII 128） |

## 易错点提醒

### 1. while 而不是 if

收缩窗口时必须用 `while`，而不是 `if`。因为每次加入新字符后，可能需要连续移出多个字符才能恢复合法状态。用 `if` 只会移出一次，无法保证窗口合法。

### 2. 先更新 count，再收缩

`right` 对应的新字符要先加入 `count`，再判断是否需要收缩。顺序颠倒会导致统计错误。

### 3. 答案在收缩之后更新

`ans` 必须在 `while` 循环之后更新，此时窗口已处于合法状态。如果在收缩前更新，可能记录了含重复字符的窗口长度。

### 4. Rust 中用数组代替 HashMap

ASCII 字符集固定为 128 个，使用 `[0u32; 128]` 比 `HashMap` 更高效，且无需处理哈希冲突。

## 小结

| 方法 | 时间复杂度 | 空间复杂度 | 是否推荐提交 |
| --- | --- | --- | --- |
| 暴力法 | `O(n^2)` | `O(∣Σ∣)` | 否，会超时 |
| 不定长滑动窗口 | `O(n)` | `O(∣Σ∣)` | 是 |

这题是不定长滑动窗口的经典入门题。与定长窗口的核心差异只有一点：

**窗口的收缩不再由大小决定，而是由窗口内部的"合法性"驱动——只要状态不合法，就持续从左边移出元素。**

理解了这个模式，后续遇到"最长合法子串/子数组"一类的问题，都可以用同一个框架来处理。
