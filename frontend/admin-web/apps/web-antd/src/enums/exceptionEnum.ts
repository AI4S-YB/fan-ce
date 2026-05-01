/**
 * @description: Exception related enumeration
 */
export enum ExceptionEnum {
  // error
  ERROR = 500,

  // net work error
  NET_WORK_ERROR = 10_000,

  // page not access
  PAGE_NOT_ACCESS = 403,

  // No data on the page. In fact, it is not an exception page
  PAGE_NOT_DATA = 10_100,

  // page not found
  PAGE_NOT_FOUND = 404,
}

export enum ErrorTypeEnum {
  AJAX = 'ajax',
  PROMISE = 'promise',
  RESOURCE = 'resource',
  SCRIPT = 'script',
  VUE = 'vue',
}
