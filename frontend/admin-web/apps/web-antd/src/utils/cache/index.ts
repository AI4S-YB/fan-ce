import type { CreateStorageParams } from './storageCache';

import {
  DEFAULT_CACHE_TIME,
  SHOULD_ENABLE_STORAGE_ENCRYPTION,
} from '#/settings/encryptionSetting';
import { getStorageShortName } from '#/utils/env';

import { createStorage as create } from './storageCache';

export type Options = Partial<CreateStorageParams>;

function createOptions(storage: Storage, options: Options = {}): Options {
  return {
    // No encryption in debug mode
    hasEncrypt: SHOULD_ENABLE_STORAGE_ENCRYPTION,
    storage,
    prefixKey: getStorageShortName(),
    ...options,
  };
}

export const WebStorage: any = create(createOptions(sessionStorage));

export function createStorage(
  storage: Storage = sessionStorage,
  options: Options = {},
) {
  return create(createOptions(storage, options));
}

export function createSessionStorage(options: Options = {}) {
  return createStorage(sessionStorage, {
    ...options,
    timeout: DEFAULT_CACHE_TIME,
  });
}

export function createLocalStorage(options: Options = {}) {
  return createStorage(localStorage, {
    ...options,
    timeout: DEFAULT_CACHE_TIME,
  });
}

export default WebStorage;
