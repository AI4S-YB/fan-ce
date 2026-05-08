// visuals/blast-helpers.js — shared D3 utilities for BLAST visualizations

/**
 * Map an E-value to an HSL orange color.
 * Lower E-value (more significant) → deeper orange.
 * @param {number} evalue
 * @param {number} maxEvalue - max E-value among hits for normalization
 * @returns {string} HSL color string
 */
export function evalueToColor(evalue, maxEvalue) {
  if (maxEvalue <= 0 || evalue <= 0) return 'hsl(20, 82%, 50%)';
  const v = Math.max(0, 1 - Math.log10(evalue + 1) / Math.log10(maxEvalue + 1));
  return `hsl(20, 82%, ${Math.round((1 - v * 0.7) * 100)}%)`;
}

/**
 * Format E-value for display with superscript notation.
 * @param {number} evalue
 * @returns {string} HTML string
 */
export function prettifyEvalue(evalue) {
  if (evalue === 0) return '0';
  if (evalue < 1e-100) return '&lt;1×10<sup>-100</sup>';
  const exp = Math.floor(Math.log10(evalue));
  const mantissa = evalue / Math.pow(10, exp);
  return `${mantissa.toFixed(1)}×10<sup>${exp}</sup>`;
}

/**
 * Format axis tick labels with SI prefixes for bp/aa.
 * @param {number} n - tick value
 * @param {'nucleic_acid'|'amino_acid'} seqType
 * @returns {string}
 */
export function formatTick(n, seqType) {
  const unit = seqType === 'amino_acid' ? ' aa' : ' bp';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + ' M' + unit;
  if (n >= 1e3) return (n / 1e3).toFixed(1) + ' k' + unit;
  return n + unit;
}

/**
 * Detect sequence type from sequence characters.
 * @param {string} seq
 * @returns {'nucleic_acid'|'amino_acid'}
 */
export function detectSeqType(seq) {
  const clean = seq.replace(/[^A-Za-z]/g, '').toUpperCase();
  const dnaLetters = new Set('ATCGN');
  const nonDna = [...clean].filter(c => c >= 'A' && c <= 'Z' && !dnaLetters.has(c));
  return nonDna.length / clean.length > 0.15 ? 'amino_acid' : 'nucleic_acid';
}

/**
 * Group flat BLAST TSV rows into query→hits→hsps structure.
 * @param {object[]} rows - TSV rows with columns: Query, Hit_ID, Hit_Accession,
 *   Hit_Def, Length, Score, Evalue, Identity, Positives, Gaps, QStart, QEnd,
 *   SStart, SEnd, QSeq, SSeq, Midline, Link
 * @param {string} querySeq - the original query FASTA sequence
 * @returns {object[]} array of query groups, each with { name, length, type, hits }
 */
export function groupBlastTable(rows, querySeq) {
  const queryMap = new Map();
  const qLen = querySeq.replace(/[^A-Za-z]/g, '').length;
  const qType = detectSeqType(querySeq);

  for (const r of rows) {
    const qName = r.Query || 'Query';
    if (!queryMap.has(qName)) {
      queryMap.set(qName, { name: qName, length: qLen, type: qType, hits: [] });
    }
    const q = queryMap.get(qName);
    let hit = q.hits.find(h => h.id === r.Hit_ID);
    if (!hit) {
      hit = {
        id: r.Hit_ID,
        accession: r.Hit_Accession || '',
        def: r.Hit_Def || '',
        length: +(r.Length) || 0,
        hsps: []
      };
      q.hits.push(hit);
    }
    hit.hsps.push({
      qStart: +r.QStart, qEnd: +r.QEnd,
      sStart: +r.SStart, sEnd: +r.SEnd,
      evalue: +r.Evalue, bitScore: +r.Score,
      identity: +r.Identity, positives: +(r.Positives || 0), gaps: +(r.Gaps || 0),
      qSeq: r.QSeq || '', sSeq: r.SSeq || '', midline: r.Midline || ''
    });
  }
  return [...queryMap.values()];
}

/**
 * Group GeneInfo BLAST XML data into the same shape.
 * GeneInfo data: { db_name: [ hit_objects ] }
 * Each hit: { Hit_id, Hit_accession, Hit_def, Hit_len, Hit_hsps: { Hsp: { Hsp_score, Hsp_evalue, ... } } }
 * @param {Record<string, any[]>} blastByDb - from gene annotation API
 * @param {string} queryName - gene ID
 * @param {number} queryLength - query sequence length
 * @param {'nucleic_acid'|'amino_acid'} queryType
 * @returns {object[]}
 */
export function groupGeneInfoBlast(blastByDb, queryName, queryLength, queryType) {
  const queries = [];
  for (const [db, hitList] of Object.entries(blastByDb)) {
    const hits = [];
    for (const h of (hitList || [])) {
      const hspObj = h.Hit_hsps?.Hsp;
      const hsp = hspObj ? {
        qStart: +(hspObj.Hsp_query_from || 0),
        qEnd: +(hspObj.Hsp_query_to || 0),
        sStart: +(hspObj.Hsp_hit_from || 0),
        sEnd: +(hspObj.Hsp_hit_to || 0),
        evalue: +(hspObj.Hsp_evalue || 0),
        bitScore: +(hspObj.Hsp_score || 0),
        identity: +(hspObj.Hsp_identity || 0),
        positives: +(hspObj.Hsp_positive || 0),
        gaps: +(hspObj.Hsp_gaps || 0),
        qSeq: hspObj.Hsp_qseq || '',
        sSeq: hspObj.Hsp_hseq || '',
        midline: hspObj.Hsp_midline || ''
      } : null;
      if (hsp) {
        hits.push({
          id: h.Hit_id || '',
          accession: h.Hit_accession || '',
          def: h.Hit_def || '',
          length: +(h.Hit_len || 0),
          hsps: [hsp]
        });
      }
    }
    if (hits.length > 0) {
      queries.push({ name: `${queryName} vs ${db}`, length: queryLength, type: queryType, hits });
    }
  }
  return queries;
}

/**
 * Debounce helper for resize handling.
 */
export function debounce(fn, delay) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

/**
 * Get collapsed state from localStorage.
 */
export function getCollapsed(key) {
  return localStorage.getItem(`blast-viz-${key}`) === '1';
}

/**
 * Save collapsed state to localStorage.
 */
export function setCollapsed(key, val) {
  localStorage.setItem(`blast-viz-${key}`, val ? '1' : '0');
}
