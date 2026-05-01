/**
 * Global authority directive
 * Used for fine-grained control of component permissions
 * @Example v-auth="RoleEnum.TEST"
 */
import type { App, Directive, DirectiveBinding } from 'vue';

import { usePermission } from '#/hooks/web/usePermission';

function isAuth(el: Element, binding: any) {
  const { hasPermission } = usePermission();
  const value = binding.value;
  if (!value) return;
  if (!hasPermission(value)) el.parentNode?.removeChild(el);
}

function hasPermission(el: Element, binding: any) {
  const { hasPermission } = usePermission();
  const value = binding.value;
  if (!value) return;
  if (!hasPermission(value)) {
    // el.parentNode?.removeChild(el);
  }
}

function mounted(el: Element, binding: DirectiveBinding<any>) {
  isAuth(el, binding);
}
const authDirective: Directive = {
  mounted,
};

const hasPermissionMounted = (el: Element, binding: DirectiveBinding<any>) => {
  hasPermission(el, binding);
};
export const hasPermissionDirective: Directive = {
  mounted: hasPermissionMounted,
};

/**
 * 注册全局 自定义指令
 */
export function setupPermissionDirective(app: App) {
  // 判断是否"拥有"指定的"所有"权限
  app.directive('auth', authDirective);
  // 判断是否"拥有"指定的"所有"权限
  app.directive('hasPermission', hasPermissionDirective);
  // 判断是否"拥有"指定的"任意"权限
}
export default authDirective;
