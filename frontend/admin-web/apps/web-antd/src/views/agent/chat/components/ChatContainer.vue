<template>
  <div class="agent-chat">
    <div class="agent-chat__panels">
      <section class="agent-chat__panel agent-chat__panel--output">
        <slot name="output"></slot>
      </section>
      <section class="agent-chat__panel agent-chat__panel--execution">
        <slot name="execution"></slot>
      </section>
    </div>
    <div class="agent-chat__input">
      <slot name="input"></slot>
    </div>
  </div>
</template>

<style scoped>
.agent-chat {
  display: flex;
  flex: 1 1 0%;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  height: 100%;
  padding: 16px;
  overflow: hidden;
  background-color: var(--ant-color-bg-layout, #f5f5f5);
}

.agent-chat__panels {
  display: flex;
  flex: 1;
  gap: 16px;
  min-height: 0;
  max-height: calc(100vh - 190px);
  overflow: hidden;
}

.agent-chat__panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background-color: var(--ant-color-bg-container, #fff);
  border-radius: 16px;
  box-shadow: 0 2px 8px rgb(0 0 0 / 8%);
}

.agent-chat__panel--output {
  border: 1px solid var(--ant-color-border-secondary, #e5e5e5);
}

.agent-chat__panel--execution {
  border: 1px solid var(--ant-color-border, #d9d9d9);
}

.agent-chat__input {
  flex-shrink: 0;
  padding: 16px;
  background-color: var(--ant-color-bg-container, #fff);
  border: 1px solid var(--ant-color-border-secondary, #e5e5e5);
  border-radius: 12px;
  box-shadow: 0 1px 4px rgb(0 0 0 / 5%);
}
</style>
