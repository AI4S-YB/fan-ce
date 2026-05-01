/**
 * @description: Request result set
 */
export enum ResultEnum {
  ERROR = -1,
  INTERNAL_SERVER_ERROR = 500,
  SUCCESS = 0,
  TIMEOUT = 400,
  TYPE = 'success',
  UNAUTHORIZED = 401,
}

/**
 * @description: request method
 */
export enum RequestEnum {
  DELETE = 'DELETE',
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
}

/**
 * @description:  contentType
 */
export enum ContentTypeEnum {
  // form-data  upload
  FORM_DATA = 'multipart/form-data;charset=UTF-8',
  // form-data qs
  FORM_URLENCODED = 'application/x-www-form-urlencoded;charset=UTF-8',
  // json
  JSON = 'application/json;charset=UTF-8',
}

export const HTTP_TAG_MAP = new Map([
  [RequestEnum.DELETE, 'error'],
  [RequestEnum.GET, 'success'],
  [RequestEnum.POST, 'processing'],
  [RequestEnum.PUT, 'warning'],
]);
