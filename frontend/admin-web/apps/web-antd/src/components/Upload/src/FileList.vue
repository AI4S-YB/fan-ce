<script lang="tsx">
import type { CSSProperties } from 'vue';

import { defineComponent, nextTick, watch } from 'vue';

import { useModalContext } from '#/components/Modal/src/hooks/useModalContext';
import { isFunction } from '#/utils/is';

import { fileListProps } from './props';

export default defineComponent({
  name: 'FileList',
  props: fileListProps,
  setup(props) {
    const modalFn = useModalContext();
    watch(
      () => props.dataSource,
      () => {
        nextTick(() => {
          modalFn?.redoModalHeight?.();
        });
      },
    );
    return () => {
      const { columns, actionColumn, dataSource } = props;
      const columnList = [...columns, actionColumn];
      return (
        // x scrollbar
        <div class="overflow-x-auto">
          <table class="file-table">
            <colgroup>
              {columnList.map((item) => {
                const { width = 0, dataIndex } = item;
                const style: CSSProperties = {
                  width: `${width}px`,
                  minWidth: `${width}px`,
                };
                return <col key={dataIndex} style={width ? style : {}} />;
              })}
            </colgroup>
            <thead>
              <tr class="file-table-tr">
                {columnList.map((item) => {
                  const { title = '', align = 'center', dataIndex } = item;
                  return (
                    <th class={['file-table-th', align]} key={dataIndex}>
                      {title}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {dataSource.map((record = {}, index) => {
                return (
                  <tr
                    class="file-table-tr"
                    key={`${index + record.name || ''}`}
                  >
                    {columnList.map((item) => {
                      const {
                        dataIndex = '',
                        customRender,
                        align = 'center',
                      } = item;
                      const render = customRender && isFunction(customRender);
                      return (
                        <td
                          class={['file-table-td break-all', align]}
                          key={dataIndex}
                        >
                          {render
                            ? customRender?.({
                                text: record[dataIndex],
                                record,
                              })
                            : record[dataIndex]}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      );
    };
  },
});
</script>

<style lang="less">
.file-table {
  width: 100%;
  border-collapse: collapse;

  .center {
    text-align: center;
  }

  .left {
    text-align: left;
  }

  .right {
    text-align: right;
  }

  &-th,
  &-td {
    padding: 12px 8px;
  }

  thead {
    background-color: hsv(0, 0, 98%);
  }

  table,
  td,
  th {
    border: 1px solid var(--border-color);
  }
}
</style>
