<script setup lang="ts">
const emit = defineEmits<{ click: [] }>();
</script>
<template>
  <div
    @click="emit('click')"
    style="position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;
           background:#409eff;color:#fff;display:flex;align-items:center;justify-content:center;
           cursor:pointer;box-shadow:0 4px 12px rgba(64,158,255,0.4);z-index:1000;
           font-size:24px;transition:transform 0.2s;"
    title="AI Assistant"
  >
    💬
  </div>
</template>
