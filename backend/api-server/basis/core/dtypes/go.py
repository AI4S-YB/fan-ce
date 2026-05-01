import os
import sys
import re
import json

def load_go_basic(go_basic_file):

    go_dict = {}
    go_id = ''
    go_name = ''
    go_namespace = ''
    with open(go_basic_file, 'rb') as go_fh:
        for line in go_fh:
            line = line.decode().strip("\n")
            if line == '[Term]':
                go_id = ''
                go_name = ''
                go_namespace = ''
            elif line.startswith("id: GO:"):
                go_id = line[4:]
            elif line.startswith("name: "):
                go_name = line[6:]
            elif line.startswith("namespace: "):
                go_namespace = line[11:]
                go_dict[go_id] = {}
                go_dict[go_id]['name'] = go_name
                go_dict[go_id]['namespace'] = go_namespace  
            elif line.startswith("alt_id: GO:"):
                go_id = line[8:]
                go_dict[go_id] = {}
                go_dict[go_id]['name'] = go_name
                go_dict[go_id]['namespace'] = go_namespace
            else:
                pass
    return go_dict

'''
 generate_go_doc: generate Gene Ontology doc for sqlite
'''
def generate_go_doc(go_txt_file, go_basic_file):

    ''' ontology to dict '''
    go_dict = load_go_basic(go_basic_file)

    ''' gaf to dict '''
    transcript_go = {}
    with open(go_txt_file, 'r') as gaf_fh:
        for line in gaf_fh:
            if line[0] == '!':
                continue
            m = line.strip("\n").split("\t")
            transcript_id = m[0]
            go_ids = m[1].split(";")
            transcript_go[transcript_id] = []
    
            for go_id in go_ids:
                go_id = go_id.strip()
                if go_id in go_dict:
                    go_name = go_dict[go_id]['name']
                    go_namespace = go_dict[go_id]['namespace']

                    go_term = {}
                    go_term['term'] = go_id
                    go_term['name'] = go_name
                    go_term['namespace'] = go_namespace
                    transcript_go[transcript_id].append(go_term)
                else:
                    print("ERR: GO ID %s is not in %s file." % (go_id, go_basic_file))
                    sys.exit()

    for transcript_id, go_terms in transcript_go.items():
        if isinstance(go_terms, list):
            transcript_go[transcript_id] = json.dumps(go_terms)

    return transcript_go



