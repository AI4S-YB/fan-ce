import type { VNode } from 'vue';

import { h } from 'vue';

import { Icon } from '#/components/Icon';
import { isString } from '#/utils/is';

export const TreeIcon: any = ({
  icon,
}: {
  icon: string | undefined | VNode;
}) => {
  if (!icon) return null;
  if (isString(icon)) return h(Icon, { icon, class: 'mr-1' });

  return h(Icon);
};
