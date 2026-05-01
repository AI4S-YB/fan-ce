export const SIDE_BAR_MINI_WIDTH = 48;
export const SIDE_BAR_SHOW_TIT_MINI_WIDTH = 80;

export enum ContentEnum {
  // fixed width
  FIXED = 'fixed',
  // auto width
  FULL = 'full',
}

// menu theme enum
export enum ThemeEnum {
  DARK = 'dark',
  LIGHT = 'light',
}

export enum SettingButtonPositionEnum {
  AUTO = 'auto',
  FIXED = 'fixed',
  HEADER = 'header',
}

export enum SessionTimeoutProcessingEnum {
  ROUTE_JUMP,
  PAGE_COVERAGE,
}

/**
 * 权限模式
 */
export enum PermissionModeEnum {
  // black
  // 后端
  BACK = 'BACK',
  // role
  // 角色权限
  ROLE = 'ROLE',
  // route mapping
  // 路由映射
  ROUTE_MAPPING = 'ROUTE_MAPPING',
}

// Route switching animation
// 路由切换动画
export enum RouterTransitionEnum {
  FADE = 'fade',
  FADE_BOTTOM = 'fade-bottom',
  FADE_SCALE = 'fade-scale',
  FADE_SIDE = 'fade-slide',
  ZOOM_FADE = 'zoom-fade',
  ZOOM_OUT = 'zoom-out',
}

export enum IconEnum {
  ADD = 'ant-design:plus-outlined',
  ADD_FOLD = 'ant-design:folder-add-outlined',
  AUTH = 'ant-design:safety-certificate-outlined',
  DELETE = 'ant-design:delete-outlined',
  DOWNLOAD = 'ant-design:cloud-download-outlined',
  EDIT = 'clarity:note-edit-line',
  EXPORT = 'ant-design:vertical-align-bottom-outlined',
  IMPORT = 'ant-design:vertical-align-top-outlined',
  LOG = 'ant-design:exception-outlined',
  PASSWORD = 'ant-design:key-outlined',
  PREVIEW = 'ant-design:eye-outlined',
  RESET = 'ant-design:sync-outlined',
  SEARCH = 'ant-design:search-outlined',
  SEND = 'ant-design:send-outlined',
  SETTING = 'ant-design:setting-outlined',
  TEST = 'ant-design:deployment-unit-outlined',
  UPLOAD = 'ant-design:cloud-upload-outlined',
  VIEW = 'ant-design:file-search-outlined',
}
