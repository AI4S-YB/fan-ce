import os
import sys



def get_genes_from_gtf(gtf_fh):
    """
    Parse GTF file; Returns iter of gene dicts
    """
    for line in gtf_fh:
        if line.startswith('#'):
            continue
        fields = line.strip('\n').split('\t')

        if fields[2] != 'gene':
            continue

        chrom = fields[0]
        start = int(fields[3])
        stop = int(fields[4])
        info = dict(x.strip().split() for x in fields[8].split(';') if x != '')
        info = {k: v.strip('"') for k, v in info.items()}
        gene_id = info['gene_id']

        gene = {
            'gene_id': gene_id,
            'chrom': fields[0],
            'start': int(fields[3]),
            'stop': int(fields[4]),
            'strand': fields[6],
        }
        yield gene

def get_transcripts_from_gtf(gtf_fh):
    """
    Parse GTF file; Returns iter of transcript dicts
    """
    for line in gtf_fh:
        if line.startswith('#'):
            continue
        fields = line.strip('\n').split('\t')

        if fields[2] != 'mRNA':
            continue

        chrom = fields[0]
        start = int(fields[3])
        stop = int(fields[4])
        info = dict(x.strip().split() for x in fields[8].split(';') if x != '')
        info = {k: v.strip('"') for k, v in info.items()}
        transcript_id = info['transcript_id']
        gene_id = info['gene_id']

        transcript = {
            'transcript_id': transcript_id,
            'gene_id': gene_id,
            'chrom': fields[0],
            'start': int(fields[3]),
            'stop': int(fields[4]),
            'strand': fields[6],
        }
        yield transcript

def get_exons_from_gtf(gtf_fh):
    """
    Parse GTF file; Returns iter of exon dicts
    """
    for line in gtf_fh:
        if line.startswith('#'):
            continue
        fields = line.strip('\n').split('\t')

        if fields[2] not in ['exon', 'CDS', 'UTR']:
            continue

        chrom = fields[0]
        feature_type = fields[2]
        start = int(fields[3])
        stop = int(fields[4])
        info = dict(x.strip().split() for x in fields[8].split(';') if x != '')
        info = {k: v.strip('"') for k, v in info.items()}
        transcript_id = info['transcript_id']
        gene_id = info['gene_id']

        exon = {
            'feature_type': feature_type,
            'transcript_id': transcript_id,
            'gene_id': gene_id,
            'chrom': fields[0],
            'start': int(fields[3]),
            'stop': int(fields[4]),
            'strand': fields[6],
        }
        yield exon


def get_ahrd_annotations(ahrd_file):
    for line in ahrd_file:
        fields = line.strip().split('\t')
        if fields[0] == 'Protein-Accession':
            yield None
        elif len(fields) >= 4:
            yield fields
        else:
            yield None

def get_canonical_transcripts(canonical_transcript_file):
    for line in canonical_transcript_file:
        m = line.strip().split()
        gene, transcript = line.strip().split()
        yield gene, transcript

'''
generate_transcript_doc: generate gene and mRNA doc for sqlite
'''

def generate_transcript_doc(gtf_file, canonical_transcripts_file, ahrd_file, itak_file):
    
    # put canonical transcripts in dict
    canonical_transcripts = {}
    canonical_gene = {}
    with open(canonical_transcripts_file) as canonical_transcript_fh:
        for gene, transcript in get_canonical_transcripts(canonical_transcript_fh):
            canonical_transcripts[gene] = transcript
            canonical_transcripts[transcript] = gene

    # put ahrd annotations in dict (for both gene and mRNA)
    ahrd_annotations = {}
    with open(ahrd_file) as ahrd_fh:
        for fields in get_ahrd_annotations(ahrd_fh):
            if fields is None:
                continue
            tid = fields[0]
            description = fields[3]
            ahrd_annotations[tid] = description
            if tid in canonical_transcripts:
                ahrd_annotations[canonical_transcripts[tid]] = description

    # put itak annotations in dict (for both gene and mRNA)
    gene_family = {}
    transcript_family = {}
    with open(itak_file, 'r') as family_fh:
        for line in family_fh:
            if line[0] == '#':
                continue
            m = line.strip("\n").split("\t")
            transcript_id = m[0]
            family_name = m[1]
            transcript_family[transcript_id] = family_name
            if transcript_id in canonical_transcripts:
                gene_family[canonical_transcripts[transcript_id]] = family_name

    # prepare gene document for sqlite
    gene_doc = {}
    with open(gtf_file) as gtf_fh:
        for gene in get_genes_from_gtf(gtf_fh):
            gene_id = gene['gene_id']
            if gene_id in canonical_transcripts:
                gene['canonical_transcript'] = canonical_transcripts[gene_id]
            if gene_id in ahrd_annotations:
                gene['description'] = ahrd_annotations[gene_id]
            if gene_id in gene_family:
                gene['family'] = gene_family[gene_id]
            gene_doc[gene_id] = gene

    # prepare transcript document for sqlite
    transcript_doc = {}
    with open(gtf_file) as gtf_fh:
        for transcript in get_transcripts_from_gtf(gtf_fh):
            transcript_id = transcript['transcript_id']
            if transcript_id in ahrd_annotations:
                transcript['description'] = ahrd_annotations[transcript_id]
            transcript_doc[transcript_id] = transcript

    # prepare exon document for sqlite
    exon_doc = []
    with open(gtf_file) as gtf_fh:
        for exon in get_exons_from_gtf(gtf_fh):
            exon_doc.append(exon)
    return gene_doc, transcript_doc, exon_doc
    



