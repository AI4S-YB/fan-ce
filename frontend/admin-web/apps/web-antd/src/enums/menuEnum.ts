/**
 * @description: menu type
 */
export enum MenuTypeEnum {
  // mixin menu
  MIX = 'mix',

  MIX_SIDEBAR = 'mix-sidebar',
  // left menu
  SIDEBAR = 'sidebar',
  // top menu
  TOP_MENU = 'top-menu',
}

// 折叠触发器位置
export enum TriggerEnum {
  // 菜单底部
  FOOTER = 'FOOTER',
  // 头部
  HEADER = 'HEADER',
  // 不显示
  NONE = 'NONE',
}

export type Mode = 'horizontal' | 'inline' | 'vertical' | 'vertical-right';

// menu mode
export enum MenuModeEnum {
  HORIZONTAL = 'horizontal',
  INLINE = 'inline',
  VERTICAL = 'vertical',
  VERTICAL_RIGHT = 'vertical-right',
}

export enum MenuSplitTyeEnum {
  NONE,
  TOP,
  LEFT,
}

export enum TopMenuAlignEnum {
  CENTER = 'center',
  END = 'end',
  START = 'start',
}

export enum MixSidebarTriggerEnum {
  CLICK = 'click',
  HOVER = 'hover',
}
