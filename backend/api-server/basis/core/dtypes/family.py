import os
import sys
import re
import gzip
import json

'''
 generate_family_doc: generate family doc for sqlite
'''
def generate_family_doc(family_file, database):
    ''' family to doc '''
    transcript_family = {}
    with open(family_file, 'r') as family_fh:
        for line in family_fh:
            if line[0] == '#':
                continue
            m = line.strip("\n").split("\t")
            transcript_id = m[0]
            family_dict = {'name': m[1], 'type': m[2], 'database': database}

            if transcript_id in transcript_family:
                transcript_family[transcript_id].append(family_dict)
            else:
                transcript_family[transcript_id] = []
                transcript_family[transcript_id].append(family_dict)

    print('Done loading gene family.')

    for transcript_id, family in transcript_family.items():
        if isinstance(family, list):
            transcript_family[transcript_id] = json.dumps(family)
    
    return transcript_family




