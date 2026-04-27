<script setup>
import { computed, onBeforeUnmount, onMounted } from "vue";
import { Github, LibraryBig, SquareTerminal } from "lucide-vue-next";

import ChatPanel from "./components/ChatPanel.vue";
import ProgressTimeline from "./components/ProgressTimeline.vue";
import RepoInputPanel from "./components/RepoInputPanel.vue";
import ReportViewer from "./components/ReportViewer.vue";
import { useAppStore } from "./stores/app";

const store = useAppStore();

onMounted(() => {
  store.loadRecentRepos();
});

onBeforeUnmount(() => {
  if (store.eventSource) {
    store.eventSource.close();
  }
});

const repoMeta = computed(() => {
  if (!store.currentRepo) return [];
  return [
    { label: "仓库名", value: store.currentRepo.repo_name, icon: Github },
    { label: "分支", value: store.currentRepo.default_branch || "-", icon: LibraryBig },
    { label: "提交", value: store.currentRepo.last_commit?.slice(0, 10) || "-", icon: SquareTerminal },
  ];
});
</script>

<template>
  <main class="page-shell">
    <div class="ambient-grid" />
    <section class="content-grid">
      <div class="left-rail">
        <RepoInputPanel
          :repo-url="store.repoUrl"
          :analyzing="store.analyzing"
          :current-repo="store.currentRepo"
          :error="store.error"
          @update:repo-url="store.repoUrl = $event"
          @analyze="store.analyzeRepository(false)"
          @refresh="store.analyzeRepository(true)"
        />

        <ProgressTimeline :current-repo="store.currentRepo" :events="store.progressEvents" />

        <section class="panel recent-panel">
          <div class="panel-header">
            <div>
              <div class="panel-tag">CACHE</div>
              <h2>最近分析</h2>
            </div>
          </div>
          <button
            v-for="item in store.recentRepos"
            :key="item.id"
            class="recent-item"
            @click="store.openRecentRepository(item)"
          >
            <strong>{{ item.repo_name }}</strong>
            <span>{{ item.latest_summary || item.normalized_url }}</span>
          </button>
          <div v-if="store.recentRepos.length === 0" class="empty-tip">这里会缓存已经分析过的仓库。</div>
        </section>
      </div>

      <div class="center-rail">
        <section class="panel meta-panel">
          <div class="panel-header">
            <div>
              <div class="panel-tag">REPOSITORY SNAPSHOT</div>
              <h2>{{ store.currentRepo?.repo_name || "等待项目" }}</h2>
            </div>
          </div>
          <div class="meta-grid">
            <div v-for="item in repoMeta" :key="item.label" class="meta-card">
              <component :is="item.icon" :size="18" />
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>

        <ReportViewer :current-repo="store.currentRepo" />
      </div>

      <div class="right-rail">
        <ChatPanel
          :messages="store.chatMessages"
          :chat-input="store.chatInput"
          :chat-pending="store.chatPending"
          :disabled="!store.currentRepo || store.currentRepo.status !== 'completed'"
          @update:chat-input="store.chatInput = $event"
          @send="store.sendChat()"
        />
      </div>
    </section>
  </main>
</template>
