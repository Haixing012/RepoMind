<script setup>
import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";
import { computed } from "vue";

const props = defineProps({
  currentRepo: { type: Object, default: null },
});

hljs.registerLanguage("bash", bash);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("js", javascript);
hljs.registerLanguage("json", json);
hljs.registerLanguage("python", python);
hljs.registerLanguage("py", python);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("ts", typescript);
hljs.registerLanguage("vue", xml);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("yml", yaml);

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(code, language) {
    if (language && hljs.getLanguage(language)) {
      return `<pre class="hljs"><code>${hljs.highlight(code, { language }).value}</code></pre>`;
    }
    return `<pre class="hljs"><code>${markdown.utils.escapeHtml(code)}</code></pre>`;
  },
});

function normalizeReportMarkdown(source) {
  const text = (source || "").trim();
  const fenced = text.match(/^```(?:markdown|md)?\s*\n([\s\S]*?)\n```$/i);
  return fenced ? fenced[1].trim() : text;
}

const reportSource = computed(() =>
  normalizeReportMarkdown(
    props.currentRepo?.report_markdown ||
      "## 等待报告\n\n分析完成后，这里会展示目录结构、核心模块、调用链和阅读建议。",
  ),
);

const reportHtml = computed(() => DOMPurify.sanitize(markdown.render(reportSource.value)));
</script>

<template>
  <section class="panel report-panel">
    <div class="panel-header">
      <div>
        <div class="panel-tag">REPORT</div>
        <h2>源码解读报告</h2>
      </div>
      <div class="stack-chips">
        <span v-for="item in currentRepo?.tech_stack || []" :key="item">{{ item }}</span>
      </div>
    </div>

    <div class="summary-card">
      <div class="summary-label">TL;DR</div>
      <p>{{ currentRepo?.latest_summary || "先提交一个仓库，系统会生成项目摘要。" }}</p>
    </div>

    <article class="markdown-body" v-html="reportHtml" />
  </section>
</template>
