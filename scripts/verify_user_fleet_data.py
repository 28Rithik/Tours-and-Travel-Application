import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import VehicleType, VehicleCategory

user_data = """
Toyota Innova 2.5 VX	7+d
Toyota Innova Crysta 2.4 GX+	6+d, 7+d
Toyota Innova Hycross VX	6+d, 7+d
Maruti Suzuki Invicto Zeta Plus	6+d, 7+d
Toyota Corolla Altis	4+d
Honda City V	4+d
Maruti Suzuki Ciaz Sigma 1.5	4+d
Toyota Etios VXD	4+d
Honda Amaze VX 1.2	4+d
Hyundai Aura E 1.2	4+d
Maruti Suzuki Dzire Lxi	4+d
Toyota Rumion S Petrol	6+d
Maruti Suzuki Ertiga Lxi 	8+d
Kia Carens Clavis HTE(O) 1.5	6+d
Mahindra Marazzo M2 7 STR	7+d
Tata Winger Tourist 3200 AC	13+d
Force Motors Cityline AC	9+d
MG ZS EV Excite Pro	4+d
BYD eMax 7 Premium	6+d
Tata Nexon EV	4+d
Tata Tigor EV XT	4+d
Toyota Camry Hybrid	3+d
Mercedes Benz E220d LWB	3+d
Mercedes-Benz S-Class S350d	3+d
Toyota Fortuner 4x4 2.8 4WD	5+d
Toyota Veilfire Executive Lounge	5+d
Mercedes Benz V-Class V 300d	5+d
Kia Carnival Limousine	7+d
Toyota HiAce Commuter H300 GL 2023	10+d
Toyota Coaster 4.2l	17+d
Toyota GranAce 3R 2.8l	7+d
Force Traveller T2 4020 AC	26+d
Force Traveller T1 4020 AC	20+d
Force Traveller T1 3700 AC	17+d
Force Traveller T1 3350 AC	14+d
Force Urbania 4400	16+d
Force Urbania 3615	13+d
Force Urbania 3350	9+d
Force Traveller T2 4020 AC FG	26+d
Force Traveller T1 4020 AC FG	20+d
Force Traveller T1 3700 AC Maharaja FG	14+d (1x1 Maharaja)
Force Traveller T1 3350 AC Maharaja FG	9+d (1x1 Maharaja)
Force Urbania 4400 Maharaja	13+d
Force Urbania 3615 Maharaja	9+d
Bharat Benz 1017 Fixed Glass	35+d (Seater 2x2)
Force MonoBus T3 MB 5200 AC Fixed Glass	41+d
SML Isuzu Hiroi 5300 Fixed Glass	40+d PB
SML Isuzu Executive LX 5100 Fixed Glass	35+d (Seater 2x2)
SML Isuzu Swaraj Mazda EcoMax T3500	20+d
SML Isuzu Asai 3335 AC	20+d (PB Seater 2x2)
Eicher 2050 Pandyan Coach	21+d (PB Seater 2x2)
Eicher 2050 Aadhavan Coach	21+d (PB Seater 2x2)
Eicher 2050 Joy Coach	21+d (PB Seater 2x2)
SML Isuzu 3335 Vinayaka Coach	25+d (PB Seater 2x2)
SML Isuzu 3335 Skylar Sahara Coach	25+d (PB Seater 2x2)
SML Isuzu 3335 Pandyan Coach FG	25+d (PB Seater 2x2)
SML Isuzu 3335 Aadhavan Coach FG	25+d (PB Seater 2x2)
Bharat Benz 1017 Ojes Body FG	25+d (PB Seater 2x1)
Bharat Benz 1017 Navigo FG	25+d (PB Seater 2x1)
Bharat Benz 1017 Skylar Sahara Coach 	35+d (PB Seater 2x2) 
Bharat Benz 1017 Ojes Fedora Body	35+d (PB Seater 2x2) 
Bharat Benz 1017 Prakash Astra	35+d (PB Seater 2x2) 
Bharat Benz 1017 Ojes Body FG	35+d (PB Seater 2x2) 
Bharat Benz 1017 Prakash Astra FG	35+d (PB Seater 2x2) 
Bharat Benz 1624 Prakash Zedastra	53+2d (PB Seater 3x2)
Bharat Benz 1624 ZedVega	53+2d (PB Seater 3x2)
Eicher 6016 Prakash Zedastra	53+2d (PB Seater 3x2)
Ashok Leyland Viking 11.4m Zedastra	53+2d (PB Seater 3x2)
Ashok Leyland Viking 11.4m Zedvega	53+2d (PB Seater 3x2)
Volvo Eicher 6016 R LPO VECV 12.4 m FG	43+2d (PB Seater 2x2)
Bharat Benz 1624 MG Glider 12m FG	45+2d (PB Seater 2x2)
Bharat Benz 1624 Prakash Capella GT 11.4m FG	45+2d (PB Seater 2x2)
Bharat Benz 1624 Prakash Zedastra FG	45+2d (PB Seater 2x2)
Bharat Benz 1624 Prakash Zedastra 13.5m	52+2d (PB Seater 2x2)
Bharat Benz 1924 Glider 13.5m	52+2d (PB Seater 2x2)
Volvo Eicher 6019 Pro VECV 13.5m	52+2d (PB Seater 2x2)
Volvo 9400 B8R 12m Biaxle	45+2d (Seater 2x2)
Volvo 9400 B11R 13.5m Bi-Axle	51+2d (Seater 2x2)
Volvo 9400 B11R 14.5m Multi-Axle	55+2d (Seater 2x2)
Volvo 9600 B8R 12.2m Bi-Axle	43+2d (Seater 2x2)
Volvo 9600 B8R 13.5m Multi-Axle	47+2d (Seater 2x2)
Volvo 9600 B8R 15m Multi-Axle	55+2d (Seater 2x2)
Scania Metrolink HD 12m Bi-Axle	45+2d (Seater 2x2)
Scania Metrolink HD 13.7m Multi-Axle	53+2d (Seater 2x2)
Scania Metrolink HD 14.5m Multi-Axle	57+2d (Seater 2x2)
Mercedes Benz 2441 SHD 15m Multiaxle	59+2d (Seater 2x2)
Volvo Eicher 6016 N Sutlej S-1800+	45+2d (Seater 2x2)
Eicher 6019 R Synaty Destino 12m	45+2d (Seater 2x2)
Eicher 6016 6200 WB Sahara Dexter	45+2d (Seater 2x2)
Volvo Eicher 6016 Pro Syanty 12 m 	45+2d (Seater 2x2)
Bharat Benz 1624 MG Tigra	45+2d (PB Seater 2x2)
Bharat Benz 1624 Damodar Rudra	45+2d (PB Seater 2x2)
Bharat Benz 1624 Damodar Spyder 2.0	45+2d (PB Seater 2x2)
Bharat Benz 1624 Damodar Super High Deck+	45+2d (PB Seater 2x2)
Bharat Benz 1624 Damodar Kalpa	45+2d (PB Seater 2x2)
Bharat Benz 1624 Synaty Umang	45+2d (PB Seater 2x2)
Bharat Benz 1624 Synaty Destino 12m	45+2d (PB Seater 2x2)
Bharat Benz 1624 Sutlej S-1800+	45+2d (PB Seater 2x2)
Bharat Benz 1624 Sahara Meraki	45+2d (PB Seater 2x2)
Bharat Benz 1624 Veeramaha Samrat V8 Mk III	45+2d (PB Seater 2x2)
Bharat Benz 1624 Aravali Stunner	45+2d (PB Seater 2x2)
Mahindra Cruzio Grande 4440	32+d (Seater 2x2)
Mahindra Cruzio Grande 5360	40+d (Seater 2x2)
Tata Ultra Prime 50+D AC LPO11.6/54 FG	50+d (PB 3x2)
Tata Ultra Prime 42+D AC LPO11.6/54 FG	50+d (PB 3x2)
Tata Ultra Prime 55+D LPO11.6/54	55+d (3x2)
Tata Ultra Prime 44+D LPO11.6/54	44+d (PB 3x2)
Tata Ultra Prime 34+D LPO8.6/44	34+d (PB 3x2)
Eicher Skyline Pro Next 3011 L AC FG	55+d (3x2)
Eicher Skyline Pro Next 3010 L AC FG	44+d (HHR 2x2), 40
Eicher Skyline Pro Next 3009 H AC FG	36+d (HHR 2x2), 32
Eicher Skyline Next 2112 M AC	50+d (HHR 3x2)
Eicher Skyline Next 2090 L AC	40+d (HHR 2x2), 35
Eicher Skyline Next 2075 H AC	32+d (HHR 2x2), 28
Eicher Skyline Next 2075 G AC	28+d (HHR 2x2)
Force Traveller T2 4020 AC Staff	25+d
Force Traveller T1 3700 AC Staff	17+d
Force Urbania 4400 Staff	16+d
Force Urbania 3615 Staff	13+d
Force MonoBus T3 MB 5200 AC Staff	41+d
Force MonoBus T3 MB 4020 AC Staff	33+d
Bharat Benz 1017 AC Staff	35+d (Seater 2x2)
Bharat Benz 1017 Fixed Glass Staff	35+d HH (Seater 2x2)
SML Isuzu Hiroi 4370 Staff	34+d SR
SML Isuzu Hiroi 5300 Staff	42+d SR
SML Isuzu Executive LX 4240 Staff	30+d HBR
SML Isuzu Executive LX 5100 Staff	37+d HBR
Ashok Leyland Lynx Oyster 5200 LS1510	52+d (3x2)
Ashok Leyland Lynx Strong REC Coach	52+d (3x2)
Ashok Leyland Lynx Prakash Vega	52+d (3x2)
Ashok Leyland Lynx Arrow Coach	52+d (3x2)
Ashok Leyland Lynx MG Glider Fixed Glass AC	52+d (3x2)
Bharat Benz 1017 Mini Bus	35+d
Eicher 2090 L Mini Bus	35+d
Ashok Leyland Viking 222 12m Route Line Bus	55+2d
Bharat Benz 1624 12m Route Line Bus	56+2d
Bharat Benz 1017 JCBL Caravan 9m	nil
Bharat Benz 1017 OJES Body Caravan	nil
Force Traveller 4020 Caravan	nil
Force Urbania 4400 Caravan	nil
Volvo 9400 JCBL Caravan 12m	nil
Bharat Benz 1017 Single Door Vanity Van	nil
Bharat Benz 1017 Three Door Vanity Van	nil
Force Traveller 4020 T2 Vanity Van	nil
Volvo 9400 12m JCBL Vanity Van	nil
Bharat Benz 1924 MG Glider Z+	36+2d
Bharat Benz 1924 MG Tigra	36+2d
Bharat Benz 1924 Prakash Capella GT	36+2d
Bharat Benz 1924 Damodar Rudra	36+2d
Bharat Benz 1924 Damodar Spyder 2.0	36+2d
Bharat Benz 1924 Damodar Super High Deck+	36+2d
Bharat Benz 1924 Damodar Kalpa	36+2d
Bharat Benz 1924 Damodar Prabal	36+2d
Bharat Benz 1924 Sutlej SL1800+	36+2d
Bharat Benz 1924 Veera V8 Mk III	36+2d
Bharat Benz 1924 Synaty Lavie	36+2d
Bharat Benz 1924 Synaty Destino 	36+2d
Bharat Benz 1924 Aravali Stunner	36+2d
Bharat Benz 1924 Sahara Meraki	36+2d
Bharat Benz 1924 R2 Prime+ REC	36+2d
Bharat Benz 1924 Shakti Coach	36+2d
Bharat Benz 1924 Jaswant Type 1 Coach	36+2d
Bharat Benz 1924 Jaswant Type 2 Coach	36+2d
Bharat Benz 1924 Shri Dharmraj Body	36+2d
Bharat Benz 1924	36+2d
Tata LPO 1618 Mirabelle S5300	36+2d
Ashok Leyland Garud TF 2513.5 Veera V8 Mk III	36+2d
Volvo Eicher 6019 Pro Veera V8 mk III	36+2d
Ashok Leyland Garud TF 2513.5 SL1800+	36+2d
Volvo Eicher 6019 Pro Sutlej SL1800+	36+2d
Bharat Benz 1924 Chassis - 49 Lakhs	nil
Ashok Leyland Garud TF 2513.5 - 40 Lakhs	nil
Ashok Leyland Garud TF 2513 Rudra	36+2d
Ashok Leyland Garud TF 2513 Spyder	36+2d
Ashok Leyland Garud TF 2513 Kalpa	36+2d
Volvo Eicher 6019 Pro Rudra	36+2d
Volvo Eicher 6019 Pro Spyder	36+2d
Volvo Eicher 6019 Pro Super High Deck	36+2d
Volvo Eicher 6019 Pro Capella GT	36+2d
Volvo Eicher 6019 Pro Stella	36+2d
Volvo Eicher 6019 Pro VECV Body	36+2d
Volvo 9400 B11R 14.5m	40+2d (AC Sleeper 2+1)
Volvo 9400 B11R 14.5m MG Star Z	40+2d (AC Sleeper 2+1)
Mercedes Benz 2441 SHD	40+2d (AC Sleeper 2+1)
Mercedes Benz 2441 SHD MG Dream Z	40+2d (AC Sleeper 2+1)
Scania Metrolink HD 14.5m	40+2d (AC Sleeper 2+1)
Volvo B8R 9600s 15m	40+2d (AC Sleeper 2+1)
Volvo B8R 9600 SLX 15m	40+2d (AC Sleeper 2+1)
Volvo B8R 9600 SLX 15m 42B	42+2d (AC Sleeper 2+1)
BharatBenz 1017 : School	49+d
BharatBenz 917 : School	39+d
SML Isuzu Executive LX School 4240 N	40+d (AC Seater 3x2)
SML Isuzu S7 5100 School	52+d
SML Isuzu S7 4240 School	42+d
Force Traveller School 4020 WB	26+d
Force Traveller 26 School	25+d
Force Monobus LWB	55+d
Force Monobus SWB	50+d
Force Traveller Monobus Scholar 5200	60+d
Force Traveller Monobus Scholar 4020	48 +d
Eicher Sykline Pro Next 3011 K	66+d (3x3 Seater)
Eicher Skyline Pro Next 3009 H AC	53+d ( Seater)
Eicher Starline Next 2050 C	22+d
Eicher Starline Next-Gen 2050 D	25+d
Eicher Starline Next-Gen 2070 E	30+d
Eicher Starline Next-Gen 2090 K	45+d
Ashok Leyland Oyster Wide School 4900	63+d, 53+d
Ashok Leyland Oyster School 3900	36+d
Ashok Leyland Switch Mobility EiV 12	45+d (HB 2x2) 
Tata Starbus Ultra 9/7 EV	20+d (2x2)
Tata Starbus Ultra 9/9 EV	31+d (HBR 2x2)
Tata Starbus Ultra 9/12 EV	45+d (HB 2x2) 
Eicher Skyline Pro-E 3012 12m	50+d (PB 2x2)
Eicher Skyline Pro-E 9m	32+d (PB 2x2)
Force E - Traveller	14+d
Tata Ultra 9/9 EV (3x2)	48+2d Bench
Tata Ultra 9/9 EV (2x2)	40+2d Bench
Eicher Skyline Pro-E 12m (2x2)	50+d PB
Eicher Skyline Pro-E 9m (2x2)	32+d PMS
"""

lines = [l.strip() for l in user_data.strip().split('\n') if l.strip()]
exact_matches = 0
fuzzy_matches = 0
unmatched = []

all_db = {vt.name.lower().strip(): vt for vt in VehicleType.objects.all()}

for line in lines:
    parts = line.split('\t')
    raw_name = parts[0].strip()
    clean_name = re.sub(r'\s+', ' ', raw_name)
    clean_lower = clean_name.lower()
    
    if clean_lower in all_db:
        exact_matches += 1
    else:
        # Check fuzzy
        found_match = False
        for db_name, vt in all_db.items():
            if clean_lower in db_name or db_name in clean_lower:
                fuzzy_matches += 1
                found_match = True
                break
        if not found_match:
            unmatched.append(clean_name)

print("=" * 60)
print(f"Total Lines from User Input: {len(lines)}")
print(f"Exact Matches in Database:   {exact_matches}")
print(f"Fuzzy/Variant Matches in DB: {fuzzy_matches}")
print(f"Total Matched:               {exact_matches + fuzzy_matches}")
print(f"Unmatched:                   {len(unmatched)}")
if unmatched:
    print("\nUnmatched entries:")
    for u in unmatched:
        print(f" - {u}")
print("=" * 60)
