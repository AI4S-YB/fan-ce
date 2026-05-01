interface onImgLoadType {
  index: number;
  url: string;
  dom: HTMLImageElement;
}

export interface Options {
  show?: boolean;
  imageList: string[];
  index?: number;
  scaleStep?: number;
  defaultWidth?: number;
  maskClosable?: boolean;
  rememberState?: boolean;
  onImgLoad?: (params: onImgLoadType) => void;
  onImgError?: (params: onImgLoadType) => void;
}

export interface Props {
  show: boolean;
  instance: Props;
  imageList: string[];
  index: number;
  scaleStep: number;
  defaultWidth: number;
  maskClosable: boolean;
  rememberState: boolean;
}

export interface PreviewActions {
  resume: () => void;
  close: () => void;
  prev: () => void;
  next: () => void;
  setScale: (scale: number) => void;
  setRotate: (rotate: number) => void;
}

export interface ImageProps {
  alt?: string;
  fallback?: string;
  src: string;
  width: number | string;
  height?: number | string;
  placeholder?: boolean | string;
  preview?:
    | boolean
    | {
        getContainer: (() => HTMLElement) | HTMLElement | string;
        onOpenChange?: (open: boolean, prevOpen: boolean) => void;
        open?: boolean;
      };
}

export type ImageItem = ImageProps | string;
