# -*- coding: utf-8 -*-
"""犬子老師雷達 Sector Taxonomy 2.1。

Production 唯一族群 resolver。
- official industry 是 fallback，不等於窄族群。
- primary_group 才能進核心族群分。
- secondary/theme 只做解釋與搜尋，不重複灌分。
- confidence <80 或 peer_count <3 時回傳 None，讓既有 scorer 退回官方產業 proxy。
- 主分類代號衝突直接 fail closed，不再 setdefault 靜默吃第一個。
"""
from __future__ import annotations
from collections import Counter

TAXONOMY_VERSION="2.1.0"
PRIMARY_GROUP_MIN_CONFIDENCE=80
SECONDARY_GROUP_MIN_CONFIDENCE=70
PRIMARY_GROUP_MIN_PEERS=3

INDUSTRY_NAMES={
"01":"水泥工業","02":"食品工業","03":"塑膠工業","04":"紡織纖維","05":"電機機械","06":"電器電纜",
"08":"玻璃陶瓷","09":"造紙工業","10":"鋼鐵工業","11":"橡膠工業","12":"汽車工業","14":"建材營造",
"15":"航運業","16":"觀光餐旅","17":"金融保險","18":"貿易百貨","19":"綜合","20":"其他","21":"化學工業",
"22":"生技醫療","23":"油電燃氣","24":"半導體業","25":"電腦及週邊設備業","26":"光電業","27":"通信網路業",
"28":"電子零組件業","29":"電子通路業","30":"資訊服務業","31":"其他電子業","32":"文化創意","33":"農業科技",
"34":"電子商務","35":"綠能環保","36":"數位雲端","37":"運動休閒","38":"居家生活"}

PRIMARY_GROUPS={
    'PCB／多層板': "2313 2355 2367 2368 3044 3715 4927 4958 5469 6191 8155".split(),
    'CCL／銅箔': "2383 6213 6274 8358".split(),
    'ABF載板': "3037 3189 8046".split(),
    'PCB設備／耗材': "1595 3455 3563 6664 8021".split(),
    'AI伺服器ODM': "2317 2356 2382 3231 3706 6669".split(),
    '伺服器機構件／滑軌': "2059 3013 6117 8210".split(),
    '電源／UPS': "2301 2308 3078 6282 6409 6412".split(),
    'BBU／電池備援': "3211 3323 6121 6781".split(),
    '散熱': "2421 3017 3324 3338 3483 3653 6230 8996".split(),
    '高速連接／線材': "3023 3533 3605 3665 6197 6290".split(),
    'CPO／光通訊': "3081 3163 3234 3363 3450 4908 4971 4979 6426 6442".split(),
    '晶圓代工': "2303 2330 5347 6770".split(),
    'IC封裝測試': "2329 2449 3265 3372 3374 3711 6147 6239 6257 6271 6451 8131 8150".split(),
    'ASIC／IC設計服務／IP': "3035 3443 3529 3661 6533 6643 8227".split(),
    'IC設計': "2379 2401 2436 2454 2458 3014 3034 3141 3227 3545 3592 4919 4961 4966 5269 5274 5471 6104 6138 6202 6415 6462 6526 6679 6719 8016 8054 8081".split(),
    '記憶體IC': "2337 2344 2408 3006 5351 6531".split(),
    '儲存控制／模組': "2451 3260 4967 4973 8271 8299".split(),
    '功率半導體': "2481 3317 3675 3707 5425 6435 8261".split(),
    '化合物半導體／磊晶': "2455 3016 3105 4991 8086".split(),
    '矽晶圓': "3532 5483 6182 6488".split(),
    '半導體測試介面': "3581 6223 6510 6515 6683".split(),
    '半導體設備': "2467 3131 3413 3583 3680 5443 6187 6532 6640 6788 6937 7734 7751 7769".split(),
    '半導體廠務／工程': "2404 5536 6139 6196 6613 6667 6691 6903".split(),
    '半導體材料／電子化學': "1727 1785 4749 4768 4772 5234".split(),
    '被動元件': "2327 2375 2492 3026 6173 8042".split(),
    '網通設備': "2345 2419 3062 3596 3704 4906 5388 6285".split(),
    '主機板／PC硬體': "2357 2376 2377 3515 4938".split(),
    '工業電腦': "2395 3022 6166 6414 6579 8050".split(),
    '自動化／線性傳動': "1590 1597 2049 4540 4576 7750".split(),
    '重電／電網': "1503 1504 1513 1514 1519 2371".split(),
    '電線電纜': "1605 1608 1609 2061".split(),
    '航太／國防': "2634 3004 4541 8033 8222".split(),
}
GROUP_CONFIDENCE={g:90 for g in PRIMARY_GROUPS}
GROUP_CONFIDENCE.update({'IC設計':85,'半導體廠務／工程':85,'半導體材料／電子化學':85,'主機板／PC硬體':85,'航太／國防':85})

SECONDARY_GROUPS={
'1303':[{'confidence':78,'exposure_note':'電子材料/銅箔基板相關業務存在，但公司營運高度多角化，不列主族群核心計分。','group':'CCL／電子材料'}],
'2301':[{'confidence':82,'exposure_note':'伺服器電源為重要應用。','group':'AI伺服器電源'}],
'2308':[{'confidence':88,'exposure_note':'AI伺服器電源為重要應用，但公司主業更廣。','group':'AI伺服器電源'}],
'2317':[{'confidence':85,'exposure_note':'AI伺服器為重要應用，但主分類維持ODM。','group':'AI伺服器供應鏈'}],
'2379':[{'confidence':88,'exposure_note':'網通/連線晶片為重要產品線；保留為次分類，避免與IC設計主群重複灌分。','group':'網通IC'}],
'2382':[{'confidence':90,'exposure_note':'AI伺服器為主要成長應用。','group':'AI伺服器供應鏈'}],
'3017':[{'confidence':90,'exposure_note':'AI伺服器散熱為核心成長應用。','group':'AI伺服器散熱'}],
'3231':[{'confidence':90,'exposure_note':'AI伺服器為主要成長應用。','group':'AI伺服器供應鏈'}],
'3324':[{'confidence':90,'exposure_note':'AI伺服器散熱為核心成長應用。','group':'AI伺服器散熱'}],
'3653':[{'confidence':85,'exposure_note':'伺服器高階散熱/機構零件應用。','group':'AI伺服器散熱'}],
'4966':[{'confidence':90,'exposure_note':'高速介面晶片曝險。','group':'高速傳輸IC'}],
'5269':[{'confidence':90,'exposure_note':'高速I/O控制晶片曝險。','group':'高速傳輸IC'}],
'6282':[{'confidence':80,'exposure_note':'伺服器電源為重要應用。','group':'AI伺服器電源'}],
'6412':[{'confidence':82,'exposure_note':'伺服器電源為重要應用。','group':'AI伺服器電源'}],
'6526':[{'confidence':85,'exposure_note':'連線/網通晶片曝險。','group':'網通IC'}],
'6669':[{'confidence':95,'exposure_note':'AI伺服器為核心營運曝險。','group':'AI伺服器供應鏈'}],
'8996':[{'confidence':85,'exposure_note':'液冷/熱交換相關應用。','group':'AI伺服器散熱'}]}
THEME_TAGS={
'1503':['電網建設'],'1504':['自動化／機器人','電網建設'],'1513':['電網建設'],'1514':['電網建設'],'1519':['電網建設'],
'1590':['自動化／機器人'],'1597':['自動化／機器人'],'1605':['電網建設'],'1608':['電網建設'],'1609':['電網建設'],
'2049':['自動化／機器人'],'2061':['電網建設'],'2301':['AI'],'2308':['AI','自動化／機器人'],'2313':['AI'],'2317':['AI'],
'2356':['AI'],'2368':['AI'],'2371':['電網建設'],'2382':['AI'],'2383':['AI'],'2634':['國防航太'],'3004':['國防航太'],
'3017':['AI'],'3037':['AI'],'3044':['AI'],'3081':['AI','CPO／光通訊'],'3163':['AI','CPO／光通訊'],'3189':['AI'],
'3211':['AI'],'3231':['AI'],'3234':['CPO／光通訊'],'3323':['AI'],'3324':['AI'],'3363':['AI','CPO／光通訊'],
'3450':['AI','CPO／光通訊'],'3653':['AI'],'3706':['AI'],'4540':['自動化／機器人'],'4541':['國防航太'],
'4576':['自動化／機器人'],'4908':['CPO／光通訊'],'4971':['CPO／光通訊'],'4979':['AI','CPO／光通訊'],
'6121':['AI'],'6274':['AI'],'6282':['AI'],'6412':['AI'],'6426':['CPO／光通訊'],'6442':['AI','CPO／光通訊'],
'6669':['AI'],'6781':['AI'],'7750':['自動化／機器人'],'8033':['國防航太'],'8046':['AI'],'8222':['國防航太'],'8996':['AI']}
SECONDARY_ONLY={'1303'}

def industry_name_for(industry):
    key=str(industry or '').strip()
    return INDUSTRY_NAMES.get(key,key if key and key!='nan' else '未分類')

def _build_primary_index():
    out={}
    for group,codes in PRIMARY_GROUPS.items():
        for code in codes:
            if code in out:
                raise RuntimeError(f'Sector Taxonomy {TAXONOMY_VERSION} duplicate primary code {code}: {out[code]} vs {group}')
            out[code]=group
    return out

CODE_TO_GROUP=_build_primary_index()
GROUP_SIZES=dict(Counter(CODE_TO_GROUP.values()))

def classification_for(code,name=None,industry=None):
    code=str(code or '').strip(); official=industry_name_for(industry); group=CODE_TO_GROUP.get(code)
    conf=float(GROUP_CONFIDENCE[group]) if group else None
    peer_count=int(GROUP_SIZES.get(group,0)) if group else 0
    eligible=bool(group and conf>=PRIMARY_GROUP_MIN_CONFIDENCE and peer_count>=PRIMARY_GROUP_MIN_PEERS)
    if eligible: status,score_source='VERIFIED','PRIMARY_GROUP'
    elif group: status='PROVISIONAL'; score_source='OFFICIAL_PROXY' if official!='未分類' else 'NONE'
    elif official!='未分類': status,score_source='OFFICIAL_ONLY','OFFICIAL_PROXY'
    else: status,score_source='UNCLASSIFIED','NONE'
    secondary=[dict(x) for x in SECONDARY_GROUPS.get(code,[]) if float(x.get('confidence') or 0)>=SECONDARY_GROUP_MIN_CONFIDENCE]
    return {'taxonomy_version':TAXONOMY_VERSION,'code':code,'name':str(name or code),'official_industry':official,
        'primary_group':group,'primary_group_confidence':conf,'secondary_groups':secondary,'theme_tags':list(THEME_TAGS.get(code,[])),
        'supply_chain_role':[group] if group else [],'classification_status':status,
        'classification_reason':(f'Taxonomy {TAXONOMY_VERSION} 主分類：{group}；高信心且同儕樣本足夠才進核心族群分。' if group else ('尚無高信心窄主族群；使用官方產業 proxy。' if official!='未分類' else '分類證據不足。')),
        'peer_count':peer_count,'score_source':score_source,'core_sector_score_eligible':eligible}

def sector_group_for(code,name=None,industry=None):
    c=classification_for(code,name=name,industry=industry)
    return c['primary_group'] if c['core_sector_score_eligible'] else None

def sector_confidence_for(code,name=None,industry=None):
    return classification_for(code,name=name,industry=industry)['primary_group_confidence']

def taxonomy_stats():
    eligible=sum(1 for code in CODE_TO_GROUP if classification_for(code)['core_sector_score_eligible'])
    return {'taxonomy_version':TAXONOMY_VERSION,'registry_entries':len(set(CODE_TO_GROUP)|SECONDARY_ONLY),'primary_groups':len(PRIMARY_GROUPS),
        'eligible_primary_codes':eligible,'primary_group_min_confidence':PRIMARY_GROUP_MIN_CONFIDENCE,'secondary_group_min_confidence':SECONDARY_GROUP_MIN_CONFIDENCE,
        'primary_group_min_peers':PRIMARY_GROUP_MIN_PEERS,'group_sizes':dict(sorted(GROUP_SIZES.items()))}
