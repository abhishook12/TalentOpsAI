from __future__ import annotations

import json
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.models import Recruiter


BATCH_KEY = f"email_domain_hq_backfill_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

DOMAIN_MAP = {
    "brooksource.com": {
        "location": "Indianapolis, IN",
        "state": "IN",
        "source_url": "https://www.brooksource.com/locations/headquarters.html",
        "source_note": "Official Brooksource headquarters page",
    },
    "randstadusa.com": {
        "location": "Atlanta, GA",
        "state": "GA",
        "source_url": "https://www.randstadusa.com/about/",
        "source_note": "Official Randstad USA about page with registered office",
    },
    "judge.com": {
        "location": "Wayne, PA",
        "state": "PA",
        "source_url": "https://www.judge.com/about-judge/locations/wayne/",
        "source_note": "Official Judge location page for Wayne office / headquarters",
    },
    "insightglobal.com": {
        "location": "Atlanta, GA",
        "state": "GA",
        "source_url": "https://insightglobal.com/locations/georgia/staffing-agency-atlanta-ga/",
        "source_note": "Official Insight Global Atlanta page stating headquarters in Atlanta, GA",
    },
    "roberthalf.com": {
        "location": "Menlo Park, CA",
        "state": "CA",
        "source_url": "https://www.roberthalf.com/us/en/about/investor-center/contact-us",
        "source_note": "Official Robert Half investor contact page with corporate headquarters",
    },
    "kforce.com": {
        "location": "Tampa, FL",
        "state": "FL",
        "source_url": "https://www.kforce.com/contact-us/",
        "source_note": "Official Kforce contact page with corporate headquarters",
    },
    "beaconhillstaffing.com": {
        "location": "Boston, MA",
        "state": "MA",
        "source_url": "https://beaconhillstaffing.com/",
        "source_note": "Official Beacon Hill homepage with corporate office",
    },
    "sigconsult.com": {
        "location": "McLean, VA",
        "state": "VA",
        "source_url": "https://dexian.com/contact/",
        "source_note": "sigconsult.com redirects to Dexian; official Dexian contact page lists corporate headquarters",
    },
    "eclaro.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.eclaro.com/contact-us",
        "source_note": "Official ECLARO contact page with global headquarters",
    },
    "medixteam.com": {
        "location": "Oak Brook, IL",
        "state": "IL",
        "source_url": "https://www.medixteam.com/medixlocation/chicago-il/",
        "source_note": "Official Medix headquarters location page",
    },
    "idr-inc.com": {
        "location": "Alpharetta, GA",
        "state": "GA",
        "source_url": "https://www.idr-inc.com/contact-us/",
        "source_note": "Official IDR contact page listing Atlanta headquarters in Alpharetta, GA",
    },
    "vaco.com": {
        "location": "Brentwood, TN",
        "state": "TN",
        "source_url": "https://jobs.vaco.com/home?on_site=Remote",
        "source_note": "Official Vaco careers footer listing global headquarters",
    },
    "yoh.com": {
        "location": "Philadelphia, PA",
        "state": "PA",
        "source_url": "https://www.yoh.com/about/our-locations",
        "source_note": "Official Yoh locations page listing Philadelphia physical location",
    },
    "eliassen.com": {
        "location": "Reading, MA",
        "state": "MA",
        "source_url": "https://www.eliassen.com/contact",
        "source_note": "Official Eliassen contact page listing corporate headquarters",
    },
    "mitchellmartin.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.mitchellmartin.com/contact",
        "source_note": "Official Mitchell Martin contact page listing corporate headquarters",
    },
    "itmmi.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.mitchellmartin.com/contact",
        "source_note": "Official Mitchell Martin contact page listing corporate headquarters and itmmi.com support emails",
    },
    "tandymgroup.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.tandymgroup.com/staffing-and-recruiting-locations/",
        "source_note": "Official Tandym locations page listing New York office address",
    },
    "teksystems.com": {
        "location": "Hanover, MD",
        "state": "MD",
        "source_url": "https://www.teksystems.com/en/contact-us",
        "source_note": "Official TEKsystems contact page listing corporate headquarters",
    },
    "optomi.com": {
        "location": "Atlanta, GA",
        "state": "GA",
        "source_url": "https://www.optomi.com/locations",
        "source_note": "Official Optomi locations page listing Atlanta HQ",
    },
    "apexsystems.com": {
        "location": "Glen Allen, VA",
        "state": "VA",
        "source_url": "https://www.apexsystems.com/contact-us",
        "source_note": "Official Apex Systems contact page listing corporate office",
    },
    "consultnet.com": {
        "location": "South Jordan, UT",
        "state": "UT",
        "source_url": "https://consultnet.com/services-contact/",
        "source_note": "Official ConsultNet contact page listing corporate headquarters",
    },
    "kellyservices.com": {
        "location": "Troy, MI",
        "state": "MI",
        "source_url": "https://www.kellyservices.com/contact-us/",
        "source_note": "Official Kelly Services contact page listing world headquarters",
    },
    "rht.com": {
        "location": "Menlo Park, CA",
        "state": "CA",
        "source_url": "https://www.rht.com/",
        "source_note": "rht.com is Robert Half Technology branding; Robert Half corporate headquarters previously verified as Menlo Park, CA",
    },
    "csicompanies.com": {
        "location": "Jacksonville, FL",
        "state": "FL",
        "source_url": "https://www.csicompanies.com/contact-us",
        "source_note": "Official CSI Companies contact page listing corporate headquarters",
    },
    "actalentservices.com": {
        "location": "Hanover, MD",
        "state": "MD",
        "source_url": "https://www.actalentservices.com/en/contact-us/jobseeker",
        "source_note": "Official Actalent contact page listing headquarters",
    },
    "workday.com": {
        "location": "Pleasanton, CA",
        "state": "CA",
        "source_url": "https://www.workday.com/en-us/company/about-workday/contact-us.html",
        "source_note": "Official Workday contact page listing headquarters",
    },
    "prestigestaffing.com": {
        "location": "Atlanta, GA",
        "state": "GA",
        "source_url": "https://www.prestigestaffing.com/contact/",
        "source_note": "Official Prestige Staffing contact page listing Atlanta headquarters",
    },
    "opensystemstech.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.opensystemstech.com/about-us",
        "source_note": "Official Open Systems Technologies about page listing global headquarters",
    },
    "pdstech.com": {
        "location": "Irving, TX",
        "state": "TX",
        "source_url": "https://www.pdstech.com/documents/PDSTech-Terms_Conditions_20170714.pdf",
        "source_note": "Official PDS Tech PDF states the site is controlled and operated from its headquarters in Irving, Texas",
    },
    "eclaroit.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://eclaroit.com/",
        "source_note": "Official ECLARO site lists Global Headquarters in New York, NY",
    },
    "theintersectgroup.com": {
        "location": "Atlanta, GA",
        "state": "GA",
        "source_url": "https://theintersectgroup.com/contact-us/",
        "source_note": "Official The Intersect Group contact page lists Atlanta as headquarters",
    },
    "jobot.com": {
        "location": "Newport Beach, CA",
        "state": "CA",
        "source_url": "https://jobot.com/contact",
        "source_note": "Official Jobot contact page and news page identify Jobot House in Newport Beach, CA as headquarters",
    },
    "alku.com": {
        "location": "Andover, MA",
        "state": "MA",
        "source_url": "https://www.alku.com/about/",
        "source_note": "Official ALKU about page says the company is headquartered in Andover, MA",
    },
    "systemoneservices.com": {
        "location": "Pittsburgh, PA",
        "state": "PA",
        "source_url": "https://www.systemone.com/contact/",
        "source_note": "Official System One contact page lists the corporate office in Pittsburgh, PA",
    },
    "techusa.net": {
        "location": "Pittsburgh, PA",
        "state": "PA",
        "source_url": "https://www.systemone.com/contact/",
        "source_note": "techusa.net currently serves System One branding; official System One contact page lists the corporate office in Pittsburgh, PA",
    },
    "atriumstaff.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.atriumstaff.com/locations-all/",
        "source_note": "Official Atrium locations page lists New York, NY as headquarters",
    },
    "atriumworks.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.atriumglobal.com/locations/",
        "source_note": "atriumworks.com redirects to Atrium Global; official Atrium Global locations page lists US headquarters in New York, NY",
    },
    "atriumstaffing.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.atriumstaff.com/locations-all/",
        "source_note": "Atrium Staffing uses the same Atrium staffing brand; the official Atrium locations page lists New York, NY as headquarters",
    },
    "selectgroup.com": {
        "location": "Raleigh, NC",
        "state": "NC",
        "source_url": "https://www.selectgroup.com/company",
        "source_note": "Official The Select Group company page says the firm is based in Raleigh, North Carolina",
    },
    "disys.com": {
        "location": "McLean, VA",
        "state": "VA",
        "source_url": "https://dexian.com/contact/",
        "source_note": "disys.com now serves Dexian branding; official Dexian contact page lists corporate headquarters in McLean, VA",
    },
    "ettaingroup.com": {
        "location": "Milwaukee, WI",
        "state": "WI",
        "source_url": "https://www.experis.com/en/for-businesses/expertise/enterprise-applications/games/jobs/milwaukee-test-center-openings",
        "source_note": "ettaingroup.com redirects to Experis; official Experis page references ManpowerGroup corporate headquarters in Milwaukee, WI",
    },
    "experis.com": {
        "location": "Milwaukee, WI",
        "state": "WI",
        "source_url": "https://www.experis.com/-/media/project/manpowergroup/experis/experis-us/everest-award/everest-group-peak-matrix-for-us-it-contingent-staffing-service-provider-2022---focus-on-experis.pdf",
        "source_note": "Official Experis PDF identifies US headquarters as Milwaukee, Wisconsin",
    },
    "advantagetechnical.com": {
        "location": "Cincinnati, OH",
        "state": "OH",
        "source_url": "https://advantagetechnical.com/contact-us",
        "source_note": "Official Advantage Technical contact page lists the Staffmark Group address in Cincinnati, OH for the brand contact location",
    },
    "gdhinc.com": {
        "location": "Tulsa, OK",
        "state": "OK",
        "source_url": "https://gdhinc.com/contact/",
        "source_note": "Official GDH contact page lists the corporate office in Tulsa, OK",
    },
    "astoncarter.com": {
        "location": "Hanover, MD",
        "state": "MD",
        "source_url": "https://www.astoncarter.com/locations/north-america/united-states/maryland/hanover",
        "source_note": "Official Aston Carter page identifies the Hanover, Maryland office as global headquarters",
    },
    "revolutiontechnologies.com": {
        "location": "Melbourne, FL",
        "state": "FL",
        "source_url": "https://revolutiontechnologies.com/",
        "source_note": "Official Revolution Technologies site says the company is headquartered in Melbourne, Florida",
    },
    "strategicstaff.com": {
        "location": "Detroit, MI",
        "state": "MI",
        "source_url": "https://www.strategicstaff.com/company-overview/",
        "source_note": "Official Strategic Staffing Solutions overview page says the firm is based in Detroit, MI",
    },
    "swoonstaffing.com": {
        "location": "Chicago, IL",
        "state": "IL",
        "source_url": "https://www.swoonstaffing.com/contact-us/",
        "source_note": "Official Swoon contact page lists Chicago, IL as headquarters",
    },
    "3cloudsolutions.com": {
        "location": "Downers Grove, IL",
        "state": "IL",
        "source_url": "https://3cloudsolutions.com/get-started/",
        "source_note": "Official 3Cloud contact page lists 3Cloud Headquarters in Downers Grove, Illinois",
    },
    "guidehouse.com": {
        "location": "McLean, VA",
        "state": "VA",
        "source_url": "https://guidehouse.com/locations",
        "source_note": "Official Guidehouse locations page lists headquarters in McLean, Virginia",
    },
    "pipercompanies.com": {
        "location": "McLean, VA",
        "state": "VA",
        "source_url": "https://www.pipercompanies.com/our-locations-piper-companies/",
        "source_note": "Official Piper Companies locations page lists headquarters in McLean, Virginia",
    },
    "inspyrsolutions.com": {
        "location": "Fort Lauderdale, FL",
        "state": "FL",
        "source_url": "https://www.inspyrsolutions.com/contact-us/",
        "source_note": "Official INSPYR Solutions contact page lists Fort Lauderdale, Florida as headquarters",
    },
    "libertyjobs.com": {
        "location": "West Conshohocken, PA",
        "state": "PA",
        "source_url": "https://libertyjobs.com/findus.php",
        "source_note": "Official Liberty Personnel Find Us page lists the office in West Conshohocken, Pennsylvania",
    },
    "randstadtechnologies.com": {
        "location": "Diemen, North Holland",
        "state": "NL",
        "source_url": "https://www.randstadtechnologies.com/",
        "source_note": "Official Randstad Digital site lists Randstad Digital B.V. at Diemermere 25, Diemen, The Netherlands",
    },
    "ceiamerica.com": {
        "location": "Pittsburgh, PA",
        "state": "PA",
        "source_url": "https://www.ceiamerica.com/contact/",
        "source_note": "Official CEI contact page lists the corporate headquarters in Pittsburgh, PA",
    },
    "masonfrank.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.masonfrank.com/contact",
        "source_note": "Official Mason Frank contact page lists the New York, NY office in the Americas contact section and repeats that address across U.S. candidate pages",
    },
    "jeffersonfrank.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.jeffersonfrank.com/contact",
        "source_note": "Official Jefferson Frank contact page lists the New York, NY office and repeats that address across U.S. candidate pages",
    },
    "aquent.com": {
        "location": "Boston, MA",
        "state": "MA",
        "source_url": "https://aquent.com/privacy-policy",
        "source_note": "Official Aquent privacy policy lists Aquent LLC at 501 Boylston Street, Boston, MA and the contact page uses Boston phone details",
    },
    "w3r.com": {
        "location": "Southfield, MI",
        "state": "MI",
        "source_url": "https://w3r.com/congressional-state-and-local-leaders-join-w3r-consulting-for-new-office-ribbon-cutting/",
        "source_note": "Official w3r announcement says the company opened its new world headquarters in Southfield, Michigan",
    },
    "kornferry.com": {
        "location": "Los Angeles, CA",
        "state": "CA",
        "source_url": "https://www.kornferry.com/about-us/our-story",
        "source_note": "Official Korn Ferry history says the firm was founded in Los Angeles and official company profiles reference the Los Angeles headquarters office",
    },
    "hays.com": {
        "location": "London, England",
        "state": "UK",
        "source_url": "https://www.haysplc.com/contacts",
        "source_note": "Official Hays plc contacts page lists the company secretarial and legal contact at the registered office in London",
    },
    "kavaliro.com": {
        "location": "Orlando, FL",
        "state": "FL",
        "source_url": "https://www.kavaliro.com/",
        "source_note": "Official Kavaliro site lists corporate headquarters in Orlando, Florida",
    },
    "nigelfrank.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.nigelfrank.com/contact",
        "source_note": "Official Nigel Frank contact page lists the New York, NY office in the Americas contact section",
    },
    "computerfutures.com": {
        "location": "Wilmington, DE",
        "state": "DE",
        "source_url": "https://www.computerfutures.com/en-gb/company-details/",
        "source_note": "Official Computer Futures company details page lists the U.S. registered office in Wilmington, Delaware",
    },
    "accurateusa.com": {
        "location": "Schaumburg, IL",
        "state": "IL",
        "source_url": "https://accurateusa.com/",
        "source_note": "Official Accurate Personnel site lists Accurate HQ - North in Schaumburg, Illinois",
    },
    "stevendouglas.com": {
        "location": "Sunrise, FL",
        "state": "FL",
        "source_url": "https://www.stevendouglas.com/who-we-are/locations/fort-lauderdale/",
        "source_note": "Official StevenDouglas Fort Lauderdale location page says the company is headquartered there and lists the Sunrise, Florida office address",
    },
    "innovasolutions.com": {
        "location": "Atlanta, GA",
        "state": "GA",
        "source_url": "https://innovasolutions.com/contact-us/",
        "source_note": "Official Innova Solutions contact page lists the global headquarters in Atlanta, Georgia",
    },
    "lucasgroup.com": {
        "location": "Los Angeles, CA",
        "state": "CA",
        "source_url": "https://www.lucasgroup.com/",
        "source_note": "lucasgroup.com now serves official Korn Ferry brand content; Korn Ferry official history and company profiles reference the Los Angeles headquarters office",
    },
    "turnberrysolutions.com": {
        "location": "Minneapolis, MN",
        "state": "MN",
        "source_url": "https://www.turnberrysolutions.com/contact-us",
        "source_note": "Official Turnberry contact page lists the Minneapolis hub as a headquarters location",
    },
    "matlensilver.com": {
        "location": "Somerville, NJ",
        "state": "NJ",
        "source_url": "https://matlensilver.com/contact-us/",
        "source_note": "Official Matlen Silver contact page lists the Somerville, New Jersey office as the primary company contact location",
    },
    "nttdata.com": {
        "location": "Plano, TX",
        "state": "TX",
        "source_url": "https://us.nttdata.com/en/about-us/company-information",
        "source_note": "Official NTT DATA North America company information page lists headquarters in Plano, Texas",
    },
    "intepros.com": {
        "location": "Plymouth Meeting, PA",
        "state": "PA",
        "source_url": "https://www.intepros.com/contact-us/",
        "source_note": "Official IntePros contact page lists corporate headquarters in Plymouth Meeting, Pennsylvania",
    },
    "senecahq.com": {
        "location": "Chantilly, VA",
        "state": "VA",
        "source_url": "https://senecaholdings.com/contact-us/",
        "source_note": "Official Seneca Holdings contact page lists corporate office in Chantilly, Virginia",
    },
    "prosum.com": {
        "location": "El Segundo, CA",
        "state": "CA",
        "source_url": "https://www.prosum.com/contact/",
        "source_note": "Official Prosum contact page lists headquarters in El Segundo, California",
    },
    "mondo.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://mondo.com/contact-us/",
        "source_note": "Official Mondo contact page lists the New York headquarters address",
    },
    "balancestaffing.com": {
        "location": "Stockton, CA",
        "state": "CA",
        "source_url": "https://balancestaffing.com/our-branches/",
        "source_note": "Official Balance Staffing branches page lists the corporate office in Stockton, California",
    },
    "kellymitchell.com": {
        "location": "St. Louis, MO",
        "state": "MO",
        "source_url": "https://www.kellymitchell.com/",
        "source_note": "Official KellyMitchell site lists HQ in St. Louis, Missouri",
    },
    "synergishr.com": {
        "location": "Alpharetta, GA",
        "state": "GA",
        "source_url": "https://www.synergishr.com/contact/",
        "source_note": "Official Synergis contact page lists the Atlanta office in Alpharetta, Georgia as the main company contact location",
    },
    "nescoresource.com": {
        "location": "Mayfield Heights, OH",
        "state": "OH",
        "source_url": "https://hello.nescoresource.com/hubfs/Content%20Offers/Nesco%20Resource%20Interview%20Master%20Guide.pdf",
        "source_note": "Official Nesco Resource PDF lists headquarters in Mayfield Heights, Ohio",
    },
    "atwork.com": {
        "location": "Knoxville, TN",
        "state": "TN",
        "source_url": "https://www.atwork.com/about/our-story/",
        "source_note": "Official AtWork story page describes the company as a Knoxville-based franchise",
    },
    "catapultsg.com": {
        "location": "Plano, TX",
        "state": "TX",
        "source_url": "https://catapultsg.com/contact/",
        "source_note": "Official Catapult Solutions Group contact page lists headquarters in Plano, Texas",
    },
    "stand8.io": {
        "location": "Los Angeles, CA",
        "state": "CA",
        "source_url": "https://www.stand8.io/who-we-are/locations",
        "source_note": "Official STAND 8 locations page says the company is headquartered in Los Angeles, California",
    },
    "altaits.com": {
        "location": "Pittsburgh, PA",
        "state": "PA",
        "source_url": "https://www.systemone.com/contact/",
        "source_note": "altaits.com serves official System One content, and System One's corporate office is listed in Pittsburgh, Pennsylvania",
    },
    "orspartners.com": {
        "location": "King of Prussia, PA",
        "state": "PA",
        "source_url": "https://orspartners.com/",
        "source_note": "Official ORS Partners site lists the Pennsylvania office in King of Prussia as the company contact location",
    },
    "collabera.com": {
        "location": "Morristown, NJ",
        "state": "NJ",
        "source_url": "https://collabera.com/job-description/",
        "source_note": "Official Collabera job page states the position is based in the corporate headquarters in Morristown, New Jersey",
    },
    "genesis10.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.genesis10.com/locations",
        "source_note": "Official Genesis10 locations page lists headquarters in New York, New York",
    },
    "hollistergroup.com": {
        "location": "Boston, MA",
        "state": "MA",
        "source_url": "https://hollistergroup.com/community-posts/press-release-introducing-the-hollister-group-inc-staffing-cultures/",
        "source_note": "Official Hollister Group press page states the company is headquartered in Boston",
    },
    "mantech.com": {
        "location": "Herndon, VA",
        "state": "VA",
        "source_url": "https://www.mantech.com/contact/",
        "source_note": "Official ManTech contact page lists the company address in Herndon, Virginia",
    },
    "prostaff.com": {
        "location": "Cincinnati, OH",
        "state": "OH",
        "source_url": "https://www.prostaff.com/",
        "source_note": "Official Pro Staff site states the Staffmark Group corporate HQ is in Cincinnati, Ohio",
    },
    "verizon.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.verizon.com/about/our-company/verizon-corporate-headquarters",
        "source_note": "Official Verizon headquarters page lists the corporate headquarters in New York City",
    },
    "virtusa.com": {
        "location": "Southborough, MA",
        "state": "MA",
        "source_url": "https://www.virtusa.com/our-offices/americas/location-1",
        "source_note": "Official Virtusa office pages and investor materials place the company headquarters in Massachusetts, with the Southborough office listed on the official site",
    },
    "k2partnering.com": {
        "location": "London, England",
        "state": "UK",
        "source_url": "https://k2partnering.com/offices/london-hq/",
        "source_note": "Official K2 Partnering Solutions office page labels the London office as HQ",
    },
    "phaxis.com": {
        "location": "Melville, NY",
        "state": "NY",
        "source_url": "https://phaxis.com/contact-us/",
        "source_note": "Official Phaxis contact page lists HQ in Melville, New York",
    },
    "modis.com": {
        "location": "Zug, Switzerland",
        "state": "CH",
        "source_url": "https://www.akkodis.com/en/global-legal-pages/privacy-policy",
        "source_note": "modis.com now serves official Akkodis content, and the official Akkodis privacy policy lists Akkodis Group AG at a registered address in Zug, Switzerland",
    },
    "lasallenetwork.com": {
        "location": "Chicago, IL",
        "state": "IL",
        "source_url": "https://www.lasallenetwork.com/",
        "source_note": "Official LaSalle Network site consistently centers the company in Chicago with Chicago client references and the main company phone on the site footer",
    },
    "motionrecruitment.com": {
        "location": "Boston, MA",
        "state": "MA",
        "source_url": "https://motionrecruitment.com/blog/kelly-enters-agreement-to-acquire-specialty-talent-solutions-company-motion-recruitment-partners-llc",
        "source_note": "Official Motion Recruitment blog states Motion Recruitment Partners LLC is headquartered in Boston, Massachusetts",
    },
    "matrixres.com": {
        "location": "Boston, MA",
        "state": "MA",
        "source_url": "https://motionrecruitment.com/blog/kelly-enters-agreement-to-acquire-specialty-talent-solutions-company-motion-recruitment-partners-llc",
        "source_note": "matrixres.com serves official Motion Recruitment content, and the official Motion Recruitment blog states parent company Motion Recruitment Partners LLC is headquartered in Boston, Massachusetts",
    },
    "genuent.com": {
        "location": "Fort Lauderdale, FL",
        "state": "FL",
        "source_url": "https://www.genuent.com/strategic/melissa-beam-director-of-project-management",
        "source_note": "genuent.com serves official INSPYR Solutions content; this domain now routes into the INSPYR brand that is mapped to Fort Lauderdale, Florida",
    },
    "solomonpage.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://www.solomonpage.com/locations",
        "source_note": "Official Solomon Page locations page lists corporate headquarters in New York, New York",
    },
    "cbts.com": {
        "location": "Cincinnati, OH",
        "state": "OH",
        "source_url": "https://www.cbts.com/locations/",
        "source_note": "Official CBTS locations page lists the global headquarters in Cincinnati, Ohio",
    },
    "on24.com": {
        "location": "San Francisco, CA",
        "state": "CA",
        "source_url": "https://www.on24.com/contact-us/",
        "source_note": "Official ON24 contact page lists San Francisco as HQ",
    },
    "lrs.com": {
        "location": "Springfield, IL",
        "state": "IL",
        "source_url": "https://www.lrs.com/offices/lrs-offices/",
        "source_note": "Official LRS offices page lists corporate headquarters in Springfield, Illinois",
    },
    "gravityitresources.com": {
        "location": "Fort Lauderdale, FL",
        "state": "FL",
        "source_url": "https://www.gravityitresources.com/contact-us/",
        "source_note": "Official Gravity IT Resources contact page lists headquarters in Fort Lauderdale, Florida",
    },
    "atlantic-grp.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://atlanticrecruiters.com/approach/",
        "source_note": "Official Atlantic Group approach page states the firm is headquartered in NYC",
    },
    "entegee.com": {
        "location": "Braintree, MA",
        "state": "MA",
        "source_url": "https://entegee.com/contact-us/",
        "source_note": "Official Entegee contact page lists the main company address in Braintree, Massachusetts",
    },
    "ledgent.com": {
        "location": "Orange, CA",
        "state": "CA",
        "source_url": "https://www.rothstaffing.com/contact-us/",
        "source_note": "Official Ledgent pages state the brand is part of Roth Staffing Companies, whose corporate headquarters are in Orange, California",
    },
    "prolinkstaff.com": {
        "location": "Cincinnati, OH",
        "state": "OH",
        "source_url": "https://prolinkworks.com/perspectives/prolink-launches-new-headquarters",
        "source_note": "Official Prolink announcement says the company relocated its corporate headquarters to the Cincinnati, Ohio area",
    },
    "procomservices.com": {
        "location": "Cary, NC",
        "state": "NC",
        "source_url": "https://procomservices.com/en-us/contact/",
        "source_note": "Official Procom contact page lists the American head office in Cary, North Carolina",
    },
    "take2it.com": {
        "location": "Vienna, VA",
        "state": "VA",
        "source_url": "https://take2it.com/contact/",
        "source_note": "Official Take2 Consulting contact page lists the Vienna, Virginia office as the main company contact location",
    },
    "populusgroup.com": {
        "location": "Troy, MI",
        "state": "MI",
        "source_url": "https://www.populusgroup.com/en/contact",
        "source_note": "Official Populus Group contact page lists corporate headquarters in Troy, Michigan",
    },
    "abacusservice.com": {
        "location": "Southfield, MI",
        "state": "MI",
        "source_url": "https://abacusservice.com/contact/",
        "source_note": "Official Abacus Service contact page lists headquarters in Southfield, Michigan",
    },
    "vitaver.com": {
        "location": "Fort Lauderdale, FL",
        "state": "FL",
        "source_url": "https://vitaver.com/government/",
        "source_note": "Official Vitaver page lists headquarters in Fort Lauderdale, Florida",
    },
    "verticalmove.com": {
        "location": "Scottsdale, AZ",
        "state": "AZ",
        "source_url": "https://www.verticalmove.com/",
        "source_note": "Official VerticalMove site lists headquarters in Scottsdale, Arizona",
    },
    "bcforward.com": {
        "location": "Indianapolis, IN",
        "state": "IN",
        "source_url": "https://www.bcforward.com/connect/",
        "source_note": "Official BCforward contact page lists corporate headquarters in Indianapolis, Indiana",
    },
    "tier4group.com": {
        "location": "Roswell, GA",
        "state": "GA",
        "source_url": "https://tier4group.com/contact/",
        "source_note": "Official Tier4 Group contact page lists the Roswell, Georgia office as the main company location",
    },
    "lorienglobal.com": {
        "location": "Luton, England",
        "state": "UK",
        "source_url": "https://www.lorienglobal.com/us/contact-us",
        "source_note": "Official Lorien contact pages list the registered address in Luton, England",
    },
    "meridiantechnologies.net": {
        "location": "Charlotte, NC",
        "state": "NC",
        "source_url": "https://www.meridiantechnologies.net/contact/",
        "source_note": "Official Meridian Technologies contact page lists the Sales & National Recruiting Center in Charlotte, North Carolina",
    },
    "greenkeyllc.com": {
        "location": "New York, NY",
        "state": "NY",
        "source_url": "https://greenkeyllc.com/hire-with-us/client-services-overview/",
        "source_note": "Official Green Key page says the firm was founded in 2004 in New York City, and the contact page lists the New York office first",
    },
    "advantisglobal.com": {
        "location": "Fort Lauderdale, FL",
        "state": "FL",
        "source_url": "https://www.advantisglobal.com/",
        "source_note": "advantisglobal.com serves official INSPYR Solutions content, which lists the Fort Lauderdale office among primary company locations",
    },
    "tekpartners.com": {
        "location": "Fort Lauderdale, FL",
        "state": "FL",
        "source_url": "https://www.tekpartners.com/",
        "source_note": "tekpartners.com serves official INSPYR Solutions content, which lists the Fort Lauderdale office among primary company locations",
    },
    "stefanini.com": {
        "location": "Sao Paulo, Brazil",
        "state": "BR",
        "source_url": "https://stefanini.com/en/insights/news/global-acquisition-safeway-consultancy",
        "source_note": "Official Stefanini news states the group has global headquarters in Sao Paulo, Brazil",
    },
    "cai.io": {
        "location": "Allentown, PA",
        "state": "PA",
        "source_url": "https://www.cai.io/contact-us",
        "source_note": "Official CAI contact page lists headquarters in Allentown, Pennsylvania",
    },
    "epitec.com": {
        "location": "Southfield, MI",
        "state": "MI",
        "source_url": "https://epitec.com/contact/",
        "source_note": "Official Epitec contact page lists headquarters in Southfield, Michigan",
    },
    "infinity-cs.com": {
        "location": "Los Angeles, CA",
        "state": "CA",
        "source_url": "https://www.infinity-cs.com/",
        "source_note": "infinity-cs.com serves official Korn Ferry ICS content, and Korn Ferry's corporate headquarters are in Los Angeles, California",
    },
    "workbridgeassociates.com": {
        "location": "Boston, MA",
        "state": "MA",
        "source_url": "https://motionrecruitment.com/blog/kelly-enters-agreement-to-acquire-specialty-talent-solutions-company-motion-recruitment-partners-llc",
        "source_note": "workbridgeassociates.com serves official Motion Recruitment content, and official Motion Recruitment materials state Motion Recruitment Partners LLC is headquartered in Boston, Massachusetts",
    },
    "tcml.com": {
        "location": "Norwell, MA",
        "state": "MA",
        "source_url": "https://tcml.com/",
        "source_note": "Official The Computer Merchant site lists the corporate office in Norwell, Massachusetts",
    },
    "ledgenttech.com": {
        "location": "Orange, CA",
        "state": "CA",
        "source_url": "https://www.rothstaffing.com/contact-us/",
        "source_note": "Official Ledgent Technology pages state the brand is part of Roth Staffing Companies, whose corporate headquarters are in Orange, California",
    },
    "conexess.com": {
        "location": "Nashville, TN",
        "state": "TN",
        "source_url": "https://www.conexess.com/",
        "source_note": "Official Conexess site lists Nashville, Tennessee first in the main company contact block",
    },
    "creativecircle.com": {
        "location": "Calabasas, CA",
        "state": "CA",
        "source_url": "https://everforth.com/sustainability/",
        "source_note": "Official Everforth sustainability disclosure states the companys headquarters are in Calabasas, California and Creative Circle is an Everforth brand",
    },
    "frgconsulting.com": {
        "location": "Newcastle upon Tyne, England",
        "state": "UK",
        "source_url": "https://careers.tenthrevolution.com/why-trg/where-you-can-find-us/",
        "source_note": "Official Tenth Revolution Group careers page says Newcastle upon Tyne is the hometown and host to the largest office and global HQ",
    },
    "launchcg.com": {
        "location": "Westlake, OH",
        "state": "OH",
        "source_url": "https://www.theplanetgroup.com/contact-us",
        "source_note": "Official The Planet Group contact page lists Westlake, Ohio as headquarters for the parent company behind Launch Consulting Group",
    },
    "medasource.com": {
        "location": "Indianapolis, IN",
        "state": "IN",
        "source_url": "https://www.medasource.com/contact",
        "source_note": "Official Medasource contact page lists Medasource Headquarters in Indianapolis, Indiana",
    },
    "vsoftconsulting.com": {
        "location": "Louisville, KY",
        "state": "KY",
        "source_url": "https://www.vsoftconsulting.com/locations/",
        "source_note": "Official V-Soft locations page says V-Soft Consulting is headquartered in Louisville, Kentucky",
    },
    "yorksolutions.net": {
        "location": "Chicago, IL",
        "state": "IL",
        "source_url": "https://www.yorksolutions.net/who-we-are/",
        "source_note": "Official York Solutions history page says the company grew from its Chicago headquarters",
    },
    "diversant.com": {
        "location": "Atlanta, GA",
        "state": "GA",
        "source_url": "https://innovasolutions.com/company/global-locations/",
        "source_note": "diversant.com now serves Innova Solutions content, and the official global locations page lists Atlanta as the global HQ",
    },
    "ssctech.com": {
        "location": "Windsor, CT",
        "state": "CT",
        "source_url": "https://www.ssctech.com/about/offices",
        "source_note": "Official SS&C offices page lists Corporate Headquarters in Windsor, Connecticut",
    },
    "talentbridge.com": {
        "location": "Charlotte, NC",
        "state": "NC",
        "source_url": "https://talentbridge.com/thank-you/",
        "source_note": "Official TalentBridge pages list the Corporate Office at 6100 Fairview Road, Charlotte, North Carolina",
    },
}


def merge_metadata(existing_value: str | None, evidence: dict) -> str:
    metadata = {}
    if existing_value:
        try:
            parsed = json.loads(existing_value) if isinstance(existing_value, str) else existing_value
            if isinstance(parsed, dict):
                metadata = dict(parsed)
        except Exception:
            metadata = {"raw_metadata": str(existing_value)}
    metadata["email_domain_hq_backfill"] = evidence
    return json.dumps(metadata, default=str)


def main() -> None:
    session = SessionLocal()
    try:
        recruiters = (
            session.query(Recruiter)
            .filter((Recruiter.location == None) | (Recruiter.location == ""))
            .filter(Recruiter.email != None)
            .all()
        )

        updated = []
        for recruiter in recruiters:
            if "@" not in recruiter.email:
                continue
            domain = recruiter.email.strip().lower().split("@", 1)[1]
            mapped = DOMAIN_MAP.get(domain)
            if not mapped:
                continue

            recruiter.location = mapped["location"]
            recruiter.location_confidence = "high"
            recruiter.state = mapped["state"]
            recruiter.state_source = "email_domain_hq"
            recruiter.state_confidence = "high"
            recruiter.state_reason = "Filled from verified company HQ mapped from email domain"
            recruiter.metadata_json = merge_metadata(
                recruiter.metadata_json,
                {
                    "batch_key": BATCH_KEY,
                    "domain": domain,
                    "location": mapped["location"],
                    "state": mapped["state"],
                    "source_url": mapped["source_url"],
                    "source_note": mapped["source_note"],
                },
            )
            updated.append((recruiter.recruiter_id, recruiter.recruiter_name, recruiter.email, mapped["location"], mapped["state"]))

        session.commit()

        print(f"updated_recruiters={len(updated)}")
        for recruiter_id, recruiter_name, email, location, state in updated[:80]:
            print(f"{recruiter_id} | {recruiter_name} | {email} | {location} | {state}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
