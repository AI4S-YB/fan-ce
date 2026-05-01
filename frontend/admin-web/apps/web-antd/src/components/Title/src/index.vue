<script setup lang="ts">
defineProps({
  title: {
    type: String,
    required: true,
  },
  lineColor: {
    type: String,
    default: 'hsl(var(--primary))',
  },
  lineWidth: {
    type: Number,
    default: 4,
  },
});
</script>

<template>
  <div class="title-container">
    <div
      class="title-line"
      :style="{
        backgroundColor: lineColor,
        width: `${lineWidth}px`,
      }"
    ></div>
    <h3 class="title-text">{{ title }}</h3>
  </div>
</template>

<style scoped>
.title-container {
  display: flex;
  gap: 5px;
  align-items: center;
  margin-bottom: 5px;
  background-color: #e8f3ff;
}

.title-line {
  width: 2px;
  height: 28px;
  border-radius: 1px;
}

.title-text {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: rgb(0 0 0 / 85%);
}
</style>
