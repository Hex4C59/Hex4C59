+++
title = "1. Two Sum"
date = 2026-03-22T18:30:00+08:00
draft = false
author = "Hex4C59"
description = "LeetCode 1 Two Sum 题解，使用哈希表在一次遍历中完成查找。"
summary = "LeetCode 1 Two Sum 题解，包含哈希表思路、复杂度分析与 Python、Rust 实现。"
tags = ["leetcode", "hot-100", "array", "hash-table"]
categories = ["LeetCode"]
series = ["hot-100"]
difficulty = "easy"
problem_id = 1
source = "leetcode"
languages = ["Python", "Rust"]
ShowToc = true
+++

## 题目链接

- https://leetcode.cn/problems/two-sum/description/

## 题目描述

> 给定一个整数数组 `nums` 和一个目标值 `target`，请你在该数组中找出**和为目标值**的那**两个**整数，并返回它们的数组下标。
>
> 你可以假设每种输入只会对应一个答案，且同样的元素不能被重复利用。

## 示例

### 示例 1

```text
输入：nums = [2, 7, 11, 15], target = 9
输出：[0, 1]
解释：因为 nums[0] + nums[1] = 2 + 7 = 9
```

### 示例 2

```text
输入：nums = [3, 2, 4], target = 6
输出：[1, 2]
```

### 示例 3

```text
输入：nums = [3, 3], target = 6
输出：[0, 1]
```

## 提示

- `2 <= nums.length <= 10^4`
- `-10^9 <= nums[i] <= 10^9`
- `-10^9 <= target <= 10^9`
- 只会存在一个有效答案

## 思路分析

### 暴力法

先从最直接的思路出发：使用两层循环枚举所有数对，判断它们的和是否等于 `target`。

这种方法实现简单，但时间复杂度是 `O(n^2)`。数据量小时可以接受，但并不是这道题最优雅的解法。

### 哈希表

更优的思路是使用哈希表。

遍历到当前数字 `x` 时，我们只需要知道 `target - x` 是否已经在前面出现过。如果出现过，就说明找到了答案。

可以用一个字典记录 `{数值: 下标}`。遍历数组时，先查询需要的值是否已经存在；如果不存在，再把当前值和下标存入字典。

```text
nums = [2, 7, 11, 15], target = 9

遍历 x = 2：need = 9 - 2 = 7，字典里没有 7，存入 {2: 0}
遍历 x = 7：need = 9 - 7 = 2，字典里有 2，对应下标 0，返回 [0, 1]
```

这样只需要一次遍历，就能把时间复杂度优化到 `O(n)`。

## 通用解法模板

> **边查边存** 是哈希表解题的经典模式：
> 遍历时先查字典里有没有“需要的值”，没有则把“当前值”存入字典。

这个模式会在很多题目中反复出现，比如三数之和、四数之和、子数组和等问题。

## 代码实现

### Python

```python
def two_sum(nums, target):
    seen = {}

    for i, x in enumerate(nums):
        need = target - x

        if need in seen:
            return [seen[need], i]

        seen[x] = i

    return []
```

### Rust

```rust
use std::collections::HashMap;

impl Solution {
    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
        let mut seen: HashMap<i32, usize> = HashMap::new();

        for (i, &x) in nums.iter().enumerate() {
            let need = target - x;

            if let Some(&j) = seen.get(&need) {
                return vec![j as i32, i as i32];
            }

            seen.insert(x, i);
        }

        vec![]
    }
}
```

## 复杂度分析

| 项目 | 复杂度 | 说明 |
| --- | --- | --- |
| 时间复杂度 | `O(n)` | 只遍历一次数组，哈希表查询平均为 `O(1)` |
| 空间复杂度 | `O(n)` | 哈希表最多存储 `n` 个元素 |

相比暴力法的 `O(n^2)`，这是典型的**用空间换时间**。

## 易错点提醒

```python
# 错误：先存再查，可能会错误使用同一个元素两次
seen[x] = i
if need in seen:
    return [seen[need], i]

# 正确：先查再存
if need in seen:
    return [seen[need], i]
seen[x] = i
```

## 小结

| 方法 | 时间复杂度 | 空间复杂度 |
| --- | --- | --- |
| 暴力双循环 | `O(n^2)` | `O(1)` |
| 哈希表 | `O(n)` | `O(n)` |

两数之和是哈希表最经典的入门题之一。它的核心不在于技巧有多复杂，而在于帮助我们建立一种重要意识：

当题目要求“快速查找某个值是否出现过”时，优先考虑哈希表。