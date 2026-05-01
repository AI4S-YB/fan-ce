from collections import defaultdict

"""
 split_xml and etree_to_dist are used for parsing XML file 
"""
def robust_decode_line(line):
    """健壮的行解码函数"""
    if isinstance(line, str):
        return line.strip("\n")
    
    # 尝试多种解码策略
    strategies = [
        ('utf-8', 'strict'),
        ('utf-8', 'ignore'), 
        ('latin-1', 'strict'),
        ('gbk', 'ignore')
    ]
    
    for encoding, errors in strategies:
        try:
            return line.decode(encoding, errors=errors).strip("\n")
        except (UnicodeDecodeError, LookupError):
            continue
    
    # 最后备选
    return line.decode('utf-8', errors='replace').strip("\n")

def split_xml(xml_fh, keyword):
    iteration_xml = ''
    iteration_switch = 0

    for line in xml_fh:
        line = robust_decode_line(line)
        line_str = line.lstrip()

        if line_str == "<" + keyword + ">":
            iteration_switch = 1
            iteration_xml = line + "\n"
        elif line_str == "</" + keyword + ">":
            iteration_switch = 0
            iteration_xml += line + "\n"
            yield iteration_xml
        else:
            if iteration_switch == 1:
                iteration_xml += line + "\n"

def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v
                     for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v)
                        for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
              d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d