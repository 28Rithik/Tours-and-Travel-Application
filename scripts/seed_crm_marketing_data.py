import os
import sys
import random
import datetime
from decimal import Decimal

# Configure UTF-8 for console output on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.utils import timezone
from core.models import Client, VehicleType
from operations.models import Booking
from packages.models import Package
from crm.models import Inquiry, CustomerPreference, CommunicationLog
from marketing.models import Coupon, EmailCampaign, UpsellRecommendation

def seed_data():
    print("==================================================================")
    print("  SEEDING 50 CORRELATED RECORDS FOR CRM & MARKETING")
    print("==================================================================")

    # 1. Fetch reference objects
    clients = list(Client.objects.all().order_by('id')[:50])
    if len(clients) < 50:
        print(f"Warning: Only {len(clients)} clients available. Creating additional clients to reach 50...")
        for i in range(len(clients) + 1, 51):
            c = Client.objects.create(
                name=f"Enterprise Client {i:03d} (South India)",
                party_type=random.choice(['corporate', 'individual', 'travel_agency', 'hotel']),
                phone=f"98400{i:05d}",
                email=f"client{i:03d}@travelcorp.example"
            )
            clients.append(c)
    
    vehicle_types = list(VehicleType.objects.all())
    vt_crysta = VehicleType.objects.filter(name__icontains='Crysta').first() or vehicle_types[0]
    vt_tt = VehicleType.objects.filter(name__icontains='Tempo').first() or vehicle_types[0]
    vt_bus = VehicleType.objects.filter(name__icontains='Bus').first() or vehicle_types[0]
    vt_sedan = VehicleType.objects.filter(name__icontains='Sedan').first() or vehicle_types[0]
    vt_coach = VehicleType.objects.filter(name__icontains='Coach').first() or vehicle_types[0]

    # Pre-fetch 50 packages across major categories
    packages = list(Package.objects.filter(is_active=True).order_by('id')[:50])
    if len(packages) < 50:
        packages = list(Package.objects.all().order_by('id')[:50])
    print(f"Loaded {len(clients)} clients, {len(vehicle_types)} vehicle types, {len(packages)} packages.")

    # ------------------------------------------------------------------
    # A. SEED 50 CUSTOMER PREFERENCES (1 per client)
    # ------------------------------------------------------------------
    print("\n--- Seeding 50 Customer Preferences ---")
    CustomerPreference.objects.all().delete()

    dietary_options = [
        "Pure Vegetarian Brahmin Catering (No Onion/No Garlic for Temple Tours)",
        "Jain Food Only (Strict vegetarian, no root vegetables)",
        "South Indian Traditional Veg & Non-Veg Multi-Cuisine Buffet",
        "Halal Certified Meals with Chettinad & Malabar Specialities",
        "Standard Corporate Buffet with Morning High Tea & Refreshments",
        "Mild Spices / Diabetic-Friendly Meals for Senior Citizens",
        "Continental Breakfast with Traditional South Indian Thali Dinners",
        "Kids Friendly Mild Menu & Packed Travel Snacks Kit",
        "Authentic Kerala Sadya on Plantain Leaf & Coastal Seafood Dinner",
        "Pure Veg Udupi Style Tiffin & Coffee Service during Travel",
    ]

    pref_count = 0
    for idx, client in enumerate(clients):
        # Match vehicle preference to client profile
        if client.party_type == 'corporate':
            pref_vt = random.choice([vt_coach, vt_bus, vt_crysta])
        elif client.party_type == 'travel_agency':
            pref_vt = random.choice([vt_tt, vt_coach, vt_crysta])
        elif client.party_type == 'hotel':
            pref_vt = random.choice([vt_crysta, vt_sedan])
        else:
            pref_vt = random.choice([vt_sedan, vt_crysta, vt_tt])

        diet = dietary_options[idx % len(dietary_options)]
        whatsapp_opt = (idx % 7 != 0) # 85% opt-in
        email_opt = (idx % 9 != 0)    # 88% opt-in

        CustomerPreference.objects.create(
            client=client,
            preferred_vehicle_type=pref_vt,
            dietary_requirements=diet,
            whatsapp_opt_in=whatsapp_opt,
            email_opt_in=email_opt
        )
        pref_count += 1
    print(f"✅ Created {pref_count} Customer Preferences.")

    # ------------------------------------------------------------------
    # B. SEED 50 INQUIRIES (Sales Pipeline)
    # ------------------------------------------------------------------
    print("\n--- Seeding 50 Inquiries ---")
    Inquiry.objects.all().delete()

    inquiry_templates = [
        # Devotional / Temple
        ("Chennai Central", "Tirupati Balaji & Kalahasti", "round_trip", vt_crysta, 380, 9500, "Senior citizens on board; require wheelchair darshan slot coordination.", "Pilgrimage Yatra"),
        ("T. Nagar, Chennai", "Navagraha 9 Temple Circuit (Kumbakonam)", "round_trip", vt_tt, 750, 26000, "Pure vegetarian Brahmin meals at hotel stopovers. Driver should know temple timings.", "Navagraha Circuit"),
        ("Coimbatore Junction", "Palani - Madurai - Rameswaram", "round_trip", vt_tt, 850, 32000, "Early morning Agnitheertham snanam and Ramanathaswamy special darshan.", "Arupadai Pilgrimage"),
        ("Bangalore Electronic City", "Kukke Subramanya & Dharmasthala", "round_trip", vt_crysta, 720, 22500, "Ashlesha Bali pooja slot booking confirmed; need prompt pickup at 5 AM.", "Divine Karnataka"),
        ("Madurai Airport", "Kanyakumari & Suchindram Temple", "outstation", vt_crysta, 520, 16800, "Sunset view hotel stay + Sunrise darshan transfer.", "South Cap Tour"),
        
        # College / School Industrial Visits
        ("Guindy, Chennai", "Kochi Infopark & Munnar Tea Plantation IV", "round_trip", vt_coach, 1400, 115000, "52 Engineering students + 3 faculty. Need 2+2 pushback AC coach with PA sound system.", "College IV Kerala"),
        ("Tambaram, Chennai", "Mysore Silk Factory & Coorg Coffee Estates IV", "round_trip", vt_bus, 1250, 98000, "Campfire & DJ night permission at Coorg resort required. Food AP plan included.", "College IV Karnataka"),
        ("Trichy Central", "Bangalore Tech Park & ISRO Heritage Center IV", "round_trip", vt_bus, 980, 82000, "Industrial visit entry permission letters ready. Require hotel near Electronic City.", "Tech IV Bangalore"),
        ("Salem New Bus Stand", "Goa Shipyard & Marine Engineering IV", "round_trip", vt_coach, 1950, 145000, "4N/5D trip for 48 students. Dual drivers mandatory for continuous highway safety.", "Goa Coastal IV"),
        ("Coimbatore", "Hyderabad T-Hub & Ramoji Film City IV", "round_trip", vt_coach, 1800, 138000, "Students IV with 3-star AC hotel quad sharing and packed lunches during plant visits.", "Hyderabad Mega IV"),

        # Hill Station Getaways
        ("Chennai Airport", "Ooty & Coonoor Scenic Getaway", "round_trip", vt_crysta, 1100, 29500, "Family vacation with 2 kids. Need child safety seat and experienced hill driver.", "Ooty Escape"),
        ("Coimbatore Airport", "Kodaikanal Lake & Pillar Rocks Retreat", "round_trip", vt_crysta, 480, 15800, "Stay at hillside resort. Need sightseeing to Berijam Lake & Pine Forest.", "Kodai Weekend"),
        ("Kochi Airport", "Munnar Tea Gardens & Eravikulam Safari", "round_trip", vt_crysta, 360, 14200, "Honeymoon couple. Flower bed decoration and candle light dinner requested at resort.", "Munnar Romance"),
        ("Bangalore Airport", "Coorg Abbey Falls & Dubare Elephant Camp", "round_trip", vt_crysta, 540, 17500, "River rafting booking assistance required in Dubare.", "Coorg Adventure"),
        ("Madurai", "Valparai Tea Valleys & Sholayar Dam", "round_trip", vt_tt, 580, 23000, "Nature photography club 12 members. Early morning bird watching stops.", "Valparai Wild"),

        # Leisure & Beach
        ("Adyar, Chennai", "Pondicherry French Colony & Promenade Beach", "round_trip", vt_sedan, 340, 6800, "Weekend trip with friends. Need drop at White Town boutique villa.", "Pondy Leisure"),
        ("Chennai", "Goa Calangute & Dudhsagar Waterfalls Tour", "round_trip", vt_tt, 2100, 58000, "Extended friends group trip. AC Tempo Traveller with luggage roof carrier.", "Goa Explorer"),
        ("Trivandrum Airport", "Varkala Cliff Beach & Kovalam Lighthouse", "outstation", vt_crysta, 220, 8900, "Beach resort drop with luggage handling and multilingual driver.", "Kerala Coast"),
        ("Chennai Central", "Mahabalipuram Shore Temple & ECR Beach", "local", vt_sedan, 140, 3600, "Single day foreign delegate excursion. English fluent chauffeur needed.", "Heritage Day Tour"),
        ("Bangalore", "Mangalore & Udupi Beach Temple Trail", "round_trip", vt_tt, 890, 31000, "Coastal cuisine food trail + Malpe beach water sports.", "Coastal Karnataka"),

        # Corporate Outings & Airport Transfers
        ("Tidel Park, Chennai", "ECR Beach Resort Annual Offsite", "local", vt_coach, 90, 18500, "Corporate team building for 50 tech employees. Pickup at 8 AM, return at 9 PM.", "Corporate Offsite"),
        ("Siruseri IT Park, Chennai", "Yelagiri Hill Station Team Retreat", "round_trip", vt_bus, 460, 42000, "Trekking & adventure camp activities. High tea and buffet lunch required.", "Tech Team Retreat"),
        ("Chennai Airport", "Pondicherry Windflower Resort Corporate Meet", "outstation", vt_tt, 320, 13500, "Executive delegates arrival from Mumbai & Delhi. Water bottles and wet wipes in vehicle.", "Exec Summit"),
        ("OMR Chennai", "Chennai International Airport Drop (VIP)", "airport", vt_crysta, 45, 2400, "MD international departure. Chauffeur in formal uniform required.", "Airport VIP"),
        ("Anna Nagar, Chennai", "Vellore Golden Temple & Silk Saree Shopping", "round_trip", vt_sedan, 290, 5900, "Family day trip with elderly mother. Wheelchair friendly stops.", "Golden Temple Day"),
    ]

    now = timezone.now()
    inquiries = []
    
    statuses = ['new', 'quoted', 'won', 'lost']
    status_weights = [15, 20, 10, 5] # 50 total distribution
    status_list = ['new']*15 + ['quoted']*20 + ['won']*10 + ['lost']*5
    random.shuffle(status_list)

    for i in range(50):
        tmpl = inquiry_templates[i % len(inquiry_templates)]
        client = clients[i]
        status = status_list[i]
        
        # Pickup dates staggered around upcoming dates
        pickup_offset_days = random.randint(-5, 45)
        pickup_date = (now + datetime.timedelta(days=pickup_offset_days)).date()
        duration_days = random.choice([1, 2, 3, 4, 5])
        drop_date = pickup_date + datetime.timedelta(days=duration_days - 1) if duration_days > 1 else pickup_date

        guest_names = [
            "Dr. K. Sivasubramanian", "Prof. R. Meenakshi Sundaram", "Mr. Anandhakrishnan",
            "Mrs. Geetha Rajagopalan", "Mr. Senthil Nathan", "Ms. Preethi Balaji",
            "Mr. Vigneshwaran Pillai", "Capt. Ramesh Babu", "Mrs. Subhalakshmi Iyer",
            "Mr. Karthik Narayanan", "Dr. A. Venkatesan", "Mr. Mohammed Rafiq",
            "Mrs. Nirmala Govindarajan", "Mr. Praveen Kumar", "Ms. Lavanya Sundar"
        ]
        guest_name = f"{guest_names[i % len(guest_names)]} (Guest #{i+1:02d})"
        guest_phone = f"+91 9840{random.randint(100000, 999999)}"

        km = tmpl[4] + random.randint(-20, 40)
        price = Decimal(tmpl[5] + random.randint(-500, 1500))

        # Add notes reflective of status
        if status == 'new':
            notes = f"Hot lead received via website form. Client requested callback regarding {tmpl[7]}."
        elif status == 'quoted':
            notes = f"Official quote for ₹{price:,.0f} sent on WhatsApp & email. Follow-up scheduled in 2 days."
        elif status == 'won':
            notes = f"Deal closed! Advance payment received. Booking generated and coach assigned."
        else: # lost
            notes = "Client postponed journey due to college examination schedule / date change."

        inq = Inquiry.objects.create(
            inquiry_number=f"INQ-2026-{i+1:04d}",
            party=client,
            guest_name=guest_name,
            guest_phone=guest_phone,
            pickup_location=tmpl[0],
            destination=tmpl[1],
            pickup_date=pickup_date,
            pickup_time=datetime.time(random.choice([5, 6, 7, 8, 9, 14, 18, 22]), 0),
            drop_date=drop_date,
            journey_type=tmpl[2],
            vehicle_type=tmpl[3],
            special_requirements=tmpl[6],
            estimated_km=km,
            quoted_price=price,
            status=status,
            notes=notes
        )
        # Stagger created_at so admin filters (hot leads < 3d, stale > 7d) have real variety
        created_age_days = random.choice([0, 1, 2, 4, 8, 12, 18])
        created_dt = now - datetime.timedelta(days=created_age_days, hours=random.randint(1, 10))
        Inquiry.objects.filter(id=inq.id).update(created_at=created_dt)
        inquiries.append(inq)

    print(f"✅ Created 50 Inquiries with distributed pipeline stages (Hot Leads, Quoted, Won, Lost).")

    # ------------------------------------------------------------------
    # C. SEED 50 COMMUNICATION LOGS (Related to Clients & Bookings)
    # ------------------------------------------------------------------
    print("\n--- Seeding 50 Communication Logs ---")
    CommunicationLog.objects.all().delete()

    comm_log_templates = [
        ("whatsapp", "Hello {guest}! Your quotation for {dest} has been generated (Quoted Rate: ₹{price}). View your complete tour plan and vehicle specs here: https://sivagayathiritravels.com/quote/{inq}", "delivered"),
        ("email", "Subject: Quotation & Tour Itinerary Confirmation - {dest}\n\nDear {guest},\nThank you for contacting Sivagayathiri Travels. Attached is our detailed proposal for your upcoming tour to {dest}. Includes pushback luxury seating, toll/parking permits, and all-inclusive driver bata.", "sent"),
        ("whatsapp", "Namaste {guest}, your booking {b_num} is CONFIRMED for {dest}. Chauffeur assigned: Mr. {driver} (Mob: +91 9444{rand4}). Vehicle: {vt} (Reg: TN-01-BK-{rand3}). Have a safe and divine journey!", "delivered"),
        ("email", "Subject: Booking Confirmation & Driver Dispatch Details [{b_num}]\n\nDear {guest},\nWe are pleased to confirm your vehicle reservation. The chauffeur will report at {pickup} 30 minutes prior to scheduled departure. Emergency desk: 0422-4000000.", "sent"),
        ("whatsapp", "Payment Received: We have received ₹{adv} towards booking {b_num}. Balance amount ₹{bal} can be settled at trip completion. Download GST tax receipt: https://sivagayathiritravels.com/receipt/{b_num}", "delivered"),
        ("whatsapp", "Trip Reminder: Your trip to {dest} begins tomorrow at {time}. Please keep your Aadhaar / ID proofs ready for hotel check-in and darshan slots. Sivagayathiri 24x7 Control Room.", "delivered"),
        ("email", "Subject: How was your journey with Sivagayathiri Travels? 🌟\n\nDear {guest},\nWe hope you had a pleasant trip to {dest}. Please take 30 seconds to rate your driver and vehicle cleanliness. We look forward to serving you again!", "sent"),
        ("whatsapp", "Festive Early Bird: Plan your Navratri & Diwali family holiday with 15% discount using coupon code 'FESTIVE15'. Valid across all Hill Station and Devotional circuits!", "sent"),
        ("email", "Subject: Special Corporate Travel Privilege - Sivagayathiri Travels\n\nDear HR / Admin Team at {client},\nEnjoy dedicated account management, monthly credit billing, and 100% verified AC coaches for all your offsite events and daily employee transit.", "sent"),
        ("whatsapp", "Chauffeur Update: Coach {vt} has arrived at pickup point {pickup}. Chauffeur is waiting at entrance. Please board at your convenience.", "delivered")
    ]

    sample_bookings = list(Booking.objects.filter(party__in=clients)[:50])
    drivers = ["M. Senthil Kumar", "K. Murugan", "R. Saravanan", "A. Rajendran", "P. Vijayakumar", "G. Manikandan"]

    comm_count = 0
    for i in range(50):
        client = clients[i]
        inq = inquiries[i]
        b = sample_bookings[i % len(sample_bookings)] if sample_bookings else None
        b_num = b.booking_number if b else f"BK-2026-{1000+i}"
        
        tmpl = comm_log_templates[i % len(comm_log_templates)]
        comm_type = tmpl[0]
        status = tmpl[2]
        if i % 15 == 0:
            status = 'failed' # realistic failure rate

        adv = Decimal(inq.quoted_price or 15000) * Decimal('0.3')
        bal = Decimal(inq.quoted_price or 15000) - adv

        msg = tmpl[1].format(
            guest=inq.guest_name.split()[0],
            dest=inq.destination,
            price=f"{inq.quoted_price:,.0f}" if inq.quoted_price else "12,500",
            inq=inq.inquiry_number,
            b_num=b_num,
            driver=drivers[i % len(drivers)],
            rand4=f"{random.randint(1000, 9999)}",
            rand3=f"{random.randint(100, 999)}",
            vt=inq.vehicle_type.name if inq.vehicle_type else "Innova Crysta",
            pickup=inq.pickup_location,
            adv=f"{adv:,.0f}",
            bal=f"{bal:,.0f}",
            time="06:00 AM",
            client=client.name
        )

        cl = CommunicationLog.objects.create(
            client=client,
            booking=b,
            comm_type=comm_type,
            message_content=msg,
            status=status
        )
        # Stagger sent_at
        sent_offset_hours = random.randint(1, 240)
        CommunicationLog.objects.filter(id=cl.id).update(sent_at=now - datetime.timedelta(hours=sent_offset_hours))
        comm_count += 1
    print(f"✅ Created {comm_count} Communication Logs (WhatsApp & Email).")

    # ------------------------------------------------------------------
    # D. SEED 50 COUPONS (Marketing)
    # ------------------------------------------------------------------
    print("\n--- Seeding 50 Promotional Coupons ---")
    Coupon.objects.all().delete()

    coupon_schemes = [
        # (code, pct, flat, days_valid, limit, used, active)
        ("TIRUPATI500", None, 500, 45, 100, 34, True),
        ("OOTYFEST10", 10.0, None, 60, 50, 18, True),
        ("COLLEGEIV20", 20.0, None, 90, 30, 12, True),
        ("PONDYBEACH15", 15.0, None, 30, 40, 22, True),
        ("RAMESHWARAM1000", None, 1000, 40, 60, 41, True),
        ("KODAIRETREAT", 12.0, None, 50, 45, 15, True),
        ("MUNNARESCAPE", 10.0, None, 60, 50, 29, True),
        ("COORGEXP15", 15.0, None, 45, 35, 11, True),
        ("NAVAGRAHA750", None, 750, 90, 80, 52, True),
        ("BANGALOREIV", 18.0, None, 75, 25, 9, True),
        ("GOAWEEKEND", None, 2500, 30, 20, 17, True),
        ("CHIDAMBARAM", None, 500, 45, 50, 20, True),
        ("KABINISAFARI", 15.0, None, 60, 30, 8, True),
        ("EARLYBIRD2026", 15.0, None, 120, 150, 63, True),
        ("DIWALIRETREAT", None, 2000, 25, 100, 88, True),
        ("WEEKENDGETAWAY", 10.0, None, 30, 80, 39, True),
        ("TEMPLEPASS500", None, 500, 60, 100, 45, True),
        ("CORPORATEVIP", None, 5000, 90, 20, 6, True),
        ("FAMILYHOLIDAY", 12.5, None, 45, 50, 24, True),
        ("SUMMERHILLSTN", 15.0, None, 180, 200, 77, True),
        ("SABARIMALA50", 10.0, None, 40, 100, 82, True),
        ("KANYAKUMARI", None, 1200, 50, 40, 16, True),
        ("VALPARAIRIG", 10.0, None, 60, 30, 13, True),
        ("MYSOREHERITAGE", None, 800, 45, 50, 27, True),
        ("VAGAMONJEEP", 15.0, None, 60, 40, 19, True),
    ]

    coupons_created = 0
    today = timezone.now().date()

    for i in range(50):
        tmpl = coupon_schemes[i % len(coupon_schemes)]
        suffix = f"_{i+1}" if i >= len(coupon_schemes) else ""
        code = f"{tmpl[0]}{suffix}"[:20]
        
        # Link to corresponding package
        pkg = packages[i % len(packages)] if packages else None
        
        # Stagger expiry dates (some expired, some active, some high discount)
        if i == 48:
            exp_date = today - datetime.timedelta(days=5) # Expired
            is_active = False
        elif i == 49:
            exp_date = today + datetime.timedelta(days=3) # Expiring soon
            is_active = True
        else:
            exp_date = today + datetime.timedelta(days=tmpl[3] + (i * 2))
            is_active = tmpl[6]

        limit = tmpl[4]
        used = min(tmpl[5] + random.randint(0, 5), limit)

        Coupon.objects.create(
            code=code,
            discount_percent=Decimal(tmpl[1]) if tmpl[1] else None,
            flat_discount=Decimal(tmpl[2]) if tmpl[2] else None,
            applicable_package=pkg,
            usage_limit=limit,
            used_count=used,
            expiry_date=exp_date,
            is_active=is_active
        )
        coupons_created += 1
    print(f"✅ Created {coupons_created} Coupons with diverse discount tiers & real package links.")

    # ------------------------------------------------------------------
    # E. SEED 50 EMAIL CAMPAIGNS (Marketing)
    # ------------------------------------------------------------------
    print("\n--- Seeding 50 Email Campaigns ---")
    EmailCampaign.objects.all().delete()

    campaign_blueprints = [
        ("Navratri Divine Temple Yatra 2026",
         "🕉️ Experience Divine Grace: Exclusive Temple Yatra Packages across Tamil Nadu & Andhra",
         "Explore Tirupati Balaji VIP Darshan, Navagraha 9 Temple Yatra, and Arupadai Veedu Murugan temples with pure vegetarian Brahmin catering and luxury AC coaches."),
        
        ("College & School Industrial Visits 2026-27",
         "🎓 Plan Your Institution's Annual IV: Kochi IT Hub, Mysore Silk & Bangalore Tech Parks",
         "Sivagayathiri Travels offers all-inclusive student packages with complimentary faculty passes, DJ campfire nights, industrial plant entry permits, and 2+2 pushback air suspension buses."),
        
        ("Autumn Hill Station Escapes - Ooty & Munnar",
         "⛰️ Cool Mist, Crisp Tea Gardens: 15% Early-Bird Discount on Hill Station Getaways",
         "Escape the city heat to Ooty, Kodaikanal, and Munnar. Enjoy handpicked tea-estate resort stays, scenic lake boat rides, and private Innova Crysta transfers."),
        
        ("Corporate Annual Retreat & Team Building",
         "🏢 Recharge Your Team: Beachfront Offsites & Hillside Adventure Retreats",
         "From ECR luxury beach villas to Yelagiri adventure challenges, we manage end-to-end corporate transportation, team facilitators, conference setups, and gala dinners."),
        
        ("Diwali Festive Holiday Early Bird 2026",
         "🪔 Celebrate Diwali in God's Own Country - Special Kerala Alleppey & Vagamon Packages",
         "Spend the festival of lights cruising the backwaters on a private houseboat and soaking in the pine forests of Vagamon. Use promo code DIWALIRETREAT for flat ₹2,000 off!"),

        ("Sacred South India Teertha Yatra for Elders",
         "🙏 Peaceful, Hassle-Free Pilgrimage for Senior Citizens with Wheelchair & Doctor-on-Call",
         "Rameswaram, Madurai Meenakshi, and Kanyakumari. Ground floor hotel accommodations, leisurely travel pace, and satvik diet tailored for senior comfort."),

        ("Weekend Getaways from Chennai: Pondy & Mahabs",
         "🏖️ Sun, Sand & French Heritage: 2-Day Refreshing Escapes from Chennai",
         "Take a relaxing drive down ECR to White Town Pondicherry. Experience French bakeries, Auroville, and tranquil beaches with our sanitized Swift Dzire and Innova cabs."),

        ("Karnataka Wildlife & Heritage Discovery",
         "🐅 Mysore Palace & Bandipur Tiger Safari: An Unforgettable Family Road Trip",
         "Witness royal grandeur at Mysore Palace, spot wild elephants at Bandipur, and explore coffee plantations in Coorg with our knowledgeable chauffeurs."),

        ("Sabarimala Mandala Yatra AC Coach Bookings",
         "🕉️ Swamiye Saranam Ayyappa: 40 & 54 Seater AC Luxury Coaches for Sabarimala Pilgrims",
         "Equipped with audio/video devotional systems, ample luggage storage for irumudi kattu, and experienced hill ghat section drivers."),

        ("Goa Coastal Explorer & Dudhsagar Expedition",
         "🌊 Sunsets, Waterfalls & Heritage Churches: Discover Goa with Sivagayathiri Travels",
         "Tailored youth & family packages with beach resort stays, catamaran cruises, water sports passes, and dedicated Tempo Traveller transport.")
    ]

    campaign_count = 0
    for i in range(50):
        blueprint = campaign_blueprints[i % len(campaign_blueprints)]
        var_num = (i // len(campaign_blueprints)) + 1
        name = f"{blueprint[0]} (Edition {var_num:02d})"
        subject = f"{blueprint[1]} [Issue #{i+1:02d}]"
        
        body_html = f"""
<div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 650px; margin: 0 auto; background: #0f172a; color: #f8fafc; border-radius: 12px; overflow: hidden; border: 1px solid #1e293b;">
    <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 32px 24px; text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 24px; letter-spacing: -0.5px;">SIVAGAYATHIRI TOURS & TRAVELS</h1>
        <p style="margin: 8px 0 0 0; color: #e0f2fe; font-size: 14px;">Premier South Indian Tour Operator & Coach Fleet Specialists</p>
    </div>
    <div style="padding: 28px 24px;">
        <h2 style="color: #38bdf8; font-size: 20px; margin-top: 0;">{subject}</h2>
        <p style="line-height: 1.6; color: #cbd5e1; font-size: 15px;">{blueprint[2]}</p>
        
        <div style="background: #1e293b; border-left: 4px solid #38bdf8; padding: 16px; margin: 20px 0; border-radius: 4px;">
            <h4 style="margin: 0 0 8px 0; color: #f8fafc; font-size: 15px;">🌟 Why Travelers Choose Sivagayathiri:</h4>
            <ul style="margin: 0; padding-left: 20px; color: #94a3b8; font-size: 13.5px; line-height: 1.6;">
                <li>Modern Coach Fleet (Innova Crysta, Force Urbania, 40 & 54 Seater Luxury Buses)</li>
                <li>Experienced, police-verified chauffeurs with ghat-road certification</li>
                <li>Customized food arrangements (Satvik / Veg / Multi-Cuisine)</li>
                <li>24x7 GPS vehicle tracking and dispatch support desk</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 28px 0 16px 0;">
            <a href="https://sivagayathiritravels.com/campaign/{i+1}" style="background: #0284c7; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block; font-size: 14px;">
                View Itinerary & Claim Offer
            </a>
        </div>
    </div>
    <div style="background: #090d16; padding: 16px 24px; text-align: center; border-top: 1px solid #1e293b;">
        <p style="margin: 0; font-size: 12px; color: #64748b;">
            Sivagayathiri Tours & Travels • 100 Feet Road, Gandhipuram, Coimbatore • Tel: 0422-4000000<br>
            You are receiving this because you booked or inquired with Sivagayathiri Travels.
        </p>
    </div>
</div>
"""
        # Stagger sent status: 40 sent, 10 drafts
        if i % 5 == 0:
            sent_at = None # Draft
        else:
            sent_offset = random.randint(1, 90)
            sent_at = now - datetime.timedelta(days=sent_offset, hours=random.randint(1, 12))

        is_active = (i % 8 != 0)

        EmailCampaign.objects.create(
            name=name,
            subject=subject,
            body_html=body_html,
            sent_at=sent_at,
            is_active=is_active
        )
        campaign_count += 1
    print(f"✅ Created {campaign_count} Email Campaigns (both Sent and Draft editions with rich HTML).")

    # ------------------------------------------------------------------
    # F. SEED 50 UPSELL RECOMMENDATIONS (Marketing / Packages Add-Ons)
    # ------------------------------------------------------------------
    print("\n--- Seeding 50 Upsell Recommendations ---")
    UpsellRecommendation.objects.all().delete()

    upsell_catalog = [
        # Experience upgrades
        ("🔥 Campfire & DJ Music Night Setup", 
         "Private bonfire setup at resort premises with sound box, professional DJ playlist, and roasted marshmallows/snacks. Perfect for college groups and friends.", 4500),
        ("🛕 VIP Temple Darshan & Special Archana Pass Assistance", 
         "Skip the regular queue with expedited VIP entrance slots and special archana prasadam coordination at major pilgrim temples.", 1800),
        ("⛵ Luxury Private Alleppey Houseboat Upgrade", 
         "Upgrade from day motorboat to overnight luxury AC premium houseboat with onboard chef serving traditional Kerala Karimeen fry and meals.", 8500),
        ("🚙 4x4 Off-Road Mountain Jeep Safari", 
         "Thrilling 3-hour off-road mountain safari deep into tea valleys, viewpoint peaks, and hidden pine forest trails where regular buses cannot go.", 3200),
        ("🎙️ Multilingual Professional Certified Tour Guide", 
         "Government-approved expert guide fluent in Tamil, English, and Hindi to explain temple architecture, historical monuments, and regional folklore.", 2500),
        ("🍢 Beachside Bonfire & BBQ Dinner Setup", 
         "Exclusive beachside dining setup with charcoal grilled seafood, paneer tikka, and soothing ocean ambient music.", 3800),
        ("🚌 Pushback Air-Suspension Volvo Coach Upgrade", 
         "Upgrade your group bus transit to 2+2 ultra-luxury air-suspension Volvo multi-axle coach with individual USB charging and reclining pushback seats.", 12500),
        ("🛡️ Comprehensive Group Travel & Medical Insurance", 
         "Door-to-door accidental, medical emergency, and baggage loss protection cover for all traveling passengers throughout the journey.", 650),
        ("🎥 High-Definition Drone Videography & Reel Edit", 
         "Professional drone pilot capturing cinematic aerial shots of your group at scenic landmarks, edited into an Instagram-ready highlight video.", 7500),
        ("🍲 Pure Brahmin Satvik / Jain Catering Upgrade", 
         "Dedicated traveling cook team providing fresh, steaming home-style Udupi vegetarian food without onion/garlic at all journey stops.", 3200),
        ("⏰ Early Check-In & Late Check-Out Guaranteed Pass", 
         "Guaranteed room handover upon early 6 AM arrival and extended check-out until 6 PM on departure day without extra night room charges.", 1500),
        ("💐 Honeymoon Special: Flower Bed & Candlelight Dinner", 
         "Romantic room decoration with fresh exotic roses, heart-shaped chocolate cake, and a private 4-course candlelit dinner.", 2900),
        ("🧗 Adventure Rope Activities & Zipline Pass", 
         "Pre-booked tickets for high-rope course, Burma bridge, and 200m scenic valley zipline with certified safety harness and instructors.", 1200),
        ("🍵 Authentic Tea Factory Tasting & Gift Hamper", 
         "Guided factory tour explaining orthodox vs CTC tea processing, followed by 5 premium tea tastings and a complimentary 500g gift pack per family.", 850),
        ("🦽 Wheelchair & Dedicated Porter Assistance Service", 
         "Foldable sanitized wheelchair with dedicated assistant porter assisting senior citizens through railway stations and temple corridors.", 1400),
    ]

    upsell_count = 0
    for i in range(50):
        tmpl = upsell_catalog[i % len(upsell_catalog)]
        pkg = packages[i % len(packages)] if packages else None
        if not pkg:
            continue

        title = f"{tmpl[0]} for {pkg.name[:45]}"
        description = f"{tmpl[1]} Specially curated for travelers booking the '{pkg.name}' tour circuit."
        price = Decimal(tmpl[2]) + Decimal(random.choice([0, 200, 500, -100]))

        UpsellRecommendation.objects.create(
            package=pkg,
            title=title[:255],
            description=description,
            price=price
        )
        upsell_count += 1
    print(f"✅ Created {upsell_count} Upsell Recommendations linked to actual travel packages.")

    print("\n==================================================================")
    print("  SEEDING COMPLETE: 50 RECORDS GENERATED FOR ALL 6 MODELS")
    print("==================================================================")

if __name__ == '__main__':
    seed_data()
