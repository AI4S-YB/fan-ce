/**
 * 格式化文件大小 单位：B、KB、MB、GB
 * @param value
 * @returns
 */
export const formatFileSize = (value: any | null) => {
  if (value === null || value === '') {
    return '0 M';
  }
  const unitArr = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const srcSize = Number.parseFloat(value);
  const index = Math.floor(Math.log(srcSize) / Math.log(1024));
  const size = srcSize / 1024 ** index;
  if (unitArr[index]) {
    return size.toFixed(2) + unitArr[index];
  }
  return '文件太大';
};
