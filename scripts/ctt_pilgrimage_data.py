# ctt_pilgrimage_data.py
# 18 Sacred Pilgrimage Packages from chennaitourstravels.com
# Rebranded 100% for Siva Gayathri Tours & Travels

import decimal

PILGRIMAGE_PACKAGES = [
    {
        'code': 'SGT-CTT-009',
        'name': 'Lord Murugan Aarupadai Veedu 6 Sacred Abodes Pilgrimage Tour',
        'destination': 'Thiruttani / Swamimalai / Palani / Thiruparankundram / Pazhamudircholai / Thiruchendur',
        'category': 'pilgrimage',
        'duration_days': 6,
        'duration_nights': 5,
        'base_price': decimal.Decimal('11500.00'),
        'price_with_food': decimal.Decimal('15500.00'),
        'price_without_food': decimal.Decimal('11500.00'),
        'is_devotional': True,
        'description': 'The complete 6 Sacred Abodes of Lord Murugan (Aarupadaiveedu) pilgrimage across Tamil Nadu. Experience Thiruttani, Swamimalai, Palani, Thiruparankundram, Pazhamudircholai, and the coastal shrine of Thiruchendur.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Chennai to Thiruttani Murugan Temple (5th Abode)',
                'route': 'Chennai to Thiruttani to Kumbakonam (310 km)',
                'activities': 'Morning departure from Chennai to Thiruttani hill temple (5th Abode) where Lord Muruga married Valli. Climb the 365 steps representing days of the year. Special darshan. Pure veg lunch. Drive to Swamimalai near Kumbakonam for overnight stay.',
                'morning': '06:00 AM pickup, Thiruttani hill temple darshan',
                'sightseeing': 'Thiruttani Subramanya Swamy Hill Temple, Saravana Poigai',
                'evening': 'Drive to Swamimalai, hotel check-in, dinner',
                'night_stay': 'Swamimalai / Kumbakonam Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Swamimalai Murugan Temple (4th Abode) to Madurai',
                'route': 'Swamimalai to Madurai (220 km)',
                'activities': 'Morning darshan at Swamimalai (4th Abode), where Lord Muruga preached the Pranava Mantra Om to His father Lord Shiva. Drive to Madurai. Check-in at hotel. Evening darshan at Thiruparankundram (1st Abode), the sacred rock-cut cave temple where Muruga wed Deivanai.',
                'morning': 'Swamimalai Swaminatha Swamy temple darshan',
                'sightseeing': 'Swamimalai Temple (60 Steps), Thiruparankundram Cave Temple',
                'evening': 'Thiruparankundram evening deeparadhana, dinner',
                'night_stay': 'Madurai Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 3,
                'title': 'Pazhamudircholai (6th Abode) & Palani Transfer',
                'route': 'Madurai to Palani (120 km)',
                'activities': 'Morning visit to Pazhamudircholai (6th Abode) atop the lush Alagar Hills, surrounded by mountain streams and Noopura Gangai sacred spring. Visit Kallazhagar Temple. Proceed to Palani (3rd Abode). Evening winch/ropeway ascent to Palani hill temple for Viswaroopa Darshan of Lord Dhandayuthapani.',
                'morning': 'Pazhamudircholai Solaimalai Murugan Temple, Noopura Gangai',
                'sightseeing': 'Pazhamudircholai Murugan Temple, Kallazhagar Temple, Palani Hill',
                'evening': 'Palani Dhandayuthapani evening abhishekam & panchamirtham',
                'night_stay': 'Palani Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 4,
                'title': 'Palani Golden Chariot Darshan to Thiruchendur',
                'route': 'Palani to Thiruchendur (270 km)',
                'activities': 'Early morning Golden Chariot darshan at Palani hill. Drive south towards the Gulf of Mannar coast to Thiruchendur (2nd Abode), where Lord Muruga vanquished Surapadman. Arrive and check-in to seashore hotel.',
                'morning': 'Palani morning pooja, drive to Thiruchendur',
                'sightseeing': 'Palani Hill View, Western Ghats landscape, Tuticorin coast',
                'evening': 'Sunset view on Thiruchendur beach, temple visit',
                'night_stay': 'Thiruchendur Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 5,
                'title': 'Thiruchendur Seashore Temple Darshan (2nd Abode)',
                'route': 'Thiruchendur to Madurai / Trichy (250 km)',
                'activities': 'Holy sea bath in the calm Bay of Bengal and holy dip in Nazhikkinaru sweet-water well on the seashore. Grand Viswaroopa Darshan of Lord Subramanya Swamy and Senthil Andavar. Special archana. Afternoon drive to Trichy / Madurai.',
                'morning': 'Nazhikkinaru holy bath, Thiruchendur grand darshan',
                'sightseeing': 'Thiruchendur Subramanya Swamy Temple, Valli Cave, Nazhikkinaru',
                'evening': 'Travel to Trichy, hotel check-in, dinner',
                'night_stay': 'Trichy Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 6,
                'title': 'Trichy Rockfort / Srirangam & Return to Chennai',
                'route': 'Trichy to Chennai (330 km)',
                'activities': 'Morning visit to Sri Ranganathaswamy Temple Srirangam or Rockfort Ucchi Pillayar Temple. Breakfast. Comfortable return drive to Chennai with divine blessings of Lord Murugan.',
                'morning': 'Srirangam Temple darshan, breakfast',
                'sightseeing': 'Srirangam Temple Raja Gopuram, Rockfort Temple',
                'evening': 'Return drive to Chennai, drop at residence by 08:00 PM',
                'night_stay': 'Departure / Return',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Thiruchendur Subramanya Swamy Temple (2nd Abode)', 'deity': 'Lord Senthil Andavar', 'darshan_type': 'special_entry_300', 'slot_time': '07:30 AM - 09:30 AM', 'location': 'Main Sanctorum', 'dress_code': 'Traditional Dhoti/Kurta for Men, Saree for Women', 'prasad': 'Ilai Vibhuti Prasadam', 'senior_citizen': True},
            {'temple_name': 'Palani Dhandayuthapani Swamy Temple (3rd Abode)', 'deity': 'Lord Dhandayuthapani', 'darshan_type': 'winch_ropeway', 'slot_time': '05:30 PM - 07:30 PM', 'location': 'Hill Top Sanctum via Ropeway', 'dress_code': 'Traditional Attire', 'prasad': 'Authentic Palani Panchamirtham Prasadam', 'senior_citizen': True},
            {'temple_name': 'Swamimalai Swaminatha Swamy Temple (4th Abode)', 'deity': 'Lord Swaminatha Swamy', 'darshan_type': 'special_entry_300', 'slot_time': '08:00 AM - 09:30 AM', 'location': 'Hill Shrine (60 Steps)', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti & Kumkum Prasadam', 'senior_citizen': True},
            {'temple_name': 'Thiruparankundram Murugan Temple (1st Abode)', 'deity': 'Lord Subramanya with Deivanai', 'darshan_type': 'special_entry_300', 'slot_time': '05:00 PM - 06:30 PM', 'location': 'Rock-cut Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam', 'senior_citizen': True},
            {'temple_name': 'Thiruttani Subramanya Swamy Temple (5th Abode)', 'deity': 'Lord Muruga with Valli', 'darshan_type': 'special_entry_300', 'slot_time': '08:30 AM - 10:00 AM', 'location': 'Hill Top Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Panchamirtham Prasadam', 'senior_citizen': True},
            {'temple_name': 'Pazhamudircholai Solaimalai Murugan (6th Abode)', 'deity': 'Lord Muruga with Valli & Deivanai', 'darshan_type': 'general', 'slot_time': '09:00 AM - 10:30 AM', 'location': 'Forest Hill Shrine', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-010',
        'name': 'Thondaimandalam Chennai Suburban Navagraha 9 Planets Pilgrimage Circuit',
        'destination': 'Chennai Suburbs (Somangalam, Kovur, Poonamallee, Porur, Mangadu, Kundrathur, Pozhichalur, Gerugambakkam, Kolapakkam)',
        'category': 'devotional',
        'duration_days': 1,
        'duration_nights': 0,
        'base_price': decimal.Decimal('899.00'),
        'price_with_food': decimal.Decimal('1299.00'),
        'price_without_food': decimal.Decimal('899.00'),
        'is_devotional': True,
        'description': 'The sacred 9 Navagraha temples of Thondaimandalam located at the outskirts of Chennai. Each temple features Lord Shiva representing one of the 9 celestial planets (Grahas) for complete dosha nivruthi.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Thondaimandalam 9 Navagraha Sthalams Circuit',
                'route': 'Chennai Suburban Navagraha Circuit (140 km)',
                'activities': '06:00 AM pickup. Visit 1. Kolapakkam Sri Agatheeswarar (Sun / Suryan), 2. Somangalam Sri Somanadheeswarar (Moon / Chandran), 3. Poonamallee Sri Vaidheeswarar (Mars / Sevvai), 4. Kovur Sri Sundhareswarar (Mercury / Budhan), 5. Porur Sri Ramanadheswarar (Jupiter / Guru). Pure vegetarian lunch. Visit 6. Mangadu Sri Velleeswarar (Venus / Sukran), 7. Pozhichalur Sri Agatheeswarar (Saturn / Sani), 8. Kundrathur Sri Nageswarar (Rahu), and 9. Gerugambakkam Sri Neelakandeswarar (Kethu). Return drop by 08:30 PM.',
                'morning': '06:00 AM pickup, visit Suryan, Chandran, Sevvai, Budhan temples',
                'sightseeing': 'Kolapakkam, Somangalam, Poonamallee, Kovur, Porur, Mangadu, Pozhichalur, Kundrathur, Gerugambakkam',
                'evening': 'Sani, Rahu, and Kethu parihara darshan, return drop',
                'night_stay': 'Same Day Tour',
                'meals': 'Pure Vegetarian Meals'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Kolapakkam Sri Agatheeswarar (Suriyan / Sun)', 'deity': 'Lord Shiva (Suriyan Stalam)', 'darshan_type': 'general', 'slot_time': '07:00 AM - 08:00 AM', 'location': 'Main Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam', 'senior_citizen': True},
            {'temple_name': 'Somangalam Sri Somanadheeswarar (Chandran / Moon)', 'deity': 'Lord Shiva (Chandran Stalam)', 'darshan_type': 'general', 'slot_time': '08:30 AM - 09:30 AM', 'location': 'Main Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam', 'senior_citizen': True},
            {'temple_name': 'Pozhichalur Sri Agatheeswarar (Sani / Saturn)', 'deity': 'Lord Shiva (Saneeswarar Stalam)', 'darshan_type': 'general', 'slot_time': '04:30 PM - 05:30 PM', 'location': 'Main Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Gingelly Oil Lamp Pooja & Vibhuti', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-011',
        'name': 'Nava Thirupathi 9 Sacred Divya Desams Pilgrimage Tour',
        'destination': 'Tirunelveli / Thoothukudi / Alwar Thirunagari / Srivaikuntam',
        'category': 'pilgrimage',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5800.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5800.00'),
        'is_devotional': True,
        'description': 'A sacred Divya Desam pilgrimage to the Nava Thirupathi (9 Temples dedicated to Lord Vishnu) in the Thamirabarani river basin near Tiruchendur. Associated with the 9 planetary deities and Nammalwar mangalasasanam.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival Tirunelveli - Srivaikuntam & Thiru Varagunamangai',
                'route': 'Tirunelveli to Srivaikuntam (35 km)',
                'activities': 'Arrival in Tirunelveli, hotel check-in and breakfast. Visit 1. Srivaikuntam Srivaikuntanathan Perumal (Surya Stalam) with towering gopuram. Visit 2. Thiru Varagunamangai Natham Vijayasana Perumal (Chandran Stalam). Pure satvik Vaishnavite lunch. Visit 3. Thiru Pulinkudi Kasinivendan Perumal (Budhan Stalam). Evening return to hotel.',
                'morning': 'Arrival, check-in, visit Srivaikuntam and Natham',
                'sightseeing': 'Srivaikuntanathan Perumal, Vijayasana Perumal, Kasinivendan Perumal',
                'evening': 'Vaishnavite evening prayer, dinner',
                'night_stay': 'Tirunelveli Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Irattai Thirupathi, Thenthiruperai & Alwar Thirunagari',
                'route': 'Thamirabarani Basin Circuit (60 km)',
                'activities': 'Full day visiting 4. Irattai Thirupathi South - Devapiran (Rahu Stalam), 5. Irattai Thirupathi North - Aravindalochanan (Ketu Stalam), 6. Thenthiruperai Makara Nedunkuzhai Kannan (Sukran Stalam), 7. Thirukkolur Vaithamanidhi Perumal (Sevvai Stalam, birthplace of Madhurakavi Alwar), and 8. Alwar Thirunagari Adinathar Perumal (Guru Stalam, birthplace of Nammalwar with sacred Tamarind tree).',
                'morning': 'Visit Irattai Thirupathi and Thenthiruperai',
                'sightseeing': 'Devapiran, Aravindalochanan, Makara Nedunkuzhai Kannan, Vaithamanidhi Perumal, Alwar Thirunagari',
                'evening': 'Alwar Thirunagari sacred Tamarind tree darshan, dinner',
                'night_stay': 'Tirunelveli Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 3,
                'title': 'Thirukkulanthai & Return Journey',
                'route': 'Perungulam to Tirunelveli (50 km)',
                'activities': 'Morning visit to 9. Thirukkulanthai Sri Srinivasa Perumal / Mayakoothan (Sani Stalam) where the Lord danced to vanquish the demon. Complete pradakshinam and mangalasasanam. Traditional lunch. Afternoon transfer to Tirunelveli / Madurai Railway Station / Airport for departure.',
                'morning': 'Thirukkulanthai Mayakoothan darshan, breakfast',
                'sightseeing': 'Sri Srinivasa Perumal Mayakoothan Temple',
                'evening': 'Departure with divine grace of Nava Thirupathi Perumals',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Srivaikuntanathan Perumal Temple (Surya Stalam)', 'deity': 'Lord Kallapiran', 'darshan_type': 'general', 'slot_time': '09:00 AM - 10:30 AM', 'location': 'Main Garbhagriha', 'dress_code': 'Traditional Dhoti/Saree', 'prasad': 'Thulasi & Theertham', 'senior_citizen': True},
            {'temple_name': 'Alwar Thirunagari Sri Adinathar Temple (Guru Stalam)', 'deity': 'Lord Adinatha & Nammalwar', 'darshan_type': 'general', 'slot_time': '04:00 PM - 05:30 PM', 'location': 'Moolavar Sanctum & Gnana Tamarind Tree', 'dress_code': 'Traditional Attire', 'prasad': 'Laddu & Thulasi', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-012',
        'name': 'Nava Kailasam 9 Sacred Shiva Temples of Thamirabarani Circuit',
        'destination': 'Papanasam / Cheranmahadevi / Kodaganallur / Srivaikuntam / Senthamangalam',
        'category': 'pilgrimage',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5700.00'),
        'price_with_food': decimal.Decimal('7800.00'),
        'price_without_food': decimal.Decimal('5700.00'),
        'is_devotional': True,
        'description': 'A divine Shaivite yatra across the 9 Nava Kailasam shrines along the sacred Thamirabarani River. Established by Sage Agastya’s disciple Sage Romasa, each temple corresponds to one of the 9 Navagrahas with Lord Shiva as the supreme deity.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Papanasam, Cheranmahadevi & Kodaganallur',
                'route': 'Tirunelveli to Papanasam (55 km)',
                'activities': 'Arrival in Tirunelveli. Visit 1. Papanasam Sri Papanasar (Surya Stalam) nestled at Western Ghats foothills with holy Thamirabarani bath, 2. Cheranmahadevi Sri Kailasanathar (Chandran Stalam), and 3. Kodaganallur Sri Kailasanathar (Sevvai / Angaragan Stalam). Overnight stay in Tirunelveli.',
                'morning': 'Arrival, drive to Papanasam for holy river dip and darshan',
                'sightseeing': 'Papanasam Papanasar, Agasthiyar Falls, Cheranmahadevi Kailasanathar, Kodaganallur',
                'evening': 'Kodaganallur evening pooja, hotel check-in, dinner',
                'night_stay': 'Tirunelveli Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Kunnathur, Murappanadu, Srivaikuntam & Thentiruperai',
                'route': 'Thamirabarani Mid-stream Circuit (75 km)',
                'activities': 'Visit 4. Kunnathur Sri Kothaparameswarar (Rahu Stalam), 5. Murappanadu Sri Kailasanathar (Guru Stalam, where river flows northward like Kashi), 6. Srivaikuntam Sri Kailasanathar (Sani Stalam), and 7. Thentiruperai Sri Kailasanathar (Budhan Stalam). Return to hotel.',
                'morning': 'Visit Kunnathur and Murappanadu temples',
                'sightseeing': 'Kunnathur, Murappanadu North-flowing River, Srivaikuntam, Thentiruperai',
                'evening': 'Thentiruperai darshan, dinner',
                'night_stay': 'Tirunelveli Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 3,
                'title': 'Rajapathy, Senthamangalam & Departure',
                'route': 'Tuticorin to Tirunelveli (60 km)',
                'activities': 'Morning visit to 8. Rajapathy Sri Kailasanathar (Kethu Stalam) and 9. Senthamangalam / Punnaikkayal Sri Kailasanathar (Sukran Stalam) near the river estuary. Complete the 9 Kailasam pradakshina. Traditional lunch. Afternoon drop at Tirunelveli Railway Station / Madurai Airport.',
                'morning': 'Visit Rajapathy and Senthamangalam temples',
                'sightseeing': 'Rajapathy Kailasanathar, Senthamangalam Kailasanathar',
                'evening': 'Departure with cosmic blessings of Lord Shiva',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Papanasam Sri Papanasar Temple (Surya Stalam)', 'deity': 'Lord Papanasar & Ulagambigai', 'darshan_type': 'general', 'slot_time': '08:30 AM - 10:00 AM', 'location': 'Main River Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam', 'senior_citizen': True},
            {'temple_name': 'Murappanadu Sri Kailasanathar Temple (Guru Stalam)', 'deity': 'Lord Kailasanathar', 'darshan_type': 'general', 'slot_time': '11:00 AM - 12:30 PM', 'location': 'Uttaravahini River Ghat Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti & Theertham', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-013',
        'name': 'Madurai Meenakshi Sundareswarar Temple & Cultural Heritage Tour',
        'destination': 'Madurai City & Temples',
        'category': 'devotional',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('2800.00'),
        'price_with_food': decimal.Decimal('3800.00'),
        'price_without_food': decimal.Decimal('2800.00'),
        'is_devotional': True,
        'description': 'Explore Madurai, the Athens of the East. Darshan at the grand Meenakshi Sundareswarar Temple with 14 gopurams and Hall of 1000 Pillars, Thirumalai Nayakkar Palace, and Alagar Kovil.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival Madurai & Grand Meenakshi Amman Darshan',
                'route': 'Madurai City Tour',
                'activities': 'Arrival in Madurai, hotel check-in and lunch. Visit Thirumalai Nayakkar Palace known for massive stucco columns and light/sound show. Evening special darshan at Sri Meenakshi Sundareswarar Temple. Marvel at the Ashta Shakti Mandapam, Thousand Pillar Hall, and attend the night palliarai silver palanquin ceremony.',
                'morning': 'Arrival, hotel check-in, lunch',
                'sightseeing': 'Thirumalai Nayakkar Palace, Meenakshi Amman Temple 1000 Pillars Hall, Golden Lotus Tank',
                'evening': 'Meenakshi Amman evening palanquin procession, dinner',
                'night_stay': 'Madurai Hotel',
                'meals': 'Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Alagar Kovil, Pazhamudircholai & Departure',
                'route': 'Madurai to Alagar Hills and Return (45 km)',
                'activities': 'Morning visit to Alagar Kovil (Kallazhagar Temple) nestled in the scenic forest hills, and Pazhamudircholai Murugan Temple. Return to town for shopping of Madurai sungudi sarees and jasmine flowers. Drop at Madurai Junction / Airport.',
                'morning': 'Breakfast, visit Alagar Kovil and Pazhamudircholai',
                'sightseeing': 'Kallazhagar Temple, Pazhamudircholai, Noopura Gangai',
                'evening': 'Sungudi saree shopping, departure transfer',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Madurai Sri Meenakshi Amman Temple', 'deity': 'Goddess Meenakshi & Sundareswarar', 'darshan_type': 'special_entry_300', 'slot_time': '05:30 PM - 07:30 PM', 'location': 'Ashta Shakthi Mandapam Sanctum', 'dress_code': 'Strict Traditional Attire', 'prasad': 'Meenakshi Kumkum & Sakkarai Pongal', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-014',
        'name': 'Rameswaram Ramanathaswamy 22 Wells & Dhanushkodi Island Tour',
        'destination': 'Madurai / Rameswaram / Dhanushkodi',
        'category': 'pilgrimage',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5400.00'),
        'price_with_food': decimal.Decimal('7500.00'),
        'price_without_food': decimal.Decimal('5400.00'),
        'is_devotional': True,
        'description': 'A sacred Char Dham yatra to Rameswaram Island. Cross Pamban Sea Bridge, bathe in Agni Theertham and the 22 sacred temple wells, attend Spatika Linga Darshan, and visit the ghost town of Dhanushkodi & Ram Setu viewpoint.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Madurai to Rameswaram Island via Pamban Bridge',
                'route': 'Madurai to Rameswaram (170 km / 3.5 hrs)',
                'activities': 'Morning pickup from Madurai. Scenic drive past Ramanathapuram. Drive across the iconic Pamban Sea Bridge connecting the mainland to Rameswaram island. Check-in at hotel. Evening holy bath at Agni Theertham sea and participate in temple corridor prayers.',
                'morning': 'Pickup from Madurai, drive across Pamban Sea Bridge',
                'sightseeing': 'Pamban Bridge panoramic ocean view, Agni Theertham Sea',
                'evening': 'Ramanathaswamy Temple third corridor exploration, dinner',
                'night_stay': 'Rameswaram Hotel',
                'meals': 'Lunch, Dinner'
            },
            {
                'day': 2,
                'title': '22 Sacred Wells Holy Bath & Spatika Linga Darshan',
                'route': 'Rameswaram Island Circuit',
                'activities': 'Early morning 05:00 AM holy bath in all 22 sacred temple well theerthams inside Ramanathaswamy Temple, followed by Spatika Linga Darshan and main Jyotirlinga darshan. Breakfast. Afternoon excursion to Dhanushkodi ghost town, Adam Bridge / Ram Setu viewpoint where the Indian Ocean and Bay of Bengal converge, and Dr. APJ Abdul Kalam Memorial.',
                'morning': '05:00 AM holy snanam in 22 theerthams, Spatika Linga darshan',
                'sightseeing': '22 Theerthams, Ramanathaswamy Jyotirlinga, Dhanushkodi Ghost Town, Ram Setu Point, APJ Abdul Kalam Memorial',
                'evening': 'Sunset view at Dhanushkodi beach, dinner',
                'night_stay': 'Rameswaram Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 3,
                'title': 'Rameswaram to Madurai & Departure',
                'route': 'Rameswaram to Madurai (170 km / 3.5 hrs)',
                'activities': 'Morning visit to Gandhamadhana Parvatham for panoramic island view and Rama footprints, and Villundi Theertham. Return drive across Pamban Bridge to Madurai for departure.',
                'morning': 'Breakfast, Gandhamadhana Parvatham and Villundi Theertham',
                'sightseeing': 'Gandhamadhana Parvatham, Villundi Theertham, Pamban Rail Bridge view',
                'evening': 'Drop at Madurai Railway Station / Airport',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Rameswaram Sri Ramanathaswamy Temple (Jyotirlinga)', 'deity': 'Lord Ramanathaswamy (Spatika Lingam)', 'darshan_type': 'special_entry_300', 'slot_time': '05:30 AM - 08:30 AM', 'location': '22 Theerthams & Inner Sanctum', 'dress_code': 'Dhoti for Men, Saree for Women (Dry clothes mandatory after theertham bath)', 'prasad': 'Holy Theertham & Vibhuti', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-015',
        'name': 'Palani Dhandayuthapani Murugan Hill Temple Pilgrimage',
        'destination': 'Coimbatore / Palani / Dindigul',
        'category': 'devotional',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('2900.00'),
        'price_with_food': decimal.Decimal('3900.00'),
        'price_without_food': decimal.Decimal('2900.00'),
        'is_devotional': True,
        'description': 'Ascend the sacred Sivagiri hill in Palani to worship Lord Muruga as an ascetic yogi (Dhandayuthapani). Includes Winch / Ropeway pass, Golden Chariot darshan, and authentic panchamirtham prasadam.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival Palani & Evening Hill Top Darshan',
                'route': 'Coimbatore / Madurai to Palani (100 km)',
                'activities': 'Arrival in Palani, hotel check-in and lunch. Afternoon ropeway / winch car ascent to Sivagiri hill. Darshan of Lord Dhandayuthapani consecrated by Sage Bogar made of Navapashanam. Witness the glorious evening Golden Chariot procession (Thanga Ther). Receive authentic panchamirtham.',
                'morning': 'Arrival, check-in, lunch',
                'sightseeing': 'Palani Hill, Bogar Samadhi, Winch / Ropeway Ride',
                'evening': 'Golden Chariot procession, hill top sunset, dinner',
                'night_stay': 'Palani Hotel',
                'meals': 'Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Thiruaavinankudi Foot Temple & Departure',
                'route': 'Palani to Coimbatore / Madurai (100 km)',
                'activities': 'Morning visit to Thiruaavinankudi Temple at the foot of the hill, one of the 6 Abodes of Murugan. Visit Periyanayaki Amman Temple. Breakfast and departure transfer.',
                'morning': 'Breakfast, Thiruaavinankudi temple darshan',
                'sightseeing': 'Thiruaavinankudi Temple, Periyanayaki Amman Temple, Shanmuga River Ghats',
                'evening': 'Departure transfer',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Palani Dhandayuthapani Swamy Temple', 'deity': 'Lord Dhandayuthapani (Navapashanam)', 'darshan_type': 'winch_ropeway', 'slot_time': '05:00 PM - 07:30 PM', 'location': 'Hill Top Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Palani Panchamirtham Prasadam', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-016',
        'name': 'Tiruchendur Subramanya Swamy Seashore Temple Tour',
        'destination': 'Madurai / Tirunelveli / Tiruchendur',
        'category': 'devotional',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('3100.00'),
        'price_with_food': decimal.Decimal('4200.00'),
        'price_without_food': decimal.Decimal('3100.00'),
        'is_devotional': True,
        'description': 'Visit the magnificent seashore temple of Lord Murugan at Tiruchendur where the deity vanquished demon Surapadman. Includes holy dip in the sea and Nazhikkinaru sweet-water well.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival Tiruchendur & Seashore Sunset Darshan',
                'route': 'Madurai to Tiruchendur (180 km / 3.5 hrs)',
                'activities': 'Drive to coastal town Tiruchendur. Check-in at hotel facing the sea. Afternoon visit to the monumental 9-tier Gopuram of Subramanya Swamy Temple. Holy dip in Bay of Bengal sea and Nazhikkinaru spring. Attend evening Sayaratchai deeparadhana.',
                'morning': 'Drive to Tiruchendur, hotel check-in',
                'sightseeing': 'Tiruchendur Temple Gopuram, Seashore Beach, Nazhikkinaru',
                'evening': 'Sayaratchai deeparadhana, seashore breeze walk, dinner',
                'night_stay': 'Tiruchendur Hotel',
                'meals': 'Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Viswaroopa Morning Darshan & Return',
                'route': 'Tiruchendur to Madurai / Tirunelveli (180 km)',
                'activities': 'Early morning Viswaroopa Darshan of Lord Senthil Andavar. Visit Valli Cave shrine on the beach. Breakfast. Drive back with return drop at Madurai or Tirunelveli.',
                'morning': 'Viswaroopa Darshan, Valli Cave, breakfast',
                'sightseeing': 'Main Sanctum, Valli Cave Temple, Shanmukhar Sannidhi',
                'evening': 'Departure transfer',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Tiruchendur Subramanya Swamy Temple', 'deity': 'Lord Senthil Andavar', 'darshan_type': 'special_entry_300', 'slot_time': '06:00 AM - 08:30 AM', 'location': 'Main Sea-Facing Sanctum', 'dress_code': 'Dhoti for Men, Saree for Women', 'prasad': 'Ilai Vibhuti Prasadam', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-017',
        'name': 'Chidambaram Nataraja Temple & Pichavaram Mangrove Tour',
        'destination': 'Pondicherry / Chidambaram / Pichavaram',
        'category': 'devotional',
        'duration_days': 2,
        'duration_nights': 1,
        'base_price': decimal.Decimal('2899.00'),
        'price_with_food': decimal.Decimal('3899.00'),
        'price_without_food': decimal.Decimal('2899.00'),
        'is_devotional': True,
        'description': 'Experience the cosmic dance of Lord Shiva at the ancient Thillai Nataraja Temple (Akasha Stalam) in Chidambaram and enjoy a rowboat safari through Pichavaram Mangrove Forest.',
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival Chidambaram & Nataraja Temple Darshan',
                'route': 'Chennai / Pondicherry to Chidambaram (160 km)',
                'activities': 'Drive to Chidambaram. Hotel check-in. Visit the world-famous Thillai Nataraja Temple, covered with a gold-plated roof (Ponnambalam). Experience the mystic Chidambara Rahasyam (secret of space), the Ruby Nataraja crystal lingam abhishekam, and Govindaraja Perumal Divya Desam inside the same complex.',
                'morning': 'Arrival, check-in, lunch',
                'sightseeing': 'Thillai Nataraja Temple, Golden Roof, Sivagangai Tank, Govindaraja Perumal',
                'evening': 'Evening deeparadhana and Ruby Lingam darshan, dinner',
                'night_stay': 'Chidambaram Hotel',
                'meals': 'Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Pichavaram Mangrove Boat Safari & Return',
                'route': 'Chidambaram to Pichavaram and Return (40 km)',
                'activities': 'Morning visit to Pichavaram, the second largest mangrove forest in the world. 2-hour rowboat cruise through narrow shaded water canals under lush mangrove canopies. Visit Thillai Kali Temple. Afternoon return journey to Chennai / Trichy.',
                'morning': 'Breakfast, Pichavaram Mangrove Boat Cruise',
                'sightseeing': 'Pichavaram Mangrove Canals, Thillai Kali Temple',
                'evening': 'Return departure',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Chidambaram Thillai Nataraja Temple (Akasha Stalam)', 'deity': 'Lord Nataraja & Sivakami Amman', 'darshan_type': 'general', 'slot_time': '05:30 PM - 07:30 PM', 'location': 'Kanaka Sabha / Ponnambalam', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti & Kumkum', 'senior_citizen': True}
        ]
    },
    {
        'code': 'SGT-CTT-018',
        'name': 'Kumbakonam Navagraha 9 Cosmic Planets Temples Circuit',
        'destination': 'Kumbakonam / Thanjavur / Mayiladuthurai',
        'category': 'pilgrimage',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': decimal.Decimal('5900.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5900.00'),
        'is_devotional': True,
        'description': 'The ultimate Navagraha pilgrimage circuit around Kumbakonam covering all 9 planet temples: Suryanar Kovil (Sun), Thingalur (Moon), Vaitheeswaran Koil (Mars), Thiruvenkadu (Mercury), Alangudi (Jupiter), Kanjanur (Venus), Thirunallar (Saturn), Thirunageswaram (Rahu), and Keezhperumpallam (Ketu).',
        'itinerary': [
            {
                'day': 1,
                'title': 'Thingalur, Alangudi & Thirunageswaram',
                'route': 'Kumbakonam Temple Circuit (80 km)',
                'activities': 'Arrival in Kumbakonam, check-in. Visit 1. Thingalur Kailasanathar Temple (Moon / Chandran), 2. Alangudi Apatsahayeswarar Temple (Jupiter / Guru), and 3. Thirunageswaram Naganathar Temple (Rahu) where milk turns blue during abhishekam. Pure veg dinner.',
                'morning': 'Arrival, check-in, visit Thingalur and Alangudi',
                'sightseeing': 'Thingalur Chandran Temple, Alangudi Guru Temple, Thirunageswaram Rahu Temple',
                'evening': 'Thirunageswaram milk abhishekam, dinner',
                'night_stay': 'Kumbakonam Hotel',
                'meals': 'Lunch, Dinner'
            },
            {
                'day': 2,
                'title': 'Suryanar Kovil, Kanjanur, Vaitheeswaran & Thiruvenkadu',
                'route': 'Cauvery Delta Temple Circuit (110 km)',
                'activities': 'Full day visiting 4. Suryanar Kovil (Sun / Suriyan), 5. Kanjanur Agneeswarar Temple (Venus / Sukran), 6. Vaitheeswaran Koil (Mars / Sevvai & Lord of Healing), and 7. Thiruvenkadu Swetharanyeswarar Temple (Mercury / Budhan). Traditional lunch enroute.',
                'morning': 'Visit Suryanar Kovil and Kanjanur',
                'sightseeing': 'Suryanar Kovil, Kanjanur Sukran Temple, Vaitheeswaran Koil, Thiruvenkadu',
                'evening': 'Vaitheeswaran Koil evening pooja, dinner',
                'night_stay': 'Kumbakonam Hotel',
                'meals': 'Breakfast, Lunch, Dinner'
            },
            {
                'day': 3,
                'title': 'Keezhperumpallam, Thirunallar Saneeswarar & Return',
                'route': 'Karaikal to Kumbakonam / Chennai (90 km)',
                'activities': 'Visit 8. Keezhperumpallam Naganathar Temple (Ketu) and 9. Thirunallar Darbaranyeswarar Temple (Saturn / Sani) in Karaikal with holy dip in Nala Theertham and sesame oil lamp offering. Complete Navagraha parihara rituals. Return journey to Chennai / Trichy.',
                'morning': 'Keezhperumpallam Ketu temple and Thirunallar Sani temple',
                'sightseeing': 'Keezhperumpallam, Thirunallar Saneeswarar Temple, Nala Theertham',
                'evening': 'Departure with total peace and planetary blessings',
                'night_stay': 'Departure',
                'meals': 'Breakfast, Lunch'
            }
        ],
        'darshan_slots': [
            {'temple_name': 'Thirunallar Sri Darbaranyeswarar (Sani Stalam)', 'deity': 'Lord Saneeswarar', 'darshan_type': 'special_entry_300', 'slot_time': '09:00 AM - 11:00 AM', 'location': 'Sani Bhagavan Sannidhi', 'dress_code': 'Traditional Attire', 'prasad': 'Gingelly Oil Lamp Pooja Prasadam', 'senior_citizen': True},
            {'temple_name': 'Vaitheeswaran Koil Sri Vaidyanathar (Sevvai Stalam)', 'deity': 'Lord Vaidyanatha Swamy & Angaragan', 'darshan_type': 'special_entry_300', 'slot_time': '03:00 PM - 04:30 PM', 'location': 'Angaragan Sannidhi', 'dress_code': 'Traditional Attire', 'prasad': 'Tiruchandu Urundai Sacred Medicine Ball', 'senior_citizen': True}
        ]
    }
]
