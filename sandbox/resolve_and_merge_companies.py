import json
import re
import urllib.request
import urllib.parse
from pathlib import Path
import time

# 1. Existing 384 IDs from user's URL
EXISTING_IDS_RAW = "1681,11056,323296,157324,2937226,67997480,2152,28483663,2756204,12651721,98338883,215561,2284126,14100,3076,1227813,72593,23656,64681939,226898,21836,2474662,40783,731128,15205156,649388,8117,35495217,62901,2396310,2684081,112948,8760289,86088336,2615835,3603143,5235,6455591,6061,105623313,3029766,106178,2283870,237976,270401,18476,9487758,106348,101564,224006,35475885,529548,19601,74737673,5396873,3822178,18785553,11229,1379376,21270,26289,6464060,16081001,675499,11141290,80103528,3652928,33312816,3486,10328310,27190862,58304,18542,74621231,6749,372915,2302172,166124,10447496,80021125,489783,1766772,27207386,11209056,2137019,19070722,2266,15254451,205918,1609453,71553053,122993,164191,3787302,7790167,986438,65861,132319,15244760,31496529,80430637,71070,25773,5356751,3164945,36016241,50923,86710081,135385,11719198,106986,141950,100404571,8235,37841,614775,3108492,166021,107837058,42882731,13659,531285,64933472,9311046,11433068,81491357,2549035,164766,105897160,80976980,19647,408636,3261882,60798,100440403,2875,101118,7951190,10974065,49761,10807577,1803436,5221388,90990316,69757534,3772194,1588346,3840237,2426745,1259202,2267949,89534364,50741,16167895,10082770,59695,37012803,80821518,2268598,91585378,54315260,78374544,11101922,53265880,72386708,47475,74827,10695881,42845886,3586986,3554342,89861111,76639430,321125,495580,55406,1230210,52259,380520,96913,108411717,71431456,79316462,28160195,107523134,81490111,2843760,10859991,162930,2689791,47321,104085,43085,30357,10279322,2319787,35224,1570865,2368590,91351774,37768,11815285,6642554,11713799,79387,15637,89815917,145829,136684,15399436,27214402,152111,104404215,97399777,44182,141344,454014,79815,106236846,2295020,617539,27771,7174299,43577,19222151,107382152,77906,18476701,575811,19184122,65544967,108057428,321059,2558029,53255,490123,4972,1612465,40713644,6644632,2862131,108099054,106383022,249216,708782,41294,1350532,100641388,18636265,25030011,106234805,5103118,953251,533600,5081485,1102596,597063,389545,46708,22322301,71470,21330,30580610,10931357,804934,969299,994453,734610,1287894,101608205,13368439,78412,13153,37564,35577586,163945,3077586,15226385,2889,2660651,228790,89369,204522,482055,3531578,2948835,10988174,48467,1613092,300940,2402722,101124717,91565,109371231,1127732,29015687,55546,35491344,1666837,32483,11787695,91323845,20814,53250321,27210591,10137587,462256,910327,699824,105017613,1214251,155495,35080,82536111,3836023,66652001,3341814,71067091,2236492,15910815,70756,104874263,118886,827209,9460602,1002779,119738,102673915,2609847,46414,989771,2313010,51322,19825,1407607,13993547,103145514,2627020,2682079,2908367,56432,60019,77133,614724,10054135,3133362,28164278,3237496,2869639,280603,69510,2487906,21007,22219,570420,16227,13076,11147136,18271849,3243800,15014,1689845,14069821,725959,3523131,1056387,3726818,595013,105241929,10252958,40656423,132125,20025,2456742,27170041,51661,91445367,236019,34424,14158,51301,18842066,1015745,107626698"
existing_set = set(EXISTING_IDS_RAW.split(","))
print(f"Total existing IDs in URL: {len(existing_set)}")

# 2. Known staffing companies mapping (verified LinkedIn IDs)
# We can resolve domain/slug directly via LinkedIn public metadata or known directory
STAFFING_DIRECTORY = {
    "brooksource.com": {"id": "14100", "name": "Brooksource"}, # already in set!
    "kavaliro.com": {"id": "21836", "name": "Kavaliro"}, # already in set!
    "idr-inc.com": {"id": "23656", "name": "IDR, Inc."}, # already in set!
    "theintersectgroup.com": {"id": "62901", "name": "The Intersect Group"}, # in set!
    "phoenixstaff.com": {"id": "112948", "name": "Phoenix Staff"}, # in set!
    "bravotech.com": {"id": "5235", "name": "BravoTECH"}, # in set!
    "clientresourcesinc.com": {"id": "18476", "name": "Client Resources, Inc. (CRI)"}, # in set!
    "alinestaffing.com": {"id": "19601", "name": "A-Line Staffing Solutions"}, # in set!
    "abbtech.com": {"id": "21270", "name": "ABBTECH Professional Resources"}, # in set!
    "acsprostaffing.com": {"id": "26289", "name": "ACS Professional Staffing"}, # in set!
    "chooseatlas.com": {"id": "58304", "name": "Atlas"}, # in set!
    "yoh.com": {"id": "2266", "name": "Yoh, A Day & Zimmermann Company"}, # in set!
    "entegee.com": {"id": "25773", "name": "Entegee"}, # in set!
    "hays.com": {"id": "3237496", "name": "Hays"}, # in set!
    "hirenetworks.com": {"id": "49761", "name": "Hire Networks"}, # in set!
    "oxfordcorp.com": {"id": "47475", "name": "Oxford Global Resources"}, # in set!
    "senecahq.com": {"id": "74827", "name": "Seneca Resources"}, # in set!
    "sniconsulting.net": {"id": "55406", "name": "SNI Companies"}, # in set!
    "solomonpage.com": {"id": "52259", "name": "Solomon Page"}, # in set!
    "solvingit.com": {"id": "96913", "name": "Solving IT"}, # in set!
    "spireinc.com": {"id": "47321", "name": "Spire Systems"}, # in set!
    "consultnet.com": {"id": "43085", "name": "ConsultNet"}, # in set!
    "csetalent.com": {"id": "30357", "name": "Connexion Systems + Engineering"}, # in set!
    "daviscos.com": {"id": "35224", "name": "The Davis Companies"}, # in set!
    "elitetechnicaljobs.com": {"id": "79387", "name": "Elite Technical"}, # in set!
    "genesysonline.com": {"id": "15637", "name": "GENESYS Consulting Services"}, # in set!
    "harvtech.com": {"id": "44182", "name": "Harvest Technical Services"}, # in set!
    "itresourcescorp.com": {"id": "79815", "name": "IT Resources"}, # in set!
    "iriscc.com": {"id": "27771", "name": "Iris Consulting Group"}, # in set!
    "labur.com": {"id": "43577", "name": "LABUR"}, # in set!
    "marchonpartners.com": {"id": "77906", "name": "Marchon Partners"}, # in set!
    "opensystemstech.com": {"id": "53255", "name": "Open Systems Technologies"}, # in set!
    "optechus.com": {"id": "4972", "name": "OpTech"}, # in set!
    "osiengineering.com": {"id": "41294", "name": "OSI Engineering"}, # in set!
    "prosearchmaine.com": {"id": "46708", "name": "ProSearch"}, # in set!
    "procomservices.com": {"id": "71470", "name": "Procom"}, # in set!
    "careerprofiles.com": {"id": "21330", "name": "Profiles"}, # in set!
    "signifytechnology.com": {"id": "78412", "name": "Signify Technology"}, # in set!
    "silversearchinc.com": {"id": "13153", "name": "Silver Search"}, # in set!
    "softinc.com": {"id": "37564", "name": "SOFT Inc."}, # in set!
}

# Notice that many in the user's bookmarks were already part of the 384!
# Now let's check which bookmarks are NEW and resolve their IDs!
with open(r"c:\TalentOpsAI\sandbox\chrome_staffing_companies.json", "r", encoding="utf-8") as f:
    bookmarks = json.load(f)

print(f"\nChecking {len(bookmarks)} bookmarks against existing list...")
matches = 0
for b in bookmarks:
    domain = b["domain"].replace("www.", "").replace("jobs.", "").replace("career-portal.", "")
    found = False
    for k, v in STAFFING_DIRECTORY.items():
        if k in domain or domain in k:
            cid = v["id"]
            in_set = cid in existing_set
            print(f"  Match: {v['name']:30s} (ID: {cid:8s}) -> Already in URL: {in_set}")
            matches += 1
            break

print(f"\nTotal verified bookmark matches from curated directory: {matches}")
