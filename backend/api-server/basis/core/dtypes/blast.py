import os
import sys
import re
import gzip
import time
import json
from xml.etree import cElementTree as ET
from pprint import pprint
from .utils import etree_to_dict, split_xml


'''
 parse_blast_xml: using etree module to parse single query results
'''
def parse_blast_xml(iteration_xml, keyword):
    e = ET.XML(iteration_xml)
    d = etree_to_dict(e)
    d = d[keyword]

    ''' find the transcript id '''
    query_id = d["Iteration_query-ID"]
    query_name = d["Iteration_query-def"]
    #transcript_id = detect_transcript_id(db, organism_id, query_id, query_name)
    transcript_id = query_name    
 
    hits = ""
    if (d['Iteration_hits']):
        ''' put single hit dict to list '''
        if (isinstance(d['Iteration_hits']['Hit'], dict)):
            d['Iteration_hits']['Hit'] = [d['Iteration_hits']['Hit']]

        ''' get top 5 hits '''
        if ( len(d['Iteration_hits']['Hit']) > 5 ):
            hits = d['Iteration_hits']['Hit'][0:5]
        else:
            hits = d['Iteration_hits']['Hit']
    else:
        ''' no hit for this query '''
        pass
     
    return transcript_id, hits

'''
 generate_blast_doc: generate BLAST doc for sqlite
'''
def generate_blast_doc(db_name, xml_file):
    start_time = time.time()

    transcript_blast = {}

    # 统一使用二进制模式打开所有文件
    open_func = gzip.open if xml_file.endswith('.gz') else open
    mode = 'rb'  # 统一使用二进制模式

    with open_func(xml_file, mode) as xml_fh:
        for iteration_xml in split_xml(xml_fh, 'Iteration'):
            transcript_id, iteration_data = parse_blast_xml(iteration_xml, 'Iteration') 
            if isinstance(iteration_data, list):
                transcript_blast[transcript_id] = json.dumps(iteration_data)

    print('Done loading BLAST. Took %s seconds' % int(time.time() - start_time))

    return transcript_blast