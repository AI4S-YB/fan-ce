/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue';

  const Component: DefineComponent<object, object, any>;
  export default Component;
}

declare module 'react-msa-viewer' {
  import type { ComponentType } from 'react';

  export interface Sequence {
    name: string;
    sequence: string;
    id?: string;
  }

  export interface MSAViewerProps {
    sequences: Sequence[];
    width?: number;
    height?: number;
    tileWidth?: number;
    tileHeight?: number;
    colorScheme?: string;
    position?: { xPos: number; yPos: number };
    layout?: 'basic' | 'default' | 'inverse' | 'full' | 'compact' | 'funky';
    [key: string]: any;
  }

  export const MSAViewer: ComponentType<MSAViewerProps>;
  export const MSAProvider: ComponentType<any>;
  export const ColorScheme: Record<string, string>;
  export function createMSAStore(sequences: Sequence[]): any;
}
