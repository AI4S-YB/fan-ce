import type { Encryption, EncryptionParams } from '#/utils/cipher';

import { cacheCipher } from '#/settings/encryptionSetting';
import { EncryptionFactory } from '#/utils/cipher';
import { isNil } from '#/utils/is';

export interface CreateStorageParams extends EncryptionParams {
  prefixKey: string;
  storage: Storage;
  hasEncrypt: boolean;
  timeout?: Nullable<number>;
}
export function createStorage({
  prefixKey = '',
  storage = sessionStorage,
  key = cacheCipher.key,
  iv = cacheCipher.iv,
  timeout = null,
  hasEncrypt = true,
}: Partial<CreateStorageParams> = {}) {
  if (hasEncrypt && [key.length, iv.length].some((item) => item !== 16))
    throw new Error('When hasEncrypt is true, the key or iv must be 16 bits!');

  const persistEncryption: Encryption = EncryptionFactory.createAesEncryption({
    key: cacheCipher.key,
    iv: cacheCipher.iv,
  });

  /**
   * Cache class
   * Construction parameters can be passed into sessionStorage, localStorage,
   * @class Cache
   * @example
   */
  const WebStorage = class WebStorage {
    private encryption: Encryption;
    private hasEncrypt: boolean;
    private prefixKey?: string;
    private storage: Storage;
    constructor() {
      this.storage = storage;
      this.prefixKey = prefixKey;
      this.encryption = persistEncryption;
      this.hasEncrypt = hasEncrypt;
    }

    /**
     * Delete all caches of this instance
     */
    clear(): void {
      this.storage.clear();
    }

    /**
     * Read cache
     * @param {string} key
     * @param {*} def
     * @memberof Cache
     */
    get(key: string, def: any = null): any {
      const val = this.storage.getItem(this.getKey(key));
      if (!val) return def;

      try {
        const decVal = this.hasEncrypt ? this.encryption.decrypt(val) : val;
        const data = JSON.parse(decVal);
        const { value, expire } = data;
        if (isNil(expire) || expire >= Date.now()) return value;

        this.remove(key);
      } catch {
        return def;
      }
    }

    /**
     * Delete cache based on key
     * @param {string} key
     * @memberof Cache
     */
    remove(key: string) {
      this.storage.removeItem(this.getKey(key));
    }

    /**
     * Set cache
     * @param {string} key
     * @param {*} value
     * @param {*} expire Expiration time in seconds
     * @memberof Cache
     */
    set(key: string, value: any, expire: null | number = timeout) {
      const stringData = JSON.stringify({
        value,
        time: Date.now(),
        expire: isNil(expire) ? null : Date.now() + expire * 1000,
      });
      const stringifyValue = this.hasEncrypt
        ? this.encryption.encrypt(stringData)
        : stringData;
      this.storage.setItem(this.getKey(key), stringifyValue);
    }

    private getKey(key: string) {
      return `${this.prefixKey}${key}`.toUpperCase();
    }
  };
  return new WebStorage();
}
