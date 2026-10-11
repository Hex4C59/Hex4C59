+++
title = "智能体工程模式 03：积累你已经掌握的实现方法"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 介绍如何积累经过运行验证的代码示例，并让编程智能体组合和复用这些示例，以浏览器中的 PDF OCR 工具为例。"
summary = "把已经做成的事情连同可运行代码记录下来。它们既能帮助开发者判断技术能做到什么，也能作为编程智能体构建新工具的参考。"
tags = ["Agent", "智能体工程", "编程智能体", "代码复用", "OCR"]
categories = ["Translations"]
topics = ["agents", "agentic-engineering", "coding-agents", "code-reuse", "ocr"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 4
series_label = "积累你已经掌握的实现方法"
series_part = "基本原则"
series_number = 3
original_title = "Hoard things you know how to do"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/hoard-things-you-know-how-to-do/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
+++

> **译文信息**
>
> - 原文：[Hoard things you know how to do](https://simonwillison.net/guides/agentic-engineering-patterns/hoard-things-you-know-how-to-do/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。正文中的「我」、项目经历和效果判断均指原作者。示例代码保留原文版本，译者未执行；第二段代码依赖原页面中的元素和变量，不能独立运行。提示词中的本地路径属于作者的示例环境。

我分享的许多与编程智能体高效协作的技巧，其实是把过去职业生涯中行之有效的建议，延伸到了智能体的使用上。下面就是一个很好的例子：积累你已经掌握的实现方法。

开发软件的一项重要能力，是知道什么能做到、什么做不到，并且至少大致了解怎样才能做到。

这类问题既可能很宽泛，也可能相当冷门。网页能只用 JavaScript 完成光学字符识别（Optical Character Recognition，OCR）吗？iPhone 应用在没有运行时，也能与蓝牙设备配对吗？能不能用 Python 处理一个 100 GB 的 JSON 文件，而不先把整个文件载入内存？

你掌握的这类问题的答案越多，就越有可能发现机会，用别人尚未想到的方式，以技术解决问题。

要对这些答案有把握，最好的方法就是亲眼看到代码运行起来，证明它们可行。知道一件事在理论上做得到，与亲眼见过它被实现，并不是一回事。作为软件专业人士，值得积累的一项重要资产，就是大量这类问题的答案，以及证明这些答案的实例。

我用几种不同的方式收集这样的解决方案。我的[博客](https://simonwillison.net/)和 [TIL 博客](https://til.simonwillison.net/)里，记录了许多我摸索出来的实现方法。TIL 是 Today I Learned 的缩写，也就是「今天学到了什么」。我还有[一千多个 GitHub 仓库](https://github.com/simonw)，收集了为不同项目编写的代码，其中许多都是演示某个关键想法的小型概念验证。

最近，我也开始用大语言模型（Large Language Models，LLM）帮助自己积累更多代码方案，解决有趣的问题。

[tools.simonwillison.net](https://tools.simonwillison.net/) 是我最大的 LLM 辅助工具与原型集合。我用它收集自己所说的 [HTML 工具](https://simonwillison.net/2025/Dec/10/html-tools/)：在单个 HTML 页面中嵌入 JavaScript 和 CSS，用来解决一个具体问题。

我的 [simonw/research](https://github.com/simonw/research) 仓库则包含更大、更复杂的案例。在这些案例中，我让编程智能体研究一个问题，拿出能够运行的代码，并写一份报告，详细说明它发现了什么。

## 重新组合已有积累

为什么要收集所有这些东西？除了帮助你培养和拓展自己的能力，过程中积累的材料还能成为编程智能体很有用的输入。

我最喜欢的一种提示词用法，就是让智能体把两个或更多已经能正常工作的示例组合起来，做出一个新东西。

有一个项目让我清楚地认识到这种做法有多有效：它是我最早加入工具集的项目，一个在浏览器中运行的 [OCR 工具](https://tools.simonwillison.net/ocr)。我在[这篇文章中](https://simonwillison.net/2024/Mar/30/ocr-pdfs-images/)更详细地介绍了它。

我想要一个简单易用的浏览器工具，能够识别 PDF 页面中的文字，尤其是那些完全由扫描图像组成、根本没有文本版本的 PDF。

此前，我尝试过在浏览器中运行 [Tesseract.js OCR 库](https://tesseract.projectnaptha.com/)，发现它的能力很强。这个库提供了成熟的 Tesseract OCR 引擎的 WebAssembly 版本，让你可以从 JavaScript 中调用它，提取图像里的文字。WebAssembly 是一种可在浏览器中执行的二进制格式，使这类引擎能够在网页中运行。

但我想处理的是 PDF，而不是图像。这时，我想起自己也用过 Mozilla 的 [PDF.js](https://mozilla.github.io/pdf.js/) 库。它的功能之一，就是把 PDF 的每一页渲染成图像。

我的笔记中，恰好保存了使用这两个库的 JavaScript 代码片段。

下面是我交给模型的完整提示词，当时使用的是 Claude 3 Opus。它把两个示例放在一起，并描述了我想要的结果：

> 以下代码演示如何打开一个 PDF，并把每一页转换成一张图像：

```html
<!DOCTYPE html>
<html>
<head>
  <title>PDF to Images</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.9.359/pdf.min.js"></script>
  <style>
    .image-container img {
      margin-bottom: 10px;
    }
    .image-container p {
      margin: 0;
      font-size: 14px;
      color: #888;
    }
  </style>
</head>
<body>
  <input type="file" id="fileInput" accept=".pdf" />
  <div class="image-container"></div>

  <script>
  const desiredWidth = 800;
    const fileInput = document.getElementById('fileInput');
    const imageContainer = document.querySelector('.image-container');

    fileInput.addEventListener('change', handleFileUpload);

    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.9.359/pdf.worker.min.js';

    async function handleFileUpload(event) {
      const file = event.target.files[0];
      const imageIterator = convertPDFToImages(file);

      for await (const { imageURL, size } of imageIterator) {
        const imgElement = document.createElement('img');
        imgElement.src = imageURL;
        imageContainer.appendChild(imgElement);

        const sizeElement = document.createElement('p');
        sizeElement.textContent = `Size: ${formatSize(size)}`;
        imageContainer.appendChild(sizeElement);
      }
    }

    async function* convertPDFToImages(file) {
      try {
        const pdf = await pdfjsLib.getDocument(URL.createObjectURL(file)).promise;
        const numPages = pdf.numPages;

        for (let i = 1; i <= numPages; i++) {
          const page = await pdf.getPage(i);
          const viewport = page.getViewport({ scale: 1 });
          const canvas = document.createElement('canvas');
          const context = canvas.getContext('2d');
          canvas.width = desiredWidth;
          canvas.height = (desiredWidth / viewport.width) * viewport.height;
          const renderContext = {
            canvasContext: context,
            viewport: page.getViewport({ scale: desiredWidth / viewport.width }),
          };
          await page.render(renderContext).promise;
          const imageURL = canvas.toDataURL('image/jpeg', 0.8);
          const size = calculateSize(imageURL);
          yield { imageURL, size };
        }
      } catch (error) {
        console.error('Error:', error);
      }
    }

    function calculateSize(imageURL) {
      const base64Length = imageURL.length - 'data:image/jpeg;base64,'.length;
      const sizeInBytes = Math.ceil(base64Length * 0.75);
      return sizeInBytes;
    }

    function formatSize(size) {
      const sizeInKB = (size / 1024).toFixed(2);
      return `${sizeInKB} KB`;
    }
  </script>
</body>
</html>

```

> 以下代码演示如何对图像进行 OCR：

```javascript
async function ocrMissingAltText() {
    // Load Tesseract
    var s = document.createElement("script");
    s.src = "https://unpkg.com/tesseract.js@v2.1.0/dist/tesseract.min.js";
    document.head.appendChild(s);

    s.onload = async () => {
      const images = document.getElementsByTagName("img");
      const worker = Tesseract.createWorker();
      await worker.load();
      await worker.loadLanguage("eng");
      await worker.initialize("eng");
      ocrButton.innerText = "Running OCR...";

      // Iterate through all the images in the output div
      for (const img of images) {
        const altTextarea = img.parentNode.querySelector(".textarea-alt");
        // Check if the alt textarea is empty
        if (altTextarea.value === "") {
          const imageUrl = img.src;
          var {
            data: { text },
          } = await worker.recognize(imageUrl);
          altTextarea.value = text; // Set the OCR result to the alt textarea
          progressBar.value += 1;
        }
      }

      await worker.terminate();
      ocrButton.innerText = "OCR complete";
    };
  }

```

> 请利用这些示例，组合出一个内嵌 HTML、CSS 和 JavaScript 的单页工具。页面上要有一个大的正方形区域，用户可以把 PDF 文件拖放进去。文件放入后，把 PDF 的每一页转换成 JPEG，并显示在页面下方；随后使用 Tesseract 进行 OCR，把识别结果放在每张图像下方的文本框（textarea）中。

这次效果非常好！模型生成了一个概念验证页面，完全满足了我的需求。

之后，我又[和模型迭代了几次](https://gist.github.com/simonw/6a9f077bf8db616e44893a24ae1d36eb)，才得到最终版本。不过，只用了几分钟，我就做出了一个实用的工具，此后一直受益于它。

## 编程智能体让这种方法更加强大

这个 OCR 示例是我在 2024 年 3 月做的，距离 Claude Code 首次发布还有将近一年。编程智能体的出现，让收集可运行示例这件事变得更有价值。

如果你的编程智能体可以访问互联网，就可以让它做这样的事情：

> 使用 curl 获取 https://tools.simonwillison.net/ocr 和 https://tools.simonwillison.net/gemini-bbox 的源代码，然后构建一个新工具：让我从 PDF 中选择一页，把它传给 Gemini，并返回这一页中插图的边界框，也就是标出插图位置的矩形区域。

（我在这里明确指定 curl，是因为 Claude Code 默认会使用 WebFetch 工具，它会总结页面内容，而不是返回原始 HTML。）

编程智能体很擅长搜索，因此你可以让它在自己的计算机上运行，并告诉它去哪里寻找你希望它参考的示例：

> 为 `~/dev/ecosystem/datasette-oauth` 项目添加使用模拟 HTTP 请求的测试，参考 `~/dev/ecosystem/llm-mistral` 中的做法。

通常这样就够了。智能体会启动一个搜索子智能体来调查，并带回完成任务所需的具体信息。

由于我的许多研究代码都是公开的，我经常让编程智能体把仓库克隆到 `/tmp`，再作为输入参考：

> 从 GitHub 把 simonw/research 克隆到 `/tmp`，找到将 Rust 编译为 WebAssembly 的示例，再参考这些示例，为当前项目构建一个演示用的 HTML 页面。

这里的核心想法是：有了编程智能体，一项有用的技巧只需要摸索成功一次。只要把它记录下来，并附上能够运行的代码示例，智能体就能查阅这个示例，将它用于解决今后任何类似的项目。

---

[上一篇原文：如今，编写代码的成本已经很低](https://simonwillison.net/guides/agentic-engineering-patterns/code-is-cheap/) · [下一篇原文：AI 应该帮助我们写出更好的代码](https://simonwillison.net/guides/agentic-engineering-patterns/better-code/)
