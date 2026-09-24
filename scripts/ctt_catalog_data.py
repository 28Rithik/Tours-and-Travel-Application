# ctt_catalog_data.py
# Comprehensive Package Definitions from chennaitourstravels.com
# Rebranded 100% for Siva Gayathri Tours & Travels

import decimal

OUTSTATION_PACKAGES = [
    {
        'code': 'SGT-CTT-001',
        'name': 'Chennai to Tirupati Balaji Special Entry Darshan Package',
        'destination': 'Chennai / Tirupati / Tirumala',
        'category': 'devotional',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('999.00'),
        'price_with_food': decimal.Decimal('1099.00'),
        'price_without_food': decimal.Decimal('799.00'),
        'is_devotional': True,
        'description': 'Daily confirmed Tirupati Balaji Darshan tour package from Chennai with confirmed ₹300 Special Entry Darshan, door pickup/drop, South Indian breakfast, Andhra meals lunch, and laddu prasadam.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Tirupati Balaji Darshan & Return',
                'route': 'Chennai to Tirupati to Tirumala and Return (320 km)',
                'activities': '04:30 AM pickup from Chennai residence. Proceed to Tirupati with breakfast enroute. Ascend Tirumala hills for confirmed ₹300 Special Entry Darshan of Lord Venkateswara Balaji. Receive sacred laddu prasadam. Pure vegetarian Andhra meals lunch. Visit Sri Padmavathi Ammavari Temple at Tiruchanur and ISKCON Temple. Evening comfortable return drive to Chennai arriving by 09:30 PM.',
                'morning': '04:30 AM pickup, breakfast enroute, Tirumala Ghat drive',
                'sightseeing': 'Tirumala Venkateswara Swamy Temple, Tiruchanur Padmavathi Temple, ISKCON Temple',
                'evening': 'Tiruchanur darshan, return drive to Chennai, residence drop',
                'night_stay': 'Same Day Return',
                'meals': 'Breakfast, Andhra Meals Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Tirumala Sri Venkateswara Swamy Temple', 'deity': 'Lord Venkateswara (Balaji)', 'darshan_type': 'special_entry_300', 'slot_time': '10:30 AM - 12:30 PM', 'location': 'Vaikuntam Queue Complex 1', 'dress_code': 'Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women', 'prasad': 'TTD Sacred Laddu Prasadam', 'senior_citizen': True},
            {'temple_name': 'Sri Padmavathi Ammavari Temple (Tiruchanur)', 'deity': 'Goddess Padmavathi', 'darshan_type': 'special_entry_300', 'slot_time': '04:00 PM - 05:30 PM', 'location': 'Tiruchanur Temple Complex', 'dress_code': 'Traditional Attire', 'prasad': 'Goddess Kumkum & Laddu Prasadam', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-002',
        'name': 'Chennai to Mahabalipuram UNESCO Heritage & Beach Day Tour',
        'destination': 'Chennai / Mahabalipuram',
        'category': 'local_tour',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('399.00'),
        'price_with_food': decimal.Decimal('799.00'),
        'price_without_food': decimal.Decimal('399.00'),
        'is_devotional': False,
        'description': 'Guided 1-day road trip from Chennai along the scenic East Coast Road. Discover Shore Temple, Pancha Rathas, Arjuna Penance, Krishna Butter Ball, and Tiger Cave.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Mahabalipuram Coastal Heritage Tour',
                'route': 'Chennai to Mahabalipuram via ECR (120 km round trip)',
                'activities': '08:00 AM pickup from residence. Drive along East Coast Road. Visit Tiger Cave in Saluvankuppam. Explore Shore Temple, Pancha Rathas monolithic shrines, Arjuna Penance open-air bas relief, Krishna Butter Ball, and Lighthouse. Lunch at beachside restaurant. Evening beach walk and stone sculpting workshop visit. Return to Chennai by 07:00 PM.',
                'morning': '08:00 AM pickup, scenic drive via ECR, Tiger Cave',
                'sightseeing': 'Shore Temple, Pancha Rathas, Arjuna Penance, Krishna Butter Ball, Lighthouse, Tiger Cave',
                'evening': 'Beach walk, stone carvings shopping, return drive to Chennai',
                'night_stay': 'Same Day Return',
                'meals': 'Buffet Lunch'
            }
        ]
    },
    {
        'code': 'SGT-CTT-003',
        'name': 'Chennai to Kanchipuram Ancient Silk & Temple City Day Tour',
        'destination': 'Chennai / Kanchipuram',
        'category': 'devotional',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('350.00'),
        'price_with_food': decimal.Decimal('650.00'),
        'price_without_food': decimal.Decimal('350.00'),
        'is_devotional': True,
        'description': 'Explore Kanchipuram, the City of Thousand Temples and silk capital. Covers Ekambareswarar (Earth Stalam), Kamakshi Amman Shakti Peetham, Varadharaja Perumal, and master handloom silk weaving units.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Kanchipuram Temple Pilgrimage & Handloom Weaving',
                'route': 'Chennai to Kanchipuram (150 km round trip)',
                'activities': '07:30 AM departure from Chennai. Darshan at Ekambareswarar Temple (Pancha Bhoota Earth Stalam), Kamakshi Amman Temple, and Varadharaja Perumal Temple with sacred gold/silver lizards. South Indian vegetarian lunch. Visit traditional silk saree handloom weaving society. Return to Chennai by 08:00 PM.',
                'morning': '07:30 AM pickup, Ekambareswarar and Kailasanathar temple darshan',
                'sightseeing': 'Ekambareswarar Temple, Kamakshi Amman, Varadharaja Perumal, Silk Weaving Centers',
                'evening': 'Silk saree shopping, return drive to Chennai',
                'night_stay': 'Same Day Return',
                'meals': 'Vegetarian Meals'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Kanchipuram Kamakshi Amman Temple', 'deity': 'Goddess Kamakshi', 'darshan_type': 'special_entry_300', 'slot_time': '10:00 AM - 11:30 AM', 'location': 'Inner Sannidhi', 'dress_code': 'Traditional Attire', 'prasad': 'Kumkum & Sakkarai Pongal', 'senior_citizen': True},
            {'temple_name': 'Ekambareswarar Temple (Earth Stalam)', 'deity': 'Lord Shiva (Ekambareswarar)', 'darshan_type': 'general', 'slot_time': '11:30 AM - 12:30 PM', 'location': 'Prithvi Lingam Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-004',
        'name': 'Chennai to Pondicherry French Riviera & Auroville Day Tour',
        'destination': 'Chennai / Pondicherry',
        'category': 'holiday',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('699.00'),
        'price_with_food': decimal.Decimal('1199.00'),
        'price_without_food': decimal.Decimal('699.00'),
        'is_devotional': False,
        'description': 'A coastal day tour exploring Auroville Matrimandir viewpoint, Sri Aurobindo Ashram, French White Town, Promenade Beach, and colonial cafes.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Pondicherry Day Excursion',
                'route': 'Chennai to Pondicherry via ECR (320 km round trip)',
                'activities': '06:30 AM departure from Chennai along East Coast Road. Visit Auroville Visitor Centre and Matrimandir viewpoint. Proceed to Pondicherry White Town. Visit Sri Aurobindo Ashram, Manakula Vinayagar Temple, French War Memorial, and Goubert Promenade Beach. Lunch at a French colonial restaurant. Evening return to Chennai by 09:30 PM.',
                'morning': '06:30 AM pickup, breakfast enroute, Auroville Matrimandir',
                'sightseeing': 'Auroville Matrimandir, Sri Aurobindo Ashram, French White Town, Manakula Vinayagar Temple, Promenade Beach',
                'evening': 'Promenade beach stroll, return drive to Chennai',
                'night_stay': 'Same Day Return',
                'meals': 'Lunch at Heritage Cafe'
            }
        ]
    },
    {
        'code': 'SGT-CTT-005',
        'name': 'Chennai to Vellore Sripuram Golden Temple & Fort Day Tour',
        'destination': 'Chennai / Vellore',
        'category': 'devotional',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('390.00'),
        'price_with_food': decimal.Decimal('750.00'),
        'price_without_food': decimal.Decimal('390.00'),
        'is_devotional': True,
        'description': 'Spiritual day pilgrimage to Sripuram Golden Temple (1,500 kg pure gold) and the 16th-century granite moated Vellore Fort and Jalakandeswarar Temple.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Vellore Golden Temple & Jalakandeswarar',
                'route': 'Chennai to Vellore (280 km round trip)',
                'activities': '07:00 AM departure from Chennai. Darshan at Sripuram Golden Temple of Goddess Sri Lakshmi Narayani along the spiritual star path. Pure vegetarian lunch. Visit 16th-century Vellore Fort, Jalakandeswarar Temple with stone sculptures, and Fort Museum. Return to Chennai by 08:30 PM.',
                'morning': '07:00 AM pickup, breakfast enroute, Sripuram Golden Temple darshan',
                'sightseeing': 'Sripuram Golden Temple, Vellore Fort, Jalakandeswarar Temple',
                'evening': 'Fort exploration, return journey to Chennai',
                'night_stay': 'Same Day Return',
                'meals': 'Pure Vegetarian Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Sripuram Golden Temple', 'deity': 'Goddess Mahalakshmi Narayani', 'darshan_type': 'special_entry_300', 'slot_time': '10:30 AM - 01:00 PM', 'location': 'Star Path Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Maha Lakshmi Kumkum & Laddu', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-006',
        'name': 'Chennai to Gingee Fort (Chenji) Heritage Day Tour',
        'destination': 'Chennai / Gingee (Chenji)',
        'category': 'holiday',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('499.00'),
        'price_with_food': decimal.Decimal('899.00'),
        'price_without_food': decimal.Decimal('499.00'),
        'is_devotional': False,
        'description': 'Ascend the impregnable Troy of the East citadel in Gingee. Explore Rajagiri Fort, Krishnagiri Fort, Kalyana Mahal palace tower, royal granaries, and Krishnagiri Dam.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Gingee Fort Heritage Expedition',
                'route': 'Chennai to Gingee (310 km round trip)',
                'activities': '06:30 AM pickup from Chennai. Ascend Rajagiri Fort to view royal palace ruins, Kalyana Mahal, elephant stables, granaries, and temple shrines. Lunch at local hotel. Visit Krishnagiri Dam and surrounding lake. Return to Chennai by 08:30 PM.',
                'morning': '06:30 AM pickup, trek up Rajagiri Fort',
                'sightseeing': 'Rajagiri Fort, Krishnagiri Fort, Kalyana Mahal, Krishnagiri Dam',
                'evening': 'Sunset view, drive back to Chennai',
                'night_stay': 'Same Day Return',
                'meals': 'Lunch'
            }
        ]
    },
    {
        'code': 'SGT-CTT-007',
        'name': 'Chennai to Nagapattinam & Velankanni Shrine Day Pilgrimage',
        'destination': 'Chennai / Nagapattinam / Velankanni',
        'category': 'devotional',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('1650.00'),
        'price_with_food': decimal.Decimal('2250.00'),
        'price_without_food': decimal.Decimal('1650.00'),
        'is_devotional': True,
        'description': 'Dedicated pilgrimage to the Basilica of Our Lady of Good Health in Velankanni (Lourdes of the East), Miraculous Spring, Church Museum, and Nagapattinam coastal shrines.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Velankanni Pilgrimage & Return',
                'route': 'Chennai to Velankanni (620 km round trip)',
                'activities': '04:00 AM departure from Chennai by AC vehicle. Arrive at Velankanni Basilica by 10:30 AM. Attend holy mass, offer candles, visit Our Lady Tank miraculous spring, and church museum. Coastal lunch. Visit Velankanni beach and Nagapattinam Soundararaja Perumal Temple. Return drive to Chennai arriving by 11:30 PM.',
                'morning': '04:00 AM departure, arrival Velankanni by 10:30 AM',
                'sightseeing': 'Basilica of Our Lady of Good Health, Miraculous Tank, Museum, Velankanni Beach',
                'evening': 'Return drive to Chennai, arrival by midnight',
                'night_stay': 'Same Day Return',
                'meals': 'Breakfast, Lunch'
            }
        ]
    },
    {
        'code': 'SGT-CTT-008',
        'name': 'Chennai City Local Heritage & Spiritual Temples Day Tour',
        'destination': 'Chennai Local City Tour',
        'category': 'local_tour',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('350.00'),
        'price_with_food': decimal.Decimal('650.00'),
        'price_without_food': decimal.Decimal('350.00'),
        'is_devotional': True,
        'description': 'Guided city heritage tour of Chennai visiting Kapaleeshwarar Temple Mylapore, Parthasarathy Temple Triplicane, Santhome Basilica, Fort St. George, and Marina Beach.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai Heritage, Temples & Marina Beach',
                'route': 'Chennai City Local (80 km circuit)',
                'activities': '08:30 AM pickup from residence. Darshan at Kapaleeshwarar Temple Mylapore and Parthasarathy Temple Triplicane. Visit Santhome Cathedral Basilica, Fort St. George, Government Museum, and Marina Beach for evening sunset walk. Return drop at residence by 07:30 PM.',
                'morning': '08:30 AM pickup, Kapaleeshwarar and Parthasarathy temple darshan',
                'sightseeing': 'Kapaleeshwarar Temple, Parthasarathy Temple, Santhome Basilica, Fort St. George, Marina Beach',
                'evening': 'Marina beach walk, drop at residence by 07:30 PM',
                'night_stay': 'Same Day Tour',
                'meals': 'Traditional South Indian Lunch'
            }
        ]
    }
]
