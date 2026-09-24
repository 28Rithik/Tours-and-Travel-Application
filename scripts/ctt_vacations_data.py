# ctt_vacations_data.py
# 20 South Special Hill Station & Vacation Multi-Day Packages from chennaitourstravels.com
# Rebranded 100% for Siva Gayathri Tours & Travels

import decimal

VACATION_PACKAGES = [
    {
        'code': 'SGT-CTT-027',
        'name': 'Athirappilly, Munnar & Thekkady Hills & Waterfalls Tour',
        'destination': 'Cochin / Athirappilly / Munnar / Thekkady',
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('6199.00'),
        'price_with_food': decimal.Decimal('8499.00'),
        'price_without_food': decimal.Decimal('6199.00'),
        'is_devotional': False,
        'description': 'Experience the Niagara of India at Athirappilly Falls along with the misty tea carpet hills of Munnar and spice plantations of Thekkady.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Cochin - Athirappilly Falls - Munnar Transfer', 'route': 'Cochin to Athirappilly to Munnar (170 km)', 'activities': 'Pickup from Cochin. Drive to the majestic 80-foot Athirappilly Waterfalls. Enjoy spray walk and forest viewpoints. Ascend through Neriamangalam bridge and Cheeyappara falls to Munnar. Hotel check-in, dinner.', 'morning': 'Pickup from Cochin, Athirappilly Falls visit', 'sightseeing': 'Athirappilly Waterfalls, Vazhachal Forest, Cheeyappara Falls', 'evening': 'Munnar hotel check-in, campfire, dinner', 'night_stay': 'Munnar Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Munnar Tea Sanctuary & Sightseeing', 'route': 'Munnar Local Circuit', 'activities': 'Full day in Munnar visiting Mattupetty Dam, Kundala Lake, Eco Point, Top Station viewpoints, and Tata Tea Museum. Tea tasting and shopping.', 'morning': 'Breakfast, Mattupetty boating and Eco Point', 'sightseeing': 'Mattupetty Dam, Kundala Lake, Echo Point, Tata Tea Museum', 'evening': 'Resort leisure, dinner', 'night_stay': 'Munnar Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Munnar to Thekkady Boating & Departure', 'route': 'Munnar to Thekkady to Cochin (190 km)', 'activities': 'Morning drive to Thekkady. Boat safari in Periyar Lake spotting wild elephants, bisons, and birds. Spice plantation walk. Evening drive back to Cochin for departure.', 'morning': 'Breakfast, Periyar Lake wildlife boating', 'sightseeing': 'Periyar Tiger Reserve, Spice Plantations', 'evening': 'Drop at Cochin Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-028',
        'name': 'Bangalore, Mysore & Ooty Royal Heritage Circuit',
        'destination': 'Bangalore / Mysore / Ooty / Coonoor',
        'category': 'holiday',
        'duration_days': 6,
        'duration_nights': 5,
        'base_price': decimal.Decimal('7999.00'),
        'price_with_food': decimal.Decimal('11500.00'),
        'price_without_food': decimal.Decimal('7999.00'),
        'is_devotional': False,
        'description': 'A 6-day royal Karnataka and Nilgiri hills holiday covering Garden City Bangalore, royal palaces of Mysore, and misty tea plantations of Ooty and Coonoor.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Bangalore - Garden City Sightseeing', 'route': 'Bangalore Local', 'activities': 'Pickup from Bangalore. Visit Lalbagh Botanical Garden with glass house, Vidhana Soudha, Cubbon Park, and ISKCON Temple. Overnight in Bangalore.', 'morning': 'Pickup, hotel check-in', 'sightseeing': 'Lalbagh, Vidhana Soudha, Cubbon Park, ISKCON Temple', 'evening': 'MG Road / Brigade Road stroll, dinner', 'night_stay': 'Bangalore Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Bangalore to Srirangapatna & Mysore Palace', 'route': 'Bangalore to Mysore (145 km)', 'activities': 'Drive to Mysore. Stop at Tipu Sultan summer palace in Srirangapatna. Arrive Mysore, visit Mysore Royal Palace and Brindavan Gardens musical fountain.', 'morning': 'Breakfast, drive to Mysore via Srirangapatna', 'sightseeing': 'Srirangapatna, Mysore Palace, Chamundi Hills, Brindavan Gardens', 'evening': 'Brindavan Gardens musical fountain, dinner', 'night_stay': 'Mysore Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Mysore Zoo to Ooty Nilgiri Hills Transfer', 'route': 'Mysore to Ooty via Bandipur (125 km)', 'activities': 'Morning visit to Sri Chamarajendra Zoological Gardens. Drive through Bandipur and Mudumalai tiger reserves. Ascend 36 hairpin bends to Ooty.', 'morning': 'Breakfast, Mysore Zoo visit, jungle safari drive', 'sightseeing': 'Mysore Zoo, Bandipur Forest, Kalhatty Ghats', 'evening': 'Arrive Ooty, hotel check-in, campfire, dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Ooty Lake, Botanical Garden & Doddabetta', 'route': 'Ooty Local Circuit', 'activities': 'Visit Doddabetta Peak (highest in South India), Ooty Botanical Garden, Rose Garden, and boat ride in Ooty Lake. Homemade chocolate shopping.', 'morning': 'Breakfast, Doddabetta Peak panoramic view', 'sightseeing': 'Doddabetta Peak, Botanical Garden, Rose Garden, Ooty Lake', 'evening': 'Boating, chocolate shopping, dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 5, 'title': 'Coonoor Tea Gardens & Sim’s Park Excursion', 'route': 'Ooty to Coonoor and Return (40 km)', 'activities': 'Excursion to Coonoor by Toy Train or car. Visit Sim’s Park, Dolphin’s Nose viewpoint, Lamb’s Rock, and Highfield Tea Factory.', 'morning': 'Nilgiri Mountain Railway Toy Train ride to Coonoor', 'sightseeing': 'Toy Train, Sim’s Park, Dolphin’s Nose, Lamb’s Rock, Tea Factory', 'evening': 'Return to Ooty, resort dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 6, 'title': 'Pykara Lake, Waterfalls & Coimbatore Departure', 'route': 'Ooty to Coimbatore (90 km)', 'activities': 'Visit Pykara Lake and Pykara Waterfalls with speedboating. Descend the Nilgiri hills to Coimbatore Airport / Railway Junction for departure.', 'morning': 'Breakfast, Pykara Lake speedboating', 'sightseeing': 'Pykara Lake, Pykara Falls, Shooting Spot Pine Forests', 'evening': 'Drop at Coimbatore Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-029',
        'name': 'Bangalore & Mysore Royal Heritage Getaway',
        'destination': 'Bangalore / Mysore',
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('4900.00'),
        'price_with_food': decimal.Decimal('6800.00'),
        'price_without_food': decimal.Decimal('4900.00'),
        'is_devotional': False,
        'description': 'A compact 3-day royal holiday covering Bangalore Lalbagh, Mysore Maharaja Palace, Chamundi Hills, Srirangapatna, and Brindavan Gardens.',
        'itinerary': [
            {'day': 1, 'title': 'Bangalore City Highlights', 'route': 'Bangalore Local', 'activities': 'Pickup from Bangalore. Visit Lalbagh, Cubbon Park, Vidhana Soudha, and Bangalore Palace. Check-in, dinner.', 'morning': 'Pickup, city tour', 'sightseeing': 'Lalbagh, Bangalore Palace, Cubbon Park', 'evening': 'Dinner at hotel', 'night_stay': 'Bangalore Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Bangalore to Mysore & Royal Palace', 'route': 'Bangalore to Mysore (145 km)', 'activities': 'Drive to Mysore. Visit Tipu Sultan fort Srirangapatna, Mysore Palace, and Brindavan Gardens illumination.', 'morning': 'Breakfast, drive to Mysore', 'sightseeing': 'Srirangapatna, Mysore Palace, Brindavan Gardens', 'evening': 'Musical fountain, dinner', 'night_stay': 'Mysore Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Chamundi Hills, Mysore Zoo & Departure', 'route': 'Mysore to Bangalore (145 km)', 'activities': 'Visit Chamundeshwari Temple atop Chamundi Hills, Nandi monolith, and Mysore Zoo. Drive back to Bangalore for departure.', 'morning': 'Breakfast, Chamundi Hills visit', 'sightseeing': 'Chamundi Hills, Monolithic Nandi, Mysore Zoo', 'evening': 'Drop at Bangalore Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-030',
        'name': 'Malabar Coast Beaches & Historical Bekal Fort Tour',
        'destination': 'Calicut / Kannur / Bekal / Kasaragod',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('4499.00'),
        'price_with_food': decimal.Decimal('6299.00'),
        'price_without_food': decimal.Decimal('4499.00'),
        'is_devotional': False,
        'description': 'Discover North Kerala’s pristine coastline: Calicut beach where Vasco da Gama landed at Kappad, Kannur drive-in beach, and the sea-facing Bekal Fort.',
        'itinerary': [
            {'day': 1, 'title': 'Calicut to Kannur Coastal Drive', 'route': 'Calicut to Kannur (90 km)', 'activities': 'Arrival in Calicut. Visit historic Kappad Beach (Vasco da Gama landing site 1498) and Sargaalaya Arts Village. Proceed to Kannur. Experience Muzhappilangad Drive-in Beach (Asia’s longest drive-in beach). Hotel check-in, Malabar seafood dinner.', 'morning': 'Arrival Calicut, Kappad Beach and Sargaalaya', 'sightseeing': 'Kappad Beach, Sargaalaya Arts Village, Muzhappilangad Drive-in Beach', 'evening': 'Sunset drive on beach sands, dinner', 'night_stay': 'Kannur Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Kannur to Bekal Fort & Kasaragod', 'route': 'Kannur to Bekal to Kasaragod (85 km)', 'activities': 'Morning visit to St. Angelo Fort in Kannur. Drive to Kasaragod to explore the keyhole-shaped Bekal Fort jutting into the Arabian Sea (famous from movie Bombay). Visit Bekal Beach Park and Chandragiri Fort. Departure transfer.', 'morning': 'Breakfast, St. Angelo Fort and drive to Bekal', 'sightseeing': 'St. Angelo Fort, Bekal Fort, Bekal Beach Park, Chandragiri River', 'evening': 'Departure transfer at Kasaragod / Mangalore', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-031',
        'name': 'Coorg & Wayanad Coffee Hills & Mist Holiday',
        'destination': 'Mysore / Coorg / Wayanad',
        'category': 'hill_station',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('6799.00'),
        'price_with_food': decimal.Decimal('9199.00'),
        'price_without_food': decimal.Decimal('6799.00'),
        'is_devotional': False,
        'description': 'A tranquil twin-hill getaway across the aromatic coffee estates of Coorg and misty rainforest ridges of Wayanad. Features Abbey Falls, Talacauvery, Banasura Sagar Dam, and Edakkal Caves.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Mysore to Coorg - Abbey Falls & Raja Seat', 'route': 'Mysore to Coorg (120 km / 3 hrs)', 'activities': 'Pickup from Mysore. Scenic drive through sandalwood and coffee territory into Madikeri, Coorg. Check-in to resort, lunch. Visit Abbey Falls cascading amidst coffee plantations, Omkareshwara Temple, and Raja’s Seat for sunset over rolling Western Ghats.', 'morning': 'Pickup from Mysore, coffee trail drive', 'sightseeing': 'Abbey Falls, Omkareshwara Temple, Raja’s Seat', 'evening': 'Resort campfire, Coorg traditional pork/veg dinner', 'night_stay': 'Coorg Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Talacauvery & Wayanad Transfer', 'route': 'Coorg to Wayanad via Kutta (110 km / 3 hrs)', 'activities': 'Morning visit to Talacauvery (birthplace of River Kaveri) and Bhagamandala. Drive across Kerala border into Wayanad. Visit Banasura Sagar Dam (largest earthen dam in India) with speedboating.', 'morning': 'Breakfast, Talacauvery and Bhagamandala', 'sightseeing': 'Talacauvery, Bhagamandala, Banasura Sagar Dam', 'evening': 'Check-in to Wayanad resort, musical evening, dinner', 'night_stay': 'Wayanad Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Edakkal Caves, Soochipara Falls & Calicut Drop', 'route': 'Wayanad to Calicut (85 km / 2.5 hrs)', 'activities': 'Morning trek to prehistoric Neolithic rock carvings at Edakkal Caves. Visit Soochipara Waterfalls. Drive down Thamarassery Churam mountain pass with 9 hairpin bends to Calicut for departure.', 'morning': 'Breakfast, Edakkal Caves prehistoric petroglyphs trek', 'sightseeing': 'Edakkal Caves, Soochipara Falls, Lakkidi Viewpoint', 'evening': 'Drop at Calicut Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-032',
        'name': 'Goa Sun, Sand & Portuguese Heritage Holiday',
        'destination': 'Goa (Panaji, Calangute, Baga, Old Goa, Vasco)',
        'category': 'holiday',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('5599.00'),
        'price_with_food': decimal.Decimal('8499.00'),
        'price_without_food': decimal.Decimal('5599.00'),
        'is_devotional': False,
        'description': 'Enjoy the vibrant holiday spirit of Goa. Covers North Goa beaches (Calangute, Baga, Anjuna, Vagator), historical Fort Aguada, UNESCO World Heritage Old Goa churches, and Mandovi River sunset cruise.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Goa & Beach Resort Leisure', 'route': 'Vasco / Dabolim / Mopa to Resort', 'activities': 'Pickup from railway station / airport. Transfer to beach resort, check-in. Lunch. Afternoon at leisure enjoying beach walks or pool. Sunset beach stroll and welcome dinner.', 'morning': 'Pickup and resort check-in', 'sightseeing': 'Private beach access, palm groves', 'evening': 'Beach sunset, Goan seafood dinner', 'night_stay': 'Goa Beach Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'North Goa Forts, Beaches & Water Sports', 'route': 'North Goa Coastal Circuit', 'activities': 'Explore 17th-century Portuguese Fort Aguada and lighthouse. Visit Calangute Beach, Baga Beach, Anjuna Beach, and Vagator red cliff beach. Water sports options (parasailing, jet ski). Evening Tito’s Lane nightlife stroll.', 'morning': 'Breakfast, Fort Aguada visit', 'sightseeing': 'Fort Aguada, Calangute, Baga, Anjuna, Vagator Beach', 'evening': 'Night market / beach shack dining', 'night_stay': 'Goa Beach Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Old Goa UNESCO Heritage & Mandovi Sunset Cruise', 'route': 'South Goa & Panaji (60 km circuit)', 'activities': 'Visit Basilica of Bom Jesus (storing mortal remains of St. Francis Xavier), Se Cathedral, and Church of St. Francis of Assisi. Walk through Fontainhas Latin Quarter in Panaji. Evening 1-hour sunset cruise on Mandovi River with Goan folk music and dance.', 'morning': 'Breakfast, Old Goa heritage churches', 'sightseeing': 'Basilica of Bom Jesus, Se Cathedral, Fontainhas Latin Quarter, Mandovi Cruise', 'evening': 'Mandovi River Sunset Cruise, gala dinner', 'night_stay': 'Goa Beach Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Goa Shopping & Departure', 'route': 'Resort to Vasco / Dabolim', 'activities': 'Breakfast, check out at 11:00 AM. Souvenir shopping for Goan feni, spices, and cashews. Transfer to airport / station for departure.', 'morning': 'Breakfast, leisure and check-out', 'sightseeing': 'Local Goan craft market', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-033',
        'name': 'Mysore Royal Gardens & Ooty Nilgiri Hills Tour',
        'destination': 'Mysore / Bandipur / Ooty / Coonoor',
        'category': 'hill_station',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('6599.00'),
        'price_with_food': decimal.Decimal('8999.00'),
        'price_without_food': decimal.Decimal('6599.00'),
        'is_devotional': False,
        'description': 'A popular 3-day holiday pairing the grandeur of Mysore with the cool tea slopes of Ooty and Coonoor.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Mysore & Palace to Ooty', 'route': 'Mysore to Ooty (125 km)', 'activities': 'Pickup from Mysore. Visit Mysore Royal Palace and Chamundi Hills. Drive through Bandipur tiger reserve and climb Nilgiri hills. Check-in to Ooty hotel, dinner.', 'morning': 'Mysore Palace visit, lunch', 'sightseeing': 'Mysore Palace, Chamundi Hills, Bandipur Forest', 'evening': 'Arrive Ooty, hotel check-in, campfire, dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Ooty & Coonoor Sightseeing', 'route': 'Ooty to Coonoor and Return (40 km)', 'activities': 'Visit Doddabetta Peak, Botanical Garden, Sim’s Park Coonoor, Dolphin’s Nose, and Tea Factory. Evening boating in Ooty Lake.', 'morning': 'Breakfast, Doddabetta and Coonoor', 'sightseeing': 'Doddabetta Peak, Botanical Garden, Sim’s Park, Ooty Lake', 'evening': 'Boating, homemade chocolate shopping, dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Pykara Lake & Coimbatore Departure', 'route': 'Ooty to Coimbatore (90 km)', 'activities': 'Morning visit to Pykara Lake and waterfalls. Descend Nilgiris to Coimbatore for departure.', 'morning': 'Breakfast, Pykara Lake speedboating', 'sightseeing': 'Pykara Lake, Pykara Waterfalls', 'evening': 'Drop at Coimbatore Airport / Junction', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-034',
        'name': 'Wayanad Rainforest, Wildlife & Waterfalls Nature Escape',
        'destination': 'Calicut / Wayanad / Sultan Bathery',
        'category': 'hill_station',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3899.00'),
        'price_with_food': decimal.Decimal('5299.00'),
        'price_without_food': decimal.Decimal('3899.00'),
        'is_devotional': False,
        'description': 'Immerse yourself in Wayanad’s lush green canopy: Edakkal Caves prehistoric rock art, Soochipara Falls, Pookode natural freshwater lake, and Muthanga wildlife safari.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Wayanad - Pookode Lake & Banasura Dam', 'route': 'Calicut to Wayanad (85 km)', 'activities': 'Pickup from Calicut. Drive up Thamarassery ghat pass. Visit Pookode Lake nestled amidst evergreen hills, Lakkidi Viewpoint, and Banasura Sagar Dam. Hotel check-in, dinner.', 'morning': 'Pickup from Calicut, ghats drive, Pookode Lake', 'sightseeing': 'Pookode Lake, Lakkidi Viewpoint, Banasura Sagar Dam', 'evening': 'Resort campfire, Kerala dinner', 'night_stay': 'Wayanad Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Edakkal Caves, Soochipara Falls & Departure', 'route': 'Wayanad to Calicut (85 km)', 'activities': 'Trek to Edakkal Caves to observe stone age petroglyphs. Visit Soochipara Waterfalls. Afternoon drive back to Calicut for departure.', 'morning': 'Breakfast, Edakkal Caves trek and Soochipara Falls', 'sightseeing': 'Edakkal Caves, Soochipara Waterfalls, Tea Gardens', 'evening': 'Drop at Calicut Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-035',
        'name': 'Yelagiri Hills Nature & Boating Getaway',
        'destination': 'Chennai / Yelagiri Hills',
        'category': 'hill_station',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3399.00'),
        'price_with_food': decimal.Decimal('4499.00'),
        'price_without_food': decimal.Decimal('3399.00'),
        'is_devotional': False,
        'description': 'A peaceful Eastern Ghats hill escape to Yelagiri with 14 hairpin bend viewpoints, Punganoor Lake pedal boating, Nature Park, and Jalagamparai Waterfalls.',
        'itinerary': [
            {'day': 1, 'title': 'Chennai to Yelagiri Hills - Lake & Nature Park', 'route': 'Chennai to Yelagiri (230 km)', 'activities': 'Morning departure from Chennai. Climb 14 hairpin bends. Check-in to resort, lunch. Afternoon pedal boating in Punganoor Lake and Nature Park walk. Evening campfire, dinner.', 'morning': '07:00 AM pickup, scenic ghat road drive', 'sightseeing': '14 Hairpin Viewpoint, Punganoor Lake, Nature Park', 'evening': 'Campfire, dinner', 'night_stay': 'Yelagiri Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Jalagamparai Waterfalls Trek & Return', 'route': 'Yelagiri to Chennai (230 km)', 'activities': 'Morning excursion to Jalagamparai Waterfalls and Murugan hill temple. Lunch. Check out and return drive to Chennai.', 'morning': 'Breakfast, Jalagamparai Waterfalls trek', 'sightseeing': 'Jalagamparai Falls, Murugan Temple, Telescope House', 'evening': 'Return drive to Chennai arriving by 08:30 PM', 'night_stay': 'Return to Chennai', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-036',
        'name': 'Yercaud Shevaroy Hills & Emerald Lake Resort Tour',
        'destination': 'Salem / Yercaud Hills',
        'category': 'hill_station',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('4959.00'),
        'price_with_food': decimal.Decimal('6459.00'),
        'price_without_food': decimal.Decimal('4959.00'),
        'is_devotional': False,
        'description': 'Jewel of the South Eastern Ghats holiday. Boating in Emerald Lake, Lady’s Seat, Pagoda Point, Killiyur Waterfalls, and Shevaroy Temple.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Salem to Yercaud - Lake & Viewpoints', 'route': 'Salem to Yercaud (35 km / 20 hairpin bends)', 'activities': 'Pickup from Salem. Drive up the 20 hairpin bends to Yercaud at 1,515 meters. Check-in, lunch. Boating in Yercaud Emerald Lake, visit Anna Park, Lady’s Seat, and Pagoda Point. Campfire, dinner.', 'morning': 'Pickup from Salem, ghats drive, hotel check-in', 'sightseeing': 'Yercaud Lake, Anna Park, Lady’s Seat, Gent’s Seat, Pagoda Point', 'evening': 'Musical campfire, dinner', 'night_stay': 'Yercaud Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Killiyur Falls, Shevaroy Cave Temple & Return', 'route': 'Yercaud to Salem (35 km)', 'activities': 'Trek to the 300-foot Killiyur Waterfalls. Visit Shevaroy Temple atop the highest peak inside a narrow cave shrine. Spice and coffee shopping. Descend to Salem for departure.', 'morning': 'Breakfast, Killiyur Falls trek and Shevaroy Temple', 'sightseeing': 'Killiyur Waterfalls, Shevaroy Temple, Botanical Garden, Montfort School view', 'evening': 'Drop at Salem Junction', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-037',
        'name': 'Kumarakom, Alleppey & Athirappilly Backwaters & Cascades',
        'destination': 'Cochin / Athirappilly / Kumarakom / Alleppey',
        'category': 'holiday',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('7999.00'),
        'price_with_food': decimal.Decimal('10999.00'),
        'price_without_food': decimal.Decimal('7999.00'),
        'is_devotional': False,
        'description': 'A complete 4-day Kerala water circuit: the thunderous Athirappilly waterfalls, bird paradise in Kumarakom lagoon, and an authentic houseboat stay in Alleppey.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Cochin to Athirappilly Waterfalls', 'route': 'Cochin to Athirappilly (70 km)', 'activities': 'Pickup from Cochin. Visit Athirappilly and Vazhachal waterfalls. Hotel check-in, dinner.', 'morning': 'Pickup, drive to Athirappilly', 'sightseeing': 'Athirappilly Falls, Vazhachal Reserve', 'evening': 'Resort relaxation, dinner', 'night_stay': 'Athirappilly Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Athirappilly to Kumarakom Bird Sanctuary', 'route': 'Athirappilly to Kumarakom (120 km)', 'activities': 'Drive to Kumarakom on the banks of Vembanad Lake. Visit Kumarakom Bird Sanctuary. Lakeside resort check-in, sunset canoe ride.', 'morning': 'Breakfast, drive to Kumarakom', 'sightseeing': 'Kumarakom Bird Sanctuary, Vembanad Lake', 'evening': 'Sunset canoe ride, dinner', 'night_stay': 'Kumarakom Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Kumarakom to Alleppey Houseboat Cruise', 'route': 'Kumarakom to Alleppey (35 km)', 'activities': 'Board private deluxe AC Houseboat at 12:30 PM. Cruise through Vembanad backwaters, Kuttanad paddy fields. Meals served onboard.', 'morning': 'Breakfast, board houseboat at 12:30 PM', 'sightseeing': 'Alleppey Backwaters, Kuttanad Canals', 'evening': 'Overnight on houseboat, traditional Kerala dinner', 'night_stay': 'Deluxe Houseboat (Alleppey)', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Houseboat Checkout & Cochin Departure', 'route': 'Alleppey to Cochin (80 km)', 'activities': 'Houseboat breakfast, checkout by 09:00 AM. Transfer to Cochin Airport / Railway Station for departure.', 'morning': 'Breakfast on boat, checkout', 'sightseeing': 'Fort Kochi sights (if time permits)', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-038',
        'name': 'Kumarakom Luxury Houseboat Lagoon Cruise',
        'destination': 'Cochin / Kumarakom',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('13799.00'),
        'price_with_food': decimal.Decimal('16799.00'),
        'price_without_food': decimal.Decimal('13799.00'),
        'is_devotional': False,
        'description': 'An exclusive private luxury houseboat experience in Kumarakom on Vembanad Lake with private chef, personalized Kerala culinary feasts, and lagoon cruising.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Kumarakom & Houseboat Embarkation', 'route': 'Cochin to Kumarakom (75 km)', 'activities': 'Pickup from Cochin. Board private luxury houseboat at Kumarakom jetty at 12:30 PM. Welcome drink. Cruise across Vembanad Lake. Traditional Karimeen lunch. Evening canoe ride into village canals. Sunset tea with Kerala snacks. Candlelight dinner onboard.', 'morning': 'Pickup from Cochin, arrive Kumarakom jetty', 'sightseeing': 'Vembanad Lake, Pathiramanal Island view, Village Canals', 'evening': 'Canoe ride, candlelight dinner onboard', 'night_stay': 'Private Luxury Houseboat', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Morning Lagoon Cruise & Departure', 'route': 'Kumarakom to Cochin (75 km)', 'activities': 'Early morning cruise as fishermen cast nets across the lagoon. Kerala appam and stew breakfast on deck. Check-out by 09:30 AM. Transfer to Cochin airport / station.', 'morning': 'Morning cruise, authentic Kerala breakfast', 'sightseeing': 'Bird watching on Vembanad Lake', 'evening': 'Drop at Cochin Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-039',
        'name': 'South Special 10-Day Complete Grand Holiday Circuit',
        'destination': 'Chennai / Bangalore / Mysore / Ooty / Kodaikanal / Madurai / Kanyakumari',
        'category': 'holiday',
        'duration_days': 10,
        'duration_nights': 9,
        'base_price': decimal.Decimal('19500.00'),
        'price_with_food': decimal.Decimal('26500.00'),
        'price_without_food': decimal.Decimal('19500.00'),
        'is_devotional': False,
        'description': 'The master 10-day vacation of South India combining royal palaces, twin queen hill stations (Ooty & Kodaikanal), cultural heritage of Madurai, and lands end at Kanyakumari.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Bangalore - City Sights', 'route': 'Bangalore City Tour', 'activities': 'Arrival in Bangalore. Visit Lalbagh, Vidhana Soudha, Cubbon Park. Hotel check-in, dinner.', 'morning': 'Pickup, check-in', 'sightseeing': 'Lalbagh, Vidhana Soudha', 'evening': 'Dinner', 'night_stay': 'Bangalore Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Bangalore to Mysore Heritage', 'route': 'Bangalore to Mysore (145 km)', 'activities': 'Drive to Mysore via Srirangapatna. Visit Mysore Palace and Brindavan Gardens illumination.', 'morning': 'Breakfast, drive to Mysore', 'sightseeing': 'Mysore Palace, Brindavan Gardens', 'evening': 'Musical fountain, dinner', 'night_stay': 'Mysore Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Mysore to Ooty Nilgiri Hills', 'route': 'Mysore to Ooty (125 km)', 'activities': 'Drive through Bandipur and Mudumalai tiger reserves. Climb 36 hairpin bends to Ooty. Hotel check-in.', 'morning': 'Breakfast, jungle safari drive', 'sightseeing': 'Bandipur, Mudumalai, Ooty Hills', 'evening': 'Campfire, dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Ooty & Coonoor Highlights', 'route': 'Ooty to Coonoor (40 km)', 'activities': 'Visit Doddabetta Peak, Botanical Garden, Sim’s Park, Dolphin’s Nose, and Ooty Lake boating.', 'morning': 'Breakfast, Doddabetta Peak', 'sightseeing': 'Doddabetta, Sim’s Park, Ooty Lake', 'evening': 'Boating, dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 5, 'title': 'Ooty to Kodaikanal Princess of Hills', 'route': 'Ooty to Kodaikanal (260 km / 6.5 hrs)', 'activities': 'Descend Nilgiris and climb the Palani Hills to Kodaikanal. Check-in to resort, evening walk around Kodai Lake.', 'morning': 'Breakfast, scenic mountain highway drive', 'sightseeing': 'Silver Cascade Waterfalls, Kodai Lake', 'evening': 'Kodai Lake stroll, dinner', 'night_stay': 'Kodaikanal Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 6, 'title': 'Kodaikanal Sightseeing', 'route': 'Kodaikanal Circuit', 'activities': 'Visit Pillar Rocks, Green Valley View, Coaker’s Walk, Pine Forest, and pedal boating in star-shaped Kodai Lake.', 'morning': 'Breakfast, Pillar Rocks and Coaker’s Walk', 'sightseeing': 'Pillar Rocks, Green Valley View, Pine Forest, Kodai Lake', 'evening': 'Boating, homemade chocolates shopping, dinner', 'night_stay': 'Kodaikanal Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 7, 'title': 'Kodaikanal to Madurai Cultural Capital', 'route': 'Kodaikanal to Madurai (120 km)', 'activities': 'Drive to Madurai. Check-in, lunch. Visit Thirumalai Nayakkar Palace. Evening Meenakshi Amman Temple special darshan.', 'morning': 'Breakfast, drive down hills to Madurai', 'sightseeing': 'Thirumalai Nayakkar Mahal, Meenakshi Amman Temple', 'evening': 'Temple evening procession, dinner', 'night_stay': 'Madurai Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 8, 'title': 'Madurai to Rameswaram Island', 'route': 'Madurai to Rameswaram (170 km)', 'activities': 'Cross Pamban Sea Bridge. Visit Ramanathaswamy Temple 22 wells, Dhanushkodi ghost town, and Ram Setu viewpoint.', 'morning': 'Breakfast, drive across Pamban Bridge', 'sightseeing': 'Pamban Bridge, Ramanathaswamy Temple, Dhanushkodi', 'evening': 'Sunset view, dinner', 'night_stay': 'Rameswaram Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 9, 'title': 'Rameswaram to Kanyakumari Lands End', 'route': 'Rameswaram to Kanyakumari (310 km)', 'activities': 'Drive to Kanyakumari. Ferry to Vivekananda Rock Memorial and Thiruvalluvar Statue. Sunset at Triveni Sangam.', 'morning': 'Breakfast, drive to Kanyakumari', 'sightseeing': 'Vivekananda Rock Memorial, Thiruvalluvar Statue, Kumari Amman Temple', 'evening': 'Sunset view, dinner', 'night_stay': 'Kanyakumari Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 10, 'title': 'Kanyakumari Sunrise & Trivandrum Departure', 'route': 'Kanyakumari to Trivandrum (95 km)', 'activities': 'Spectacular sunrise over ocean. Visit Padmanabhaswamy Temple Trivandrum. Drop at Trivandrum Airport / Railway Station.', 'morning': 'Sunrise over ocean, breakfast, drive to Trivandrum', 'sightseeing': 'Padmanabhaswamy Temple, Kovalam Beach', 'evening': 'Departure transfer with incredible memories', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-040',
        'name': 'Tamil Nadu Classical Cultural & Temple Heritage Tour',
        'destination': 'Chennai / Mahabalipuram / Thanjavur / Madurai',
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5900.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5900.00'),
        'is_devotional': True,
        'description': 'A 3-day deep dive into Tamil Nadu’s classical art, architecture, and dynasties: Pallavas at Mahabalipuram, Cholas at Thanjavur, and Pandyas at Madurai.',
        'itinerary': [
            {'day': 1, 'title': 'Chennai to Mahabalipuram & Thanjavur', 'route': 'Chennai to Mahabalipuram to Thanjavur (320 km)', 'activities': 'Morning pickup from Chennai. Visit Shore Temple and Arjuna Penance in Mahabalipuram. Drive to Thanjavur. Visit Brihadeeswarar Temple at sunset.', 'morning': 'Pickup from Chennai, Mahabalipuram heritage', 'sightseeing': 'Shore Temple, Arjuna Penance, Thanjavur Big Temple', 'evening': 'Brihadeeswarar evening illumination, dinner', 'night_stay': 'Thanjavur Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Thanjavur Palace to Madurai Meenakshi', 'route': 'Thanjavur to Trichy to Madurai (180 km)', 'activities': 'Visit Thanjavur Royal Palace and Saraswathi Mahal Library. Stop at Srirangam in Trichy. Proceed to Madurai. Evening Meenakshi Amman Temple darshan.', 'morning': 'Breakfast, Thanjavur Palace and Srirangam Temple', 'sightseeing': 'Thanjavur Palace, Srirangam Temple, Meenakshi Amman Temple', 'evening': 'Meenakshi Amman evening aarti, dinner', 'night_stay': 'Madurai Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Madurai Heritage & Departure', 'route': 'Madurai Local & Departure', 'activities': 'Visit Thirumalai Nayakkar Palace and Gandhi Memorial Museum. Sungudi saree and jasmine flower shopping. Drop at Madurai Junction / Airport.', 'morning': 'Breakfast, Thirumalai Nayakkar Palace', 'sightseeing': 'Thirumalai Nayakkar Palace, Gandhi Museum', 'evening': 'Drop at airport / railway station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    }
]
