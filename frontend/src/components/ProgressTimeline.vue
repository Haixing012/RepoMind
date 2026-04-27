<script setup>
defineProps({
  currentRepo: { type: Object, default: null },
  events: { type: Array, default: () => [] },
});
</script>

<template>
  <section class="panel timeline-panel">
    <div class="panel-header">
      <div>
        <div class="panel-tag">RUN STATUS</div>
        <h2>分析进度</h2>
      </div>
      <div class="status-chip" :data-state="currentRepo?.status || 'idle'">
        {{ currentRepo?.status || "idle" }}
      </div>
    </div>

    <div class="progress-track">
      <div class="progress-bar" :style="{ width: `${Math.round((currentRepo?.progress || 0) * 100)}%` }" />
    </div>

    <div class="progress-metrics">
      <strong>{{ Math.round((currentRepo?.progress || 0) * 100) }}%</strong>
      <span>{{ currentRepo?.current_step || "等待任务" }}</span>
    </div>

    <div class="timeline-list">
      <div
        v-for="(event, index) in events.slice().reverse()"
        :key="`${event.step}-${index}`"
        class="timeline-item"
      >
        <div class="timeline-dot" />
        <div>
          <div class="timeline-step">{{ event.step }}</div>
          <div class="timeline-detail">{{ event.detail || "处理中" }}</div>
        </div>
      </div>

      <div v-if="events.length === 0" class="empty-tip">
        提交仓库后，这里会实时推送分析阶段。
      </div>
    </div>
  </section>
</template>
