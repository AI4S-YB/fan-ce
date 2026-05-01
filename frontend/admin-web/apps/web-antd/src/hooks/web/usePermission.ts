import type { RoleEnum } from '#/enums/roleEnum';

import { useAccessStore } from '@vben/stores';

import { PermissionModeEnum } from '#/enums/appEnum';
import projectSetting from '#/settings/projectSetting';
import { useAppStore } from '#/store/modules/app';
// import { RootRoute } from '#/router/routes';
import { useUserStore } from '#/store/modules/user';
import { isArray } from '#/utils/is';

// User permissions related operations
export function usePermission() {
  const userStore = useUserStore();
  const appStore = useAppStore();
  const accessStore = useAccessStore();

  /**
   * Change permission mode
   */
  function togglePermissionMode() {
    appStore.setProjectConfig({
      permissionMode:
        projectSetting.permissionMode === PermissionModeEnum.BACK
          ? PermissionModeEnum.ROUTE_MAPPING
          : PermissionModeEnum.BACK,
    });
    location.reload();
  }
  /**
   * 基于权限码判断是否有权限
   * @description: Determine whether there is permission，The permission code is judged by the user's permission code
   * @param codes
   */
  function hasAccessByCodes(codes: string[]) {
    const userCodesSet = new Set(accessStore.accessCodes);

    const intersection = codes.filter((item) => userCodesSet.has(item));
    return intersection.length > 0;
  }

  function hasPermission(
    value?: RoleEnum | RoleEnum[] | string | string[],
    def = true,
  ): boolean {
    // return true;
    if (!value) return def;
    if (value === '*') return true;
    if (!isArray(value)) {
      // return userStore.getRoleList?.includes(value as RoleEnum);
      return hasAccessByCodes([value]);
    }
    if (isArray(value)) {
      return hasAccessByCodes(value);
    }
    return false;
  }

  /**
   * Change roles
   * @param roles
   */
  async function changeRole(roles: RoleEnum | RoleEnum[]): Promise<void> {
    if (projectSetting.permissionMode !== PermissionModeEnum.ROUTE_MAPPING)
      throw new Error(
        'Please switch PermissionModeEnum to ROUTE_MAPPING mode in the configuration to operate!',
      );

    if (!isArray(roles)) roles = [roles];

    userStore.setUserRoles(roles);
    // await resume();
  }

  /**
   * refresh menu data
   */
  // function refreshMenu() {
  //   resume();
  // }

  return { changeRole, hasPermission, togglePermissionMode, hasAccessByCodes };
}
