import { defineStore } from "pinia";

const API_BASE = "http://127.0.0.1:8000/api";

export const useAppStore = defineStore("app", {
  state: () => ({
    repoUrl: "",
    analyzing: false,
    currentRepo: null,
    progressEvents: [],
    recentRepos: [],
    eventSource: null,
    chatMessages: [],
    chatPending: false,
    chatInput: "",
    error: "",
  }),
  actions: {
    async loadRecentRepos() {
      try {
        const response = await fetch(`${API_BASE}/repos`);
        this.recentRepos = await response.json();
      } catch (error) {
        console.error(error);
      }
    },
    async analyzeRepository(forceRefresh = false) {
      this.error = "";
      this.analyzing = true;
      this.progressEvents = [];
      this.chatMessages = [];

      try {
        const response = await fetch(`${API_BASE}/repos/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            repo_url: this.repoUrl,
            force_refresh: forceRefresh,
          }),
        });
        if (!response.ok) {
          throw new Error("分析任务创建失败");
        }
        this.currentRepo = await response.json();
        this.chatMessages = [
          {
            role: "assistant",
            content: "分析完成后，你可以直接问我这个项目怎么启动、某个模块做了什么，或者先从哪里看代码。",
          },
        ];
        this.attachEventSource(this.currentRepo.id);
        await this.loadRecentRepos();
      } catch (error) {
        this.error = error.message || "请求失败";
        this.analyzing = false;
      }
    },
    attachEventSource(repositoryId) {
      if (this.eventSource) {
        this.eventSource.close();
      }
      const source = new EventSource(`${API_BASE}/repos/${repositoryId}/events`);
      source.addEventListener("progress", async (event) => {
        const payload = JSON.parse(event.data);
        this.progressEvents = [...this.progressEvents, payload].slice(-18);
        if (this.currentRepo) {
          this.currentRepo = {
            ...this.currentRepo,
            status: payload.status,
            progress: payload.progress,
            current_step: payload.step,
          };
        }
        if (payload.status === "completed" || payload.status === "failed") {
          this.analyzing = false;
          await this.refreshCurrentRepository();
          source.close();
        }
      });
      source.onerror = () => {
        source.close();
      };
      this.eventSource = source;
    },
    async refreshCurrentRepository() {
      if (!this.currentRepo?.id) return;
      const response = await fetch(`${API_BASE}/repos/${this.currentRepo.id}`);
      if (!response.ok) return;
      this.currentRepo = await response.json();
      await this.loadRecentRepos();
    },
    async openRecentRepository(repository) {
      this.repoUrl = repository.repo_url;
      this.currentRepo = repository;
      this.progressEvents = [];
      this.chatMessages = [
        {
          role: "assistant",
          content: "这个项目已经有缓存报告了。你可以继续提问，我会按需去读源码。",
        },
      ];
      if (repository.status !== "completed") {
        this.attachEventSource(repository.id);
      } else {
        this.analyzing = false;
        await this.refreshCurrentRepository();
      }
    },
    async sendChat() {
      if (!this.currentRepo?.id || !this.chatInput.trim() || this.chatPending) return;
      const question = this.chatInput.trim();
      this.chatInput = "";
      this.chatPending = true;
      this.chatMessages.push({ role: "user", content: question });
      const assistantMessage = { role: "assistant", content: "" };
      this.chatMessages.push(assistantMessage);

      try {
        const response = await fetch(`${API_BASE}/repos/${this.currentRepo.id}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        });
        if (!response.ok || !response.body) {
          throw new Error("问答请求失败");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          assistantMessage.content += decoder.decode(value, { stream: true });
        }
      } catch (error) {
        assistantMessage.content = `问答失败：${error.message || "未知错误"}`;
      } finally {
        this.chatPending = false;
      }
    },
  },
});
