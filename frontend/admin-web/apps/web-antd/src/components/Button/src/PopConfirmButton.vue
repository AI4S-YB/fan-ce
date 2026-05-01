<script lang="ts">
import { computed, defineComponent, h, unref } from 'vue';

import { Popconfirm } from 'ant-design-vue';
import { omit } from 'lodash-es';

import { useAttrs } from '#/hooks/core/useAttrs';
import { $t as t } from '#/locales';
import { extendSlots } from '#/utils/helper/tsxHelper';

import BasicButton from './BasicButton.vue';

const props = {
  /**
   * Whether to enable the drop-down menu
   * @default: true
   */
  enable: {
    type: Boolean,
    default: true,
  },
};

export default defineComponent({
  name: 'PopButton',
  inheritAttrs: false,
  props,
  setup(props, { slots }) {
    const attrs = useAttrs();

    // get inherit binding value
    const getBindValues = computed(() => {
      return Object.assign(
        {
          okText: t('common.okText'),
          cancelText: t('common.cancelText'),
        },
        { ...props, ...unref(attrs) },
      );
    });

    return () => {
      const bindValues = omit(unref(getBindValues), 'icon');
      const btnBind = omit(bindValues, 'title') as Recordable;
      if (btnBind.disabled) btnBind.color = '';
      const Button = h(BasicButton, btnBind, extendSlots(slots));

      // If it is not enabled, it is a normal button
      if (!props.enable) return Button;

      return h(Popconfirm, bindValues, { default: () => Button });
    };
  },
});
</script>
