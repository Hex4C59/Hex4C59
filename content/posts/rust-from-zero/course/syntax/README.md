# 语法细读独立程序

这些程序对应第二、三、四、六到十章的语法细读。每个文件都有自己的 `main`，没有第三方依赖，也没有加入 Cargo 的正常目标。

在下载包的 `rust-course` 中逐个编译。macOS / Linux shell 示例：

```sh
mkdir -p target/syntax
rustc --edition 2024 syntax/syntax02-inference.rs -o target/syntax/inference
./target/syntax/inference
```

PowerShell 示例：

```powershell
New-Item -ItemType Directory -Force target/syntax
rustc --edition 2024 syntax/syntax02-inference.rs -o target/syntax/inference.exe
./target/syntax/inference.exe
```

也可以把一个文件的完整内容复制到自己的 Cargo 项目 `src/main.rs`，分别运行。不要把多个 `main` 拼进同一个入口。下面正常程序的预期输出写在各章正文中；几个程序还包含验证类型或数值的断言。

## 正常程序

| 文件 | 章节 |
| --- | --- |
| `syntax/syntax02-inference.rs` | 第 2 章 |
| `syntax/syntax02-conversion.rs` | 第 2 章 |
| `syntax/syntax03-unit.rs` | 第 3 章 |
| `syntax/syntax03-branches.rs` | 第 3 章 |
| `syntax/syntax03-loop-value.rs` | 第 3 章 |
| `syntax/syntax03-short-circuit.rs` | 第 3 章 |
| `syntax/syntax04-binding-mut.rs` | 第 4 章 |
| `syntax/syntax04-reborrow.rs` | 第 4 章 |
| `syntax/syntax04-shared-copy.rs` | 第 4 章 |
| `syntax/syntax06-pattern-binding.rs` | 第 6 章 |
| `syntax/syntax06-borrow-pattern.rs` | 第 6 章 |
| `syntax/syntax06-ref-and-reference.rs` | 第 6 章 |
| `syntax/syntax06-wildcard.rs` | 第 6 章 |
| `syntax/syntax06-let-else.rs` | 第 6 章 |
| `syntax/syntax07-question-result.rs` | 第 7 章 |
| `syntax/syntax07-question-option.rs` | 第 7 章 |
| `syntax/syntax08-paths.rs` | 第 8 章 |
| `syntax/syntax08-attributes-macros.rs` | 第 8 章 |
| `syntax/syntax09-type-parameters.rs` | 第 9 章 |
| `syntax/syntax09-independent-lifetimes.rs` | 第 9 章 |
| `syntax/syntax09-sized.rs` | 第 9 章 |
| `syntax/syntax10-call-traits.rs` | 第 10 章 |

## 故意失败的程序

从 `rust-course` 运行，例如：

```sh
rustc --edition 2024 --emit=metadata compile-fail/syntax02-mixed.rs
rustc --explain E0308
```

第一条预期失败。语法 2024 edition 的引用模式限制没有单独的错误编号，表中注明本次实际诊断文字；其他诊断的措辞和提示也可能随版本变化。

| 文件 | 预期诊断 |
| --- | --- |
| `compile-fail/syntax02-mixed.rs` | `E0308` |
| `compile-fail/syntax02-reassign.rs` | `E0308` |
| `compile-fail/syntax03-branch-types.rs` | `E0308` |
| `compile-fail/syntax03-condition.rs` | `E0308` |
| `compile-fail/syntax03-while-value.rs` | `E0571` |
| `compile-fail/syntax04-shared-write.rs` | `E0594` |
| `compile-fail/syntax04-reference-move.rs` | `E0382` |
| `compile-fail/syntax06-let-refutable.rs` | `E0005` |
| `compile-fail/syntax06-ref-2024.rs` | `cannot explicitly borrow within an implicitly-borrowing pattern` |
| `compile-fail/syntax06-underscore-name.rs` | `E0382` |
| `compile-fail/syntax06-else-diverge.rs` | `E0308` |
| `compile-fail/syntax07-option-result.rs` | `E0277` |
| `compile-fail/syntax08-private-child.rs` | `E0603` |
| `compile-fail/syntax09-same-type.rs` | `E0308` |
| `compile-fail/syntax09-return-impl.rs` | `E0308` |
| `compile-fail/syntax09-shared-lifetime.rs` | `E0597` |
| `compile-fail/syntax09-implicit-sized.rs` | `E0277` |
| `compile-fail/syntax10-fn-mut.rs` | `E0525` |
| `compile-fail/syntax10-once-move.rs` | `E0382` |
| `compile-fail/syntax10-closure-type.rs` | `E0308` |

2026-10-13 在 macOS arm64、rustc 1.99.0 上从正文提取并验证了这 22 个正常程序和 20 个预期失败的程序。正常程序还通过了编译器警告检查。声明的最低 Rust 1.85、Windows 和 Linux 未在本轮实测。
