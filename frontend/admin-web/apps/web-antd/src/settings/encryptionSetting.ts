import { isDevMode } from '#/utils/env';

// 缓存默认过期时间
export const DEFAULT_CACHE_TIME = 60 * 60 * 24 * 7;
// 开启缓存加密后，加密密钥。采用aes加密
export const cacheCipher = {
  key: '_11111777771111@',
  iv: '@11111666661111_',
};

// 是否加密缓存，默认生产环境加密
export const SHOULD_ENABLE_STORAGE_ENCRYPTION = !isDevMode();
// export const SHOULD_ENABLE_STORAGE_ENCRYPTION = true;
