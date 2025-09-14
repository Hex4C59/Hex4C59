+++
title = "Python函数的一些思考"
date = 2025-09-14T11:08:49+08:00
draft = true
Toc = true
author = "Hex4C59"
tags = ["Python", "编程"]
+++

我一般用Python写深度学习项目，用到最多的就是for循环遍历列表，但我一般是用AI辅助编程，对于AI生成的代码我只会大致理解其意思，并没有深入思考其本质。这些AI产生的代码使我不安，我写这篇博客主要目的是通过对Python里一些常用函数用法的思考来加深对编程的理解。

### 一、`os.walk()`是什么

`os.walk()` 是Python`os`模块中用于**遍历目录树**的函数。它会递归地生成某个目录下所有子目录和文件的信息，适合做文件搜索、批量处理等操作。

### 二、函数签名

**函数签名**指的是函数的**名字 + 参数信息**（包括参数个数、顺序、名称、类型、默认值等），有时还包括返回值类型。它描述了调用函数所需的接口。换句话，函数前面就是函数的**“名片”**，让别人知道如何使用这个函数，而不需要关心函数内部是怎么实现的。

在Python中，签名主要包含函数名、参数，可选地包括类型注解和返回值类型。

在Python里，一个函数签名长这样:

```Python
def add(a: int, b: int = 0) -> int:
    return a + b
```

签名部分是这样的：

```Python
def add(a: int, b: int = 0) -> int
```

回到原来的话题，os.walk()函数的签名如下：

```Python
os.walk(top, topdown=True, onerror=None, followlinks=False)
```

- `top` 要遍历的目录路径（字符串类型）
- `topdown`（默认`True`）
  - `True`: 先返回当前目录，再返回子目录（自顶向下遍历）。
  - `False`：先返回子目录，再返回当前目录（自低向上遍历）。
- `onerror` 出现错误时的回调函数，一般用不到。
- `followlinks` （默认`False`）
  
    是否跟随符号链接（symlink）。如果设为`True`，可能会出现无限递归循环。

### 三、返回值

`os.walk()` 返回一个 **生成器**，每次迭代会得到一个三元组：

```Python
(dirpath,dirnames,filenames)
```

- `dirpath`: 当前遍历到的目录路径（字符串）
- `dirnames`: 当前目录下的所有子目录名（列表）。
- `filenames`：当前目录下的所有子文件名（列表）。
  
### 四、基本用法

项目结构如下所示

```txt
processed_data
├── normal_data
│   ├── group_one
│   │   ├── table_one_normal.xlsx
│   │   ├── table_three_normal.xlsx
│   │   └── table_two_normal.xlsx
│   ├── group_three
│   │   ├── table_one_normal.xlsx
│   │   ├── table_three_normal.xlsx
│   │   └── table_two_normal.xlsx
│   └── group_two
│       ├── table_one_normal.xlsx
│       ├── table_three_normal.xlsx
│       └── table_two_normal.xlsx
└── patient
    ├── group_one
    │   ├── table_one.xlsx
    │   ├── table_three.xlsx
    │   └── table_two.xlsx
    ├── group_three
    │   ├── table_one.xlsx
    │   ├── table_three.xlsx
    │   └── table_two.xlsx
    └── group_two
        ├── table_one.xlsx
        ├── table_three.xlsx
        └── table_two.xlsx
```

我的遍历文件的代码如下:

```Python
for dirpath, dirnames, filenames in os.walk(root_dir):
    print("当前目录路径:", dirpath)
    print("子目录列表:", dirnames)
    print("文件列表:", filenames)
```

这是第一种写法，当我运行完脚本后得到的结果如下：

```txt
当前目录路径: ./processed_data/patient
子目录列表: ['group_one', 'group_three', 'group_two']
文件列表: []
当前目录路径: ./processed_data/patient/group_one
子目录列表: []
文件列表: ['table_two.xlsx', 'table_one.xlsx', 'table_three.xlsx']
当前目录路径: ./processed_data/patient/group_three
子目录列表: []
文件列表: ['table_two.xlsx', 'table_one.xlsx', 'table_three.xlsx']
当前目录路径: ./processed_data/patient/group_two
子目录列表: []
文件列表: ['table_two.xlsx', 'table_one.xlsx', 'table_three.xlsx']
```

从结果可以看到，一开始遍历时，dirpath代表是要遍历的根路径（root_dir），然后dirnames代表的是根路径下的子目录，这是一个列表，filenames应该是这个根目录下包含的文件，但当前根目录下只有子目录，没有文件，所以它是空的。

然后这个函数会一直遍历到包含文件的那个子目录，这时dirpath就代表的是包含最靠近文件的那个目录，dirname为空了（因为目录下没有其他目录了），filenames是目录下文件名的列表。

所以虽然是返回的的是三元组，但其实只表示两层含义：根目录及其子目录，或者根目录及其子文件。
