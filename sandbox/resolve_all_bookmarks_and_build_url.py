import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import json
import re
import urllib.request
import urllib.parse
from pathlib import Path
import time
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

EXISTING_IDS_RAW = "1681,11056,323296,157324,2937226,67997480,2152,28483663,2756204,12651721,98338883,215561,2284126,14100,3076,1227813,72593,23656,64681939,226898,21836,2474662,40783,731128,15205156,649388,8117,35495217,62901,2396310,2684081,112948,8760289,86088336,2615835,3603143,5235,6455591,6061,105623313,3029766,106178,2283870,237976,270401,18476,9487758,106348,101564,224006,35475885,529548,19601,74737673,5396873,3822178,18785553,11229,1379376,21270,26289,6464060,16081001,675499,11141290,80103528,3652928,33312816,3486,10328310,27190862,58304,18542,74621231,6749,372915,2302172,166124,10447496,80021125,489783,1766772,27207386,11209056,2137019,19070722,2266,15254451,205918,1609453,71553053,122993,164191,3787302,7790167,986438,65861,132319,15244760,31496529,80430637,71070,25773,5356751,3164945,36016241,50923,86710081,135385,11719198,106986,141950,100404571,8235,37841,614775,3108492,166021,107837058,42882731,13659,531285,64933472,9311046,11433068,81491357,2549035,164766,105897160,80976980,19647,408636,3261882,60798,100440403,2875,101118,7951190,10974065,49761,10807577,1803436,5221388,90990316,69757534,3772194,1588346,3840237,2426745,1259202,2267949,89534364,50741,16167895,10082770,59695,37012803,80821518,2268598,91585378,54315260,78374544,11101922,53265880,72386708,47475,74827,10695881,42845886,3586986,3554342,89861111,76639430,321125,495580,55406,1230210,52259,380520,96913,108411717,71431456,79316462,28160195,107523134,81490111,2843760,10859991,162930,2689791,47321,104085,43085,30357,10279322,2319787,35224,1570865,2368590,91351774,37768,11815285,6642554,11713799,79387,15637,89815917,145829,136684,15399436,27214402,152111,104404215,97399777,44182,141344,454014,79815,106236846,2295020,617539,27771,7174299,43577,19222151,107382152,77906,18476701,575811,19184122,65544967,108057428,321059,2558029,53255,490123,4972,1612465,40713644,6644632,2862131,108099054,106383022,249216,708782,41294,1350532,100641388,18636265,25030011,106234805,5103118,953251,533600,5081485,1102596,597063,389545,46708,22322301,71470,21330,30580610,10931357,804934,969299,994453,734610,1287894,101608205,13368439,78412,13153,37564,35577586,163945,3077586,15226385,2889,2660651,228790,89369,204522,482055,3531578,2948835,10988174,48467,1613092,300940,2402722,101124717,91565,109371231,1127732,29015687,55546,35491344,1666837,32483,11787695,91323845,20814,53250321,27210591,10137587,462256,910327,699824,105017613,1214251,155495,35080,82536111,3836023,66652001,3341814,71067091,2236492,15910815,70756,104874263,118886,827209,9460602,1002779,119738,102673915,2609847,46414,989771,2313010,51322,19825,1407607,13993547,103145514,2627020,2682079,2908367,56432,60019,77133,614724,10054135,3133362,28164278,3237496,2869639,280603,69510,2487906,21007,22219,570420,16227,13076,11147136,18271849,3243800,15014,1689845,14069821,725959,3523131,1056387,3726818,595013,105241929,10252958,40656423,132125,20025,2456742,27170041,51661,91445367,236019,34424,14158,51301,18842066,1015745,107626698"

existing_ids = [x.strip() for x in EXISTING_IDS_RAW.split(",") if x.strip()]
existing_set = set(existing_ids)
print(f"Loaded {len(existing_set)} existing company IDs from URL.")

with open(r"c:\TalentOpsAI\sandbox\chrome_staffing_companies.json", "r", encoding="utf-8") as f:
    bookmarks = json.load(f)

print(f"Loaded {len(bookmarks)} company bookmarks from Chrome.")

new_ids = []
resolved_map = {}

# Specific manual resolutions for bookmarks from screenshots
MANUAL_RESOLVED = {
    "cullertongroup.com": ("Cullerton Group", "28985285"),
    "talentfish.com": ("TalentFish", "56405890"),
    "completestaffingsolutions.com": ("Complete Staffing Solutions", "1457175"),
    "calculatedhire.com": ("Calculated Hire", "6575603"),
    "carexconsulting.com": ("Carex Consulting Group", "10974065"),
    "innovien.com": ("Innovien Solutions", "16260045"),
    "phaxis.com": ("Phaxis", "106083"),
    "solvingit.com": ("Solving IT", "95639"),
    "prosearchmaine.com": ("ProSearch", "85153"),
    "bct-corp.com": ("BCT IT Solutions", "1826040"),
    "bstonetalent.com": ("Blackstone Talent Group", "48467"),
    "burnettspecialists.com": ("Burnett Specialists", "50741"),
    "cornerstonetechtalent.com": ("CornerStone Technology Talent", "2487906"),
    "corpsteam.com": ("Corps Team", "10447496"),
    "doylegroup-it.com": ("Doyle Group", "226898"),
    "joineei.com": ("Enterprise Engineering Inc", "215561"),
    "elevationhr-talentstack.tal.net": ("ElevationHR", "380520"),
    "fueltalent.com": ("Fuel Talent", "15205156"),
    "gforcelifesciences.com": ("GForce Life Sciences", "15244760"),
    "hendersonscott.com": ("Henderson Scott", "1259202"),
    "hightrail.com": ("HighTrail", "105623313"),
    "hkaa.com": ("HKA Enterprises", "72593"),
    "lunadatasolutions.com": ("Luna Data Solutions", "489783"),
    "mmdtech.com": ("MMD Services", "675499"),
    "partners-consulting.com": ("Partner's Consulting", "18542"),
    "peakperformers.org": ("Peak Performers", "1379376"),
    "pmopartners.com": ("PMO Partners", "27207386"),
    "perennialresources.com": ("Perennial Resources", "205918"),
    "odysseyis.com": ("Odyssey Information Services", "166124"),
    "stottandmay.com": ("Stott and May", "6464060"),
    "sandcherry.com": ("Sand Cherry Associates", "164191"),
    "dcshq.com": ("Dynamic Computing Services", "2756204"),
    "burtchworks.com": ("Burtch Works", "12651721"),
    "partnersinstaffing.com": ("Pinnacle Partners", "98338883"),
    "bridgesourcesolutions.com": ("BridgeSource Solutions", "80103528"),
    "equal-plus.com": ("Equal Plus", "64681939")
}

added_count = 0
for domain, (name, cid) in MANUAL_RESOLVED.items():
    if cid not in existing_set:
        existing_set.add(cid)
        new_ids.append(cid)
        resolved_map[cid] = name
        added_count += 1
        print(f"  [NEW ADDED] {name} (ID: {cid})")
    else:
        print(f"  [ALREADY IN LIST] {name} (ID: {cid})")

print(f"\nSuccessfully added {added_count} brand-new companies from your bookmarks!")
print(f"Total merged company IDs: {len(existing_set)}")

# Re-assemble the new f_C parameter
all_merged_ids = list(existing_set)
new_fc_param = ",".join(all_merged_ids)

# Build the complete URL
BASE_SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/?"
    "keywords=jobs&"
    "geoId=103644278&"
    "f_TPR=r86400&"
    f"f_C={urllib.parse.quote(new_fc_param)}&"
    "f_SAL=f_SA_id_226001%3A273001%2C274001%2C272002"
)

out_file = Path(r"c:\TalentOpsAI\sandbox\updated_linkedin_jobs_url.txt")
with open(out_file, "w", encoding="utf-8") as f:
    f.write(BASE_SEARCH_URL)

print(f"\nUpdated URL written to: {out_file}")
print(f"Total URL length: {len(BASE_SEARCH_URL)} characters")
