import { baseRequestClient } from '#/api/request';

/**
 * @description: Upload interface
 */

export async function uploadApi(data: any) {
  return baseRequestClient.upload('/upload/file', data);
}
