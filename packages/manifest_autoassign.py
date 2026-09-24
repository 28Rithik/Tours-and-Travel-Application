"""
manifest_autoassign.py
======================
Auto-Assignment Engine for Siva Gayathri Tours & Travels
=========================================================

Logic Rules (matching real-world College IV practice):
- Faculty     -> Distributed EQUALLY across ALL buses (1-2 per bus)
                 so every bus has a supervising staff member.
- All students -> MIXED buses (boys & girls travel together, by roll number)
- Rooms        -> Gender-separated: Boys Room M101+, Girls Room F201+,
                  Faculty Twin Room F01+ (Male) / F51+ (Female)
- Room sharing -> 4-per-room for students, 2-per-room (twin) for faculty
"""

import math
from .models import TourPassengerManifest, CollegeIVExpedition


def auto_assign_for_expedition(iv_expedition_id: int, seats_per_bus: int = 50, students_per_room: int = 4) -> dict:
    """
    Auto-assign Bus, Seat Numbers, and Room Allocation for all passengers
    in a given CollegeIVExpedition.

    Faculty      : Spread equally across all buses — every bus gets at least
                   one faculty supervisor. Faculty sit in seat 01A/01B/02A...
                   at the front of each bus.
    Students     : Fill remaining seats in roll-number order (mixed gender).
    Room Alloc   : Boys → Room M101+, Girls → Room F201+, Faculty → Room F01+ (twin).
    """
    try:
        expedition = CollegeIVExpedition.objects.get(pk=iv_expedition_id)
    except CollegeIVExpedition.DoesNotExist:
        return {'error': f'CollegeIVExpedition #{iv_expedition_id} not found.'}

    passengers = list(
        TourPassengerManifest.objects
        .filter(iv_expedition=expedition)
        .order_by('category', 'roll_number', 'passenger_name')
    )

    if not passengers:
        return {'error': 'No passengers found for this expedition. Please import the manifest first.'}

    faculty         = [p for p in passengers if p.category == 'faculty']
    male_students   = [p for p in passengers if p.category != 'faculty' and p.gender != 'female']
    female_students = [p for p in passengers if p.category != 'faculty' and p.gender == 'female']

    # Mixed student list — sorted by roll number so classmates sit near each other
    all_students = sorted(
        male_students + female_students,
        key=lambda p: (p.roll_number or '', p.passenger_name)
    )

    total_students = len(all_students)
    n_faculty      = len(faculty)

    # ── Calculate total buses needed ──────────────────────────────────────────
    # Each bus has seats_per_bus seats total.
    # We spread faculty across buses (1-2 per bus), students fill the rest.
    # Simple approach: calculate buses based on total passengers.
    total_pax    = total_students + n_faculty
    n_buses      = max(1, math.ceil(total_pax / seats_per_bus))

    # Faculty per bus (rounded up so every bus gets at least 1 if possible)
    faculty_per_bus = n_faculty / n_buses  # may be fractional — distribute round-robin

    # ── Build per-bus layout ──────────────────────────────────────────────────
    # bus_layout[i] = list of seats in bus i+1  (faculty first, then students)
    # We assign faculty to buses round-robin so it's as equal as possible.

    # Step 1: Assign faculty to buses
    for i, f in enumerate(faculty):
        bus_num = (i % n_buses) + 1          # round-robin: bus 1, 2, 3... wrap
        f.bus_assignment = f"Bus {bus_num:02d}"

    # Step 2: Assign seat numbers to faculty within their bus
    # Track how many faculty are already placed per bus
    fac_count_per_bus = {}
    for f in faculty:
        bn = f.bus_assignment
        fac_count_per_bus[bn] = fac_count_per_bus.get(bn, 0) + 1

    fac_seat_idx_per_bus = {}   # running seat index per bus for faculty
    for f in faculty:
        bn = f.bus_assignment
        idx = fac_seat_idx_per_bus.get(bn, 0)
        pair   = (idx // 2) + 1
        letter = 'A' if (idx % 2 == 0) else 'B'
        f.seat_number = f"{pair:02d}{letter}"
        fac_seat_idx_per_bus[bn] = idx + 1

    # Faculty rooms: twin-sharing, gender-split
    male_fac_room   = 1
    female_fac_room = 51   # Female faculty rooms start at F51 to avoid clash
    male_fac_in_room   = 0
    female_fac_in_room = 0
    for f in faculty:
        if f.gender == 'female':
            f.room_sharing_number = f"Room F{female_fac_room:02d} (Twin - Faculty Female)"
            female_fac_in_room += 1
            if female_fac_in_room >= 2:
                female_fac_room    += 1
                female_fac_in_room  = 0
        else:
            f.room_sharing_number = f"Room F{male_fac_room:02d} (Twin - Faculty Male)"
            male_fac_in_room += 1
            if male_fac_in_room >= 2:
                male_fac_room    += 1
                male_fac_in_room  = 0

    # Step 3: Assign students to buses in order, skipping faculty seats
    # For each bus, track next available student seat (after faculty front seats)
    student_seat_idx_per_bus = dict(fac_seat_idx_per_bus)  # start after faculty seats
    # Students are distributed sequentially: fill Bus 01 remaining → Bus 02 → ...
    current_bus    = 1
    student_seat   = student_seat_idx_per_bus.get(f"Bus {current_bus:02d}", 0)

    male_room_num      = 101
    male_seat_in_room  = 0
    female_room_num    = 201
    female_seat_in_room = 0

    for s in all_students:
        # Advance to next bus if current bus is full
        while student_seat >= seats_per_bus:
            current_bus  += 1
            student_seat  = student_seat_idx_per_bus.get(f"Bus {current_bus:02d}", 0)

        bus_key = f"Bus {current_bus:02d}"
        s.bus_assignment = bus_key

        pair   = (student_seat // 2) + 1
        letter = 'A' if (student_seat % 2 == 0) else 'B'
        s.seat_number = f"{pair:02d}{letter}"

        student_seat += 1
        student_seat_idx_per_bus[bus_key] = student_seat

        # Room: gender-separated
        if s.gender == 'female':
            s.room_sharing_number = f"Room F{female_room_num:03d} ({students_per_room} Sharing - Girls)"
            female_seat_in_room += 1
            if female_seat_in_room >= students_per_room:
                female_room_num     += 1
                female_seat_in_room  = 0
        else:
            s.room_sharing_number = f"Room M{male_room_num:03d} ({students_per_room} Sharing - Boys)"
            male_seat_in_room += 1
            if male_seat_in_room >= students_per_room:
                male_room_num    += 1
                male_seat_in_room = 0

    # ── Bulk save ──────────────────────────────────────────────────────────────
    TourPassengerManifest.objects.bulk_update(
        passengers,
        ['bus_assignment', 'seat_number', 'room_sharing_number'],
        batch_size=100
    )

    all_buses = sorted(set(p.bus_assignment for p in passengers))

    return {
        'success': True,
        'expedition': str(expedition),
        'total_passengers': len(passengers),
        'faculty_assigned': n_faculty,
        'male_students_assigned': len(male_students),
        'female_students_assigned': len(female_students),
        'n_buses': n_buses,
        'mixed_buses': all_buses,
        'male_buses': all_buses,   # kept for backward compat
        'female_buses': [],
        'seats_per_bus': seats_per_bus,
        'students_per_room': students_per_room,
        'faculty_per_bus_approx': round(faculty_per_bus, 1),
    }
