# ctt_specialized_data.py
# Specialized Kerala, Student IV & Weekend Packages from chennaitourstravels.com
# Rebranded 100% for Siva Gayathri Tours & Travels

import decimal

SPECIALIZED_PACKAGES = [
    {
        'code': 'SGT-CTT-055',
        'name': 'Luxury Munnar Tree House & Alleppey Houseboat Experience',
        'destination': 'Cochin / Munnar / Alleppey',
        'category': 'holiday',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('8999.00'),
        'price_with_food': decimal.Decimal('11999.00'),
        'price_without_food': decimal.Decimal('8999.00'),
        'is_devotional': False,
        'description': 'Experience the magical synergy of misty mountain canopy living and serene backwater navigation. Stay 2 nights in an eco-luxury Tree House resort in Munnar surrounded by tea gardens and spice valleys, and 1 night on a private deluxe AC Houseboat cruising the palm-fringed lagoons of Alleppey with full traditional Kerala meals.',
        'itinerary': [
            {'day': 1, 'title': 'Cochin Arrival & Tree House Resort Check-in', 'route': 'Cochin to Munnar (130 km / 4 hrs)', 'activities': 'Pickup from Cochin Airport / Station. Scenic drive past Cheeyappara and Valara waterfalls. 4x4 Jeep transfer to treehouse eco-retreat in Munnar. Welcome herbal drink and sunset from tree canopy balcony. Candlelight dinner and overnight stay in Munnar Tree House.', 'morning': 'Pickup from Cochin, scenic ghats drive', 'sightseeing': 'Cheeyappara Falls, Valara Falls, Karadippara Viewpoint', 'evening': 'Candlelight dinner, treehouse stay', 'night_stay': 'Munnar Tree House Resort', 'meals': 'Dinner'},
            {'day': 2, 'title': 'Munnar Guided Tea Sanctuary & Plantation Trek', 'route': 'Munnar Local Circuit', 'activities': 'Optional morning sunrise yoga on resort deck. Guided plantation walking tour learning about cardamom, pepper, and tea. Visit Mattupetty Dam, Kundala Lake, and Tata Tea Museum. Return for cozy evening in treehouse.', 'morning': 'Resort yoga session, plantation walk, breakfast', 'sightseeing': 'Mattupetty Dam, Kundala Lake, Tea Museum, Echo Point', 'evening': 'Bonfire, organic mountain cuisine dinner', 'night_stay': 'Munnar Tree House Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Munnar to Alleppey Private Houseboat Cruise', 'route': 'Munnar to Alleppey (165 km / 5 hrs)', 'activities': 'Drive to Alleppey. Board private 1-bedroom AC Deluxe Houseboat at 12:30 PM. Leisurely glide along Vembanad Lake, Kuttanad paddy fields below sea level, and peaceful canal villages. Authentic Kerala lunch and evening tea with banana fritters served onboard.', 'morning': 'Breakfast at treehouse, scenic drive to Alleppey', 'sightseeing': 'Vembanad Lake, Kuttanad Canals, Village Life, Sunset Cruise', 'evening': 'Canoe ride in narrow canals, traditional Karimeen fish curry dinner onboard', 'night_stay': 'Private Deluxe Houseboat (Alleppey)', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Houseboat Breakfast - Cochin Drop', 'route': 'Alleppey to Cochin (80 km / 2 hrs)', 'activities': 'Morning cruise through mist-laden backwaters. Delicious Kerala breakfast on houseboat deck. Check-out by 09:00 AM. Transfer to Cochin Airport / Railway Station.', 'morning': 'Houseboat breakfast, checkout', 'sightseeing': 'Fort Kochi Chinese Fishing Nets (if time permits)', 'evening': 'Drop at airport / railway station for departure', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-056',
        'name': 'Dewalokam Organic Farm Stay & Alleppey Backwaters Retreat',
        'destination': 'Cochin / Dewalokam Farm / Alleppey',
        'category': 'family_vacation',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('9499.00'),
        'price_with_food': decimal.Decimal('12499.00'),
        'price_without_food': decimal.Decimal('9499.00'),
        'is_devotional': False,
        'description': 'An authentic experiential rural escape at Dewalokam Organic Farm on the banks of River Kannadipuzha, paired with an Alleppey backwater houseboat cruise. Experience pesticide-free farm gastronomy, cow milking, bamboo rafting, river swimming, and spice trail walks.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Cochin - Transfer to Dewalokam Farm', 'route': 'Cochin to Dewalokam (65 km / 1.5 hrs)', 'activities': 'Pickup from Cochin and transfer to Dewalokam Organic Farm. Warm family welcome. Afternoon swim in the crystal-clear river Kannadipuzha or bamboo rafting. Evening cooking demonstration using freshly harvested farm spices.', 'morning': 'Pickup from Cochin, check-in to Farmstay', 'sightseeing': 'River Kannadipuzha, Organic vegetable farms, Honeybee apiaries', 'evening': 'Interactive farm dinner with organic produce', 'night_stay': 'Dewalokam Organic Farmstay', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Farm Life, Spice Trail & Village Walk', 'route': 'Dewalokam Village & Forest Walk', 'activities': 'Participate in morning farm activities: cow milking, feeding goats and ducks, collecting honey. Guided walk through rubber and nutmeg plantations. Afternoon nature walk through neighboring forest and rubber tapping study.', 'morning': 'Fresh farm breakfast, spice plantation walk', 'sightseeing': 'Nutmeg, Pepper, Cinnamon, Vanilla and Rubber plantations', 'evening': 'Riverbank campfire, Kerala sadhya dinner', 'night_stay': 'Dewalokam Organic Farmstay', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Dewalokam to Alleppey Houseboat Cruise', 'route': 'Dewalokam to Alleppey (85 km / 2.5 hrs)', 'activities': 'Breakfast at farm, check out and drive to Alleppey. Board private deluxe houseboat at 12:30 PM. Cruise through enchanting backwater channels, coconut palms, and rural communities. Freshly prepared meals on board.', 'morning': 'Breakfast at farm, transfer to Alleppey', 'sightseeing': 'Alleppey backwaters, Vembanad Lake canals, village paddy fields', 'evening': 'Sunset view on the lake, dinner and overnight on houseboat', 'night_stay': 'Deluxe Houseboat (Alleppey)', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Alleppey Checkout & Cochin Departure', 'route': 'Alleppey to Cochin (80 km / 2 hrs)', 'activities': 'Houseboat breakfast, checkout at 09:00 AM. Transfer to Cochin airport or railway station.', 'morning': 'Breakfast, check out and airport transfer', 'sightseeing': 'Scenic coastal highway transfer', 'evening': 'Departure flight / train', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-057',
        'name': 'Kerala Spice Plantation Homestay & Houseboat Retreat',
        'destination': 'Cochin / Thekkady / Alleppey',
        'category': 'family_vacation',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('8799.00'),
        'price_with_food': decimal.Decimal('11799.00'),
        'price_without_food': decimal.Decimal('8799.00'),
        'is_devotional': False,
        'description': 'Stay in a heritage plantation homestay nestled within 50 acres of cardamom, pepper, and vanilla plantations in Thekkady high ranges, followed by a private luxury houseboat stay in Alleppey.',
        'itinerary': [
            {'day': 1, 'title': 'Cochin to Thekkady Plantation Homestay', 'route': 'Cochin to Thekkady (145 km / 4 hrs)', 'activities': 'Pickup from Cochin. Ascend scenic mountain highway to Thekkady. Check-in to ancestral plantation bungalow. Welcome tea and estate walk. Traditional Syrian Christian Kerala dinner.', 'morning': 'Pickup from Cochin, scenic mountain drive', 'sightseeing': 'Cardamom estates, pepper vines, mountain valleys', 'evening': 'Home-cooked dinner with hosts', 'night_stay': 'Thekkady Plantation Homestay', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Periyar Lake Safari & Spice Harvesting Study', 'route': 'Thekkady Local', 'activities': 'Early morning boat safari on Periyar Lake spotting wild elephants and bisons. Breakfast. Afternoon hands-on experience harvesting cardamom and black pepper. Cooking masterclass with plantation chef.', 'morning': 'Periyar wildlife boat safari, breakfast', 'sightseeing': 'Periyar Tiger Reserve, Spice Drying Yards', 'evening': 'Campfire, cultural stories, dinner', 'night_stay': 'Thekkady Plantation Homestay', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Thekkady to Alleppey Houseboat Cruise', 'route': 'Thekkady to Alleppey (135 km / 3.5 hrs)', 'activities': 'Drive down to Alleppey backwaters. Board private AC deluxe houseboat at 12:30 PM. Leisurely cruise through palm-lined canals and Vembanad Lake. Traditional meals onboard.', 'morning': 'Breakfast at homestay, transfer to Alleppey', 'sightseeing': 'Alleppey Backwaters, Kuttanad Paddy Fields', 'evening': 'Sunset canoe ride, dinner onboard', 'night_stay': 'Deluxe Houseboat (Alleppey)', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Houseboat Checkout & Cochin Departure', 'route': 'Alleppey to Cochin (80 km / 2 hrs)', 'activities': 'Breakfast on deck, check out at 09:00 AM. Transfer to Cochin Airport / Railway Station for departure.', 'morning': 'Houseboat breakfast, checkout', 'sightseeing': 'Coastal highway views', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-058',
        'name': 'Students IV: Munnar, Thekkady & Alleppey Educational Tour',
        'destination': 'Chennai / Munnar / Thekkady / Alleppey',
        'category': 'college_iv',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('5599.00'),
        'price_with_food': decimal.Decimal('5599.00'),
        'price_without_food': decimal.Decimal('4299.00'),
        'is_devotional': False,
        'description': 'Student Industrial Visit (IV) combining tea processing industry exposure in Munnar, biodiversity study in Periyar Tiger Reserve Thekkady, and a boat cruise through Alleppey backwaters.',
        'itinerary': [
            {'day': 1, 'title': 'Chennai Departure to Munnar', 'route': 'Chennai to Munnar (580 km)', 'activities': 'Late evening departure from college campus / Chennai by premium air-suspension coach. Overnight journey with music and entertainment onboard.', 'morning': 'Boarding and departure coordination', 'sightseeing': 'Scenic highway transit', 'evening': 'Overnight journey in coach', 'night_stay': 'Overnight Coach Journey', 'meals': 'Travel Pack'},
            {'day': 2, 'title': 'Arrival Munnar & Industrial Visit', 'route': 'Munnar Hills', 'activities': 'Arrival in Munnar, hotel check-in and refreshment. Afternoon industrial visit to KDHP Tea Processing Factory and Tata Tea Museum. Guided interaction with plant engineers. Resort DJ and campfire.', 'morning': 'Hotel check-in, breakfast', 'sightseeing': 'Tata Tea Museum, KDHP Processing Plant', 'evening': 'DJ and Campfire at resort, dinner', 'night_stay': 'Munnar Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Munnar Sightseeing to Thekkady', 'route': 'Munnar to Thekkady (85 km / 3 hrs)', 'activities': 'Visit Mattupetty Dam, Eco Point, and Kundala Lake. Proceed to Thekkady. Visit organic spice plantation for botany and agriculture study. Evening Kathakali and Kalaripayattu shows.', 'morning': 'Breakfast, Mattupetty Dam boating', 'sightseeing': 'Mattupetty Dam, Eco Point, Spice Plantation', 'evening': 'Kathakali cultural show, dinner', 'night_stay': 'Thekkady Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Thekkady Boating - Alleppey Cruise - Return', 'route': 'Thekkady to Alleppey to Chennai', 'activities': 'Morning wildlife boating in Periyar Lake. Drive to Alleppey for a backwater motorboat cruise through Vembanad Lake. Evening return coach to Chennai.', 'morning': 'Periyar wildlife boating, breakfast', 'sightseeing': 'Periyar National Park, Alleppey Backwaters', 'evening': 'Return departure to Chennai', 'night_stay': 'Overnight Coach Journey', 'meals': 'Breakfast, Lunch, Dinner'}
        ]
    },
    {
        'code': 'SGT-CTT-059',
        'name': 'Students IV: Coorg & Ooty Twin Hill Station Expedition',
        'destination': 'Coorg / Mysore / Ooty / Coimbatore',
        'category': 'college_iv',
        'duration_days': 5,
        'duration_nights': 4,
        'base_price': decimal.Decimal('3539.00'),
        'price_with_food': decimal.Decimal('3539.00'),
        'price_without_food': decimal.Decimal('2899.00'),
        'is_devotional': False,
        'description': 'Student expedition covering Coorg coffee estates, Abbey Falls, Mysore Royal Palace, Doddabetta Peak in Ooty, and Black Thunder Theme Park.',
        'itinerary': [
            {'day': 1, 'title': 'Chennai to Mysore / Coorg', 'route': 'Chennai to Mysore (480 km)', 'activities': 'Departure from Chennai Central. Overnight journey to Mysore. Transfer to Coorg hills.', 'morning': 'Boarding and departure', 'sightseeing': 'Deccan plateau transit', 'evening': 'Overnight transit', 'night_stay': 'Overnight Train / Coach', 'meals': 'Dinner onboard'},
            {'day': 2, 'title': 'Arrival Coorg & Sightseeing', 'route': 'Mysore to Coorg (120 km)', 'activities': 'Arrival in Coorg, resort check-in. Visit Abbey Falls, Raja Seat sunset garden, and Omkareshwara Temple. Evening DJ campfire.', 'morning': 'Resort check-in, breakfast', 'sightseeing': 'Abbey Falls, Raja Seat, Omkareshwara Temple', 'evening': 'Campfire with DJ party, dinner', 'night_stay': 'Coorg Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Talacauvery & Coffee Plantation Study', 'route': 'Coorg Local', 'activities': 'Excursion to Talacauvery (origin of River Kaveri) and Bhagamandala. Guided tour of organic coffee processing estates.', 'morning': 'Breakfast, drive to Talacauvery', 'sightseeing': 'Talacauvery, Bhagamandala, Coffee Plantations', 'evening': 'Local market visit, resort dinner', 'night_stay': 'Coorg Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Coorg to Mysore Heritage & Ooty Transfer', 'route': 'Coorg to Mysore to Ooty (160 km)', 'activities': 'Drive to Mysore. Visit Chamundi Hills, Mysore Zoo, and Mysore Royal Palace. Climb 36 hairpin bends to Ooty.', 'morning': 'Breakfast, Mysore Palace tour', 'sightseeing': 'Chamundi Hills, Mysore Palace, Bandipur Forest', 'evening': 'Check-in at Ooty hotel, dinner', 'night_stay': 'Ooty Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 5, 'title': 'Ooty Highlights - Black Thunder - Departure', 'route': 'Ooty to Mettupalayam (90 km)', 'activities': 'Visit Doddabetta Peak and Botanical Garden. Descend to Black Thunder Theme Park for thrill rides. Return coach to Chennai.', 'morning': 'Breakfast, Doddabetta Peak', 'sightseeing': 'Doddabetta Peak, Botanical Garden, Black Thunder Water Park', 'evening': 'Return departure to Chennai', 'night_stay': 'Overnight Coach Journey', 'meals': 'Breakfast, Lunch, Dinner'}
        ]
    },
    {
        'code': 'SGT-CTT-060',
        'name': 'Students IV: Goa Coastal Ecology & Heritage Expedition',
        'destination': 'Goa (Panaji, Calangute, Old Goa, Vasco)',
        'category': 'college_iv',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('5599.00'),
        'price_with_food': decimal.Decimal('5599.00'),
        'price_without_food': decimal.Decimal('4199.00'),
        'is_devotional': False,
        'description': 'Student expedition to Goa exploring marine biology, coastal ecosystems, UNESCO Portuguese architecture, Fort Aguada, Old Goa basilicas, and Mandovi river cruise.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Goa & Resort Check-in', 'route': 'Vasco / Airport to Resort', 'activities': 'Pickup from Vasco station / airport. Transfer to beach resort, check-in. Lunch, briefing, beach volleyball. Welcome dinner.', 'morning': 'Pickup and resort check-in', 'sightseeing': 'Resort private beach and palm groves', 'evening': 'Beach sunset, welcome dinner', 'night_stay': 'Goa Beach Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'North Goa Forts & Marine Study', 'route': 'North Goa Coastal Circuit', 'activities': 'Guided tour of Fort Aguada and lighthouse. Visit Calangute, Baga, Anjuna, and Vagator beaches. Study coastal geomorphology. DJ campfire.', 'morning': 'Breakfast, Fort Aguada visit', 'sightseeing': 'Fort Aguada, Calangute, Baga, Anjuna, Vagator Beach', 'evening': 'Flea market walk, DJ musical campfire, dinner', 'night_stay': 'Goa Beach Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Old Goa UNESCO Heritage & Mandovi Cruise', 'route': 'South Goa & Panaji', 'activities': 'Visit Basilica of Bom Jesus and Se Cathedral in Old Goa. Explore Fontainhas Latin Quarter. 1-hour sunset cruise on Mandovi River with Goan folk dance.', 'morning': 'Breakfast, Old Goa heritage tour', 'sightseeing': 'Basilica of Bom Jesus, Se Cathedral, Fontainhas, Mandovi Cruise', 'evening': 'Mandovi River Sunset Cruise, gala dinner', 'night_stay': 'Goa Beach Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Shopping & Departure', 'route': 'Resort to Vasco Station / Airport', 'activities': 'Breakfast, souvenir shopping for cashews and handicrafts. Check out at 11:00 AM. Transfer for departure.', 'morning': 'Breakfast, leisure and check-out', 'sightseeing': 'Panaji local craft emporium', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-061',
        'name': 'Weekend Getaway: Chennai - Kanchipuram - Mahabalipuram Circuit',
        'destination': 'Chennai / Kanchipuram / Mahabalipuram',
        'category': 'local_tour',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('1919.00'),
        'price_with_food': decimal.Decimal('2899.00'),
        'price_without_food': decimal.Decimal('1919.00'),
        'is_devotional': True,
        'description': 'A 2-day heritage weekend break from Chennai. Experience Pallava rock-cut shrines in Mahabalipuram and the temple city of Kanchipuram with silk saree weaving.',
        'itinerary': [
            {'day': 1, 'title': 'Chennai to Kanchipuram Silk & Temple City', 'route': 'Chennai to Kanchipuram (76 km / 1.5 hrs)', 'activities': 'Pickup from Chennai. Visit Ekambareswarar, Kailasanathar, Kamakshi Amman, and Varadharaja Perumal. Visit silk weavers. Drive to Mahabalipuram beach resort.', 'morning': 'Pickup, drive to Kanchipuram', 'sightseeing': 'Ekambareswarar, Kailasanathar, Kamakshi Amman, Silk Centers', 'evening': 'Drive to Mahabalipuram, check-in, dinner', 'night_stay': 'Mahabalipuram Beach Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 2, 'title': 'Mahabalipuram UNESCO Heritage & Beach Walk', 'route': 'Mahabalipuram to Chennai via ECR (60 km)', 'activities': 'Sunrise at Shore Temple. Explore Pancha Rathas, Arjuna Penance, and Krishna Butter Ball. Seafood lunch. Return drive along ECR to Chennai.', 'morning': 'Breakfast, Shore Temple exploration', 'sightseeing': 'Shore Temple, Pancha Rathas, Arjuna Penance, Krishna Butter Ball', 'evening': 'Return drop at Chennai residence', 'night_stay': 'Return to Chennai', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-062',
        'name': 'Weekend Coastal Tour: Chennai - Pondicherry - Chidambaram',
        'destination': 'Chennai / Pondicherry / Chidambaram',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('2899.00'),
        'price_with_food': decimal.Decimal('3999.00'),
        'price_without_food': decimal.Decimal('2899.00'),
        'is_devotional': True,
        'description': 'A balanced weekend retreat traversing the French Riviera of the East (Pondicherry) and cosmic dancer shrine of Lord Nataraja in Chidambaram.',
        'itinerary': [
            {'day': 1, 'title': 'Chennai to Pondicherry French Riviera', 'route': 'Chennai to Pondicherry via ECR (160 km / 3.5 hrs)', 'activities': 'Drive along scenic ECR. Visit Auroville Matrimandir viewpoint, Sri Aurobindo Ashram, French White Town, and Promenade Beach. Dinner at seaside restaurant.', 'morning': '06:30 AM departure, drive via ECR', 'sightseeing': 'Auroville Matrimandir, Sri Aurobindo Ashram, French White Town, Promenade Beach', 'evening': 'French cafe dinner, seaside stroll', 'night_stay': 'Pondicherry Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 2, 'title': 'Pondicherry - Chidambaram Nataraja Temple - Return', 'route': 'Pondicherry to Chidambaram to Chennai (240 km / 5 hrs)', 'activities': 'Drive to Chidambaram. Darshan at Thillai Nataraja Temple (Akasha Stalam). Rowboat cruise through Pichavaram Mangrove Forests. Return drive to Chennai.', 'morning': 'Breakfast, drive to Chidambaram', 'sightseeing': 'Thillai Nataraja Temple, Chidambara Rahasyam, Pichavaram Mangrove Forest', 'evening': 'Return drive to Chennai, residence drop', 'night_stay': 'Return to Chennai', 'meals': 'Breakfast, Lunch'}
        ]
    }
]
