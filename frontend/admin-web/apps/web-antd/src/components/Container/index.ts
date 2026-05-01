import { withInstall } from '#/utils/index';

import collapseContainer from './src/collapse/CollapseContainer.vue';
import lazyContainer from './src/LazyContainer.vue';
import scrollContainer from './src/ScrollContainer.vue';

export const CollapseContainer = withInstall(collapseContainer);
export const ScrollContainer = withInstall(scrollContainer);
export const LazyContainer = withInstall(lazyContainer);

export * from './src/typing';
