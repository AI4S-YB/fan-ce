<script lang="ts" setup>
import { computed, ref, unref, watch, watchEffect } from 'vue';

import { zxcvbn } from '@zxcvbn-ts/core';
import { InputPassword } from 'ant-design-vue';

import { propTypes } from '#/utils/propTypes';
import { useDesign } from '#/utils/vbenModle';

defineOptions({ name: 'StrengthMeter' });

const props = defineProps({
  value: propTypes.string,
  showInput: propTypes.bool.def(true),
  disabled: propTypes.bool,
});
const emit = defineEmits(['score-change', 'change']);

const innerValueRef = ref('');
const { prefixCls } = useDesign('strength-meter');

const getPasswordStrength = computed(() => {
  const { disabled } = props;
  if (disabled) return -1;
  const innerValue = unref(innerValueRef);
  const score = innerValue ? zxcvbn(unref(innerValueRef)).score : -1;
  emit('score-change', score);
  return score;
});

function handleChange(e: ChangeEvent) {
  emit('change', e.target.value);
  innerValueRef.value = e.target.value;
}

watchEffect(() => {
  innerValueRef.value = props.value || '';
});

watch(
  () => unref(innerValueRef),
  (val) => {
    emit('change', val);
  },
);
</script>

<template>
  <div :class="prefixCls" class="relative">
    <InputPassword
      v-if="showInput"
      v-bind="$attrs"
      allow-clear
      :value="innerValueRef"
      :disabled="disabled"
      @change="handleChange"
    >
      <template v-for="item in Object.keys($slots)" #[item]="data">
        <slot :name="item" v-bind="data || {}"></slot>
      </template>
    </InputPassword>
    <div :class="`${prefixCls}-bar`">
      <div
        :class="`${prefixCls}-bar--fill`"
        :data-score="getPasswordStrength"
      ></div>
    </div>
  </div>
</template>

<style lang="less" scoped>
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-strength-meter';
@error-color: 'red';
@warning-color: 'red';
@success-color: 'red';
@disabled-color: 'red';
@white: 'red';
.@{prefix-cls} {
  &-bar {
    position: relative;
    height: 6px;
    margin: 10px auto 6px;
    background-color: @disabled-color;
    border-radius: 6px;

    &::before,
    &::after {
      position: absolute;
      z-index: 10;
      display: block;
      width: 20%;
      height: inherit;
      content: '';
      background-color: transparent;
      border-color: @white;
      border-style: solid;
      border-width: 0 5px;
    }

    &::before {
      left: 20%;
    }

    &::after {
      right: 20%;
    }

    &--fill {
      position: absolute;
      width: 0;
      height: inherit;
      background-color: transparent;
      border-radius: inherit;
      transition:
        width 0.5s ease-in-out,
        background 0.25s;

      &[data-score='0'] {
        width: 20%;
        background-color: @error-color;
      }

      &[data-score='1'] {
        width: 40%;
        background-color: @error-color;
      }

      &[data-score='2'] {
        width: 60%;
        background-color: @warning-color;
      }

      &[data-score='3'] {
        width: 80%;
        background-color: @success-color;
      }

      &[data-score='4'] {
        width: 100%;
        background-color: @success-color;
      }
    }
  }
}
</style>
