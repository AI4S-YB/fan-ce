export enum sizeEnum {
  LG = 'LG',
  MD = 'MD',
  SM = 'SM',
  XL = 'XL',
  XS = 'XS',
  XXL = 'XXL',
}

export enum screenEnum {
  LG = 960,
  MD = 768,
  SM = 640,
  XL = 1280,
  XS = 320,
  XXL = 1536,
}

const screenMap = new Map<sizeEnum, number>();

screenMap.set(sizeEnum.XS, screenEnum.XS);
screenMap.set(sizeEnum.SM, screenEnum.SM);
screenMap.set(sizeEnum.MD, screenEnum.MD);
screenMap.set(sizeEnum.LG, screenEnum.LG);
screenMap.set(sizeEnum.XL, screenEnum.XL);
screenMap.set(sizeEnum.XXL, screenEnum.XXL);

export { screenMap };
