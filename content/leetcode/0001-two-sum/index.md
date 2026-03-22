+++
title = "1. 两数之和"
date = 2026-03-22T18:30:00+08:00
draft = false
author = "Hex4C59"
description = "LeetCode 1 两数之和题解，包含暴力枚举与哈希表两种思路。"
summary = "LeetCode 1 两数之和题解，包含暴力法、哈希表优化、复杂度分析，以及 Python / Rust 实现。"
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

> 给定一个整数数组 `nums` 和一个整数 `target`，请你在数组中找出和为 `target` 的那两个整数，并返回它们的数组下标。
>
> 你可以假设每种输入只会对应一个答案，且同一个元素不能被重复使用。

这道题的关键点有两个：

- 返回的是**下标**，不是元素本身
- 题目保证**恰好存在一个有效答案**

## 示例

### 示例 1

```text
输入：nums = [2, 7, 11, 15], target = 9
输出：[0, 1]
解释：nums[0] + nums[1] = 2 + 7 = 9
```

### 示例 2

```text
输入：nums = [3, 2, 4], target = 6
输出：[1, 2]
解释：nums[1] + nums[2] = 2 + 4 = 6
```

### 示例 3

```text
输入：nums = [3, 3], target = 6
输出：[0, 1]
解释：不能重复使用同一个元素，因此答案是两个不同位置的 3
```

## 提示

- `2 <= nums.length <= 10^4`
- `-10^9 <= nums[i] <= 10^9`
- `-10^9 <= target <= 10^9`
- 只会存在一个有效答案

## 思路分析

### 暴力法

最直接的想法是枚举所有下标对 `(i, j)`，判断：

```text
nums[i] + nums[j] == target
```

只要找到满足条件的两个下标，就可以直接返回。

这种方法为什么容易想到？因为题目本身就是在问：

- 选哪两个数
- 它们的和是否等于 `target`

所以最朴素的写法就是双重循环，把所有可能都试一遍。

```text
nums = [2, 7, 11, 15], target = 9

枚举 (0, 1) -> 2 + 7 = 9，找到答案
```

如果换一个更一般的过程，就是：

- 固定第一个下标 `i`
- 再枚举第二个下标 `j`
- 判断 `nums[i] + nums[j]` 是否等于 `target`

这个思路没有任何技巧，优点是实现简单，缺点是会枚举很多不必要的组合。它的时间复杂度是 `O(n^2)`。

### 哈希表

更优的思路是使用哈希表，把问题从“找两个数”改写成“当前这个数需要谁来配对”。

假设当前遍历到数字 `x`，那么它想要凑出 `target`，还需要一个值：

```text
need = target - x
```

于是问题就变成：

**在前面遍历过的数字里，有没有出现过 `need`？**

如果出现过，就说明答案已经找到了；如果没有，就把当前数字和它的下标存进哈希表，留给后面的数字使用。

可以用一个字典 / `HashMap` 记录：

```text
{数值: 下标}
```

手推一下：

```text
nums = [2, 7, 11, 15], target = 9

遍历到 2：need = 7
前面没有 7
存入 {2: 0}

遍历到 7：need = 2
前面有 2，对应下标 0
返回 [0, 1]
```

这个方法的核心不是“同时找两个数”，而是：

- 遍历当前值 `x`
- 计算它需要的值 `need`
- 去哈希表里快速查 `need` 是否出现过

因为哈希表的查询平均复杂度是 `O(1)`，所以整个过程只需要一次遍历，时间复杂度就能优化到 `O(n)`。

## 通用解法模板

> 这道题是哈希表“边查边存”模板的经典入门题。

这类题的通用思路是：

1. 遍历数组中的当前元素
2. 先计算“当前元素还缺什么值”
3. 去哈希表中查这个值是否已经出现过
4. 如果出现过，直接返回答案
5. 如果没有出现过，再把当前元素存入哈希表

这个模式会在很多题目里反复出现，比如：

- 两数之和
- 子数组和为 K
- 连续数组
- 四数相加 II

当题目本质上是在问“某个值之前有没有出现过”时，优先考虑哈希表通常是正确方向。

## 代码实现

### 暴力法 Python

```python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        n = len(nums)

        for i in range(n):
            for j in range(i + 1, n):
                if nums[i] + nums[j] == target:
                    return [i, j]

        return []
```

### 暴力法 Rust

```rust
impl Solution {
    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
        for i in 0..nums.len() {
            for j in i + 1..nums.len() {
                if nums[i] + nums[j] == target {
                    return vec![i as i32, j as i32];
                }
            }
        }

        vec![]
    }
}
```

### 哈希表 Python

```python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}

        for i, x in enumerate(nums):
            need = target - x

            if need in seen:
                return [seen[need], i]

            seen[x] = i

        return []
```

### 哈希表 Rust

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
| 暴力法时间复杂度 | `O(n^2)` | 双重循环枚举所有下标对 |
| 哈希表时间复杂度 | `O(n)` | 只遍历一次数组，哈希表查询平均为 `O(1)` |
| 空间复杂度 | `O(n)` | 哈希表最多存储 `n` 个元素 |

哈希表解法是典型的**用空间换时间**：

- 多使用一个 `HashMap`
- 换来从 `O(n^2)` 到 `O(n)` 的优化

## 易错点提醒

### 1. 一定要先查再存

这是这道题最容易写错的地方。

错误写法：

```python
seen[x] = i
if need in seen:
    return [seen[need], i]
```

正确写法：

```python
if need in seen:
    return [seen[need], i]
seen[x] = i
```

为什么？因为题目不允许重复使用同一个元素。

如果你先把当前元素放进去，再查 `need`，就有可能错误地把当前元素自己拿来和自己配对。

### 2. 返回的是下标，不是数值

这道题不是返回 `[x, need]`，而是返回它们在数组中的位置。

所以哈希表里存的应该是：

```text
{数值: 下标}
```

而不是只存一个布尔值表示出现过。

### 3. Rust 里 `get` 返回的是引用

Rust 的 `HashMap::get(&need)` 返回的是：

```text
Option<&usize>
```

所以代码里写的是：

```rust
if let Some(&j) = seen.get(&need)
```

这里的 `&j` 表示把引用里的值取出来，拿到真正的下标 `j`。

另外，LeetCode 要求返回 `Vec<i32>`，而数组下标通常是 `usize``，所以还需要：

```rust
j as i32
```

和

```rust
i as i32
```

做类型转换。

## 小结

| 方法 | 时间复杂度 | 空间复杂度 | 是否推荐提交 |
| --- | --- | --- | --- |
| 暴力法 | `O(n^2)` | `O(1)` | 可以理解思路，但不是最优 |
| 哈希表 | `O(n)` | `O(n)` | 是 |

两数之和是哈希表最经典的入门题之一。真正需要记住的不是这道题本身，而是它背后的模式：

**当题目要求“快速判断某个值是否已经出现过”时，优先考虑哈希表；当遍历过程中可以把问题转化为“当前值需要谁来配对”时，优先考虑边查边存。**
