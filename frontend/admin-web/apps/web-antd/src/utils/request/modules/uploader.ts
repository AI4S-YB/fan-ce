import type { AxiosRequestConfig, AxiosResponse } from 'axios';

import type { RequestClient } from '../request-client';
// 文件上传参数
export interface UploadFileParams {
  // 其他的扩展参数
  data?: Recordable;
  // 后台用于接收file对象的参数名称
  name?: string;
  // file name
  file: Blob | File;
  // 传给后端的，文件名
  filename?: string;
  [key: string]: any;
}
class FileUploader {
  private client: RequestClient;

  constructor(client: RequestClient) {
    this.client = client;
  }

  public async upload(
    url: string,
    data: UploadFileParams,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse> {
    const formData = new FormData();
    const customFilename = data.name || 'file';
    if (data.filename)
      formData.append(customFilename, data.file, data.filename);
    else formData.append(customFilename, data.file);

    if (data.data) {
      Object.keys(data.data).forEach((key) => {
        const value = data.data?.[key];
        if (Array.isArray(value)) {
          value.forEach((item) => {
            formData.append(`${key}[]`, item);
          });
          return;
        }

        if (value !== undefined) {
          formData.append(key, value);
        }
      });
    }

    // Object.entries(data).forEach(([key, value]) => {
    //   formData.append(key, value);
    // });

    const finalConfig: AxiosRequestConfig = {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers,
      },
      timeout: 60 * 60 * 1000, // 1小时
    };

    return this.client.post2(url, formData, finalConfig);
  }
}

export { FileUploader };
