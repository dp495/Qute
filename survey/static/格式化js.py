import json

def myhash(str: str) -> int:
    P = 19260817
    # M = int(1e9-999)
    # both P and M are prime numbers
    hash = len(str) * P and 0xffffffff
    for c in str:
        hash = (hash * P ^ ord(c)) and 0xffffffff
    return hash

with open(r'q-large.json',mode='r',encoding='utf8') as jfile:
    qlarge = json.loads(jfile.read())

for page in qlarge:
    for question in page:
        question['choices'].sort(key=lambda item: myhash(item['text']))
        i = 0
        for line in question['choices']:
            line['index'] = i
            i += 1

with open(r'q-large.json',mode='w',encoding='utf8') as jfile:
    jfile.write(json.dumps(qlarge,ensure_ascii=False,indent=2))