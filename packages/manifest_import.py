import csv
import io
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TourPassengerManifest, CollegeIVExpedition, PackageInventory


@login_required
def download_manifest_template_csv(request):
    """
    Downloads a standardized CSV manifest template for Siva Gayathri Tours and Travels.
    Ready for College coordinators to fill out or paste from Google Sheets.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="siva_gayathri_manifest_template.csv"'
    response.write('\ufeff')  # UTF-8 BOM for Microsoft Excel compatibility

    writer = csv.writer(response)
    # ────────────────────────────────────────────────────────────────
    # NOTE: Bus Assignment, Seat Number & Room Allocation are NOT
    # included here — they are AUTO-ASSIGNED by the system after
    # import using the "🚌 Auto-Assign Bus, Seat & Room" admin action.
    # Coordinators only need to fill Name, Category, Gender, Roll No,
    # Age, Phone & Emergency Contact.
    # ────────────────────────────────────────────────────────────────
    writer.writerow([
        'Passenger Name',
        'Category (student/faculty)',
        'Gender (male/female)',
        'Roll Number / Register ID',
        'Age',
        'Phone Number',
        'Parent / Emergency Contact',
        'Special Assistance (yes/no)'
    ])

    # Sample rows — Faculty staff (filled by college coordinator)
    writer.writerow(['Dr. S. K. Narayanan', 'faculty', 'male',  'FAC-01', '45', '9842533777', '9438171311', 'no'])
    writer.writerow(['Dr. M. Deepa',        'faculty', 'female','FAC-02', '42', '9842533778', '9438171312', 'no'])
    # Sample rows — Students (Bus/Seat/Room will be auto-assigned)
    writer.writerow(['Aakash R',     'student', 'male',   '711522205001', '21', '9876543210', '9123456780', 'no'])
    writer.writerow(['Abinash S',    'student', 'male',   '711522205002', '21', '9876543211', '9123456781', 'no'])
    writer.writerow(['Bhavana M',    'student', 'female', '711522205051', '21', '9876543250', '9123456790', 'no'])
    writer.writerow(['Charulatha K', 'student', 'female', '711522205052', '21', '9876543251', '9123456791', 'no'])

    return response


@login_required
def upload_manifest_csv_view(request):
    """
    Renders the upload form and processes uploaded CSV files to bulk create passenger records.
    """
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        iv_id = request.POST.get('iv_expedition')
        departure_id = request.POST.get('departure_batch')
        clear_existing = request.POST.get('clear_existing') == '1'

        if not csv_file:
            messages.error(request, "⚠️ Please choose a CSV file to upload.")
            return redirect('/packages/manifest/upload/')

        if not csv_file.name.endswith(('.csv', '.txt')):
            messages.error(request, "⚠️ Invalid file format. Please upload a standard comma-separated .csv file.")
            return redirect('/packages/manifest/upload/')

        iv_obj = None
        if iv_id:
            try:
                iv_obj = CollegeIVExpedition.objects.get(pk=iv_id)
            except CollegeIVExpedition.DoesNotExist:
                pass

        departure_obj = None
        if departure_id:
            try:
                departure_obj = PackageInventory.objects.get(pk=departure_id)
            except PackageInventory.DoesNotExist:
                pass

        try:
            # Read decoded text
            file_data = csv_file.read().decode('utf-8-sig', errors='replace')
            reader = csv.reader(io.StringIO(file_data))
            header = next(reader, None)

            if not header:
                messages.error(request, "⚠️ The uploaded CSV file is empty.")
                return redirect('/packages/manifest/upload/')

            # Normalize headers
            norm_header = [h.strip().lower() for h in header]
            
            def get_col_idx(candidates):
                for cand in candidates:
                    for idx, h in enumerate(norm_header):
                        if cand in h:
                            return idx
                return None

            idx_name = get_col_idx(['passenger name', 'name', 'student name'])
            idx_cat = get_col_idx(['category'])
            idx_gender = get_col_idx(['gender', 'sex'])
            idx_roll = get_col_idx(['roll', 'register', 'reg no', 'id'])
            idx_age = get_col_idx(['age'])
            idx_bus = get_col_idx(['bus', 'coach'])
            idx_seat = get_col_idx(['seat'])
            idx_room = get_col_idx(['room', 'sharing'])
            idx_phone = get_col_idx(['phone', 'mobile', 'contact'])
            idx_emergency = get_col_idx(['emergency', 'parent'])
            idx_assist = get_col_idx(['special', 'assistance', 'senior'])

            if idx_name is None:
                messages.error(request, "⚠️ Could not find a 'Passenger Name' column in the uploaded file.")
                return redirect('/packages/manifest/upload/')

            if clear_existing:
                if iv_obj:
                    TourPassengerManifest.objects.filter(iv_expedition=iv_obj).delete()
                elif departure_obj:
                    TourPassengerManifest.objects.filter(departure=departure_obj).delete()

            passengers_to_create = []
            student_count = 0
            faculty_count = 0

            for row_num, row in enumerate(reader, start=2):
                if not row or not any(row):
                    continue
                
                name = row[idx_name].strip() if idx_name < len(row) else ''
                if not name:
                    continue

                raw_cat = row[idx_cat].strip().lower() if (idx_cat is not None and idx_cat < len(row)) else 'student'
                category = 'faculty' if 'fac' in raw_cat or 'staff' in raw_cat else 'student'

                raw_gender = row[idx_gender].strip().lower() if (idx_gender is not None and idx_gender < len(row)) else 'male'
                gender = 'female' if raw_gender.startswith('f') or 'woman' in raw_gender or 'girl' in raw_gender else 'male'

                roll = row[idx_roll].strip() if (idx_roll is not None and idx_roll < len(row)) else ''
                
                raw_age = row[idx_age].strip() if (idx_age is not None and idx_age < len(row)) else ''
                age = int(raw_age) if raw_age.isdigit() else None

                bus = row[idx_bus].strip() if (idx_bus is not None and idx_bus < len(row)) else ''
                seat = row[idx_seat].strip() if (idx_seat is not None and idx_seat < len(row)) else ''
                room = row[idx_room].strip() if (idx_room is not None and idx_room < len(row)) else ''
                phone = row[idx_phone].strip() if (idx_phone is not None and idx_phone < len(row)) else ''
                emergency = row[idx_emergency].strip() if (idx_emergency is not None and idx_emergency < len(row)) else ''
                
                raw_assist = row[idx_assist].strip().lower() if (idx_assist is not None and idx_assist < len(row)) else 'no'
                assistance = True if raw_assist in ['yes', 'true', '1', 'y'] else False

                passengers_to_create.append(
                    TourPassengerManifest(
                        iv_expedition=iv_obj,
                        departure=departure_obj,
                        passenger_name=name,
                        category=category,
                        gender=gender,
                        roll_number=roll,
                        age=age,
                        bus_assignment=bus,
                        seat_number=seat,
                        room_sharing_number=room,
                        phone=phone,
                        emergency_contact=emergency,
                        senior_assistance_needed=assistance
                    )
                )

                if category == 'faculty':
                    faculty_count += 1
                else:
                    student_count += 1

            if passengers_to_create:
                TourPassengerManifest.objects.bulk_create(passengers_to_create, batch_size=100)
                total = len(passengers_to_create)
                target_desc = f"for '{iv_obj.college_name}'" if iv_obj else "into the departure batch"
                messages.success(
                    request,
                    f"🎉 Successfully imported {total} passengers {target_desc} ({student_count} Students + {faculty_count} Faculty Staff)!"
                )
                return redirect('/admin/package_tours/passengermanifestproxy/')
            else:
                messages.warning(request, "⚠️ No valid passenger rows were found in the uploaded file.")
                return redirect('/packages/manifest/upload/')

        except Exception as e:
            messages.error(request, f"❌ Error importing CSV: {str(e)}")
            return redirect('/packages/manifest/upload/')

    # GET request: render the upload UI
    expeditions = CollegeIVExpedition.objects.all().order_by('-start_date')
    departures = PackageInventory.objects.all().order_by('-departure_date')
    selected_iv = request.GET.get('iv_id', '')

    context = {
        'expeditions': expeditions,
        'departures': departures,
        'selected_iv': selected_iv,
    }
    return render(request, 'packages/upload_manifest_modal.html', context)
