<script lang="tsx">
import type { TreeProps } from 'ant-design-vue/es/tree/Tree';

import type { CSSProperties } from 'vue';

import type {
  CheckKeys,
  FieldNames,
  KeyType,
  TreeActionType,
  TreeItem,
  TreeState,
} from './types/tree';

import type { CreateContextOptions } from '#/components/ContextMenu';

import {
  computed,
  defineComponent,
  onMounted,
  reactive,
  ref,
  toRaw,
  unref,
  watch,
  watchEffect,
} from 'vue';

import { Empty, Spin, Tree } from 'ant-design-vue';
import { cloneDeep, difference, get, omit } from 'lodash-es';

import { ScrollContainer } from '#/components/Container';
import { $t } from '@vben/locales';
import { useContextMenu } from '#/hooks/web/useContextMenu';
import { eachTree, filter, treeToList } from '#/utils/helper/treeHelper';
import { extendSlots, getSlot } from '#/utils/helper/tsxHelper';
import { isArray, isBoolean, isEmpty, isFunction } from '#/utils/is';
import { useNamespace } from '#/utils/vben';

import TreeHeader from './components/TreeHeader.vue';
import { useTree } from './hooks/useTree';
import { TreeIcon } from './TreeIcon';
import { treeEmits, treeProps } from './types/tree';

export default defineComponent({
  name: 'BasicTree',
  inheritAttrs: false,
  props: treeProps,
  emits: treeEmits,
  setup(props, { attrs, slots, emit, expose }) {
    const { b } = useNamespace('tree');
    const state = reactive<TreeState>({
      checkStrictly: props.checkStrictly,
      expandedKeys: props.expandedKeys || [],
      selectedKeys: props.selectedKeys || [],
      checkedKeys: props.checkedKeys || [],
    });

    const searchState = reactive({
      startSearch: false,
      searchText: '',
      searchData: [] as TreeItem[],
    });

    const treeDataRef = ref<TreeItem[]>([]);

    const [createContextMenu] = useContextMenu();

    const getFieldNames = computed((): Required<FieldNames> => {
      const { fieldNames } = props;
      return {
        children: 'children',
        title: 'name',
        key: 'id',
        ...fieldNames,
      };
    });

    const {
      deleteNodeByKey,
      insertNodeByKey,
      insertNodesByKey,
      filterByLevel,
      updateNodeByKey,
      getAllKeys,
      getChildrenKeys,
      getEnabledKeys,
      getSelectedNode,
    } = useTree(treeDataRef, getFieldNames);

    const getBindValues = computed(() => {
      const propsData = {
        blockNode: true,
        ...attrs,
        ...props,
        expandedKeys: state.expandedKeys,
        selectedKeys: state.selectedKeys,
        checkedKeys: state.checkedKeys,
        checkStrictly: state.checkStrictly,
        fieldNames: unref(getFieldNames),
        'onUpdate:expandedKeys': (v: KeyType[]) => {
          state.expandedKeys = v;
          emit('update:expandedKeys', v);
        },
        'onUpdate:selectedKeys': (v: KeyType[]) => {
          state.selectedKeys = v;
          emit('update:selectedKeys', v);
        },
        onCheck: (
          v: CheckKeys,
          e: { checked: Boolean; node: { eventKey: any } },
        ) => {
          let currentValue = toRaw(state.checkedKeys) as KeyType[];
          if (isArray(currentValue) && searchState.startSearch) {
            const value = e.node.eventKey;
            currentValue = difference(currentValue, getChildrenKeys(value));
            if (e.checked) currentValue.push(value);

            state.checkedKeys = currentValue;
          } else {
            state.checkedKeys = v;
          }

          const rawVal = toRaw(state.checkedKeys);
          emit('update:value', rawVal);
          emit('check', rawVal, e);
        },
        onRightClick: handleRightClick,
      };
      return omit(propsData, 'treeData', 'class') as TreeProps;
    });

    const getTreeData = computed((): TreeItem[] =>
      searchState.startSearch ? searchState.searchData : unref(treeDataRef),
    );

    const getNotFound = computed((): boolean => {
      return !getTreeData.value || getTreeData.value.length === 0;
    });

    function getIcon(params: TreeItem, icon?: string) {
      if (!icon && props.renderIcon && isFunction(props.renderIcon))
        return props.renderIcon(params);
      return icon;
    }

    async function handleRightClick({ event, node }: Recordable) {
      const { rightMenuList: menuList = [], beforeRightClick } = props;
      const contextMenuOptions: CreateContextOptions = { event, items: [] };

      if (beforeRightClick && isFunction(beforeRightClick)) {
        const result = await beforeRightClick(node, event);
        if (Array.isArray(result)) contextMenuOptions.items = result;
        else Object.assign(contextMenuOptions, result);
      } else {
        contextMenuOptions.items = menuList;
      }
      if (!contextMenuOptions.items?.length) return;
      contextMenuOptions.items = contextMenuOptions.items.filter(
        (item) => !item.hidden,
      );
      createContextMenu(contextMenuOptions);
    }

    function setExpandedKeys(keys: KeyType[]) {
      state.expandedKeys = keys;
    }

    function getExpandedKeys() {
      return state.expandedKeys;
    }
    function setSelectedKeys(keys: KeyType[]) {
      state.selectedKeys = keys;
    }

    function getSelectedKeys() {
      return state.selectedKeys;
    }

    function setCheckedKeys(keys: CheckKeys) {
      state.checkedKeys = keys;
    }

    function getCheckedKeys() {
      return state.checkedKeys;
    }

    function checkAll(checkAll: boolean) {
      state.checkedKeys = checkAll ? getEnabledKeys() : ([] as KeyType[]);
      emit('check', state.checkedKeys, []);
    }

    function expandAll(expandAll: boolean) {
      state.expandedKeys = expandAll ? getAllKeys() : ([] as KeyType[]);
    }

    function onStrictlyChange(strictly: boolean) {
      state.checkStrictly = strictly;
    }

    watch(
      () => props.searchValue,
      (val) => {
        if (val !== searchState.searchText) searchState.searchText = val;
      },
      {
        immediate: true,
      },
    );

    watch(
      () => props.treeData,
      (val) => {
        if (val) handleSearch(searchState.searchText);
      },
    );

    function handleSearch(searchValue: string) {
      if (searchValue !== searchState.searchText)
        searchState.searchText = searchValue;
      emit('update:searchValue', searchValue);
      if (!searchValue) {
        searchState.startSearch = false;
        return;
      }
      const {
        filterFn,
        checkable,
        expandOnSearch,
        checkOnSearch,
        selectedOnSearch,
      } = unref(props);
      searchState.startSearch = true;
      const { title: titleField, key: keyField } = unref(getFieldNames);

      const matchedKeys: string[] = [];
      searchState.searchData = filter(
        unref(treeDataRef),
        (node) => {
          const result = filterFn
            ? filterFn(searchValue, node, unref(getFieldNames))
            : (node[titleField]?.includes(searchValue) ?? false);
          if (result) matchedKeys.push(node[keyField]);

          return result;
        },
        unref(getFieldNames),
      );

      if (expandOnSearch) {
        const expandKeys = treeToList(searchState.searchData).map(
          (val: { [x: string]: any }) => {
            return val[keyField];
          },
        );
        if (expandKeys && expandKeys.length > 0) setExpandedKeys(expandKeys);
      }

      if (checkOnSearch && checkable && matchedKeys.length > 0)
        setCheckedKeys(matchedKeys);

      if (selectedOnSearch && matchedKeys.length > 0)
        setSelectedKeys(matchedKeys);
    }

    function handleClickNode(key: string, children: TreeItem[]) {
      if (!props.clickRowToExpand || !children || children.length === 0) return;
      if (state.expandedKeys.includes(key)) {
        const keys = [...state.expandedKeys];
        const index = keys.indexOf(key);
        if (index !== -1) keys.splice(index, 1);

        setExpandedKeys(keys);
      } else {
        setExpandedKeys([...state.expandedKeys, key]);
      }
    }

    watchEffect(() => {
      treeDataRef.value = props.treeData as TreeItem[];
    });

    onMounted(() => {
      const level = Number.parseInt(props.defaultExpandLevel as string);
      if (level > 0) state.expandedKeys = filterByLevel(level);
      else if (props.defaultExpandAll) expandAll(true);
    });

    watchEffect(() => {
      state.expandedKeys = props.expandedKeys;
    });

    watchEffect(() => {
      state.selectedKeys = props.selectedKeys;
    });

    watchEffect(() => {
      state.checkedKeys = props.checkedKeys;
    });

    watch(
      () => props.value,
      () => {
        state.checkedKeys = toRaw(props.value || []);
      },
      { immediate: true },
    );

    watch(
      () => state.checkedKeys,
      () => {
        const v = toRaw(state.checkedKeys);
        emit('update:value', v);
        emit('change', v);
      },
    );

    watchEffect(() => {
      state.checkStrictly = props.checkStrictly;
    });

    const instance: TreeActionType = {
      getTreeData: () => treeDataRef,
      setExpandedKeys,
      getExpandedKeys,
      setSelectedKeys,
      getSelectedKeys,
      setCheckedKeys,
      getCheckedKeys,
      insertNodeByKey,
      insertNodesByKey,
      deleteNodeByKey,
      updateNodeByKey,
      getSelectedNode,
      checkAll,
      expandAll,
      filterByLevel: (level: number) => {
        state.expandedKeys = filterByLevel(level);
      },
      setSearchValue: (value: string) => {
        handleSearch(value);
      },
      getSearchValue: () => {
        return searchState.searchText;
      },
    };

    function renderAction(node: TreeItem) {
      const { actionList } = props;
      if (!actionList || actionList.length === 0) return;
      return actionList.map((item, index) => {
        let nodeShow = true;
        if (isFunction(item.show)) nodeShow = item.show?.(node);
        else if (isBoolean(item.show)) nodeShow = item.show;

        if (!nodeShow) return null;

        return (
          <span class={b('action')} key={index}>
            {item.render(node)}
          </span>
        );
      });
    }

    const treeData = computed(() => {
      const data = cloneDeep(getTreeData.value);
      eachTree(data, (item, _parent) => {
        const searchText = searchState.searchText;
        const { highlight } = unref(props);
        const {
          title: titleField,
          key: keyField,
          children: childrenField,
        } = unref(getFieldNames);

        const icon = getIcon(item, item.icon);
        const title = get(item, titleField);

        const searchIdx = searchText ? title.indexOf(searchText) : -1;
        const isHighlight =
          searchState.startSearch &&
          !isEmpty(searchText) &&
          highlight &&
          searchIdx !== -1;
        const highlightStyle = `color: ${isBoolean(highlight) ? '#f50' : highlight}`;

        const titleDom = isHighlight ? (
          <span
            class={unref(getBindValues)?.blockNode ? `${b('content')}` : ''}
          >
            <span>{title.slice(0, searchIdx)}</span>
            <span style={highlightStyle}>{searchText}</span>
            <span>
              {title.slice(searchIdx + (searchText as string).length)}
            </span>
          </span>
        ) : (
          title
        );

        const iconDom = icon ? (
          <TreeIcon icon={icon} />
        ) : slots.icon ? (
          <span class="mr-1">{getSlot(slots, 'icon')}</span>
        ) : null;

        item[titleField] = (
          <span
            class={`${b('title')} flex pl-2`}
            onClick={handleClickNode.bind(
              null,
              item[keyField],
              item[childrenField],
            )}
          >
            {slots?.title ? (
              <>
                {iconDom}

                {/* {titleDom} */}
                {getSlot(slots, 'title', item)}
                <span class={b('actions')}>{renderAction(item)}</span>
              </>
            ) : (
              <>
                {iconDom}
                {titleDom}

                <span class={b('actions')}>{renderAction(item)}</span>
              </>
            )}
          </span>
        );
        return item;
      });
      return data;
    });

    expose(instance);

    return () => {
      const {
        title,
        helpMessage,
        toolbar,
        search,
        checkable,
        showStrictlyButton,
      } = props;
      const showTitle = title || toolbar || search || slots.headerTitle;
      const scrollStyle: CSSProperties = { height: 'calc(100% - 38px)' };
      return (
        <div class={[b(), 'h-full', attrs.class]}>
          {showTitle && (
            <TreeHeader
              checkable={checkable}
              checkAll={checkAll}
              expandAll={expandAll}
              helpMessage={helpMessage}
              onSearch={handleSearch}
              onStrictlyChange={onStrictlyChange}
              search={search}
              searchText={searchState.searchText}
              showStrictlyButton={showStrictlyButton}
              title={title}
              toolbar={toolbar}
            >
              {extendSlots(slots)}
            </TreeHeader>
          )}
          <Spin
            spinning={unref(props.loading)}
            tip={$t('component.drawer.loadingText')}
            wrapperClassName={unref(props.treeWrapperClassName)}
          >
            <ScrollContainer style={scrollStyle} v-show={!unref(getNotFound)}>
              <Tree
                {...unref(getBindValues)}
                showIcon={false}
                treeData={treeData.value}
              >
                {extendSlots(slots, ['title', 'type'])}
              </Tree>
            </ScrollContainer>
            <Empty
              class="!mt-4"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              v-show={unref(getNotFound)}
            />
          </Spin>
        </div>
      );
    };
  },
});
</script>
