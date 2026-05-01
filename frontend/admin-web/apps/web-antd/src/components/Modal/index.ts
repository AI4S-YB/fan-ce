import { withInstall } from '#/utils';

import basicModal from './src/BasicModal.vue';

import './src/index.less';

export const BasicModal = withInstall(basicModal);
export { useModal, useModalInner } from './src/hooks/useModal';
export { useModalContext } from './src/hooks/useModalContext';
export * from './src/typing';
