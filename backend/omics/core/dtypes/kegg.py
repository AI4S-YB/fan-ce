import os
import sys
import re
import json

'''
 generate_kegg_doc: generate KEGG doc for sqlite
'''
def generate_kegg_doc(kegg_file):

    ''' kegg to dict '''
    transcript_kegg = {}
    with open(kegg_file, 'r') as fh:
        for line in fh:
            # ATCG00500.1	ko:K01963,ko:K02696	map00061	Fatty acid biosynthesis
            m = line.strip("\n").split("\t")
            transcript_id = m[0]
            orthologs = m[1].split(",")
            pathway = m[2]
            description = m[3]

            kegg_doc = {}
            kegg_doc['pathway'] = pathway
            kegg_doc['description'] = description
            kegg_doc['orthology'] = []
            for otholog in orthologs:
                kegg_doc['orthology'].append(otholog)

            if transcript_id in transcript_kegg:
                transcript_kegg[transcript_id].append(kegg_doc)
            else:
                transcript_kegg[transcript_id] = []
                transcript_kegg[transcript_id].append(kegg_doc)
    
    for transcript_id, keggs in transcript_kegg.items():
        if isinstance(keggs, list):
            transcript_kegg[transcript_id] = json.dumps(keggs)
        
    return transcript_kegg
