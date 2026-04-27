<script setup>
import { Bot, CornerDownLeft, LoaderCircle, User } from "lucide-vue-next";

defineProps({
  messages: { type: Array, default: () => [] },
  chatInput: { type: String, default: "" },
  chatPending: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["update:chatInput", "send"]);
</script>

<template>
  <section class="panel chat-panel">
    <div class="panel-header">
      <div>
        <div class="panel-tag">SOURCE Q&A</div>
        <h2>交互式问答</h2>
      </div>
      <div class="status-chip" :data-state="disabled ? 'idle' : 'ready'">
        {{ disabled ? "等待项目" : "可提问" }}
      </div>
    </div>

    <div class="chat-stream">
      <div
        v-for="(message, index) in messages"
        :key="index"
        class="chat-message"
        :data-role="message.role"
      >
        <div class="avatar">
          <Bot v-if="message.role === 'assistant'" :size="16" />
          <User v-else :size="16" />
        </div>
        <div class="bubble">{{ message.content }}</div>
      </div>
    </div>

    <div class="chat-box">
      <textarea
        :value="chatInput"
        rows="4"
        :disabled="disabled || chatPending"
        placeholder="例如：这个项目的主入口在哪里？配置是怎么加载的？"
        @input="emit('update:chatInput', $event.target.value)"
        @keydown.ctrl.enter.prevent="emit('send')"
      />
      <button class="primary-btn" :disabled="disabled || chatPending || !chatInput.trim()" @click="emit('send')">
        <LoaderCircle v-if="chatPending" class="spin" :size="18" />
        <CornerDownLeft v-else :size="16" />
        <span>{{ chatPending ? "回答中" : "发送问题" }}</span>
      </button>
    </div>
  </section>
</template>
