<script setup>
import { LoaderCircle, RefreshCw, Search } from "lucide-vue-next";

defineProps({
  repoUrl: { type: String, required: true },
  analyzing: { type: Boolean, required: true },
  currentRepo: { type: Object, default: null },
  error: { type: String, default: "" },
});

const emit = defineEmits(["update:repoUrl", "analyze", "refresh"]);
</script>

<template>
  <section class="panel hero-panel">
    <div class="panel-tag">PROJECT LEARNING ASSISTANT</div>
    <div class="hero-copy">
      <h1>把任意开源项目讲明白。</h1>
      <p>
        输入 GitHub 仓库地址，系统会自动克隆源码、生成完整阅读报告，并提供可以自己查文件的源码问答助手。
      </p>
    </div>

    <div class="repo-form">
      <label class="field">
        <span>GitHub 仓库地址</span>
        <div class="field-shell">
          <Search :size="18" />
          <input
            :value="repoUrl"
            type="url"
            placeholder="https://github.com/owner/repo"
            @input="emit('update:repoUrl', $event.target.value)"
          />
        </div>
      </label>

      <div class="field-actions">
        <button class="primary-btn" :disabled="analyzing || !repoUrl" @click="emit('analyze')">
          <LoaderCircle v-if="analyzing" class="spin" :size="18" />
          <span>{{ analyzing ? "分析中" : "开始分析" }}</span>
        </button>
        <button
          class="ghost-btn"
          :disabled="analyzing || !currentRepo"
          @click="emit('refresh')"
        >
          <RefreshCw :size="16" />
          <span>强制重跑</span>
        </button>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
    </div>
  </section>
</template>
