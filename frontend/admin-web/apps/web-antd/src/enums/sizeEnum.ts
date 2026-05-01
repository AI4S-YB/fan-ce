export enum SizeEnum {
  DEFAULT = 'default',
  LARGE = 'large',
  SMALL = 'small',
}

export enum SizeNumberEnum {
  DEFAULT = 48,
  LARGE = 64,
  SMALL = 16,
}

export const sizeMap: Map<SizeEnum, SizeNumberEnum> = (() => {
  const map = new Map<SizeEnum, SizeNumberEnum>();
  map.set(SizeEnum.DEFAULT, SizeNumberEnum.DEFAULT);
  map.set(SizeEnum.SMALL, SizeNumberEnum.SMALL);
  map.set(SizeEnum.LARGE, SizeNumberEnum.LARGE);
  return map;
})();
