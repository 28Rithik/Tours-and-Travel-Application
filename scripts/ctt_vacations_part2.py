# ctt_vacations_part2.py
# Remaining Vacation, Destination, Kerala, Student IV & Weekend Packages from chennaitourstravels.com
# Rebranded 100% for Siva Gayathri Tours & Travels

import decimal

VACATION_PACKAGES_PART2 = [
    {
        'code': 'SGT-CTT-041',
        'name': 'South India Wildlife Sanctuaries & Elephant Safari Tour',
        'destination': 'Mudumalai / Bandipur / Wayanad',
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5900.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5900.00'),
        'is_devotional': False,
        'description': 'An exhilarating wildlife expedition through the Nilgiri Biosphere Reserve. Includes open jeep safaris in Mudumalai and Bandipur National Parks, Theppakadu Elephant Camp interaction, and birding in Wayanad sanctuary.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Mudumalai & Evening Jungle Safari', 'route': 'Coimbatore / Mysore to Mudumalai (110 km)', 'activities': 'Pickup and transfer to jungle lodge in Mudumalai. Lunch. Afternoon open gypsy safari in Mudumalai Tiger Reserve spotting spotted deer, sambar, wild boars, peacocks, and Indian gaurs. Evening jungle campfire, dinner.', 'morning': 'Pickup, drive to Mudumalai, lodge check-in', 'sightseeing': 'Mudumalai Tiger Reserve, Moyar River Gorge', 'evening': 'Jungle safari, campfire, dinner', 'night_stay': 'Mudumalai Jungle Lodge', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Theppakadu Elephant Camp & Bandipur Safari', 'route': 'Mudumalai to Bandipur (25 km)', 'activities': 'Early morning visit to Theppakadu Elephant Camp to witness elephant bathing and feeding. Breakfast. Afternoon tiger safari in Bandipur National Park across Karnataka border. Evening wildlife documentary screening.', 'morning': 'Theppakadu Elephant Camp, breakfast', 'sightseeing': 'Elephant Camp, Bandipur National Park Safari', 'evening': 'Campfire, dinner', 'night_stay': 'Bandipur Jungle Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Muthanga Wildlife Sanctuary & Departure', 'route': 'Bandipur to Sultan Bathery to Calicut (120 km)', 'activities': 'Morning jeep drive in Wayanad Muthanga Wildlife Sanctuary. Breakfast. Scenic return drive down the Western Ghats to Calicut / Coimbatore for departure.', 'morning': 'Breakfast, Muthanga wildlife drive', 'sightseeing': 'Muthanga Wildlife Sanctuary, Chembra peak views', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-042',
        'name': 'Tamil Nadu Scenic Beaches & Coastal Forts Gateway Tour',
        'destination': 'Chennai / Mahabalipuram / Pondicherry / Tranquebar',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3800.00'),
        'price_with_food': decimal.Decimal('5200.00'),
        'price_without_food': decimal.Decimal('3800.00'),
        'is_devotional': False,
        'description': 'Explore Tamil Nadu’s historic coastline along the Bay of Bengal: Covelong surfing beach, Mahabalipuram shore, Pondicherry French promenade, and the 1620 Danish Fort Dansborg in Tranquebar (Tharangambadi).',
        'itinerary': [
            {'day': 1, 'title': 'Chennai to Mahabalipuram & Pondicherry Beaches', 'route': 'Chennai to Pondicherry via ECR (160 km)', 'activities': 'Morning coastal drive along ECR. Visit Covelong beach and Mahabalipuram Shore Temple. Proceed to Pondicherry. Check-in at seaside hotel. Walk along Promenade Beach, visit French War Memorial and Old Lighthouse. Coastal seafood dinner.', 'morning': '07:30 AM pickup, coastal drive via ECR', 'sightseeing': 'Covelong Beach, Shore Temple, Promenade Beach, French Quarter', 'evening': 'Seaside promenade walk, dinner', 'night_stay': 'Pondicherry Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Pondicherry to Tranquebar Danish Fort & Return', 'route': 'Pondicherry to Tranquebar to Chennai (280 km)', 'activities': 'Drive south to the historic Danish settlement of Tranquebar (Tharangambadi - Place of the Singing Waves). Explore Fort Dansborg built in 1620 directly on the ocean shore, New Jerusalem Church, and Maritime Museum. Afternoon return drive to Chennai.', 'morning': 'Breakfast, drive to Tranquebar', 'sightseeing': 'Fort Dansborg, Danish Governor Bungalow, Zion Church, Tranquebar Beach', 'evening': 'Return drive to Chennai by 09:30 PM', 'night_stay': 'Departure / Return', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-043',
        'name': 'Tamil Nadu Grand Temple Festivals & Heritage Cultural Tour',
        'destination': 'Madurai / Thanjavur / Chidambaram / Kumbakonam',
        'category': 'devotional',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5900.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5900.00'),
        'is_devotional': True,
        'description': 'Experience the grandeur of Tamil festival culture: witness Natyanjali dance festivals, temple car chariot processions, temple elephant rituals, and nadaswaram instrumental music across the ancient temple cities.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Madurai - Temple Car & Chariot Heritage', 'route': 'Madurai Local', 'activities': 'Arrival in Madurai. Check-in, lunch. Visit Meenakshi Amman Temple to observe traditional temple rituals, elephant blessings, and the massive wooden temple chariot (Ther). Evening classical Carnatic music and nadaswaram recital.', 'morning': 'Arrival, check-in, lunch', 'sightseeing': 'Meenakshi Temple Chariot Mandapam, Thousand Pillar Hall', 'evening': 'Temple musical rituals, dinner', 'night_stay': 'Madurai Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Thanjavur Chola Arts & Bronze Sculpting', 'route': 'Madurai to Thanjavur (180 km)', 'activities': 'Drive to Thanjavur. Visit Brihadeeswarar Temple. Attend an authentic lost-wax bronze casting demonstration in Swamimalai where Chola bronzes have been cast for a millennium. Visit Tanjore painting artists. Dinner at heritage hotel.', 'morning': 'Breakfast, drive to Thanjavur', 'sightseeing': 'Brihadeeswarar Temple, Swamimalai Bronze Casting, Tanjore Painting studios', 'evening': 'Cultural demonstration, dinner', 'night_stay': 'Thanjavur Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Chidambaram Natyanjali Heritage & Departure', 'route': 'Thanjavur to Chidambaram to Chennai / Trichy (200 km)', 'activities': 'Visit Chidambaram Nataraja Temple, where all 108 Karanas of Bharatanatyam are sculpted on the gopurams. Traditional lunch. Return departure to Chennai / Trichy.', 'morning': 'Breakfast, Chidambaram Nataraja Temple darshan', 'sightseeing': '108 Natya Karanas Gopuram, Ponnambalam Golden Roof', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-044',
        'name': 'South India Western & Eastern Ghats Hill Stations Panorama',
        'destination': 'Ooty / Coonoor / Kodaikanal / Yercaud',
        'category': 'hill_station',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('8500.00'),
        'price_with_food': decimal.Decimal('11500.00'),
        'price_without_food': decimal.Decimal('8500.00'),
        'is_devotional': False,
        'description': 'A grand panorama of South India’s premier hill stations across the Western and Eastern Ghats: Nilgiri mountains of Ooty and Coonoor, Palani Hills of Kodaikanal, and Shevaroy hills of Yercaud.',
        'itinerary': [
            {'day': 1, 'title': 'Coimbatore to Ooty & Coonoor', 'route': 'Coimbatore to Ooty (90 km)', 'activities': 'Pickup from Coimbatore. Climb Nilgiri hills. Visit Sim’s Park Coonoor, Dolphin’s Nose, Doddabetta Peak, and Botanical Garden in Ooty. Resort campfire, dinner.', 'morning': 'Pickup from Coimbatore, ghats climb', 'sightseeing': 'Sim’s Park, Dolphin’s Nose, Doddabetta Peak', 'evening': 'Campfire, Nilgiri dinner', 'night_stay': 'Ooty Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Ooty to Kodaikanal Transfer', 'route': 'Ooty to Kodaikanal (260 km / 6.5 hrs)', 'activities': 'Scenic highway through tea and spice landscapes. Ascend to Kodaikanal. Check-in, evening walk around Kodai Lake. Dinner.', 'morning': 'Breakfast, mountain transit drive', 'sightseeing': 'Silver Cascade Falls, Kodai Lake', 'evening': 'Kodai Lake stroll, dinner', 'night_stay': 'Kodaikanal Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Kodaikanal Highlights - Pillar Rocks & Boating', 'route': 'Kodaikanal Circuit', 'activities': 'Visit Pillar Rocks, Green Valley View, Coaker’s Walk, Pine Forest, and pedal boating in Kodai Lake. Homemade chocolate shopping.', 'morning': 'Breakfast, Pillar Rocks and Coaker’s Walk', 'sightseeing': 'Pillar Rocks, Green Valley View, Pine Forest, Kodai Lake', 'evening': 'Boating, dinner', 'night_stay': 'Kodaikanal Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Kodaikanal to Madurai / Coimbatore Departure', 'route': 'Kodaikanal to Madurai (120 km)', 'activities': 'Breakfast, check out. Descend Palani hills. Transfer to Madurai / Coimbatore Airport or Railway Station for departure.', 'morning': 'Breakfast, scenic descent', 'sightseeing': 'Ghat viewpoints, waterfall stops', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-045',
        'name': 'Madurai, Rameswaram & Kanyakumari Southern Splendor Tour',
        'destination': 'Madurai / Rameswaram / Kanyakumari',
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5900.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5900.00'),
        'is_devotional': True,
        'description': 'The classic golden triangle of Tamil Nadu: Meenakshi Temple Madurai, sacred island Rameswaram with Pamban Bridge and Dhanushkodi, and Vivekananda Rock at Kanyakumari.',
        'itinerary': [
            {'day': 1, 'title': 'Madurai to Rameswaram Island', 'route': 'Madurai to Rameswaram (170 km)', 'activities': 'Morning visit to Meenakshi Amman Temple in Madurai. Drive across Pamban Sea Bridge to Rameswaram. Holy bath in 22 theerthams, Spatika Lingam darshan.', 'morning': 'Meenakshi Temple darshan, drive to Rameswaram', 'sightseeing': 'Meenakshi Amman Temple, Pamban Bridge, Ramanathaswamy Temple', 'evening': 'Dhanushkodi visit, hotel dinner', 'night_stay': 'Rameswaram Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Rameswaram to Kanyakumari Lands End', 'route': 'Rameswaram to Kanyakumari (310 km / 5.5 hrs)', 'activities': 'Drive to Kanyakumari. Ferry to Vivekananda Rock Memorial and Thiruvalluvar Statue. Visit Kumari Amman Temple. Sunset at Triveni Sangam.', 'morning': 'Breakfast, drive to Kanyakumari', 'sightseeing': 'Vivekananda Rock Memorial, Thiruvalluvar Statue, Sunset Point', 'evening': 'Sunset view, dinner', 'night_stay': 'Kanyakumari Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Kanyakumari Sunrise & Trivandrum Departure', 'route': 'Kanyakumari to Trivandrum (95 km)', 'activities': 'Ocean sunrise view. Visit Padmanabhaswamy Temple Trivandrum and Kovalam Beach. Drop at Trivandrum Airport / Railway Station.', 'morning': 'Sunrise view, breakfast, drive to Trivandrum', 'sightseeing': 'Padmanabhaswamy Temple, Kovalam Beach', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-046',
        'name': 'Hyderabad City of Pearls, Charminar & Golconda Tour',
        'destination': 'Hyderabad / Secunderabad',
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5800.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5800.00'),
        'is_devotional': False,
        'description': 'Explore Hyderabad: the majestic Golconda Fort with acoustic wonders, Charminar, Salar Jung Museum, Hussain Sagar Lake Buddha statue, and authentic Hyderabadi Dum Biryani.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Hyderabad - Golconda Fort & Qutb Shahi Tombs', 'route': 'Hyderabad City Tour', 'activities': 'Pickup from Hyderabad airport / station. Hotel check-in. Visit the massive Golconda Fort with Fateh Darwaza clapping portico, and Qutb Shahi royal tombs. Authentic Hyderabadi biryani dinner.', 'morning': 'Pickup, check-in, lunch', 'sightseeing': 'Golconda Fort, Sound & Light Show, Qutb Shahi Tombs', 'evening': 'Hyderabadi Dum Biryani dinner', 'night_stay': 'Hyderabad Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Charminar, Laad Bazaar, Salar Jung & Hussain Sagar', 'route': 'Old City & Tank Bund', 'activities': 'Visit iconic 16th-century Charminar, Mecca Masjid, and Laad Bazaar pearl and lacquer bangle markets. Explore world-famous Salar Jung Museum with the Musical Clock. Evening boat ride in Hussain Sagar Lake to the monolithic Buddha statue.', 'morning': 'Breakfast, Charminar and Salar Jung Museum', 'sightseeing': 'Charminar, Mecca Masjid, Salar Jung Museum, Hussain Sagar Buddha Statue', 'evening': 'Lumbini Park musical fountain, dinner', 'night_stay': 'Hyderabad Hotel', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Ramoji Film City / Birla Mandir & Departure', 'route': 'Hyderabad Local & Departure', 'activities': 'Morning visit to white marble Birla Mandir atop Naubat Pahad overlooking the city. Souvenir shopping for pearls and Karachi bakery fruit biscuits. Transfer to Hyderabad Airport / Secunderabad Station.', 'morning': 'Breakfast, Birla Mandir and shopping', 'sightseeing': 'Birla Mandir, Naubat Pahad, Pearl Market', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-047',
        'name': 'Munnar Tea Hills Honeymoon & Romantic Hill Retreat',
        'destination': 'Cochin / Munnar',
        'category': 'holiday',
        'duration_days': 4,
        'duration_nights': 3,
        'base_price': decimal.Decimal('7999.00'),
        'price_with_food': decimal.Decimal('10999.00'),
        'price_without_food': decimal.Decimal('7999.00'),
        'is_devotional': False,
        'description': 'A romantic luxury hill getaway in Munnar. Includes flower bed decoration, private candlelight dinner, tea garden walks, Cheeyappara waterfalls, Mattupetty boating, and mountain mist views.',
        'itinerary': [
            {'day': 1, 'title': 'Cochin to Munnar Honeymoon Welcome', 'route': 'Cochin to Munnar (130 km / 4 hrs)', 'activities': 'Pickup from Cochin. Scenic mountain drive past Cheeyappara and Valara waterfalls. Check-in to luxury resort in Munnar. Welcome drink, flower-decorated room, candlelight dinner.', 'morning': 'Pickup from Cochin, waterfalls drive', 'sightseeing': 'Cheeyappara Falls, Valara Falls, Karadippara View', 'evening': 'Candlelight dinner with cake, overnight stay', 'night_stay': 'Munnar Luxury Resort', 'meals': 'Dinner'},
            {'day': 2, 'title': 'Munnar Sightseeing & Boating', 'route': 'Munnar Local Circuit', 'activities': 'Visit Mattupetty Dam, Kundala Lake, Eco Point, and Top Station. Guided walk through lush emerald tea gardens. Visit Tata Tea Museum.', 'morning': 'Breakfast, Mattupetty boating and Eco Point', 'sightseeing': 'Mattupetty Dam, Kundala Lake, Echo Point, Tea Museum', 'evening': 'Resort campfire, dinner', 'night_stay': 'Munnar Luxury Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 3, 'title': 'Eravikulam National Park & Tea Sanctuary', 'route': 'Munnar Rajamalai Circuit', 'activities': 'Morning visit to Eravikulam National Park (habitat of the endangered Nilgiri Tahr and Neelakurinji flower). Afternoon leisure and spa massage at resort.', 'morning': 'Breakfast, Eravikulam National Park safari', 'sightseeing': 'Eravikulam National Park, Anamudi Peak view, Blossom Park', 'evening': 'Couples Ayurvedic spa massage, dinner', 'night_stay': 'Munnar Luxury Resort', 'meals': 'Breakfast, Lunch, Dinner'},
            {'day': 4, 'title': 'Munnar to Cochin Departure', 'route': 'Munnar to Cochin (130 km / 4 hrs)', 'activities': 'Breakfast, check out. Scenic drive down the ghats with shopping for fresh cardamom and spices. Drop at Cochin Airport / Railway Station.', 'morning': 'Breakfast, checkout and spice shopping', 'sightseeing': 'Spice garden visit, scenic viewpoints', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-048',
        'name': 'Thekkady Periyar Wildlife & Spice Valley Retreat',
        'destination': 'Cochin / Thekkady (Kumily)',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3899.00'),
        'price_with_food': decimal.Decimal('5299.00'),
        'price_without_food': decimal.Decimal('3899.00'),
        'is_devotional': False,
        'description': 'Explore Thekkady, the spice capital of Kerala. Features Periyar Lake boat safari inside Periyar Tiger Reserve, guided spice plantation tour, and traditional Kathakali & Kalaripayattu martial arts shows.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Thekkady & Periyar Lake Boating', 'route': 'Cochin / Madurai to Thekkady (140 km)', 'activities': 'Pickup and transfer to Thekkady. Check-in to resort, lunch. Boat safari on Periyar Lake spotting herds of wild elephants, sambar deer, and aquatic birds. Evening attend live Kathakali dance drama and Kalaripayattu martial arts performances.', 'morning': 'Pickup, scenic drive, hotel check-in', 'sightseeing': 'Periyar Tiger Reserve Lake, Kathakali Cultural Centre', 'evening': 'Kalaripayattu show, Kerala dinner', 'night_stay': 'Thekkady Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Spice Plantation Walk & Departure', 'route': 'Thekkady to Cochin / Madurai (140 km)', 'activities': 'Morning guided walking tour through organic spice plantations learning about black pepper, cardamom, vanilla, and cinnamon. Spice shopping. Return transfer for departure.', 'morning': 'Breakfast, guided spice plantation tour', 'sightseeing': 'Spice Plantations, Kumily Elephant Ride Centre', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-049',
        'name': 'Vagamon Pine Forest, Kurisumala & Green Meadows Tour',
        'destination': 'Cochin / Kottayam / Vagamon',
        'category': 'hill_station',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3799.00'),
        'price_with_food': decimal.Decimal('5199.00'),
        'price_without_food': decimal.Decimal('3799.00'),
        'is_devotional': False,
        'description': 'Discover the untouched highland paradise of Vagamon: towering British Pine Forests, rolling velvet Green Meadows, Kurisumala Ashram dairy farm, and Vagamon Lake boating.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Vagamon - Pine Forest & Green Meadows', 'route': 'Cochin to Vagamon (105 km / 3 hrs)', 'activities': 'Pickup from Cochin. Ascend the misty Idukki high ranges. Check-in to resort, lunch. Walk through the fragrant Vagamon Pine Forest planted during the British era. Stroll across the rolling velvet Green Meadows (Motta Kunnu). Evening boating in Vagamon Lake. Campfire, dinner.', 'morning': 'Pickup from Cochin, scenic ghats drive', 'sightseeing': 'Vagamon Pine Forest, Green Meadows, Vagamon Lake', 'evening': 'Campfire, Kerala dinner', 'night_stay': 'Vagamon Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Kurisumala, Thangal Para & Departure', 'route': 'Vagamon to Cochin (105 km / 3 hrs)', 'activities': 'Morning visit to Kurisumala Ashram dairy farm and Thangal Para spherical rock formation with panoramic valley views. Lunch. Return drive to Cochin for departure.', 'morning': 'Breakfast, Kurisumala and Thangal Para', 'sightseeing': 'Kurisumala Ashram, Thangal Para, Murugan Hill view', 'evening': 'Drop at Cochin Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-050',
        'name': 'Alappuzha (Alleppey) Backwaters & Houseboat Holiday',
        'destination': 'Cochin / Alleppey',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('6999.00'),
        'price_with_food': decimal.Decimal('9499.00'),
        'price_without_food': decimal.Decimal('6999.00'),
        'is_devotional': False,
        'description': 'Experience the Venice of the East on a private deluxe AC Houseboat cruising the palm-fringed canals, Kuttanad paddy fields, and Vembanad Lake in Alleppey.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Alleppey & Houseboat Cruise', 'route': 'Cochin to Alleppey (80 km)', 'activities': 'Pickup from Cochin. Board private deluxe AC Houseboat at 12:30 PM. Cruise along Vembanad Lake and Kuttanad canals. Authentic Kerala lunch onboard. Evening canoe ride into village waterways. Candlelight dinner onboard.', 'morning': 'Pickup from Cochin, arrive Alleppey jetty', 'sightseeing': 'Vembanad Lake, Kuttanad Canals, Village Life', 'evening': 'Canoe ride, Karimeen fish fry dinner onboard', 'night_stay': 'Private Deluxe Houseboat', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Morning Backwater Cruise & Alleppey Beach', 'route': 'Alleppey to Cochin (80 km)', 'activities': 'Morning cruise with breakfast on deck. Check-out at 09:00 AM. Visit historic Alleppey Beach and 150-year-old pier. Transfer to Cochin for departure.', 'morning': 'Houseboat breakfast, checkout', 'sightseeing': 'Alleppey Beach, Old Sea Bridge Pier, Lighthouse', 'evening': 'Drop at Cochin Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast'}
        ]
    },
    {
        'code': 'SGT-CTT-051',
        'name': 'Fort Kochi & Mattancherry Heritage Gateway Tour',
        'destination': 'Cochin (Fort Kochi, Mattancherry, Marine Drive)',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3200.00'),
        'price_with_food': decimal.Decimal('4500.00'),
        'price_without_food': decimal.Decimal('3200.00'),
        'is_devotional': False,
        'description': 'Explore the Queen of the Arabian Sea: cantilevered Chinese Fishing Nets, St. Francis Church (oldest European church in India), Mattancherry Dutch Palace, Jewish Synagogue, and Jew Town antique markets.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Cochin - Fort Kochi Colonial Walk', 'route': 'Cochin Local', 'activities': 'Pickup from Cochin. Hotel check-in. Walk along Fort Kochi beach to view iconic Chinese Fishing Nets. Visit St. Francis Church and Santa Cruz Cathedral Basilica. Evening stroll through art cafes. Seafood dinner.', 'morning': 'Pickup, hotel check-in, lunch', 'sightseeing': 'Chinese Fishing Nets, St. Francis Church, Santa Cruz Basilica', 'evening': 'Sunset view at beach, dinner', 'night_stay': 'Fort Kochi Heritage Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Mattancherry Jewish Quarter & Marine Drive', 'route': 'Cochin Local & Departure', 'activities': 'Visit Mattancherry Dutch Palace with Ramayana murals, and the 1568 Paradesi Jewish Synagogue in Jew Town with Belgian crystal chandeliers. Antique shopping. Marine Drive boat cruise. Departure transfer.', 'morning': 'Breakfast, Mattancherry Dutch Palace and Jew Town', 'sightseeing': 'Dutch Palace, Paradesi Synagogue, Jew Town Antiques, Marine Drive', 'evening': 'Departure transfer', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    },
    {
        'code': 'SGT-CTT-052',
        'name': 'Guruvayur Sri Krishna Temple & Thrissur Cultural Tour',
        'destination': 'Cochin / Guruvayur / Thrissur',
        'category': 'devotional',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3400.00'),
        'price_with_food': decimal.Decimal('4600.00'),
        'price_without_food': decimal.Decimal('3400.00'),
        'is_devotional': True,
        'description': 'Pilgrimage to Bhuloka Vaikuntam at Guruvayur Sri Krishna Temple, along with Punnathur Kotta elephant sanctuary housing over 50 temple elephants, and Thrissur Vadakkunnathan Temple.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Cochin to Guruvayur Temple Darshan', 'route': 'Cochin to Guruvayur (90 km / 2.5 hrs)', 'activities': 'Pickup from Cochin. Drive to holy town Guruvayur. Check-in to hotel. Special darshan of Lord Guruvayurappan (infant Krishna in four-armed posture). Attend evening Seeveli elephant procession with Panchavadyam drumming.', 'morning': 'Pickup, drive to Guruvayur, hotel check-in', 'sightseeing': 'Guruvayur Sri Krishna Temple, Deepastambham, Temple Tank', 'evening': 'Seeveli elephant procession, satvik dinner', 'night_stay': 'Guruvayur Hotel', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Punnathur Kotta Elephant Camp & Thrissur', 'route': 'Guruvayur to Thrissur to Cochin (100 km)', 'activities': 'Visit Punnathur Kotta (Anakkotta) royal palace elephant sanctuary housing 50+ majestic tuskers. Drive to Thrissur. Darshan at ancient Vadakkunnathan Temple (Shiva). Return transfer to Cochin for departure.', 'morning': 'Breakfast, Punnathur Kotta elephant sanctuary', 'sightseeing': 'Punnathur Kotta Elephant Camp, Vadakkunnathan Temple', 'evening': 'Departure transfer at Cochin', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ],
        'darshan_slots': [
            {'temple_name': 'Guruvayur Sri Krishna Temple (Bhuloka Vaikuntam)', 'deity': 'Lord Guruvayurappan (Sri Krishna)', 'darshan_type': 'special_entry_300', 'slot_time': '05:30 PM - 07:30 PM', 'location': 'Nalambalam Sanctum', 'dress_code': 'Strict Kerala Mundu/Dhoti without shirt or vest for Men, Saree/Set-Mundu for Women', 'prasad': 'Palpayasam & Neypayasam Prasadam', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-053',
        'name': 'Trivandrum & Kovalam Coastal Temple Tour',
        'destination': 'Trivandrum / Kovalam',
        'category': 'holiday',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3600.00'),
        'price_with_food': decimal.Decimal('4900.00'),
        'price_without_food': decimal.Decimal('3600.00'),
        'is_devotional': True,
        'description': 'Experience Kerala’s capital: the ultra-sacred Sree Padmanabhaswamy Temple, crescent beaches of Kovalam, Vizhinjam lighthouse, Napier Museum, and Kuthiramalika Palace.',
        'itinerary': [
            {'day': 1, 'title': 'Arrival Trivandrum & Sree Padmanabhaswamy Darshan', 'route': 'Trivandrum City & Kovalam (25 km)', 'activities': 'Pickup from Trivandrum. Check-in. Darshan at Sree Padmanabhaswamy Temple (Lord Vishnu in Ananthasayanam posture viewed through 3 doors). Visit Kuthiramalika (Mansion of Horses) Palace. Drive to Kovalam beach resort. Sunset at Lighthouse Beach.', 'morning': 'Pickup, check-in, Padmanabhaswamy darshan', 'sightseeing': 'Padmanabhaswamy Temple, Kuthiramalika Palace, Kovalam Beach', 'evening': 'Lighthouse Beach sunset, seaside dinner', 'night_stay': 'Kovalam Beach Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Kovalam Beaches & Trivandrum Departure', 'route': 'Kovalam to Trivandrum (18 km)', 'activities': 'Morning visit to Hawah Beach and Samudra Beach. Climb Vizhinjam Lighthouse for 360-degree ocean panoramas. Visit Napier Museum and Art Gallery in Trivandrum. Departure transfer.', 'morning': 'Breakfast, Vizhinjam Lighthouse and Napier Museum', 'sightseeing': 'Vizhinjam Lighthouse, Hawah Beach, Napier Museum, Zoo', 'evening': 'Drop at Trivandrum Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ],
        'darshan_slots': [
            {'temple_name': 'Thiruvananthapuram Sree Padmanabhaswamy Temple', 'deity': 'Lord Anantha Padmanabha', 'darshan_type': 'vip_break', 'slot_time': '09:00 AM - 11:00 AM', 'location': 'Ottakkal Mandapam (3-Doors View)', 'dress_code': 'Strict Kerala Dhoti / Mundu without shirt for Men, Saree for Women', 'prasad': 'Holy Sandalwood & Payasam Prasadam', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-054',
        'name': 'Lakkidi & Vythiri High Range Rainforest Retreat',
        'destination': 'Calicut / Lakkidi / Vythiri',
        'category': 'hill_station',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3899.00'),
        'price_with_food': decimal.Decimal('5299.00'),
        'price_without_food': decimal.Decimal('3899.00'),
        'is_devotional': False,
        'description': 'Gateway to Wayanad high ranges. Experience the highest rainfall region of Lakkidi, the mystical Chain Tree legend, Pookode natural lake boating, and rainforest stream walks in Vythiri.',
        'itinerary': [
            {'day': 1, 'title': 'Calicut to Lakkidi Rainforest Ascent', 'route': 'Calicut to Lakkidi (65 km / 2 hrs)', 'activities': 'Pickup from Calicut. Climb the 9 hairpin curves of Thamarassery Churam. Arrive at Lakkidi Viewpoint overlooking deep gorges. Check-in to eco-resort in Vythiri. Visit Pookode Lake for pedal boating and freshwater aquarium. Visit the legendary Chain Tree. Campfire, dinner.', 'morning': 'Pickup from Calicut, scenic ghats climb', 'sightseeing': 'Thamarassery Churam, Lakkidi Viewpoint, Pookode Lake, Chain Tree', 'evening': 'Rainforest nature walk, campfire, dinner', 'night_stay': 'Vythiri Rainforest Resort', 'meals': 'Lunch, Dinner'},
            {'day': 2, 'title': 'Chembra Peak Base & Calicut Departure', 'route': 'Vythiri to Calicut (65 km)', 'activities': 'Morning guided trek to base of Chembra Peak and tea gardens. Lunch at resort. Descend to Calicut for evening departure transfer.', 'morning': 'Breakfast, Chembra foothills trek and tea garden walk', 'sightseeing': 'Chembra Peak base, Vythiri stream, Tea Factory', 'evening': 'Drop at Calicut Airport / Railway Station', 'night_stay': 'Departure', 'meals': 'Breakfast, Lunch'}
        ]
    }
]
