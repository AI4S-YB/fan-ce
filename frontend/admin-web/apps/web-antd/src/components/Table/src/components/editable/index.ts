import type { Ref } from 'vue';

import type { BasicColumn } from '#/components/Table/src/types/table';

import { h, toRaw } from 'vue';

import { isArray } from '#/utils/is';

import EditableCell from './EditableCell.vue';

interface Params {
  text: string;
  record: Recordable;
  index: number;
}

export function renderEditCell(column: BasicColumn) {
  return ({ text: value, record, index }: Params) => {
    toRaw(record).onValid = async () => {
      if (isArray(record?.validCbs)) {
        const validFns = (record?.validCbs || []).map((fn) => fn());
        const res = await Promise.all(validFns);
        return res.every((item) => !!item);
      } else {
        return false;
      }
    };

    toRaw(record).onEdit = async (edit: boolean, submit = false) => {
      if (!submit) record.editable = edit;

      if (!edit && submit) {
        if (!(await record.onValid())) return false;
        const res = await record.onSubmitEdit?.();
        if (res) {
          record.editable = false;
          return true;
        }
        return false;
      }
      // cancel
      if (!edit && !submit) record.onCancelEdit?.();

      return true;
    };

    return h(EditableCell, {
      value,
      record,
      column,
      index,
    });
  };
}

export type EditRecordRow<T = Recordable> = Partial<
  T & {
    cancelCbs: Fn[];
    editable: boolean;
    editValueRefs: Recordable<Ref>;
    onCancel: Fn;
    onEdit: (editable: boolean, submit?: boolean) => Promise<boolean>;
    onSubmit: Fn;
    onValid: () => Promise<boolean>;
    submitCbs: Fn[];
    validCbs: Fn[];
  }
>;
