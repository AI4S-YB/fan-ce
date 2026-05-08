export function evalueToColor(evalue: number, maxEvalue: number): string;
export function prettifyEvalue(evalue: number): string;
export function formatTick(n: number, seqType: 'nucleic_acid' | 'amino_acid'): string;
export function detectSeqType(seq: string): 'nucleic_acid' | 'amino_acid';
export function groupBlastTable(rows: Record<string, any>[], querySeq: string): any[];
export function groupGeneInfoBlast(blastByDb: Record<string, any[]>, queryName: string, queryLength: number, queryType: string): any[];
export function debounce(fn: (...args: any[]) => void, delay: number): (...args: any[]) => void;
export function getCollapsed(key: string): boolean;
export function setCollapsed(key: string, val: boolean): void;
