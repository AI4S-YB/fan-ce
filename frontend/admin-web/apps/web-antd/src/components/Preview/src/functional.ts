import type { Options, Props } from './typing';

import { createVNode, render } from 'vue';

import { isClient } from '#//utils/is';

import ImgPreview from './Functional.vue';

let instance: null | ReturnType<typeof createVNode> = null;
export function createImgPreview(options: Options) {
  if (!isClient) return;
  const propsData: Partial<Props> = {};
  const container = document.createElement('div');
  Object.assign(propsData, { show: true, index: 0, scaleStep: 100 }, options);

  instance = createVNode(ImgPreview, propsData);
  render(instance, container);
  document.body.append(container);
  return instance.component?.exposed;
}
