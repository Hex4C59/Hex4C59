+++
title = "2779. 数组的最大美丽值"
date = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "LeetCode 2779 数组的最大美丽值题解，排序后转化为不定长滑动窗口问题，寻找最长的合法区间。"
summary = "LeetCode 2779 题解：将「最多有多少元素能变成同一值」转化为排序后极差不超过 2k 的最长区间，配合不定长滑动窗口与 Python、Rust 实现。"
tags = ["leetcode", "array", "sorting", "sliding-window", "binary-search"]
categories = ["LeetCode"]
series = []
difficulty = "medium"
problem_id = 2779
source = "leetcode"
languages = ["Python", "Rust"]
ShowToc = true
+++

## 题目链接

- https://leetcode.cn/problems/maximum-beauty-of-an-array-after-applying-operation/

## 题目描述

> 给你一个下标从 **0** 开始的整数数组 `nums` 和一个非负整数 `k`。
>
> 在一次操作中，你可以选择数组 `nums` 中满足 `0 <= i < nums.length` 的下标 `i`，并将 `nums[i]` 替换为范围 `[nums[i] - k, nums[i] + k]` 内的任一整数。
>
> 数组的**美丽值**定义为：数组中由**相等元素**组成的**最长子序列**的长度。
>
> 返回在 **任意次** 操作后，数组可能拥有的**最大美丽值**。
>
> 注意：你可以对每个下标运行**多次**操作。

## 示例

### 示例 1

```text
输入：nums = [4, 6, 1, 2], k = 2
输出：3
解释：选择下标 1, 2, 3 并分别将它们替换为 6, 2, 4，nums = [4, 6, 2, 4]。
      子序列 [4, 4, 4] 的美丽值为 3。
      可以证明 3 是我们可以得到的最大美丽值。
```

### 示例 2

```text
输入：nums = [1, 1, 1, 1], k = 10
输出：4
解释：无需修改，所有元素已经相等，美丽值为 4。
```

## 提示

- `1 <= nums.length <= 10^5`
- `0 <= nums[i], k <= 10^5`

## 思路分析

### 题意转化

这道题乍看复杂，但仔细分析后可以发现一个关键点：

每个元素 `nums[i]` 经过操作后，可以变成区间 `[nums[i] - k, nums[i] + k]` 内的任意整数。我们希望选出尽量多的元素，让它们都能被替换成同一个值 `x`。

**元素 `nums[i]` 能被替换成 `x` 的条件是：`x` 在区间 `[nums[i] - k, nums[i] + k]` 内，即 `|nums[i] - x| <= k`。**

反过来说，若我们固定目标值 `x`，所有满足 `nums[i] - k <= x <= nums[i] + k` 的元素都可以替换成 `x`。进一步整理这个不等式：

```text
nums[i] - k <= x  =>  nums[i] <= x + k
x <= nums[i] + k  =>  x - k <= nums[i]
```

即：`x - k <= nums[i] <= x + k`，等价于 `nums[i]` 和 `x` 的差的绝对值不超过 `k`。

所以，问题转化为：**从数组中找出尽量多的元素，使得它们中的最大值与最小值之差不超过 `2k`**（因为最小值可以拉到 `x - k`，最大值可以降到 `x + k`，区间宽度为 `2k`）。

### 排序 + 不定长滑动窗口

由于我们关注的是"最大值与最小值之差"，**顺序不重要**，只需要统计有多少个元素落在某个长度为 `2k` 的区间内。

因此，先对数组排序，然后用滑动窗口寻找最长的一段，使得 `nums[right] - nums[left] <= 2k`。

```text
nums = [4, 6, 1, 2], k = 2，排序后：[1, 2, 4, 6]

left = 0, right = 0：[1]，差 = 0 <= 4，ans = 1
left = 0, right = 1：[1, 2]，差 = 1 <= 4，ans = 2
left = 0, right = 2：[1, 2, 4]，差 = 3 <= 4，ans = 3
left = 0, right = 3：[1, 2, 4, 6]，差 = 5 > 4，收缩：
  移出 nums[0]=1，left = 1
  [2, 4, 6]，差 = 4 <= 4，ans = max(3, 3) = 3
```

最终答案为 3。

### 为什么排序后不影响答案？

题目求的是**最长子序列**（不要求连续），子序列保留相对顺序，但"选哪些下标"可以自由决定。我们只关心选出了哪些值，值相同即可，因此排序不影响答案。

## 通用解法模板

排序后，问题退化为标准的不定长滑动窗口：

```python
nums.sort()
left = 0
ans = 0

for right in range(len(nums)):
    # 窗口不合法：最大值与最小值之差超过 2k
    while nums[right] - nums[left] > 2 * k:
        left += 1
    ans = max(ans, right - left + 1)
```

注意这里不需要哈希表来记录窗口状态，因为排序后窗口的最小值始终是 `nums[left]`，最大值始终是 `nums[right]`，合法性判断只需 `O(1)` 的减法。

## 代码实现

### 暴力法 Python

```python
class Solution:
    def maximumBeauty(self, nums: list[int], k: int) -> int:
        ans = 0
        n = len(nums)
        for i in range(n):
            count = 0
            # 枚举所有可能的目标值 x 的范围，实际只需找有多少元素能和 i 合并
            for j in range(n):
                if abs(nums[i] - nums[j]) <= 2 * k:
                    count += 1
            ans = max(ans, count)
        return ans
```

> 暴力法时间复杂度 `O(n^2)`，当 `n = 10^5` 时会超时，仅用于理解题意。

### 暴力法 Rust

```rust
impl Solution {
    pub fn maximum_beauty(nums: Vec<i32>, k: i32) -> i32 {
        let n = nums.len();
        let mut ans = 0;

        for i in 0..n {
            let mut count = 0;
            for j in 0..n {
                if (nums[i] - nums[j]).abs() <= 2 * k {
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
    def maximumBeauty(self, nums: list[int], k: int) -> int:
        nums.sort()
        left = 0
        ans = 0

        for right in range(len(nums)):
            while nums[right] - nums[left] > 2 * k:
                left += 1
            ans = max(ans, right - left + 1)

        return ans
```

### 滑动窗口 Rust

```rust
impl Solution {
    pub fn maximum_beauty(mut nums: Vec<i32>, k: i32) -> i32 {
        nums.sort_unstable();
        let mut left = 0;
        let mut ans = 0;

        for right in 0..nums.len() {
            while nums[right] - nums[left] > 2 * k {
                left += 1;
            }
            ans = ans.max(right - left + 1);
        }

        ans as i32
    }
}
```

> Rust 中使用 `sort_unstable()` 比 `sort()` 更快，因为题目只要求答案，不需要保持相等元素的原始相对顺序。

## 复杂度分析

| 项目 | 复杂度 | 说明 |
| --- | --- | --- |
| 暴力法时间复杂度 | `O(n^2)` | 枚举所有元素对 |
| 滑动窗口时间复杂度 | `O(n log n)` | 排序 `O(n log n)` + 滑动窗口 `O(n)` |
| 空间复杂度 | `O(1)` | 只使用若干指针变量（排序为原地） |

## 易错点提醒

### 1. 合法性条件是 `> 2k` 而不是 `>= 2k`

差值恰好等于 `2k` 时仍然合法（可以让最小值替换成 `min + k`，最大值替换成 `max - k`，两者相等）。写成 `>= 2k` 会丢失边界情况。

### 2. 一定要先排序

滑动窗口能正确工作的前提是：排序后 `nums[right]` 是当前窗口内的最大值，`nums[left]` 是最小值。不排序则无法保证这一点。

### 3. 这里不需要哈希表

与第 3、3090 题不同，这道题的窗口状态只需要比较两端的值，不需要维护频次统计。排序后 `nums[right] - nums[left]` 就是窗口内的极差，直接用即可。

### 4. Rust 中优先使用 `sort_unstable`

对于只需排序结果而不需要稳定性的场景，`sort_unstable` 在实践中通常更快，且是 Rust 竞赛中的惯用写法。

## 小结

| 方法 | 时间复杂度 | 空间复杂度 | 是否推荐提交 |
| --- | --- | --- | --- |
| 暴力法 | `O(n^2)` | `O(1)` | 否，会超时 |
| 排序 + 滑动窗口 | `O(n log n)` | `O(1)` | 是 |

这道题最有价值的地方不是滑动窗口本身，而是**题意转化**的这一步：

**把"最多有多少元素能被替换成同一个值"转化为"排序后最长的一段，使得极差不超过 2k"。**

一旦完成这个转化，滑动窗口只是常规工具。很多看似复杂的题目，真正的难点都在"转化"，而不是"算法"。
