import type { Pinia } from 'pinia';

export * from './auth';
export * from './modules/dict';
export * from './modules/platform-setup';
export * from './modules/program';
export * from './modules/workspace';
// eslint-disable-next-line import/no-mutable-exports
let pinia: Pinia;

export interface InitStoreOptions {
  namespace: string;
}

export { pinia as store };
