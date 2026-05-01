import os
import sys
import re
import gzip
import time
import json
from xml.etree import cElementTree as ET
from pprint import pprint
from .utils import etree_to_dict, split_xml


def parse_ipr_match(match_dict):

    match = {}
    match['source_term'] = 'None'
    match['source_lib'] = match_dict['signature']['signature-library-release']['@library']
    match['source_name'] = 'None'
    match['source_desc'] = 'None'
    match['ipr_term'] = 'None'
    match['ipr_desc'] = 'No IPR available'

    ''' fix the prosite db name '''
    if (match['source_lib'] == 'PROSITE_PATTERNS' or match['source_lib'] == 'PROSITE_PROFILES'):
        match['source_lib'] = 'PROSITE'
     
    if '@ac' in match_dict['signature']:
        source_term = match_dict['signature']['@ac']
        if (match['source_lib'] == 'GENE3D'):
            source_term = source_term[6:]
        elif (match['source_lib'] == 'SUPERFAMILY'):
            source_term = source_term[3:]
        else:
            pass
        match['source_term'] = source_term
    if '@name' in match_dict['signature']:
        match['source_name'] = match_dict['signature']['@name'] 
    if '@desc' in match_dict['signature']:
        match['source_desc'] = match_dict['signature']['@desc'] 

    if 'entry' in match_dict['signature']:
        if '@ac' in match_dict['signature']['entry']:
            match['ipr_term'] = match_dict['signature']['entry']['@ac']
        if '@desc' in match_dict['signature']['entry']:
            match['ipr_desc'] = match_dict['signature']['entry']['@desc']

    match['location'] = []
    for key in match_dict['locations']:
        loc = match_dict['locations'][key]
        if isinstance(loc, dict):
            m = {}
            if '@start' in loc:
                m['start'] = loc['@start']
            if '@end' in loc:
                m['end'] = loc['@end']
            if '@score' in loc:
                m['score'] = loc['@score']
            if '@evalue' in loc:
                m['evalue'] = loc['@evalue']
            match['location'].append(m)
        else:
            for locus in loc:
                m = {}
                if '@start' in locus:
                    m['start'] = locus['@start']
                if '@end' in locus:
                    m['end'] = locus['@end']
                if '@score' in locus:
                    m['score'] = locus['@score']
                if '@evalue' in locus:
                    m['evalue'] = locus['@evalue']
                match['location'].append(m)

    #pprint(match_dict)
    #pprint(match)
    return match

'''
 parse_ipr_xml: using etree module to parse match domains for single protein
'''
def parse_ipr_xml(protein_xml, keyword):
    e = ET.XML(protein_xml)
    d = etree_to_dict(e)
    d = d[keyword]
    #pprint(d)

    d['sequence'] = d['sequence']['#text']
    transcript_ids = []
    #pprint(d['xref'])
    if isinstance(d['xref'], dict):
        query_id = d['xref']['@id']
        query_name = d['xref']['@name']
        #transcript_id = detect_transcript_id(db, organism_id, query_id, query_name)
        transcript_id = query_id
        transcript_ids.append(transcript_id)
    elif isinstance(d['xref'], list):
        for xref in d['xref']:
            query_id = xref['@id']
            query_name = xref['@name']
            #transcript_id = detect_transcript_id(db, organism_id, query_id, query_name)
            transcript_id = query_id
            transcript_ids.append(transcript_id)
    del d['xref']

    if isinstance(d['matches'], dict):
        ''' format the matches for easy to view '''
        d['matches_format'] = []
        for source in d['matches']:
            if isinstance(d['matches'][source], list):
                for m in d['matches'][source]:
                    match = parse_ipr_match(m)
                    d['matches_format'].append(match)
            else:
                match = parse_ipr_match(d['matches'][source])
                d['matches_format'].append(match)
    del d['matches']

    return transcript_ids, d

'''
 generate_ipr_doc: generate InterPro document for sqlite
'''
def generate_ipr_doc(xml_file):

    start_time = time.time()
    transcript_ipr = {}
    with gzip.open(xml_file, 'rb') as xml_fh:
        for protein_xml in split_xml(xml_fh, 'protein'):
            transcript_ids, protein_doc = parse_ipr_xml(protein_xml, 'protein')
            if 'matches_format' in protein_doc:
                for transcript_id in transcript_ids:
                    transcript_ipr[transcript_id] = json.dumps(protein_doc)

    print('Done loading InterPro. Took %s seconds' % int(time.time() - start_time))

    return transcript_ipr




