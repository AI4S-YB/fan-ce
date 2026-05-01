<script lang="tsx">
import type { ColumnType } from 'ant-design-vue/lib/table/interface';

import type { PropType } from 'vue';

import type { BasicColumn } from '../types/table';

import { computed, defineComponent } from 'vue';

import BasicHelp from '#/components/Basic/src/BasicHelp.vue';
import { useDesign } from '#/utils/vbenModle';

import EditTableHeaderCell from './EditTableHeaderIcon.vue';

export default defineComponent({
  name: 'TableHeaderCell',
  components: {
    EditTableHeaderCell,
    BasicHelp,
  },
  props: {
    column: {
      type: Object as PropType<ColumnType<any>>,
      default: () => ({}),
    },
  },
  setup(props) {
    const { prefixCls } = useDesign('basic-table-header-cell');

    const getIsEdit = computed(() => !!(props.column as BasicColumn)?.edit);
    const getTitle = computed(() => {
      const column = props.column as BasicColumn;
      if (typeof column.customHeaderRender === 'function')
        return column.customHeaderRender(column);

      return column?.customTitle || props.column?.title;
    });
    const getHelpMessage = computed(
      () => (props.column as BasicColumn)?.helpMessage,
    );

    return () => {
      return (
        <div>
          {getIsEdit.value ? (
            <EditTableHeaderCell>{getTitle.value}</EditTableHeaderCell>
          ) : (
            <span class="default-header-cell">{getTitle.value}</span>
          )}
          {getHelpMessage.value && (
            <BasicHelp
              class={`${prefixCls}__help`}
              text={getHelpMessage.value}
            />
          )}
        </div>
      );
    };
  },
});
</script>

<style lang="less">
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-basic-table-header-cell';

.@{prefix-cls} {
  &__help {
    margin-left: 8px;
    color: rgb(0 0 0 / 65%) !important;
  }
}
</style>
