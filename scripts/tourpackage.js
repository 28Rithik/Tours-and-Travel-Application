document.addEventListener("DOMContentLoaded", function () {
  const WHATSAPP_NUMBER = "919629808833";
  const CALL_NUMBER = "919629808833";
  const SUPPORT_PHONE = "9629808833";
  const SUPPORT_EMAIL = "bharathiyartravels.cbe@gmail.com";
  const APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxZcAKgXwH5v0i2atZ4XTbqK0PPofoSzKLZG0TpkciJf0IQkT-vw-Hs01xD_msIMNHR/exec";

  const VEHICLES = {
    sedan: { name: "SEDAN", type: "Etios, Dzire - 4 Seater" },
    ertiga: { name: "ERTIGA", type: "6 Seater" },
    innova: { name: "INNOVA", type: "7 Seater" },
    crysta: { name: "INNOVA CRYSTA", type: "7 Seater" },
    tt14: { name: "TEMPOTRAVELLER 14", type: "12 - 14 Seater" },
    tt18: { name: "TEMPOTRAVELLER 18", type: "16 - 18 Seater" },
    urbania: { name: "URBANIA", type: "12-17 Seater" },
    coach: { name: "COACH", type: "21 Seater" }
  };

  const HOTEL_RATES = {
    "2star": {
      "double": 3300,
      "triple": 4000
    },
    "3star": {
      "double": 4500,
      "triple": 5000
    }
  };

  const packageData = {
    "1D": {
      title: "One Day Tour Packages",
      subtitle: "Select your destination",
      destinations: {
        "Isha-Marudhamalai": {
          hash: "isha-marudhamalai",
           kmLimit: 100,
          vehicles: [
            { ...VEHICLES.sedan, price: 3300 },
            { ...VEHICLES.ertiga, price: 3800 },
            { ...VEHICLES.innova, price: 4300 },
            { ...VEHICLES.crysta, price: 5000 },
            { ...VEHICLES.tt14, price: 6000 },
            { ...VEHICLES.tt18, price: 7000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Visit Perur Patteswarar Temple, Isha Yoga Center, and Marudhamalai." }
          ]
        },

        "Ooty": {
          hash: "ooty",
           kmLimit: 300,
          vehicles: [
            { ...VEHICLES.sedan, price: 6000 },
            { ...VEHICLES.ertiga, price: 7000 },
            { ...VEHICLES.innova, price: 8000 },
            { ...VEHICLES.crysta, price: 10000 },
            { ...VEHICLES.tt14, price: 12000 },
            { ...VEHICLES.tt18, price: 15000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Doddabetta Peak, Ooty Lake,Botanical Garden,Rose Garden,Tea Factory & Chocolate Museum" }
          ]
        },

        "Top Slip - Masani Amman Temple": {
           kmLimit: 300,
          hash: "top-slip-masani-amman",
          vehicles: [
          { ...VEHICLES.sedan, price: 5000 },
            { ...VEHICLES.ertiga, price: 6000 },
            { ...VEHICLES.innova, price: 7000 },
            { ...VEHICLES.crysta, price: 8000 },
            { ...VEHICLES.tt14, price: 9000 },
            { ...VEHICLES.tt18, price: 11000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Visit Top Slip, Parambikulam and Masani Amman Temple." }
          ]
        },

        "Guruvayur": {
          hash: "guruvayur",
           kmLimit: 400,
          vehicles: [
            { ...VEHICLES.sedan, price: 7000 },
            { ...VEHICLES.ertiga, price: 8500 },
            { ...VEHICLES.innova, price: 9500 },
            { ...VEHICLES.crysta, price: 11000 },
            { ...VEHICLES.tt14, price: 13000 },
            { ...VEHICLES.tt18, price: 15000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Visit Guruvayur Krishnar Temple, Punnathur Kotta, Mammiyur Sri Mahadeva Temple and Chavakkad Beach." }
          ]
        },

        "Palani": {
          hash: "palani",
           kmLimit: 250,
          vehicles: [
            { ...VEHICLES.sedan, price: 5000 },
            { ...VEHICLES.ertiga, price: 6000 },
            { ...VEHICLES.innova, price: 7000 },
            { ...VEHICLES.crysta, price: 8000 },
            { ...VEHICLES.tt14, price: 10000 },
            { ...VEHICLES.tt18, price: 11000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Palani, Palani Murugan Temple and back to Coimbatore." }
          ]
        }
      }
    },

    "2D": {
      title: "Two Day Tour Packages",
      subtitle: "Select your destination",

      destinations: {
        "Ooty": {
          hash: "ooty-2d",
           kmLimit: 350,
          vehicles: [
            { ...VEHICLES.sedan, price: 8000 },
            { ...VEHICLES.ertiga, price: 10000 },
            { ...VEHICLES.innova, price: 11000 },
            { ...VEHICLES.crysta, price: 13500 },
            { ...VEHICLES.tt14, price: 16000  },
            { ...VEHICLES.tt18, price: 18000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Ooty, Doddabetta Peak, Tea Factory, Botanical Garden. Stay at Ooty." },
            { day: "Day 2", text: "Ooty to Rose Garden, Lake (Boat House), Thread Garden, Wax Museum, Ooty to Coonoor, on the way Ketti Valley View, MRC Military Camp (Outside View), Sims Park, Dolphin’s Nose, Lamb’s Rock and back to Coimbatore." }
          ]
        },


        "Valparai": {
          hash: "valparai-2d",
           kmLimit: 350,
          vehicles: [
            { ...VEHICLES.sedan, price: 8000 },
            { ...VEHICLES.ertiga, price: 10000 },
            { ...VEHICLES.innova, price: 11000 },
            { ...VEHICLES.crysta, price: 13500 },
            { ...VEHICLES.tt14, price: 16000 },
            { ...VEHICLES.tt18, price: 18000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Valparai, on the way, Eachanari Temple, Masani Amman Temple, Aliyar Dam, Monkey Falls. Stay at Valparai." },
            { day: "Day 2", text: "Balaji Temple, Sholayar Dam, Valparai Tea Estate, Valparai Viewpoints and back to Coimbatore." }
          ]
        },


        "Kodaikanal": {
          hash: "kodaikanal-2d",
           kmLimit: 500,
          vehicles: [
            { ...VEHICLES.sedan, price: 10000 },
            { ...VEHICLES.ertiga, price: 12000 },
            { ...VEHICLES.innova, price: 13500 },
            { ...VEHICLES.crysta, price: 15500 },
            { ...VEHICLES.tt14, price: 18000 },
            { ...VEHICLES.tt18, price: 22000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Kodaikanal, Silver Cascade Falls, Kodaikanal Lake, Coakers Walk. Stay at Kodaikanal." },
            { day: "Day 2", text: "Guna Cave, Dolphin’s Nose, Echo Point, Pillar Rocks, Bryant Park, Green Valley View, Kurinji Andavar Temple and back to Coimbatore." }
          ]
        },

        "Munnar": {
          hash: "munnar-2d",
           kmLimit: 500,
          vehicles: [
            { ...VEHICLES.sedan, price: 10000 },
            { ...VEHICLES.ertiga, price: 12000 },
            { ...VEHICLES.innova, price: 13500 },
            { ...VEHICLES.crysta, price: 16000 },
            { ...VEHICLES.tt14, price: 19000 },
            { ...VEHICLES.tt18, price: 23000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Munnar, Chinnar Wildlife Sanctuary, Lakkam Waterfalls, Eravikulam National Park. Stay at Munnar." },
            { day: "Day 2", text: "Rose Garden, Elephant Safari, Mattupatty Dam, Tea Garden, Echo Point, Top Station and back to Coimbatore." }
          ]
        },



    "Mysore": {
      hash: "mysore-2d",
       kmLimit: 550,
      vehicles: [
        { ...VEHICLES.sedan, price: 11000 },
        { ...VEHICLES.ertiga, price: 13000 },
        { ...VEHICLES.innova, price: 15000 },
        { ...VEHICLES.crysta, price: 17000 },
        { ...VEHICLES.tt14, price: 23000 },
        { ...VEHICLES.tt18, price: 26500 },
        { ...VEHICLES.urbania, price: null },
        { ...VEHICLES.coach, price: null }
      ],
      itinerary: [
        { day: "Day 1", text: "Coimbatore to Mysore, Mysore Palace, Jaganmohan Palace, St. Philomena’s Church, Lalith Mahal Palace, Mysore Zoo. Stay at Mysore." },
        { day: "Day 2", text: "Chamundeshwari Temple, Rail Museum, Brindavan Gardens and back to Coimbatore." }
      ]
    },


        "Malampuzha Dam - Guruvayur": {
          hash: "malampuzha-guruvayur-2d",
           kmLimit: 400,
          vehicles: [
            { ...VEHICLES.sedan, price: 9500 },
            { ...VEHICLES.ertiga, price: 11500 },
            { ...VEHICLES.innova, price: 12500 },
            { ...VEHICLES.crysta, price: 15000 },
            { ...VEHICLES.tt14, price: 17000 },
            { ...VEHICLES.tt18, price: 20000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Punnathur Kotta, Mammiyur Sri Mahadeva Temple and Malampuzha Dam. Stay at Guruvayur." },
            { day: "Day 2", text: "Guruvayur Krishnar Temple, Chavakkad Beach and back to Coimbatore." }
          ]
        },

        "Sabarimalai": {
          hash: "sabarimalai-2d",
           kmLimit: 750,
          vehicles: [
            { ...VEHICLES.sedan, price: 13500 },
            { ...VEHICLES.ertiga, price: 16000 },
            { ...VEHICLES.innova, price: 18000 },
            { ...VEHICLES.crysta, price: 21000 },
            { ...VEHICLES.tt14, price: 23000 },
            { ...VEHICLES.tt18, price: 27000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Pamba, Sabarimalai. Stay at Sabarimalai." },
            { day: "Day 2", text: "Sabarimalai, Erumeli and back to Coimbatore." }
          ]
        },

        "Rameshwaram": {
          hash: "rameshwaram-2d",
           kmLimit: 900,
          vehicles: [
            { ...VEHICLES.sedan, price: 15000 },
            { ...VEHICLES.ertiga, price: 18000 },
            { ...VEHICLES.innova, price: 20000 },
            { ...VEHICLES.crysta, price: 23500 },
            { ...VEHICLES.tt14, price: 26000 },
            { ...VEHICLES.tt18, price: 31000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Rameshwaram Temple. Stay at Rameswaram." },
            { day: "Day 2", text: "Dhanushkodi, APJ Memorial Museum, Pambam Bridge back to Coimbatore." }
          ]
        },

        "Thiruchendur": {
          hash: "thiruchendur-2d",
           kmLimit: 900,
          vehicles: [
            { ...VEHICLES.sedan, price: 15000 },
            { ...VEHICLES.ertiga, price: 18000 },
            { ...VEHICLES.innova, price: 20000 },
            { ...VEHICLES.crysta, price: 23500 },
            { ...VEHICLES.tt14, price: 26000 },
            { ...VEHICLES.tt18, price: 31000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Thiruchendur Temple. Stay at Thiruchendur." },
            { day: "Day 2", text: "Temple Visit back to Coimbatore." }
          ]
        },

        "Thiruvannamalai": {
          hash: "thiruvannamalai-2d",
           kmLimit: 700,
          vehicles: [
            { ...VEHICLES.sedan, price: 13000 },
            { ...VEHICLES.ertiga, price: 16000 },
            { ...VEHICLES.innova, price: 17500 },
            { ...VEHICLES.crysta, price: 20500 },
            { ...VEHICLES.tt14, price: 23000 },
            { ...VEHICLES.tt18, price: 27000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Thiruvannamalai, Thiruvannamalai Girivalam. Stay at Thiruvannamalai." },
            { day: "Day 2", text: "Temple Darshan and back to Coimbatore." }
          ]
        }
      }
    },



    "3D": {
      title: "Three Day Tour Packages",
      subtitle: "Select your destination",
       kmLimit: 350,
      destinations: {
        "Ooty": {
          hash: "ooty-3d",
          vehicles: [
            { ...VEHICLES.sedan, price: 11000 },
            { ...VEHICLES.ertiga, price: 13000 },
            { ...VEHICLES.innova, price: 14500 },
            { ...VEHICLES.crysta, price: 17000 },
            { ...VEHICLES.tt14, price: 19000 },
            { ...VEHICLES.tt18, price: 22500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Ooty, Doddabetta Peak, Tea Factory, Botanical Garden. Stay at Ooty." },
            { day: "Day 2", text: "Pine forest, Kamarajar Dam (Outside View), 6th Mile, 9th Mile Shooting Spot, Pykara Waterfalls, Pykara Lake (Boating). Stay at Ooty." },
            { day: "Day 3", text: "Rose Garden, Lake (Boat House), Thread Garden, Wax Museum, Ooty to Coonoor, on the way Ketti Valley View, MRC Military Camp (Outside View), Sims Park, Dolphin’s Nose, Lamb’s Rock and back to Coimbatore." }
          ]
        },

        "Kodaikanal": {
          hash: "kodaikanal-3d",
           kmLimit: 550,
          vehicles: [
            { ...VEHICLES.sedan, price: 12000 },
            { ...VEHICLES.ertiga, price: 14500 },
            { ...VEHICLES.innova, price: 16500 },
            { ...VEHICLES.crysta, price: 19500 },
            { ...VEHICLES.tt14, price: 22500 },
            { ...VEHICLES.tt18, price: 26500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Palani Murugan Temple, Palani to Kodaikanal, Lake (Boat House), Coakers Walk. Stay at Kodaikanal." },
            { day: "Day 2", text: "Pillar Rocks, Bryant Park, Guna Cave, Green Valley View. Stay at Kodaikanal." },
            { day: "Day 3", text: "Chettiar Park, Kurinji Andavar Temple, Silver Cascade Falls and back to Coimbatore." }
          ]
        },

        "Munnar": {
          hash: "munnar-3d",
           kmLimit: 550,
          vehicles: [
            { ...VEHICLES.sedan, price: 12500 },
            { ...VEHICLES.ertiga, price: 15000 },
            { ...VEHICLES.innova, price: 17000 },
            { ...VEHICLES.crysta, price: 20000 },
            { ...VEHICLES.tt14, price: 23000 },
            { ...VEHICLES.tt18, price: 27000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Munnar, Chinnar Wildlife Sanctuary, Lakkam Waterfalls, Eravikulam National Park. Stay at Munnar." },
            { day: "Day 2", text: "Rose Garden, Elephant Safari, Mattupatty Dam, Tea Garden, Echo Point, Top Station. Stay at Munnar." },
            { day: "Day 3", text: "Kalari and Kathakali Live Performance Show, Attukadu waterfalls, Pothamedu Viewpoint, Spice Garden and back to Coimbatore." }
          ]
        },

        "Wayanad": {
          hash: "wayanad-3d",
           kmLimit: 600,
          vehicles: [
            { ...VEHICLES.sedan, price: 13500 },
            { ...VEHICLES.ertiga, price: 16000 },
            { ...VEHICLES.innova, price: 18000 },
            { ...VEHICLES.crysta, price: 21000 },
            { ...VEHICLES.tt14, price: 24000 },
            { ...VEHICLES.tt18, price: 28000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Wayanad, Banasura Sagar Dam, Edakkal Cave, Kuruva Island. Stay at Wayanad." },
            { day: "Day 2", text: "Muthunga Wildlife Sanctuary, Glass Bridge. Stay at Wayanad." },
            { day: "Day 3", text: "Pookot Lake, Lakkidi View Point and back to Coimbatore." }
          ]
        },


        "Valparai - Athirapally": {
          hash: "valparai-3d",
           kmLimit: 500,
          vehicles: [
            { ...VEHICLES.sedan, price: 12000 },
            { ...VEHICLES.ertiga, price: 14500 },
            { ...VEHICLES.innova, price: 16000 },
            { ...VEHICLES.crysta, price: 19000 },
            { ...VEHICLES.tt14, price: 22500 },
            { ...VEHICLES.tt18, price: 25500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Valparai, Loam's View Point, Monkey Falls, Tea Estates, Tiger Valley, Balaji Temple - Overnight Stay" },
            { day: "Day 2", text: "Athirapally Waterfalls, Vazhachal Falls, Charpa Falls" },
            { day: "Day 3", text: "Nallamudi Viewpoint, Chinna Kallar Falls, Valaparai Sightseeing" }
          ]
        },

        "Mysore - Coorg": {
          hash: "mysroe-coorg-3d",
           kmLimit: 850,
          vehicles: [
            { ...VEHICLES.sedan, price: 16000 },
            { ...VEHICLES.ertiga, price: 19550 },
            { ...VEHICLES.innova, price: 22000 },
            { ...VEHICLES.crysta, price: 25500 },
            { ...VEHICLES.tt14, price: 32500 },
            { ...VEHICLES.tt18, price: 38000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Dubare Elephant camp, Golden Temple, Nisargadhama forest" },
            { day: "Day 2", text: "Abbey Falls, Coffer Plant, Raja seat and Mysore Halat." },
            { day: "Day 3", text: "Mysore zoo, Mysore Palace and back to Coimbatore" }
          ]
        },



        "Navagraha Temple": {
          hash: "navagraha-temple-3d",
           kmLimit: 900,
          vehicles: [
            { ...VEHICLES.sedan, price: 17500 },
            { ...VEHICLES.ertiga, price: 21000 },
            { ...VEHICLES.innova, price: 23500 },
            { ...VEHICLES.crysta, price: 27500 },
            { ...VEHICLES.tt14, price: 32000 },
            { ...VEHICLES.tt18, price: 37000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Thanjavur, Brahadeshwara Temple, Tingalur (Chandran Temple), Alangudi (Guru Temple), Thirunangeswaram (Raaghu Temple). Stay at Mayiladuthurai." },
            { day: "Day 2", text: "Suriyanar (Suriyan Temple), Kanjanoor (Sukkran Temple), Vaithesswaran (Sevvai Temple), Thiruvenkadu (Budhan Temple). Stay at Thirunallaru." },
            { day: "Day 3", text: "Keezhperumpallam (Kethu Temple), Thirunallaru (Sani Bhagavan Temple) and back to Coimbatore." }
          ]
        }
      }
    },

    "4D": {
      title: "Four Day Tour Packages",
      subtitle: "Select your destination",
      kmLimit: 450,
      destinations: {
        "Ooty": {
          hash: "ooty-4d",
          vehicles: [
            { ...VEHICLES.sedan, price: 13500 },
            { ...VEHICLES.ertiga, price: 16000 },
            { ...VEHICLES.innova, price: 17500 },
            { ...VEHICLES.crysta, price: 21500 },
            { ...VEHICLES.tt14, price: 24000 },
            { ...VEHICLES.tt18, price: 28500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Coonoor, Ketti Valley View, MRC Military Camp (Outside View), Sim’s Park, Dolphin’s Nose, Lamb’s Rock, to Ooty, Stay at Ooty." },
            { day: "Day 2", text: "Pine forest, Kamarajar Dam, Tree Garden, 9th Mile Shooting Spot, Pykara Waterfalls, Pykara Dam. Stay at Ooty." },
            { day: "Day 3", text: "Doddabetta Peak, Tea Factory, Botanical Garden. Stay at Ooty." },
            { day: "Day 4", text: "Rose Garden, Lake (Boat House), Thread Garden, Wax Museum and back to Coimbatore." }
          ]
        },

        "Kodaikanal": {
          hash: "kodaikanal-4d",
          kmLimit: 550,
          vehicles: [
            { ...VEHICLES.sedan, price: 14500 },
            { ...VEHICLES.ertiga, price: 17000 },
            { ...VEHICLES.innova, price: 19000 },
            { ...VEHICLES.crysta, price: 23000 },
            { ...VEHICLES.tt14, price: 26000 },
            { ...VEHICLES.tt18, price: 31000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Palani Andavar Temple, to Kodaikanal, Silver Cascade Waterfalls. Stay at Kodaikanal." },
            { day: "Day 2", text: "Kodaikanal Lake, Bryant Park, Coakers Walk, Chettiar Park, Kurinji Andavar Temple. Stay at Kodaikanal." },
            { day: "Day 3", text: "Pine forest, Guna Cave, Pillar Rocks, Green Valley View, Moyer Point, Silent Valley. Stay at Kodaikanal." },
            { day: "Day 4", text: "Back to Coimbatore." }
          ]
        },


        "Ooty - Mysore": {
          hash: "ooty-mysore-4d",
                  kmLimit: 700,
          vehicles: [
            { ...VEHICLES.sedan, price: 16500 },
            { ...VEHICLES.ertiga, price: 20000 },
            { ...VEHICLES.innova, price: 22000 },
            { ...VEHICLES.crysta, price: 26000 },
            { ...VEHICLES.tt14, price: 33500 },
            { ...VEHICLES.tt18, price: 39500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Coonoor, Sims Park, Dolphin's Nose, Lamb's Rock, to Ooty, Tea Garden. Stay at Ooty." },
            { day: "Day 2", text: "Rose Garden, Botanical Garden, Lake (Boathouse), Doddabetta Peak, Tea Factory, Wax Museum, Karnataka Garden. Stay at Ooty." },
            { day: "Day 3", text: "Checkout from hotel at Ooty, Pine tree forest, 9th Mile Shooting spot, Pykara Waterfalls, Mudumalai National Park or Bandipur Wildlife Safari, Mysore Palace. Stay at Mysore." },
            { day: "Day 4", text: "Checkout from hotel at Mysore, Mysore Zoo, Chamundeshwari Temple and back to Coimbatore." }
          ]
        },

        "Munnar - Thekkady": {
          hash: "munnarthekkady-4d",
          kmLimit: 800,
          vehicles: [
            { ...VEHICLES.sedan, price: 17500 },
            { ...VEHICLES.ertiga, price: 21000 },
            { ...VEHICLES.innova, price: 23500 },
            { ...VEHICLES.crysta, price: 28000 },
            { ...VEHICLES.tt14, price: 31500 },
            { ...VEHICLES.tt18, price: 37500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Munnar, on the way sight-seeing at Lakkam Waterfalls and Eravikulam National Park. Stay at Munnar." },
            { day: "Day 2", text: "Mattupatty Dam, Rose Garden, Echo Point, Tea plantation and Top Station. Stay at Munnar." },
            { day: "Day 3", text: "Kalari and Kathakali Live performance Show, Spice Garden, Off Road Safari (Price excluded). Stay at Thekkady." },
            { day: "Day 4", text: "Periyar Wildlife Sanctuary and local sightseeings and back to Coimbatore." }
          ]
        },

        "Coorg - Chikmagalur": {
          hash: "coorgchikmagalur-4d",
          kmLimit: 1100,
          vehicles: [
            { ...VEHICLES.sedan, price: 21000 },
            { ...VEHICLES.ertiga, price: 25500 },
            { ...VEHICLES.innova, price: 28500 },
            { ...VEHICLES.crysta, price: 33500 },
            { ...VEHICLES.tt14, price: 41500 },
            { ...VEHICLES.tt18, price: 48500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
        { day: "Day 1", text: "Coimbatore to Coorg. Pickup from Airport/Railway Station, scenic drive with optional stops, check-in and relax. Stay at Coorg." },
        { day: "Day 2", text: "Abbey Falls, Raja’s Seat, Madikeri Fort, Omkareshwara Temple, Dubare Elephant Camp (optional), Cauvery Nisargadhama. Stay at Coorg." },
        { day: "Day 3", text: "Coorg to Chikmagalur. Visit Mullayanagiri Peak, Baba Budangiri, Hirekolale Lake. Stay at Chikmagalur." },
        { day: "Day 4", text: "Chikmagalur to Coimbatore. Visit Coffee Plantation (optional), return drop at Airport/Railway Station." }
      ]
        },

        "Coorg - Wayanad": {
          hash: "Coorgwayanad-4d",
          kmLimit: 900,
          vehicles: [
            { ...VEHICLES.sedan, price: 19000 },
            { ...VEHICLES.ertiga, price: 23000 },
            { ...VEHICLES.innova, price: 25500 },
            { ...VEHICLES.crysta, price: 30000 },
            { ...VEHICLES.tt14, price: 37500 },
            { ...VEHICLES.tt18, price: 44000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
    { day: "Day 1", text: "Coimbatore to Coorg. Pickup from Airport/Railway Station, scenic drive with refreshment stops, check-in and relax. Stay at Coorg." },
    { day: "Day 2", text: "Abbey Falls, Raja’s Seat, Madikeri Fort, Omkareshwara Temple, Dubare Elephant Camp (optional), Cauvery Nisargadhama. Stay at Coorg." },
    { day: "Day 3", text: "Coorg to Wayanad. Visit Edakkal Caves, Soochipara Falls / Meenmutty Falls (based on time). Stay at Wayanad." },
    { day: "Day 4", text: "Wayanad to Coimbatore. Visit Pookode Lake, Lakkidi View Point and drop at Airport/Railway Station." }
  ]
        },

        "Kodaikanal - Madurai - Rameswaram": {
          hash: "kodaikanal-madurai-rameswaram-4d",
            kmLimit: 1000,
          vehicles: [
            { ...VEHICLES.sedan, price: 20000 },
            { ...VEHICLES.ertiga, price: 24000 },
            { ...VEHICLES.innova, price: 27000 },
            { ...VEHICLES.crysta, price: 32000 },
            { ...VEHICLES.tt14, price: 35500 },
            { ...VEHICLES.tt18, price: 42000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Palani Murugan Temple, Silver Cascade waterfalls, Kodaikanal Lake, Bryant Park, Coakers Walk, Chettiar Park, Kurinji Andavar Temple. Stay at Kodaikanal." },
            { day: "Day 2", text: "Pine tree forest, Guna Cave, Pillar Rocks, Green Valley View, Moyer Point, Silent Valley. Stay at Kodaikanal." },
            { day: "Day 3", text: "Checkout from hotel at Kodaikanal, Kodaikanal to Rameswaram, Temple Darshan, Local Sight Seeing. Stay at Rameswaram." },
            { day: "Day 4", text: "Rameswaram to Madurai, Meenakshi Amman Temple and drop at Madurai Railway Station/Airport." }
          ]
        }
      }
    },

    "5D": {
      title: "Five Day Tour Packages",
      subtitle: "Select your destination",
      destinations: {
        "Ooty": {
          hash: "ooty-5d",
            kmLimit: 550,
          vehicles: [
            { ...VEHICLES.sedan, price: 16500 },
            { ...VEHICLES.ertiga, price: 19500 },
            { ...VEHICLES.innova, price: 21500 },
            { ...VEHICLES.crysta, price: 26500 },
            { ...VEHICLES.tt14, price: 30000 },
            { ...VEHICLES.tt18, price: 35500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
        { day: "Day 1", text: "Arrival and Coonoor sightseeing. Visit Sim’s Park, Lamb’s Rock, Dolphin’s Nose, Tea Gardens, then transfer to Ooty and check-in. Stay at Ooty." },
        { day: "Day 2", text: "Ooty sightseeing. Botanical Garden, Rose Garden, Ooty Lake (Boathouse), Thread Garden, Doddabetta Peak, Tea Factory & Museum, Wax Museum. Stay at Ooty." },
        { day: "Day 3", text: "Avalanche sightseeing. Visit Avalanche Lake, Emerald Lake (jeep ride if required), enjoy nature and return to Ooty. Stay at Ooty." },
        { day: "Day 4", text: "Pykara & Mudumalai. Visit Pykara Lake, Pykara Falls, Mudumalai Wildlife Sanctuary (optional safari) and return to Ooty. Stay at Ooty." },
        { day: "Day 5", text: "Check-out, optional local shopping and drop at Coimbatore / Mettupalayam." }
      ]
        },

        "Ooty - Kodaikanal": {
          hash: "ooty-kodaikanal-5d",
          kmLimit: 800,
          vehicles: [
            { ...VEHICLES.sedan, price: 19500 },
            { ...VEHICLES.ertiga, price: 23500 },
            { ...VEHICLES.innova, price: 26000 },
            { ...VEHICLES.crysta, price: 31000 },
            { ...VEHICLES.tt14, price: 35000 },
            { ...VEHICLES.tt18, price: 42000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
        { day: "Day 1", text: "Coimbatore to Coonoor & Ooty. Pickup from Coimbatore, visit Sim’s Park, Lamb’s Rock, Dolphin’s Nose, Tea Gardens, then transfer to Ooty and check-in. Stay at Ooty." },
        { day: "Day 2", text: "Ooty sightseeing. Botanical Garden, Rose Garden, Ooty Lake (Boathouse), Thread Garden, Doddabetta Peak, Tea Factory & Museum, Wax Museum. Stay at Ooty." },
        { day: "Day 3", text: "Ooty to Kodaikanal. Scenic hill drive, check-in and evening leisure / local walk. Stay at Kodaikanal." },
        { day: "Day 4", text: "Kodaikanal sightseeing. Pillar Rocks, Bryant Park, Green Valley View, Kurinji Andavar Temple, Silver Cascade Falls, Guna Cave, Pine Forest, Coaker’s Walk. Stay at Kodaikanal." },
        { day: "Day 5", text: "Kodaikanal to Coimbatore. Optional shopping / lake visit and drop at Coimbatore." }
      ]
        },


        "Ooty - Mysore - Bangalore": {
          hash: "ooty-mysore-bangalore-5d",
          kmLimit: 1200,
          vehicles: [
            { ...VEHICLES.sedan, price: 24500 },
            { ...VEHICLES.ertiga, price: 29500 },
            { ...VEHICLES.innova, price: 33000 },
            { ...VEHICLES.crysta, price: 38500 },
            { ...VEHICLES.tt14, price: 47000 },
            { ...VEHICLES.tt18, price: 55000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
        { day: "Day 1", text: "Coimbatore to Coonoor & Ooty. Pickup from Coimbatore, visit Sim’s Park, Lamb’s Rock, Dolphin’s Nose, Tea Gardens, then transfer to Ooty and check-in. Stay at Ooty." },
        { day: "Day 2", text: "Ooty sightseeing. Botanical Garden, Rose Garden, Ooty Lake (Boathouse), Thread Garden, Doddabetta Peak, Tea Factory & Museum, Wax Museum. Stay at Ooty." },
        { day: "Day 3", text: "Ooty to Mysore via Pykara. Visit Pykara Lake, Pykara Falls, drive via Mudumalai & Bandipur forest route, check-in. Stay at Mysore." },
        { day: "Day 4", text: "Mysore sightseeing. Mysore Palace, Chamundi Hills, Mysore Zoo, Brindavan Gardens, St. Philomena’s Church. Stay at Mysore." },
        { day: "Day 5", text: "Mysore to Bangalore. Visit Tipu Sultan’s Palace, Lalbagh Botanical Garden, Vidhana Soudha (outside view) and drop at Coimbatore / Bangalore" }
      ]
        },


        "Kodaikanal - Munnar": {
          hash: "kodaikanal-munnar-5d",
          kmLimit: 800,
          vehicles: [
            { ...VEHICLES.sedan, price: 19000 },
            { ...VEHICLES.ertiga, price: 23000 },
            { ...VEHICLES.innova, price: 25500 },
            { ...VEHICLES.crysta, price: 30500 },
            { ...VEHICLES.tt14, price: 34500 },
            { ...VEHICLES.tt18, price: 41500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
        { day: "Day 1", text: "Coimbatore to Munnar. Scenic hill drive via Valara Falls and Cheeyappara Falls, check-in and relax. Stay at Munnar." },
        { day: "Day 2", text: "Munnar sightseeing. Mattupetty Dam, Echo Point, Kundala Lake, Tea Museum, Eravikulam National Park (Rajamalai). Stay at Munnar." },
        { day: "Day 3", text: "Munnar to Kodaikanal. Scenic inter-state hill drive, check-in and evening leisure / lake visit. Stay at Kodaikanal." },
        { day: "Day 4", text: "Kodaikanal sightseeing. Pillar Rocks, Bryant Park, Green Valley View, Kurinji Andavar Temple, Silver Cascade Falls, Guna Cave, Pine Forest, Coaker’s Walk. Stay at Kodaikanal." },
        { day: "Day 5", text: "Kodaikanal to Coimbatore. Optional shopping / lake visit and drop at Coimbatore." }
      ]
    },

        "Kodaikanal - Madurai - Rameshwaram": {
          hash: "kodaikanal-madurai-rameshwaram-5d",
          kmLimit: 1150,
          vehicles: [
            { ...VEHICLES.sedan, price: 23500 },
            { ...VEHICLES.ertiga, price: 28500 },
            { ...VEHICLES.innova, price: 31500 },
            { ...VEHICLES.crysta, price: 37500 },
            { ...VEHICLES.tt14, price: 42000 },
            { ...VEHICLES.tt18, price: 49500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
        { day: "Day 1", text: "Coimbatore to Kodaikanal. Pickup from Coimbatore, scenic hill drive, check-in, visit Kodaikanal Lake & Coaker’s Walk. Stay at Kodaikanal." },
        { day: "Day 2", text: "Kodaikanal sightseeing. Pillar Rocks, Bryant Park, Green Valley View, Kurinji Andavar Temple, Silver Cascade Falls, Guna Cave, Pine Forest. Stay at Kodaikanal." },
        { day: "Day 3", text: "Kodaikanal to Rameswaram. Long drive with breaks, visit Ramanathaswamy Temple, Pamban Bridge (if time permits). Stay at Rameswaram." },
        { day: "Day 4", text: "Rameswaram to Madurai. Visit Dhanushkodi, APJ Abdul Kalam Memorial, proceed to Madurai, visit Meenakshi Amman Temple. Stay at Madurai." },
        { day: "Day 5", text: "Madurai to Coimbatore. Optional visit Thirumalai Nayakkar Mahal and drop at Coimbatore." }
      ]
        },


        "Munnar - Varkala - Alleppey": {
          hash: "munnar-varkala-alleppey-5d",
              kmLimit: 1100,
          vehicles: [
            { ...VEHICLES.sedan, price: 23000 },
            { ...VEHICLES.ertiga, price: 28000 },
            { ...VEHICLES.innova, price: 31000 },
            { ...VEHICLES.crysta, price: 36500 },
            { ...VEHICLES.tt14, price: 41000 },
            { ...VEHICLES.tt18, price: 49000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
      { day: "Day 1", text: "Coimbatore to Munnar. Scenic hill drive via Valara Falls and Cheeyappara Falls, check-in and relax. Stay at Munnar." },
      { day: "Day 2", text: "Munnar sightseeing. Mattupetty Dam, Echo Point, Kundala Lake, Tea Museum, Eravikulam National Park (Rajamalai). Stay at Munnar." },
      { day: "Day 3", text: "Munnar to Varkala. Transfer, visit Varkala Beach, Cliff, Janardanaswamy Temple and leisure time at beach. Stay at Varkala." },
      { day: "Day 4", text: "Varkala to Alleppey. Houseboat check-in, backwater cruise with meals and overnight stay in houseboat. Stay at Alleppey Houseboat." },
      { day: "Day 5", text: "Alleppey to Coimbatore. Check-out and return drop at Coimbatore." }
    ]
        },


      }
    },

    "6D": {
      title: "Six Day Tour Packages",
      subtitle: "Select your destination",
      destinations: {
        "Ooty - Kodaikanal - Madurai": {
          hash: "ooty-kodaikanal-madurai-6d",
            kmLimit: 1100,
          vehicles: [
            { ...VEHICLES.sedan, price: 24500 },
            { ...VEHICLES.ertiga, price: 29500 },
            { ...VEHICLES.innova, price: 33000 },
            { ...VEHICLES.crysta, price: 39000 },
            { ...VEHICLES.tt14, price: 44000 },
            { ...VEHICLES.tt18, price: 52500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
          { day: "Day 1", text: "Coimbatore to Isha & Coonoor to Ooty. Visit Isha Yoga Center, Sim’s Park, Lamb’s Rock, Dolphin’s Nose, Tea Gardens, then transfer to Ooty and check-in. Stay at Ooty." },
          { day: "Day 2", text: "Ooty sightseeing. Botanical Garden, Rose Garden, Ooty Lake (Boathouse), Thread Garden, Doddabetta Peak, Tea Factory & Museum, Wax Museum. Stay at Ooty." },
          { day: "Day 3", text: "Ooty to Kodaikanal. Scenic hill drive, check-in and evening leisure. Stay at Kodaikanal." },
          { day: "Day 4", text: "Kodaikanal sightseeing. Pillar Rocks, Bryant Park, Green Valley View, Kurinji Andavar Temple, Silver Cascade Falls, Guna Cave, Pine Forest, Coaker’s Walk. Stay at Kodaikanal." },
          { day: "Day 5", text: "Kodaikanal to Madurai. Visit Meenakshi Amman Temple, Thirumalai Nayakkar Mahal and evening shopping. Stay at Madurai." },
          { day: "Day 6", text: "Madurai sightseeing. Visit Gandhi Memorial Museum, local markets and drop at Coimbatore / Madurai." }
        ]
        },



                "Kodaikanal - Ooty - Mysore": {
                  hash: "kodaikanal-ooty-mysore-6d",
                  kmLimit: 1200,
                  vehicles: [
                    { ...VEHICLES.sedan, price: 26000 },
                    { ...VEHICLES.ertiga, price: 32000 },
                    { ...VEHICLES.innova, price: 35000 },
                    { ...VEHICLES.crysta, price: 41000 },
                    { ...VEHICLES.tt14, price: 50000 },
                    { ...VEHICLES.tt18, price: 59000 },
                    { ...VEHICLES.urbania, price: null },
                    { ...VEHICLES.coach, price: null }
                  ],
                  itinerary: [
                    { day: "Day 1", text: "Coimbatore to Palani Murugan Temple, to Kodaikanal, Silver Cascade waterfalls. Stay at Kodaikanal." },
                    { day: "Day 2", text: "Pine tree forest, Guna Cave, Pillar Rocks, Moyer Point, Kurinji Andavar Temple, Rose Garden, Dolphin’s Nose. Stay at Kodaikanal." },
                    { day: "Day 3", text: "Kodaikanal to Coonoor, Coonoor local sight-seeing, Coonoor to Ooty. Stay at Ooty." },
                    { day: "Day 4", text: "Rose Garden, Botanical Garden, Lake (Boathouse), Doddabetta Peak, Tea factory, Wax Museum. Stay at Ooty." },
                    { day: "Day 5", text: "Pine tree forest, Tree Garden, 9th Mile Shooting spot, Pykara Waterfalls, Pykara Dam, Kamarajar Dam, Mudumalai National Park, Ooty to Mysore. Stay at Mysore." },
                    { day: "Day 6", text: "Chamundeshwari Temple, Mysore Zoo, Rail Museum, Mysore Palace and back to Coimbatore." }
                  ]
                },

        "Ooty - Coorg - Mysore - Bangalore": {
          hash: "ooty-coorg-mysore-bangalore-6d",
          kmLimit: 1500,
          vehicles: [
            { ...VEHICLES.sedan, price: 29500 },
            { ...VEHICLES.ertiga, price: 35500 },
            { ...VEHICLES.innova, price: 40000 },
            { ...VEHICLES.crysta, price: 47000 },
            { ...VEHICLES.tt14, price: 56000 },
            { ...VEHICLES.tt18, price: 66000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Coonoor, Sims Park, Dolphin’s Nose, Lamb’s Rock, to Ooty, Tea Garden. Stay at Ooty." },
            { day: "Day 2", text: "Ooty sight-seeing, Kattery Park, Rose Garden, Botanical Garden, Lake (Boathouse), Doddabetta Peak, Tea factory, Wax Museum, Karnataka Garden. Stay at Ooty." },
            { day: "Day 3", text: "Checkout from hotel at Ooty, Pine tree forest, Tree Garden, 9th Mile Shooting spot, Pykara Waterfalls, Mudumalai National Park. Stay at Coorg." },
            { day: "Day 4", text: "Golden Temple, Raja Seat, Thalakaveri, Nisargadhama forest. Stay at Coorg." },
            { day: "Day 5", text: "Checkout from hotel at Coorg, Coorg to Mysore, Mysore Zoo, Rail Museum, Mysore Palace. Stay at Mysore." },
            { day: "Day 6", text: "Mysore Silk Emporium, Chamundeshwari Temple, Lalith Mahal Palace and drop at Bangalore / Coimbatore" }
          ]
        },


        "Munnar - Alleppey - Varkala - Kovalam - Trivandrum": {
          hash: "munnar-alleppey-varkala-kovalam-trivandrum-6d",
          kmLimit: 1300,
          vehicles: [
            { ...VEHICLES.sedan, price: 27000 },
            { ...VEHICLES.ertiga, price: 32500 },
            { ...VEHICLES.innova, price: 36500 },
            { ...VEHICLES.crysta, price: 43000 },
            { ...VEHICLES.tt14, price: 48000 },
            { ...VEHICLES.tt18, price: 58000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
          { day: "Day 1", text: "Coimbatore to Munnar. Scenic hill drive, visit Lakkam Waterfalls, Eravikulam National Park, check-in and relax. Stay at Munnar." },
          { day: "Day 2", text: "Munnar sightseeing. Mattupetty Dam, Echo Point, Kundala Lake, Tea Museum, Top Station (based on time). Stay at Munnar." },
          { day: "Day 3", text: "Munnar to Alleppey. Houseboat check-in, backwater cruise with meals and overnight stay in houseboat. Stay at Alleppey Houseboat." },
          { day: "Day 4", text: "Alleppey to Varkala. Visit Varkala Beach, Cliff, Janardanaswamy Temple and relax. Stay at Varkala." },
          { day: "Day 5", text: "Varkala to Kovalam. Visit Kovalam Beach, Lighthouse Beach and leisure time. Stay at Kovalam." },
          { day: "Day 6", text: "Kovalam to Drop. Optional visit Padmanabhaswamy Temple and drop at Trivandrum / Coimbatore." }
        ]
        },


        "Ooty - Wayanad - Coorg": {
          hash: "ooty-wayanad-coorg-6d",
            kmLimit: 1000,
          vehicles: [
            { ...VEHICLES.sedan, price: 24000 },
            { ...VEHICLES.ertiga, price: 29000 },
            { ...VEHICLES.innova, price: 32000 },
            { ...VEHICLES.crysta, price: 38000 },
            { ...VEHICLES.tt14, price: 46500 },
            { ...VEHICLES.tt18, price: 55000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
        { day: "Day 1", text: "Coimbatore to Coonoor & Ooty. Visit Sim’s Park, Lamb’s Rock, Dolphin’s Nose, Tea Gardens, then transfer to Ooty and check-in. Stay at Ooty." },
        { day: "Day 2", text: "Ooty sightseeing. Botanical Garden, Rose Garden, Ooty Lake (Boathouse), Thread Garden, Doddabetta Peak, Tea Factory & Museum, Wax Museum. Stay at Ooty." },
        { day: "Day 3", text: "Ooty to Wayanad. Scenic forest drive, visit Pookode Lake, Lakkidi View Point (based on time), check-in. Stay at Wayanad." },
        { day: "Day 4", text: "Wayanad sightseeing. Edakkal Caves, Soochipara Falls / Meenmutty Falls, Banasura Sagar Dam (optional). Stay at Wayanad." },
        { day: "Day 5", text: "Wayanad to Coorg. Visit Abbey Falls, Raja’s Seat, Madikeri Fort, Omkareshwara Temple, check-in. Stay at Coorg." },
        { day: "Day 6", text: "Coorg sightseeing. Dubare Elephant Camp, Cauvery Nisargadhama and drop at Mysore / Coimbatore." }
      ]
        }
      }
    },

    "7D": {
      title: "Seven Day Tour Packages",
      subtitle: "Select your destination",
          kmLimit: 1200,
      destinations: {
        "Ooty - Kodaikanal - Munnar": {
          hash: "ooty-kodaikanal-munnar-7d",
          vehicles: [
            { ...VEHICLES.sedan, price: 27500 },
            { ...VEHICLES.ertiga, price: 33500 },
            { ...VEHICLES.innova, price: 37500 },
            { ...VEHICLES.crysta, price: 44000 },
            { ...VEHICLES.tt14, price: 50000 },
            { ...VEHICLES.tt18, price: 59500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Coonoor, Sims Park, Dolphin's Nose, Lamb's Rock, to Ooty, Tea Garden. Stay at Ooty." },
            { day: "Day 2", text: "Rose Garden, Botanical Garden, Lake (Boathouse), Doddabetta Peak, Tea factory, Wax Museum. Stay at Ooty." },
            { day: "Day 3", text: "Ooty to Kodaikanal, Silver Cascade waterfalls. Stay at Kodaikanal." },
            { day: "Day 4", text: "Pine tree forest, Guna Cave, Pillar Rocks, Moyer Point, Rose Garden, Dolphin’s Nose. Stay at Kodaikanal." },
            { day: "Day 5", text: "Kodaikanal to Munnar, Lakkam waterfalls, Eravikulam national park. Stay at Munnar." },
            { day: "Day 6", text: "Rose Garden, Elephant Safari, Mattupatty Dam, Tea Garden, Kalari and Kathakali live performance show, spice garden, Top Station. Stay at Munnar." },
            { day: "Day 7", text: "Back to Coimbatore." }
          ]
        },

        "Ooty - Kodaikanal - Madurai - Rameswaram": {
          hash: "ooty-kodaikanal-madurai-rameswaram-7d",
              kmLimit: 1400,
          vehicles: [
            { ...VEHICLES.sedan, price: 30000 },
            { ...VEHICLES.ertiga, price: 36500 },
            { ...VEHICLES.innova, price: 40500 },
            { ...VEHICLES.crysta, price: 48000 },
            { ...VEHICLES.tt14, price: 54000 },
            { ...VEHICLES.tt18, price: 64500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Coonoor, Sims Park, Dolphin’s Nose, Lamb’s Rock, to Ooty, Tea Garden. Stay at Ooty." },
            { day: "Day 2", text: "Rose Garden, Botanical Garden, Lake (Boathouse), Doddabetta Peak, Tea factory, Wax Museum. Stay at Ooty." },
            { day: "Day 3", text: "Ooty to Kodaikanal, Silver Cascade waterfalls. Stay at Kodaikanal." },
            { day: "Day 4", text: "Pine tree forest, Guna Cave, Pillar Rocks, Moyer Point, Rose Garden, Dolphin’s Nose. Stay at Kodaikanal." },
            { day: "Day 5", text: "Kodaikanal to Rameswaram, Rameswaram local sight-seeing. Stay at Rameswaram." },
            { day: "Day 6", text: "Rameswaram local sight-seeing, Rameswaram to Madurai, Madurai local sight-seeing. Stay at Madurai." },
            { day: "Day 7", text: "Madurai local sight-seeing and back to Coimbatore." }
          ]
        },

        "Ooty - Mysore - Coorg - Bangalore": {
          hash: "ooty-mysore-coorg-bangalore-7d",
            kmLimit: 1500,
          vehicles: [
            { ...VEHICLES.sedan, price: 31500 },
            { ...VEHICLES.ertiga, price: 38000 },
            { ...VEHICLES.innova, price: 42500 },
            { ...VEHICLES.crysta, price: 50000 },
            { ...VEHICLES.tt14, price: 59000 },
            { ...VEHICLES.tt18, price: 70500 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Coonoor, Sims Park, Dolphin’s Nose, Lamb’s Rock, to Ooty, Tea Garden. Stay at Ooty." },
            { day: "Day 2", text: "Rose Garden, Botanical Garden, Lake (Boathouse), Doddabetta Peak, Tea factory, Wax Museum. Stay at Ooty." },
            { day: "Day 3", text: "Checkout from hotel at Ooty, Pine tree forest, Tree Garden, 9th Mile Shooting spot, Pykara Waterfalls, Pykara Dam, Kamarajar Dam, Mudumalai National Park. Stay at Coorg." },
            { day: "Day 4", text: "Coorg Local sight-seeing. Stay at Coorg." },
            { day: "Day 5", text: "Checkout from hotel at Coorg, Coorg to Mysore, Rail Museum, Lalith Mahal Palace, Brindavan Gardens. Stay at Mysore." },
            { day: "Day 6", text: "Mysore Palace, Chamundeshwari Temple, Mysore Zoo. Stay at Mysore." },
            { day: "Day 7", text: "Mysore to Bangalore and drop at Bangalore Railway Station/Airport." }
          ]
        },

        "Kodaikanal - Ooty - Mysore - Bangalore": {
          hash: "kodaikanal-ooty-mysore-bangalore-7d",
              kmLimit: 1600,
          vehicles: [
            { ...VEHICLES.sedan, price: 32500 },
            { ...VEHICLES.ertiga, price: 39500 },
            { ...VEHICLES.innova, price: 44000 },
            { ...VEHICLES.crysta, price: 52000 },
            { ...VEHICLES.tt14, price: 61500 },
            { ...VEHICLES.tt18, price: 73000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
            { day: "Day 1", text: "Coimbatore to Kodaikanal. Scenic hill drive, check-in, visit Kodaikanal Lake & Coaker’s Walk. Stay at Kodaikanal." },
            { day: "Day 2", text: "Kodaikanal sightseeing. Pillar Rocks, Bryant Park, Green Valley View, Kurinji Andavar Temple, Silver Cascade Falls, Guna Cave, Pine Forest. Stay at Kodaikanal." },
            { day: "Day 3", text: "Kodaikanal to Coonoor & Ooty. Visit Sim’s Park, Lamb’s Rock, Dolphin’s Nose, Tea Gardens, then transfer to Ooty and check-in. Stay at Ooty." },
            { day: "Day 4", text: "Ooty sightseeing. Botanical Garden, Rose Garden, Ooty Lake (Boathouse), Thread Garden, Doddabetta Peak, Tea Factory & Museum, Wax Museum. Stay at Ooty." },
            { day: "Day 5", text: "Ooty to Mysore via Pykara. Visit Pykara Lake, Pykara Falls, drive via Mudumalai & Bandipur forest route, check-in. Stay at Mysore." },
            { day: "Day 6", text: "Mysore sightseeing. Mysore Palace, Chamundi Hills, Mysore Zoo, Brindavan Gardens, St. Philomena’s Church. Stay at Mysore." },
            { day: "Day 7", text: "Mysore to Drop. Optional sightseeing / shopping and drop at Bangalore / Coimbatore." }
          ]
        },



        "Munnar - Thekkady - Alleppey - Varkala - Kovalam": {
          hash: "munnar-thekkady-varkala-alleppey-kovalam-7d",
            kmLimit: 1500,
          vehicles: [
            { ...VEHICLES.sedan, price: 31000 },
            { ...VEHICLES.ertiga, price: 37500 },
            { ...VEHICLES.innova, price: 42000 },
            { ...VEHICLES.crysta, price: 50000 },
            { ...VEHICLES.tt14, price: 56000 },
            { ...VEHICLES.tt18, price: 67000 },
            { ...VEHICLES.urbania, price: null },
            { ...VEHICLES.coach, price: null }
          ],
          itinerary: [
      { day: "Day 1", text: "Coimbatore to Munnar. Scenic hill drive, visit Lakkam Waterfalls, Eravikulam National Park, check-in and relax. Stay at Munnar." },
      { day: "Day 2", text: "Munnar sightseeing. Mattupetty Dam, Echo Point, Kundala Lake, Tea Museum, Top Station (based on time). Stay at Munnar." },
      { day: "Day 3", text: "Munnar to Thekkady. Visit Periyar Wildlife Sanctuary (optional boat safari), Spice Plantation, evening cultural shows (optional), check-in. Stay at Thekkady." },
      { day: "Day 4", text: "Thekkady to Alleppey. Houseboat check-in, backwater cruise with meals and overnight stay in houseboat. Stay at Alleppey Houseboat." },
      { day: "Day 5", text: "Alleppey to Varkala. Visit Varkala Beach, Cliff, Janardanaswamy Temple and relax. Stay at Varkala." },
      { day: "Day 6", text: "Varkala to Kovalam. Visit Kovalam Beach, Lighthouse Beach and leisure time. Stay at Kovalam." },
      { day: "Day 7", text: "Trivandrum sightseeing. Visit Padmanabhaswamy Temple, Napier Museum (based on time) and drop at Trivandrum / Coimbatore." }
    ]
        }

      }
    }
  };


  window.updateAccommodationVisibility = updateAccommodationVisibility;
window.updateHotelFields = updateHotelFields;
window.renderTariffTable = renderTariffTable;


  const destinationSidebar = document.getElementById("destinationSidebar");
  const packageTabs = document.querySelectorAll(".package-tab");
  const accommodationSelect = document.getElementById("accommodationSelect");
  const roomTypeSelect = document.getElementById("roomTypeSelect");
  const occupancySelect = document.getElementById("occupancySelect");
  const roomCountSelect = document.getElementById("roomCountSelect");
  const tariffTableBody = document.getElementById("tariffTableBody");
  const packageHeading = document.getElementById("packageHeading");
  const packageSubheading = document.getElementById("packageSubheading");
  const routeLine = document.getElementById("routeLine");
  const itineraryTitle = document.getElementById("itineraryTitle");
  const itineraryContent = document.getElementById("itineraryContent");
  const tariffSection = document.getElementById("tariffSection");

  const bookingSummary = document.getElementById("bookingSummary");
  const bookingPopupForm = document.getElementById("bookingPopupForm");
  const bookingModalEl = document.getElementById("bookingModal");
  const bookingModal = bookingModalEl ? new bootstrap.Modal(bookingModalEl) : null;

  const paymentModalEl = document.getElementById("paymentModal");
  const paymentModal = paymentModalEl ? new bootstrap.Modal(paymentModalEl) : null;
  const paymentSummaryBox = document.getElementById("paymentSummaryBox");
  const paymentOptionNote = document.getElementById("paymentOptionNote");

  const enquireWhatsappBtn = document.getElementById("enquireWhatsappBtn");
  const bookNowZeroBtn = document.getElementById("bookNowZeroBtn");
  const payOnlineBtn = document.getElementById("payOnlineBtn");
  const advancePaymentBtn = document.getElementById("advancePaymentBtn");
  const fullPaymentBtn = document.getElementById("fullPaymentBtn");
  const backToBookingBtn = document.getElementById("backToBookingBtn");

  const roomTypeField = document.getElementById("roomTypeField");
  const occupancyField = document.getElementById("occupancyField");
  const roomCountField = document.getElementById("roomCountField");
  const packageTabsRow = document.getElementById("packageTabsRow");
  const scrollLeftBtn = document.getElementById("scrollLeftBtn");
  const scrollRightBtn = document.getElementById("scrollRightBtn");
  const floatingBtns = document.getElementById("floatingBtns");

  let activePackage = "1D";
  let selectedDestinationName = "";
  let selectedBooking = null;
  let customerFormData = null;
  let savedBookingId = "";
  let withHotel = false;
  window.withHotel = false;

  function sanitizeText(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatCurrency(value) {
    if (value === null || value === undefined || value === "") return "On Request";
    return "₹ " + Number(value).toLocaleString("en-IN");
  }

  function setMinDateTime() {
    const dateInput = document.getElementById("customerDateTime");
    if (!dateInput) return;

    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    dateInput.min = now.toISOString().slice(0, 16);
  }

  function formatDateTimeAMPM(inputValue) {
    const d = new Date(inputValue);
    if (isNaN(d)) return inputValue;

    const day = String(d.getDate()).padStart(2, "0");
    const month = d.toLocaleString("en-GB", { month: "short" });
    const year = d.getFullYear();

    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;

    return `${day} ${month} ${year}, ${hours}:${minutes} ${ampm}`;
  }

  function showThankYouPopup() {
    alert("Thanks for contacting Bharathiyar Tours and Travels. Our concern team will contact you.");
  }

  function getCurrentPackageConfig() {
    return packageData[activePackage] || null;
  }

  function getCurrentDestinationConfig() {
    const pkg = getCurrentPackageConfig();
    if (!pkg || !pkg.destinations) return null;
    return pkg.destinations[selectedDestinationName] || null;
  }

  function isHotelSelected() {
    return window.withHotel === true;
  }

  function getPackageNights() {
    const match = String(activePackage || "").match(/^(\d+)D$/i);
    if (!match) return 0;
    const days = Number(match[1]);
    return days > 1 ? days - 1 : 0;
  }

  function getHotelCharge() {
    if (!isHotelSelected()) return 0;

    const roomType = roomTypeSelect?.value || "2star";
    const occupancy = occupancySelect?.value || "double";
    const roomCount = Number(roomCountSelect?.value || 1);
    const nights = getPackageNights();
    const roomRate = HOTEL_RATES?.[roomType]?.[occupancy] || 0;

    return roomRate * roomCount * nights;
  }

  function getRouteLineText(destinationName) {
    if (!destinationName) return "Coimbatore - Destination - Coimbatore";
    return `Coimbatore - ${destinationName} - Coimbatore`;
  }

  function findByHash(hash) {
    const cleanHash = String(hash || "").replace(/^#/, "").trim().toLowerCase();
    if (!cleanHash) return null;

    for (const [pkgKey, pkgValue] of Object.entries(packageData)) {
      const destinations = pkgValue?.destinations || {};
      for (const [destinationName, destinationData] of Object.entries(destinations)) {
        if ((destinationData?.hash || "").toLowerCase() === cleanHash) {
          return { pkgKey, destinationName, destinationData };
        }
      }
    }
    return null;
  }

  function updateAccommodationVisibility() {
    const accommodationFields = document.getElementById("accommodationFields");
    if (!accommodationFields) return;

    // Hide only for 1 Day
    if (activePackage === "1D") {
      accommodationFields.style.display = "none";

      withHotel = false;
const btnNoHotel = document.getElementById("btnNoHotel");
const btnYesHotel = document.getElementById("btnYesHotel");
if (btnNoHotel) btnNoHotel.classList.add("active");
if (btnYesHotel) btnYesHotel.classList.remove("active");
      if (roomTypeSelect) roomTypeSelect.value = "2star";
      if (occupancySelect) occupancySelect.value = "double";
      if (roomCountSelect) roomCountSelect.value = "1";

      [roomTypeField, occupancyField, roomCountField].forEach(field => {
        if (!field) return;
        field.classList.remove("show-hotel-field");
      });

      return;
    }

    // Show again for 2D and above
    accommodationFields.style.display = "";

    const showHotel = isHotelSelected();

    [roomTypeField, occupancyField, roomCountField].forEach(field => {
      if (!field) return;

      if (showHotel) {
        field.classList.add("show-hotel-field");
      } else {
        field.classList.remove("show-hotel-field");
      }
    });
  }

  function updateHotelFields() {
    if (!isHotelSelected()) {
      if (roomTypeSelect) roomTypeSelect.value = "2star";
      if (occupancySelect) occupancySelect.value = "double";
      if (roomCountSelect) roomCountSelect.value = "1";
    }
  }

  function updateActiveTabUI() {
    packageTabs.forEach(tab => {
      tab.classList.toggle("active", tab.dataset.package === activePackage);
    });
  }

  function updatePageHeading() {
    const pkg = getCurrentPackageConfig();
    const destination = getCurrentDestinationConfig();

    if (packageHeading) {
      packageHeading.textContent = pkg?.title || "Tour Packages";
    }

    if (packageSubheading) {
      packageSubheading.textContent = pkg?.subtitle || "Select your destination";
    }

    if (routeLine) {
      routeLine.textContent = getRouteLineText(selectedDestinationName);
    }

    if (itineraryTitle) {
      itineraryTitle.textContent = destination ? `${selectedDestinationName} Itinerary` : "Itinerary";
    }
  }

  function updateHash(hash) {
    if (!hash) return;
    const current = window.location.hash.replace(/^#/, "");
    if (current === hash) return;
    history.replaceState(null, "", `#${hash}`);
  }

  function populateDestinations(preferredDestinationName = "") {
    const pkg = getCurrentPackageConfig();
    if (!pkg || !destinationSidebar) return;

    updateActiveTabUI();

    const destinationNames = Object.keys(pkg.destinations || {});
    if (!destinationNames.length) {
      destinationSidebar.innerHTML = `<div class="text-muted">No destinations available.</div>`;
      return;
    }

    if (preferredDestinationName && pkg.destinations[preferredDestinationName]) {
      selectedDestinationName = preferredDestinationName;
    } else if (!pkg.destinations[selectedDestinationName]) {
      selectedDestinationName = destinationNames[0];
    }

    destinationSidebar.innerHTML = destinationNames.map(name => {
      const activeClass = name === selectedDestinationName ? "active" : "";
      return `
        <button type="button" class="tour-destination-btn ${activeClass}" data-destination="${sanitizeText(name)}">
          ${sanitizeText(name)}
        </button>
      `;
    }).join("");

    destinationSidebar.querySelectorAll(".tour-destination-btn").forEach(btn => {
      btn.addEventListener("click", function () {
        selectedDestinationName = this.dataset.destination;
        populateDestinations(selectedDestinationName);
        renderTariffTable();
        renderItinerary();
        updatePageHeading();

        setTimeout(() => {
          const section = document.getElementById("tariffSection");
          if (section) {
            const y = section.getBoundingClientRect().top + window.scrollY - 90;
            window.scrollTo({ top: y, behavior: "smooth" });
          }
        }, 50);
      });
    });

    updatePageHeading();

    const destination = getCurrentDestinationConfig();
    if (destination?.hash) {
      updateHash(destination.hash);
    }
  }

  function renderTariffTable() {
    const pkg = getCurrentPackageConfig();
    const destination = getCurrentDestinationConfig();

    if (!pkg || !destination || !tariffTableBody) {
      tariffTableBody.innerHTML = `
        <tr>
          <td colspan="3" class="text-center py-4">No tariffs available.</td>
        </tr>
      `;
      return;
    }

    const hotelSelected = isHotelSelected();
    const hotelCharge = getHotelCharge();

    tariffTableBody.innerHTML = destination.vehicles.map(vehicle => {
      const baseFare = vehicle.price;
      const totalFare = baseFare === null ? null : Number(baseFare) + hotelCharge;

      const bookingData = {
        packageTitle: pkg.title || "",
        packageCode: activePackage,
        destination: selectedDestinationName,
        destinationHash: destination.hash || "",
        vehicle: `${vehicle.name} - ${vehicle.type}`,
        vehicleName: vehicle.name,
        vehicleType: vehicle.type,
        tariff: totalFare,
        kmLimit: destination.kmLimit || pkg.kmLimit || "",
        withHotel: hotelSelected,
        roomType: hotelSelected ? (roomTypeSelect?.selectedOptions?.[0]?.text || roomTypeSelect?.value || "") : "",
        occupancy: hotelSelected ? (occupancySelect?.selectedOptions?.[0]?.text || occupancySelect?.value || "") : "",
        roomCount: hotelSelected ? Number(roomCountSelect?.value || 1) : 0,
        hotelCharge: hotelCharge
      };

      const encodedPayload = encodeURIComponent(JSON.stringify(bookingData));

      return `
        <tr>
          <td>
            <div class="vehicle-name">${sanitizeText(vehicle.name)}</div>
            <div class="vehicle-type">${sanitizeText(vehicle.type)}</div>
          </td>
          <td>
            ${
              totalFare === null
                ? `<div class="dynamic-tariff base-rate">On Request</div>`
                : `<div class="dynamic-tariff base-rate">${formatCurrency(totalFare)}</div>`
            }
          </td>
          <td>
            ${
              totalFare === null
                ? `<button type="button" class="btn btn-sm btn-dark" onclick="window.location.href='tel:+${CALL_NUMBER}'">Call Us</button>`
                : `<button type="button" class="btn-book-table" data-booking="${encodedPayload}">BOOK NOW</button>`
            }
          </td>
        </tr>
      `;
    }).join("");

    tariffTableBody.querySelectorAll(".btn-book-table").forEach(btn => {
      btn.addEventListener("click", function () {
        try {
          const payload = JSON.parse(decodeURIComponent(this.dataset.booking || ""));
          openBookingModal(payload);
        } catch (err) {
          alert("Unable to open booking modal.");
        }
      });
    });
  }

  function renderItinerary() {
    const destination = getCurrentDestinationConfig();

    if (!destination || !itineraryContent) {
      itineraryContent.innerHTML = `
        <tr>
          <td colspan="2">No itinerary available.</td>
        </tr>
      `;
      return;
    }

    const itinerary = destination.itinerary || [];
    if (!itinerary.length) {
      itineraryContent.innerHTML = `
        <tr>
          <td colspan="2">No itinerary available.</td>
        </tr>
      `;
      return;
    }

    itineraryContent.innerHTML = itinerary.map(item => `
      <tr>
        <td>${sanitizeText(item.day || "")}</td>
        <td>${sanitizeText(item.text || "")}</td>
      </tr>
    `).join("");
  }

  function openBookingModal(bookingData) {
    selectedBooking = bookingData;
    customerFormData = null;
    savedBookingId = "";

    if (!bookingSummary || !bookingPopupForm) return;

    bookingSummary.innerHTML = `
      <div><span>Package</span><span>${sanitizeText(selectedBooking.packageTitle)}</span></div>
      <div><span>Destination</span><span>${sanitizeText(selectedBooking.destination)}</span></div>
      <div><span>Vehicle</span><span>${sanitizeText(selectedBooking.vehicle)}</span></div>
      <div><span>KM Limit</span><span>${sanitizeText(selectedBooking.kmLimit)} KM</span></div>
      <div><span>Total Tariff</span><span>${formatCurrency(selectedBooking.tariff)}</span></div>
      ${
        selectedBooking.withHotel
          ? `<div><span>Accommodation</span><span>${sanitizeText(selectedBooking.roomType)}, ${sanitizeText(selectedBooking.occupancy)}, ${selectedBooking.roomCount} Room${selectedBooking.roomCount > 1 ? "s" : ""}</span></div>`
          : `<div><span>Accommodation</span><span>Without Hotel</span></div>`
      }
    `;

    bookingPopupForm.reset();
    setMinDateTime();

    if (bookingModal) bookingModal.show();
  }

  function validateCustomerForm() {
    const name = document.getElementById("customerName")?.value.trim();
    const phone = document.getElementById("customerPhone")?.value.trim();
    const dateTime = document.getElementById("customerDateTime")?.value;
    const pickup = document.getElementById("customerPickup")?.value.trim();

    if (!selectedBooking) {
      alert("Please select a package first.");
      return null;
    }

    if (!name || !phone || !dateTime || !pickup) {
      alert("Please fill all fields.");
      return null;
    }

    if (!/^[0-9]{10}$/.test(phone)) {
      alert("Please enter a valid 10-digit phone number.");
      return null;
    }

    const selectedDate = new Date(dateTime);
    if (selectedDate < new Date()) {
      alert("Old date and time cannot be selected.");
      return null;
    }

    return { name, phone, dateTime, pickup };
  }

  async function postToAppsScript(action, payload) {
    const response = await fetch(APPS_SCRIPT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "text/plain;charset=utf-8"
      },
      body: JSON.stringify({ action, payload })
    });

    const text = await response.text();
    let data = {};

    try {
      data = JSON.parse(text);
    } catch (e) {
      throw new Error("Invalid server response");
    }

    if (data.status !== "success") {
      throw new Error(data.message || "Request failed");
    }

    return data;
  }

  async function saveBookingToSheet(paymentTypeValue = "") {
    if (!selectedBooking || !customerFormData) {
      throw new Error("Booking data missing");
    }

    const payload = {
      packageTitle: selectedBooking.packageTitle,
      destination: selectedBooking.destination,
      vehicle: selectedBooking.vehicle,
      tariff: selectedBooking.tariff,
      withHotel: selectedBooking.withHotel,
      roomType: selectedBooking.roomType,
      occupancy: selectedBooking.occupancy,
      roomCount: selectedBooking.roomCount,
      hotelCharge: selectedBooking.hotelCharge || 0,
      kmLimit: selectedBooking.kmLimit || "",
      packageCode: selectedBooking.packageCode || "",
      customerName: customerFormData.name,
      customerPhone: customerFormData.phone,
      travelDate: formatDateTimeAMPM(customerFormData.dateTime),
      pickup: customerFormData.pickup,
      paymentType: paymentTypeValue,
      sourcePage: window.location.href
    };

    const result = await postToAppsScript("saveBooking", payload);
    savedBookingId = result.bookingId || "";
    return result;
  }

  function getAdvanceConfig() {
    const withHotel = !!selectedBooking?.withHotel;

    if (withHotel) {
      return {
        type: "ADVANCE_50",
        label: "Pay Advance 50%",
        amount: Math.round(Number(selectedBooking.tariff || 0) * 0.50)
      };
    }

    return {
      type: "ADVANCE_10",
      label: "Pay Advance 10%",
      amount: Math.round(Number(selectedBooking.tariff || 0) * 0.10)
    };
  }

  function fillPaymentSummary() {
    if (!paymentSummaryBox || !selectedBooking) return;

    const advance = getAdvanceConfig();
    const total = Number(selectedBooking.tariff || 0);

    paymentSummaryBox.innerHTML = `
      <div><span>Booking ID</span><span>${sanitizeText(savedBookingId || "-")}</span></div>
      <div><span>Package</span><span>${sanitizeText(selectedBooking.packageTitle)}</span></div>
      <div><span>Destination</span><span>${sanitizeText(selectedBooking.destination)}</span></div>
      <div><span>Vehicle</span><span>${sanitizeText(selectedBooking.vehicleName || selectedBooking.vehicle)}</span></div>
      <div><span>Total Tariff</span><span>${formatCurrency(total)}</span></div>
      <div><span>KM Limit</span><span>${sanitizeText(selectedBooking.kmLimit)} KM</span></div>
      ${
        selectedBooking.withHotel
          ? `<div><span>Hotel Charge</span><span>${formatCurrency(selectedBooking.hotelCharge)}</span></div>`
          : ``
      }
    `;

    if (paymentOptionNote) {
      paymentOptionNote.innerHTML = "";
      paymentOptionNote.style.display = "none";
    }

    if (advancePaymentBtn) {
      advancePaymentBtn.textContent = `${advance.label} - ${formatCurrency(advance.amount)}`;
    }

    if (fullPaymentBtn) {
      fullPaymentBtn.textContent = `Pay Full - ${formatCurrency(total)}`;
    }
  }

  function buildWhatsAppBookingMessage(data) {
    const url =
      window.location.href.split("#")[0] +
      (getCurrentDestinationConfig()?.hash ? `#${getCurrentDestinationConfig().hash}` : "");

    return `✨ *BHARATHIYAR TOURS & TRAVELS*
  ━━━━━━━━━━━━━━━━━
  📦 *PACKAGE DETAILS*
  ━━━━━━━━━━━━━━━━━
  📍 Destination: ${selectedBooking?.destination || ""}
  🗺️ Package: ${selectedBooking?.packageTitle || ""}
  🚘 Vehicle: ${selectedBooking?.vehicle || ""}
  💰 Tariff: ${formatCurrency(selectedBooking?.tariff || 0)}
  📏 KM Limit: ${selectedBooking?.kmLimit || ""} KM

  🏨 *Accommodation:*
  ${
    selectedBooking?.withHotel
      ? `✔ ${selectedBooking.roomType}
  ✔ ${selectedBooking.occupancy}
  ✔ ${selectedBooking.roomCount} Room${selectedBooking.roomCount > 1 ? "s" : ""}`
      : "❌ Without Hotel"
  }

  ━━━━━━━━━━━━━━━━━
  👤 *CUSTOMER DETAILS*
  ━━━━━━━━━━━━━━━━━
  🧑 Name: ${data?.name || ""}
  📞 Phone: ${data?.phone || ""}
  🗓️ Pickup: ${data?.dateTime ? formatDateTimeAMPM(data.dateTime) : ""}
  📍 Location: ${data?.pickup || ""}

  ━━━━━━━━━━━━━━━━━
  🙏 Kindly confirm availability & pricing.
  Thank you! 😊`;
  }

  function buildReceiptPayload(paymentInfo) {
    const total = Number(selectedBooking?.tariff || 0);
    const paid = Number(paymentInfo?.paidAmount || 0);

    return {
      receiptTitle: paymentInfo.paymentType === "FULL" ? "FULL PAYMENT RECEIPT" : "ADVANCE PAYMENT RECEIPT",
      paymentStatus: paymentInfo.paymentType === "FULL" ? "FULL PAYMENT RECEIVED" : "ADVANCE RECEIVED",
      quoteNo: savedBookingId,
      date: new Date().toLocaleDateString("en-GB"),
      customerName: customerFormData?.name,
      customerPhone: customerFormData?.phone,
      pickup: customerFormData?.pickup,
      drop: selectedBooking?.destination,
      vehicle: selectedBooking?.vehicle,
      packageTitle: selectedBooking?.packageTitle,
      packageCode: selectedBooking?.packageCode,
      kmLimit: selectedBooking?.kmLimit,
      travelDate: formatDateTimeAMPM(customerFormData?.dateTime),
      totalTariff: total,
      paidAmount: paid,
      pendingAmount: total - paid,
      paymentId: paymentInfo.paymentId,
      paymentType: paymentInfo.paymentType,
      terms: [
        "Driver details will be assigned before journey.",
        "Balance to be paid during trip.",
        "Extra km will be charged.",
        "Cancellation charges apply."
      ]
    };
  }

  function goToReceiptPage(paymentInfo) {
    const data = buildReceiptPayload(paymentInfo);
    sessionStorage.setItem("btt_receipt_data", JSON.stringify(data));
    window.location.href = "receipt-success.html";
  }

  async function startPayment(paymentType) {
    if (!selectedBooking || !customerFormData || !savedBookingId) {
      throw new Error("Booking is incomplete");
    }

    const createOrderResult = await postToAppsScript("createOrder", {
      bookingId: savedBookingId,
      tariff: Number(selectedBooking.tariff || 0),
      withHotel: !!selectedBooking.withHotel,
      paymentType: paymentType
    });

    if (!createOrderResult.orderId) {
      throw new Error("Failed to create order");
    }

    const options = {
      key: createOrderResult.key,
      amount: Number(createOrderResult.amount || 0) * 100,
      currency: createOrderResult.currency || "INR",
      name: "BHARATHIYAR TOURS AND TRAVELS",
      description: `${paymentType === "FULL" ? "Full Payment" : "Advance Payment"} - ${selectedBooking.packageTitle}`,
      order_id: createOrderResult.orderId,
      handler: async function (response) {
        try {
          await postToAppsScript("verifyPayment", {
            bookingId: savedBookingId,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
            paymentType: paymentType,
            amount: Number(createOrderResult.amount || 0)
          });

          if (paymentModal) paymentModal.hide();
          if (bookingModal) bookingModal.hide();

          goToReceiptPage({
    paymentType: paymentType,
    paymentId: response.razorpay_payment_id,
    paidAmount: Number(createOrderResult.amount || 0)
  });
        } catch (err) {
          alert(err.message || "Payment verified, but final step failed.");
        } finally {
          resetPaymentButtons();
        }
      },
      modal: {
        ondismiss: function () {
          resetPaymentButtons();
        }
      },
      prefill: {
        name: customerFormData?.name || "",
        contact: customerFormData?.phone || ""
      },
      theme: {
        color: "#111111"
      }
    };

    const rzp = new Razorpay(options);

    rzp.on("payment.failed", function (resp) {
      resetPaymentButtons();
      alert(resp?.error?.description || "Payment failed");
    });

    rzp.open();
  }

  function resetMainButtons() {
    if (enquireWhatsappBtn) {
      enquireWhatsappBtn.disabled = false;
      enquireWhatsappBtn.innerHTML = `<i class="bi bi-whatsapp me-2"></i>Enquire on WhatsApp`;
    }

    if (bookNowZeroBtn) {
      bookNowZeroBtn.disabled = false;
      bookNowZeroBtn.textContent = "Book Now @ ₹0";
    }

    if (payOnlineBtn) {
      payOnlineBtn.disabled = false;
      payOnlineBtn.innerHTML = `<i class="bi bi-credit-card me-2"></i>Pay Online`;
    }
  }

  function resetPaymentButtons() {
    if (!advancePaymentBtn || !fullPaymentBtn) return;

    advancePaymentBtn.disabled = false;
    fullPaymentBtn.disabled = false;

    const advance = getAdvanceConfig();
    const total = Number(selectedBooking?.tariff || 0);

    advancePaymentBtn.textContent = `${advance.label} - ${formatCurrency(advance.amount)}`;
    fullPaymentBtn.textContent = `Pay Full - ${formatCurrency(total)}`;
  }

  if (bookingPopupForm) {
    bookingPopupForm.addEventListener("submit", function (e) {
      e.preventDefault();
    });
  }

  if (enquireWhatsappBtn) {
    enquireWhatsappBtn.addEventListener("click", async function () {
      try {
        customerFormData = validateCustomerForm();
        if (!customerFormData) return;

        enquireWhatsappBtn.disabled = true;
        enquireWhatsappBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Please wait...`;

        const message = buildWhatsAppBookingMessage(customerFormData);
        const whatsappUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;

        window.open(whatsappUrl, "_blank");
        showThankYouPopup();
      } catch (err) {
        alert(err.message || "Failed to continue to WhatsApp");
      } finally {
        resetMainButtons();
      }
    });
  }

  if (bookNowZeroBtn) {
    bookNowZeroBtn.addEventListener("click", async function () {
      try {
        customerFormData = validateCustomerForm();
        if (!customerFormData) return;

        bookNowZeroBtn.disabled = true;
        bookNowZeroBtn.textContent = "Please wait...";

        await saveBookingToSheet("BOOK_NOW_ZERO");
        showThankYouPopup();

        if (bookingModal) bookingModal.hide();
        if (bookingPopupForm) bookingPopupForm.reset();
      } catch (err) {
        alert(err.message || "Failed to save booking");
      } finally {
        resetMainButtons();
      }
    });
  }

  if (payOnlineBtn) {
    payOnlineBtn.addEventListener("click", async function () {
      try {
        customerFormData = validateCustomerForm();
        if (!customerFormData) return;

        payOnlineBtn.disabled = true;
        payOnlineBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Please wait...`;

        await saveBookingToSheet("PAY_ONLINE");
        fillPaymentSummary();

        if (bookingModal) bookingModal.hide();
        if (paymentModal) paymentModal.show();
      } catch (err) {
        alert(err.message || "Failed to continue to payment");
      } finally {
        resetMainButtons();
      }
    });
  }

  if (backToBookingBtn) {
    backToBookingBtn.addEventListener("click", function () {
      if (paymentModal) paymentModal.hide();
      if (bookingModal) bookingModal.show();
    });
  }

  if (advancePaymentBtn) {
    advancePaymentBtn.addEventListener("click", async function () {
      try {
        advancePaymentBtn.disabled = true;
        fullPaymentBtn.disabled = true;
        advancePaymentBtn.textContent = "Please wait...";
        await startPayment(getAdvanceConfig().type);
      } catch (err) {
        alert(err.message || "Unable to start payment");
        resetPaymentButtons();
      }
    });
  }

  if (fullPaymentBtn) {
    fullPaymentBtn.addEventListener("click", async function () {
      try {
        advancePaymentBtn.disabled = true;
        fullPaymentBtn.disabled = true;
        fullPaymentBtn.textContent = "Please wait...";
        await startPayment("FULL");
      } catch (err) {
        alert(err.message || "Unable to start payment");
        resetPaymentButtons();
      }
    });
  }

  const phoneInput = document.getElementById("customerPhone");
  if (phoneInput) {
    phoneInput.addEventListener("input", function () {
      this.value = this.value.replace(/\D/g, "").slice(0, 10);
    });
  }

  function syncFloatingButtons(show) {
    if (!floatingBtns) return;
    floatingBtns.style.display = show ? "flex" : "none";
  }

  if (bookingModalEl) {
    bookingModalEl.addEventListener("shown.bs.modal", function () {
      document.body.classList.add("modal-open-custom");
      syncFloatingButtons(false);
    });

    bookingModalEl.addEventListener("hidden.bs.modal", function () {
      document.body.classList.remove("modal-open-custom");
      if (!paymentModalEl || !paymentModalEl.classList.contains("show")) {
        syncFloatingButtons(true);
      }
    });
  }

  if (paymentModalEl) {
    paymentModalEl.addEventListener("shown.bs.modal", function () {
      syncFloatingButtons(false);
    });

    paymentModalEl.addEventListener("hidden.bs.modal", function () {
      if (!bookingModalEl || !bookingModalEl.classList.contains("show")) {
        syncFloatingButtons(true);
      }
    });
  }

  function applyHashSelection() {
    const found = findByHash(window.location.hash);
    if (!found) return false;

    activePackage = found.pkgKey;
    selectedDestinationName = found.destinationName;

    updateAccommodationVisibility();
    updateHotelFields();
    populateDestinations(selectedDestinationName);
    renderTariffTable();
    renderItinerary();
    updatePageHeading();

    setTimeout(() => {
      const section = document.getElementById("tariffSection");
      if (section) {
        const y = section.getBoundingClientRect().top + window.scrollY - 90;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    }, 80);

    return true;
  }

  packageTabs.forEach(tab => {
    tab.addEventListener("click", function () {
      const pkg = this.dataset.package;
      if (!packageData[pkg]) return;

      activePackage = pkg;
      selectedDestinationName = "";

      updateAccommodationVisibility();
      updateHotelFields();
      populateDestinations();
      renderTariffTable();
      renderItinerary();
      updatePageHeading();

      if (packageTabsRow) {
        this.scrollIntoView({
          behavior: "smooth",
          inline: "center",
          block: "nearest"
        });
      }
    });
  });

  if (accommodationSelect) {
    accommodationSelect.addEventListener("change", function () {
      updateAccommodationVisibility();
      updateHotelFields();
      renderTariffTable();
    });
  }

  if (roomTypeSelect) {
    roomTypeSelect.addEventListener("change", function () {
      renderTariffTable();
    });
  }

  if (occupancySelect) {
    occupancySelect.addEventListener("change", function () {
      renderTariffTable();
    });
  }

  if (roomCountSelect) {
    roomCountSelect.addEventListener("change", function () {
      renderTariffTable();
    });
  }

  if (scrollLeftBtn && packageTabsRow) {
    scrollLeftBtn.addEventListener("click", function () {
      packageTabsRow.scrollBy({ left: -220, behavior: "smooth" });
    });
  }

  if (scrollRightBtn && packageTabsRow) {
    scrollRightBtn.addEventListener("click", function () {
      packageTabsRow.scrollBy({ left: 220, behavior: "smooth" });
    });
  }

  updateAccommodationVisibility();
  updateHotelFields();

  if (!applyHashSelection()) {
    populateDestinations();
    renderTariffTable();
    renderItinerary();
    updatePageHeading();
  }

  window.addEventListener("hashchange", function () {
    applyHashSelection();
  });
});
