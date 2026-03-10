import random
def handleNodes(data):
    learnPoint = []
    for _ in data:
        for _1 in _['section_leaf_list']:
            if _1.get('leaf_list',{}):
                for _2 in _1['leaf_list']:
                    learnPoint.append(_2)
            else:
                learnPoint.append(_1)
    return learnPoint



def generate_original_id() -> str:
    template = "xxxxxyxxxxxyxx4xxxyxxxxxyxxxxxyxxxxx"
    result = []
    for ch in template:
        if ch in ("x", "y"):
            a = random.randint(0, 15)  # 对应 JS: 16 * Math.random() | 0
            v = a if ch == "x" else ((a & 0x3) | 0x8)  # 对应 JS: x ? a : (a & 3 | 8)
            result.append(format(v, "x"))
        else:
            result.append(ch)
    return "".join(result)
