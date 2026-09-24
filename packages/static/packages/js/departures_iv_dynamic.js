/**
 * Siva Gayathri Tours & Travels — Group Tour & Departure Dynamic Automation
 * 1. Tour Bus Departure:
 *    - Vehicle Selection: Auto-fills seating capacity from Vehicle model API & suggests default driver
 *    - Package Selection: Auto-calculates return date (departure + duration_days - 1) & suggests base price
 *    - Live Seat Gauge & Revenue Badge
 *    - Date validation & form submit guard
 * 2. Group Expeditions (College IV, Corporate Offsite, School Tour, Family & Friends):
 *    - 1-Click Group Mode Selector: Adapts labels, placeholders, and rooming allocations (Quad vs Twin)
 *    - Smart Bus Sizer & Vehicle Hint: Innova, Urbania, Mini Coach, Luxury Coach Convoy
 *    - Package Selection: Auto-calculates End Date & Live Group Cost / Quotation Estimator
 *    - Faculty / Coordinator Ratio Guard
 *    - Date Gap Calculator & Form submit guard
 */

document.addEventListener('DOMContentLoaded', function () {
    var jq = window.django ? window.django.jQuery : (window.jQuery || null);
    if (!jq) return;
    var $ = jq;

    function setPill(id, text, color, afterEl) {
        $('#' + id).remove();
        if (text && afterEl && afterEl.length) {
            afterEl.after('<span id="' + id + '" class="sg-calc-pill sg-calc-' + color + '" style="margin-left:8px;">' + text + '</span>');
        }
    }

    // Helper: format YYYY-MM-DD
    function formatDate(d) {
        var year = d.getFullYear();
        var month = ('0' + (d.getMonth() + 1)).slice(-2);
        var day = ('0' + d.getDate()).slice(-2);
        return year + '-' + month + '-' + day;
    }

    // =========================================================================
    // 1. TOUR BUS DEPARTURE BATCH FORM
    // =========================================================================
    var depBatchPkgSelect   = $('#id_package');
    var assignedVehSelect   = $('#id_assigned_vehicle');
    var assignedDriverSelect= $('#id_assigned_driver');
    var totalSeatsInput     = $('#id_total_seats');
    var bookedSeatsInput    = $('#id_booked_seats');
    var availableSeatsInput = $('#id_available_seats');
    var statusSelect        = $('#id_status');
    var departureDateInput  = $('#id_departure_date');
    var returnDateInput     = $('#id_return_date');
    var priceOverrideInput  = $('#id_price_override');

    var cachedBatchPkg = null;

    if (totalSeatsInput.length && departureDateInput.length) {
        function updateSeatAvailability() {
            var total     = parseInt(totalSeatsInput.val(), 10)  || 0;
            var booked    = parseInt(bookedSeatsInput.val(), 10) || 0;
            var available = Math.max(0, total - booked);
            availableSeatsInput.val(available);
            var color, text;
            if (available === 0) {
                color = 'red';   text = 'Full / Sold Out';
                if (statusSelect.val() === 'open' || statusSelect.val() === 'fast_filling') statusSelect.val('sold_out');
            } else if (available <= 5) {
                color = 'blue';  text = 'Fast Filling - Only ' + available + ' Left!';
                if (statusSelect.val() === 'open') statusSelect.val('fast_filling');
            } else {
                color = 'green'; text = available + ' Seats Available';
            }
            setPill('seat-avail-badge', text, color, bookedSeatsInput);

            var price = parseFloat(priceOverrideInput.val()) || 0;
            if (price > 0 && booked > 0) {
                setPill('revenue-badge', 'Est. Revenue: ₹' + (price * booked).toLocaleString('en-IN'), 'purple', priceOverrideInput);
            } else {
                $('#revenue-badge').remove();
            }
        }

        totalSeatsInput.on('input change', updateSeatAvailability);
        bookedSeatsInput.on('input change', updateSeatAvailability);
        priceOverrideInput.on('input change', updateSeatAvailability);
        updateSeatAvailability();

        // 1.1 Vehicle Selection -> Auto-Fill Seating Capacity & Driver
        function onVehicleChange() {
            var vehId = assignedVehSelect.val();
            if (!vehId) {
                $('#veh-cap-pill').remove();
                return;
            }
            $.ajax({
                url: '/packages/api/vehicle/' + vehId + '/info/',
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    if (data.success && data.seating_capacity) {
                        totalSeatsInput.val(data.seating_capacity);
                        updateSeatAvailability();
                        setPill('veh-cap-pill', data.registration_number + ' (' + data.seating_capacity + ' Seats)', 'blue', assignedVehSelect.closest('.form-row, .form-group'));
                        
                        // Auto-suggest default driver if driver is unassigned
                        if (assignedDriverSelect.length && !assignedDriverSelect.val() && data.default_driver_id) {
                            assignedDriverSelect.val(data.default_driver_id).trigger('change.select2').trigger('change');
                        }
                    }
                }
            });
        }
        assignedVehSelect.on('change', onVehicleChange);
        if (window.jQuery && window.jQuery('#id_assigned_vehicle').length) {
            window.jQuery('#id_assigned_vehicle').on('select2:select', onVehicleChange);
        }

        // 1.2 Package Selection -> Auto-Calculate Return Date & Price
        function autoCalcDepReturnDate(durationDays) {
            var depVal = departureDateInput.val();
            if (depVal && durationDays && durationDays > 0) {
                var depDate = new Date(depVal);
                if (!isNaN(depDate.getTime())) {
                    depDate.setDate(depDate.getDate() + (durationDays - 1));
                    returnDateInput.val(formatDate(depDate));
                    validateDepReturnDates();
                    setPill('calc-duration-pill', durationDays + ' Days Package Duration Auto-Applied', 'green', returnDateInput);
                }
            }
        }

        function onBatchPkgChange() {
            var pkgId = depBatchPkgSelect.val();
            if (!pkgId) {
                cachedBatchPkg = null;
                return;
            }
            $.ajax({
                url: '/packages/api/package/' + pkgId + '/info/',
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    if (data.success) {
                        cachedBatchPkg = data;
                        if (priceOverrideInput.length && (!priceOverrideInput.val() || parseFloat(priceOverrideInput.val()) === 0)) {
                            var suggestedRate = data.price_with_food || data.base_price || 0;
                            if (suggestedRate > 0) {
                                priceOverrideInput.val(suggestedRate);
                                updateSeatAvailability();
                            }
                        }
                        autoCalcDepReturnDate(data.duration_days);
                    }
                }
            });
        }

        depBatchPkgSelect.on('change', onBatchPkgChange);
        if (window.jQuery && window.jQuery('#id_package').length) {
            window.jQuery('#id_package').on('select2:select', onBatchPkgChange);
        }

        departureDateInput.on('change input', function () {
            validateDepReturnDates();
            if (cachedBatchPkg && cachedBatchPkg.duration_days) {
                autoCalcDepReturnDate(cachedBatchPkg.duration_days);
            }
        });

        function validateDepReturnDates() {
            var dep = departureDateInput.val(), ret = returnDateInput.val();
            if (dep && ret && ret < dep) {
                setPill('dep-date-error', 'Return date is BEFORE departure!', 'red', returnDateInput);
                returnDateInput.css('border', '2px solid #ef4444');
            } else {
                $('#dep-date-error').remove();
                returnDateInput.css('border', '');
            }
        }
        returnDateInput.on('change', validateDepReturnDates);
        validateDepReturnDates();
    }


    // =========================================================================
    // 2. COLLEGE IV & GROUP EXPEDITION FORM
    // =========================================================================
    var maleInput        = $('#id_student_count_male');
    var femaleInput      = $('#id_student_count_female');
    var facultyInput     = $('#id_faculty_count');
    var totalPaxInput    = $('#id_total_pax');
    var totalPaxReadonly = $('.field-total_pax .readonly');
    var busCountInput    = $('#id_bus_count');
    var ivStartDate      = $('#id_start_date');
    var ivEndDate        = $('#id_end_date');
    var ivPackageSelect  = $('#id_package');

    var cachedIVPkg = null;
    var currentGroupMode = 'college'; // 'college', 'corporate', 'school', 'family'

    if (maleInput.length && femaleInput.length && facultyInput.length) {

        // 2.1 Group Mode Toolbar Injection
        var groupBarHtml = `
            <div class="sg-group-type-bar" id="sg-group-mode-bar">
                <span class="sg-group-bar-title"><i class="fas fa-layer-group text-warning mr-1"></i> Group Type:</span>
                <button type="button" class="sg-group-type-btn sg-group-college active" data-mode="college">
                    <i class="fas fa-graduation-cap"></i> College IV
                </button>
                <button type="button" class="sg-group-type-btn sg-group-corporate" data-mode="corporate">
                    <i class="fas fa-briefcase"></i> Corporate / IT Offsite
                </button>
                <button type="button" class="sg-group-type-btn sg-group-school" data-mode="school">
                    <i class="fas fa-school"></i> School Tour
                </button>
                <button type="button" class="sg-group-type-btn sg-group-family" data-mode="family">
                    <i class="fas fa-users"></i> Family & Friends
                </button>
                <button type="button" class="sg-btn-preset sg-btn-iv" id="sg-btn-iv-whatsapp" style="margin-left:auto; padding:4px 12px; font-size:11.5px; border-radius:4px;">
                    <i class="fab fa-whatsapp text-success mr-1"></i> WhatsApp Briefing
                </button>
            </div>
        `;

        var targetContainer = $('#collegeivexpedition_form, .change-form form, #jazzy-tabs');
        if (targetContainer.length) {
            targetContainer.first().prepend(groupBarHtml);
        } else {
            $('.form-row').first().before(groupBarHtml);
        }

        var MODES_CONFIG = {
            'college': {
                sectionTitle: '🎓 Institution & Faculty In-Charge',
                collegeLabel: 'College Name:',
                collegePlaceholder: 'e.g. PSG College of Technology / Damodaran Arts',
                deptLabel: 'Department & Batch:',
                deptPlaceholder: 'e.g. B.E. Mechanical Engineering (Batch 2023-27)',
                inchargeLabel: 'Faculty In-Charge Name:',
                inchargePhoneLabel: 'Faculty Contact Phone:',
                maleLabel: 'Male Students:',
                femaleLabel: 'Female Students:',
                facultyLabel: 'Accompanying Faculty (Free):',
                industryLabel: 'Industrial Visit Factories / Clearances:',
                industryPlaceholder: 'e.g. Ashok Leyland Hosur, Ooty Tea Factory, ISRO',
                sharingType: 'quad'
            },
            'corporate': {
                sectionTitle: '💼 Corporate Enterprise & Team Lead',
                collegeLabel: 'Company / Organization Name:',
                collegePlaceholder: 'e.g. Zoho Corp / Infosys Ltd / TCS Enterprise',
                deptLabel: 'Department / Business Unit / Team:',
                deptPlaceholder: 'e.g. DevOps & Cloud Infrastructure Team Offsite',
                inchargeLabel: 'HR / Team Lead Coordinator:',
                inchargePhoneLabel: 'Team Lead Contact Phone:',
                maleLabel: 'Male Delegates:',
                femaleLabel: 'Female Delegates:',
                facultyLabel: 'Senior Directors / VPs (Executive):',
                industryLabel: 'Offsite & Conference Venue / Agenda:',
                industryPlaceholder: 'e.g. Resort Conference Hall, Leadership Summit, Team Building Games',
                sharingType: 'twin'
            },
            'school': {
                sectionTitle: '🏫 School & Teacher In-Charge',
                collegeLabel: 'School Name:',
                collegePlaceholder: 'e.g. Chinmaya Vidyalaya / DPS Coimbatore',
                deptLabel: 'Class & Standard / Section:',
                deptPlaceholder: 'e.g. 10th & 12th Standard Outbound Tour',
                inchargeLabel: 'Teacher / Principal In-Charge:',
                inchargePhoneLabel: 'Teacher Contact Phone:',
                maleLabel: 'School Boys:',
                femaleLabel: 'School Girls:',
                facultyLabel: 'Accompanying Teachers (Free):',
                industryLabel: 'Educational Sightseeing & Museum Spots:',
                industryPlaceholder: 'e.g. Science Park, Botanical Gardens, Heritage Fort',
                sharingType: 'quad'
            },
            'family': {
                sectionTitle: '👨‍👩‍👧‍👦 Family & Friends Reunion',
                collegeLabel: 'Family / Clan / Club Group Name:',
                collegePlaceholder: 'e.g. Kovai Sundaram Family Reunion / Rotaract Club',
                deptLabel: 'Tour Occasion / Circuit Theme:',
                deptPlaceholder: 'e.g. Silver Jubilee Celebration / Mysore-Coorg Getaway',
                inchargeLabel: 'Family Elder / Tour Coordinator:',
                inchargePhoneLabel: 'Coordinator Contact Phone:',
                maleLabel: 'Adult Men:',
                femaleLabel: 'Adult Women:',
                facultyLabel: 'Children / Senior Citizens:',
                industryLabel: 'Key Tour Highlights & Stops:',
                industryPlaceholder: 'e.g. Hill Station Viewpoints, Campfire Resort, Boating',
                sharingType: 'twin'
            }
        };

        function setLabelText(fieldId, text) {
            var lbl = $('label[for="' + fieldId + '"]');
            if (lbl.length) lbl.text(text);
        }

        function applyGroupMode(mode) {
            currentGroupMode = mode;
            $('.sg-group-type-btn').removeClass('active');
            $('.sg-group-' + mode).addClass('active');

            var cfg = MODES_CONFIG[mode] || MODES_CONFIG['college'];
            
            // Re-label fields dynamically
            setLabelText('id_college_name', cfg.collegeLabel);
            $('#id_college_name').attr('placeholder', cfg.collegePlaceholder);

            setLabelText('id_department_and_batch', cfg.deptLabel);
            $('#id_department_and_batch').attr('placeholder', cfg.deptPlaceholder);

            setLabelText('id_faculty_incharge_name', cfg.inchargeLabel);
            setLabelText('id_faculty_incharge_phone', cfg.inchargePhoneLabel);

            setLabelText('id_student_count_male', cfg.maleLabel);
            setLabelText('id_student_count_female', cfg.femaleLabel);
            setLabelText('id_faculty_count', cfg.facultyLabel);

            setLabelText('id_industry_visit_targets', cfg.industryLabel);
            $('#id_industry_visit_targets').attr('placeholder', cfg.industryPlaceholder);

            // Re-label Section Title
            var fsetLegend = $('.field-college_name').closest('fieldset').find('h2, legend');
            if (fsetLegend.length) {
                fsetLegend.first().text(cfg.sectionTitle);
            }

            updateIVHeadcount();
        }

        $(document).on('click', '.sg-group-type-btn', function (e) {
            e.preventDefault();
            var mode = $(this).data('mode');
            applyGroupMode(mode);
        });

        // 2.2 Headcount & Convoy Calculation
        function updateIVHeadcount() {
            var boys     = parseInt(maleInput.val(), 10)    || 0;
            var girls    = parseInt(femaleInput.val(), 10)  || 0;
            var faculty  = parseInt(facultyInput.val(), 10) || 0;
            var students = boys + girls;
            var total    = students + faculty;

            if (totalPaxInput.length) totalPaxInput.val(total);
            if (totalPaxReadonly.length) {
                totalPaxReadonly.html('<strong>' + total + ' Pax</strong> <small class="text-muted">(' + boys + ' Male + ' + girls + ' Female + ' + faculty + ' Staff/VIPs)</small>');
            }

            // Smart Bus Sizer: Math.ceil(total / 50)
            var SEATS_PER_BUS  = 50;
            var suggestedBuses = total > 0 ? Math.ceil(total / SEATS_PER_BUS) : 1;
            var facPerBus      = faculty > 0 ? (faculty / suggestedBuses).toFixed(1) : '0';

            var vehicleHint;
            if      (total <= 7)  vehicleHint = '1 x Innova Crysta (7 Pax)';
            else if (total <= 17) vehicleHint = '1 x Force Urbania (17 Pax)';
            else if (total <= 26) vehicleHint = '1 x Mini Coach (26 Pax)';
            else if (total <= 50) vehicleHint = '1 x 50-Seat Luxury Coach';
            else                  vehicleHint = suggestedBuses + ' x 50-Seat Luxury Coach Convoy';

            if (busCountInput.length) busCountInput.val(suggestedBuses);

            // Rooming breakdown (Quad for College/School, Twin for Corporate/Family)
            var studentRooms, facultyRooms, roomDesc;
            if (currentGroupMode === 'corporate' || currentGroupMode === 'family') {
                studentRooms = Math.ceil(students / 2);
                facultyRooms = Math.ceil(faculty / 2);
                roomDesc = (studentRooms + facultyRooms) + ' Rooms (Twin Sharing Standard)';
            } else {
                studentRooms = Math.ceil(students / 4);
                facultyRooms = Math.ceil(faculty / 2);
                roomDesc = (studentRooms + facultyRooms) + ' Rooms (' + studentRooms + ' Quad + ' + facultyRooms + ' Twin)';
            }

            $('#iv-convoy-badge').remove();
            facultyInput.after(
                '<span id="iv-convoy-badge" class="sg-calc-pill sg-calc-purple" style="margin-left:8px;">' +
                '<i class="fas fa-users" style="margin-right:4px;"></i>' +
                total + ' Pax | ' + vehicleHint +
                ' | ' + roomDesc +
                (faculty > 0 ? ' | ~' + facPerBus + ' staff/bus' : '') +
                '</span>'
            );

            $('#iv-fac-ratio-badge').remove();
            if (students > 0 && faculty > 0) {
                var ratio = Math.round(students / faculty);
                var ratioColor, ratioText;
                if      (ratio > 50) { ratioColor = 'red';   ratioText = 'High group ratio: 1:' + ratio + ' (recommend max 1:50 staff ratio)'; }
                else if (ratio < 10) { ratioColor = 'blue';  ratioText = 'Staff/VIP heavy: 1:' + ratio + ' (check complimentary seats)'; }
                else                 { ratioColor = 'green'; ratioText = 'Ratio Balanced: 1 Coordinator per ' + ratio + ' Pax'; }
                facultyInput.after('<span id="iv-fac-ratio-badge" class="sg-calc-pill sg-calc-' + ratioColor + '" style="margin-left:8px;">' + ratioText + '</span>');
            }

            updateLiveGroupQuotation(total, faculty);
        }

        maleInput.on('input change', updateIVHeadcount);
        femaleInput.on('input change', updateIVHeadcount);
        facultyInput.on('input change', updateIVHeadcount);

        // 2.3 Package Selection -> Dynamic End Date & Live Price Quotation
        function autoCalcIVEndDate(durationDays) {
            var startVal = ivStartDate.val();
            if (startVal && durationDays && durationDays > 0) {
                var sDate = new Date(startVal);
                if (!isNaN(sDate.getTime())) {
                    sDate.setDate(sDate.getDate() + (durationDays - 1));
                    ivEndDate.val(formatDate(sDate));
                    updateDateGap();
                }
            }
        }

        function updateLiveGroupQuotation(totalPax, facultyCnt) {
            $('#iv-cost-badge').remove();
            if (!cachedIVPkg) return;

            var price = cachedIVPkg.price_with_food || cachedIVPkg.base_price || 0;
            var flightEst = cachedIVPkg.flight_estimate_per_pax || 0;
            var transitMode = $('#id_transit_mode').val() || cachedIVPkg.transit_mode || 'road_coach';

            if (price > 0 && totalPax > 0) {
                var paying = Math.max(0, totalPax - (facultyCnt || 0));
                var landRev = paying * price;
                var flightRev = paying * flightEst;
                var totalRev = (transitMode === 'flight_coach') ? (landRev + flightRev) : landRev;

                var quoteText = '₹' + price.toLocaleString('en-IN') + ' / head (Land AP Plan)';
                if (transitMode === 'flight_coach' && flightEst > 0) {
                    quoteText += ' + ₹' + flightEst.toLocaleString('en-IN') + ' Flights | <strong>Est. Fly-Bus Total: ₹' + totalRev.toLocaleString('en-IN') + '</strong>';
                } else {
                    quoteText += ' | <strong>Est. Total: ₹' + totalRev.toLocaleString('en-IN') + '</strong>';
                }

                var quoteBadgeHtml = (
                    '<span id="iv-cost-badge" class="sg-calc-pill sg-calc-green" style="margin-left:8px; font-size:12px;">' +
                    '<i class="fas fa-file-invoice-dollar mr-1"></i> ' + quoteText + ' ' +
                    '(' + paying + ' paying + ' + (facultyCnt || 0) + ' Free Staff)' +
                    '</span>'
                );
                ivPackageSelect.after(quoteBadgeHtml);
            }
        }

        // 2.3.1 Dynamic Transit Mode Form & Tab Adaptation
        var currentActiveTransitMode = null;

        function handleTransitModeChange(mode, forceRefresh) {
            if (!mode) {
                mode = $('#id_transit_mode').val() || 'road_coach';
            }

            // Check if already applied and not forced
            if (!forceRefresh && currentActiveTransitMode === mode && $('.sg-transit-notice').length === 1) {
                return;
            }
            currentActiveTransitMode = mode;

            // Find Tab Link in Jazzmin tabs
            var tabLink = $('a[href="#tour-transit-logistics-tab"], a[aria-controls="tour-transit-logistics-tab"], a[href*="transit"], a[href*="flight"], a[href*="logistics"]');
            if (!tabLink.length) {
                tabLink = $('.nav-tabs a.nav-link, #jazzy-tabs a').filter(function () {
                    var txt = $(this).text().toLowerCase();
                    return txt.indexOf('transit') !== -1 || txt.indexOf('flight') !== -1 || txt.indexOf('logistics') !== -1;
                });
            }

            // Find Tab Card Title / Description
            var tabCardTitle = $('#tour-transit-logistics-tab .card-title, .grp-flybus-specs .card-title, [id*="transit"] .card-title');

            // Find field rows in Jazzmin (.form-group) and standard Django Admin (.form-row)
            var modeContainer = $('#id_transit_mode').closest('.form-group');
            if (!modeContainer.length) {
                modeContainer = $('.form-group.field-transit_mode').first();
            }

            var rowFlights = $('.field-onward_transit_details, .field-return_transit_details').closest('.form-group, .form-row');
            if (!rowFlights.length) rowFlights = $('.field-onward_transit_details');

            var rowPnr = $('.field-transit_pnr_or_booking_ref, .field-baggage_allowance').closest('.form-group, .form-row');
            if (!rowPnr.length) rowPnr = $('.field-transit_pnr_or_booking_ref');

            var rowTerminal = $('.field-reporting_terminal, .field-destination_coach_partner').closest('.form-group, .form-row');
            if (!rowTerminal.length) rowTerminal = $('.field-reporting_terminal');

            var rowCity = $('.field-destination_city, .field-aadhaar_id_mandatory').closest('.form-group, .form-row');
            if (!rowCity.length) rowCity = $('.field-destination_city');

            // CRITICAL: Clean up ALL existing notice elements by class (removes any orphaned duplicate elements)
            $('.sg-transit-notice').remove();

            if (mode === 'road_coach') {
                // 1. ALL-WAY ROAD COACH
                if (tabLink.length) {
                    tabLink.first().html('<i class="fas fa-bus mr-1" style="color:#f59e0b;"></i> Road Convoy Transit');
                }
                if (tabCardTitle.length) {
                    tabCardTitle.text('🚌 All-Way Road Coach Transit (Direct Campus Ex-Garage Convoy)');
                }

                // Hide all flight/rail specific rows
                rowFlights.hide();
                rowPnr.hide();
                rowTerminal.hide();
                rowCity.hide();

                var roadNotice = `
                    <div id="sg-transit-mode-notice" class="sg-transit-notice" data-transit-mode="road_coach" style="margin-top:14px; margin-bottom:14px; background:#0f172a; border:1px solid #0284c7; border-left:5px solid #0284c7; border-radius:8px; padding:18px 22px;">
                        <div style="color:#38bdf8; font-weight:700; font-size:14.5px; margin-bottom:8px; display:flex; align-items:center; gap:8px;">
                            <i class="fas fa-bus-alt" style="color:#f59e0b; font-size:18px;"></i>
                            <span>🚌 All-Way Road Coach Mode Active (Ex-Garage Convoy)</span>
                            <span class="badge" style="background:#0369a1; color:#fff; font-size:11px; padding:3px 8px; border-radius:12px;">Zero Flight / Train Tickets Needed</span>
                        </div>
                        <div style="color:#cbd5e1; font-size:13px; line-height:1.65;">
                            This expedition travels <strong>100% by road coach</strong> directly from the institution campus to destinations and back.<br>
                            <div style="margin-top:10px; display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:10px;">
                                <div style="background:#1e293b; padding:10px 14px; border-radius:6px; border-left:3px solid #10b981;">
                                    <span style="color:#34d399; font-weight:700;"><i class="fas fa-check-circle mr-1"></i> No Flight or Train Bookings:</span>
                                    <span style="color:#94a3b8; display:block; font-size:12px; margin-top:2px;">Airline PNR, 15 kg baggage limits, and airport reporting are not required.</span>
                                </div>
                                <div style="background:#1e293b; padding:10px 14px; border-radius:6px; border-left:3px solid #f59e0b;">
                                    <span style="color:#fbbf24; font-weight:700;"><i class="fas fa-route mr-1"></i> Convoy Execution:</span>
                                    <span style="color:#94a3b8; display:block; font-size:12px; margin-top:2px;">Buses count, tour managers, and DJ campfire arrangements are configured in Tab 5 ("Convoy &amp; Tour Execution").</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                modeContainer.first().after(roadNotice);

            } else if (mode === 'flight_coach') {
                // 2. FLIGHT + DESTINATION COACH (FLY-BUS)
                if (tabLink.length) {
                    tabLink.first().html('<i class="fas fa-plane-departure mr-1" style="color:#38bdf8;"></i> Flight Logistics (Fly-Bus)');
                }
                if (tabCardTitle.length) {
                    tabCardTitle.text('✈️ Flight & Fly-Bus Logistics: Flight tickets, airline group PNR, reporting terminal, destination coach fleet partner, and passenger baggage allowance.');
                }

                rowFlights.show();
                rowPnr.show();
                rowTerminal.show();
                rowCity.show();

                $('label[for="id_onward_transit_details"]').text('Onward Flight Details:');
                $('#id_onward_transit_details').attr('placeholder', 'e.g. IndiGo 6E-241 (CJB 08:30 AM -> DEL 11:20 AM)');
                $('label[for="id_return_transit_details"]').text('Return Flight Details:');
                $('#id_return_transit_details').attr('placeholder', 'e.g. IndiGo 6E-242 (DEL 07:45 PM -> CJB 10:35 PM)');
                $('label[for="id_transit_pnr_or_booking_ref"]').text('Airline Group PNR:');
                $('#id_transit_pnr_or_booking_ref').attr('placeholder', 'e.g. Q8W9XY / IND-DEL-9842');
                $('label[for="id_reporting_terminal"]').text('Departure Airport Terminal:');
                $('#id_reporting_terminal').attr('placeholder', 'e.g. Coimbatore International Airport (CJB) - Terminal 1');
                $('label[for="id_baggage_allowance"]').text('Flight Baggage Allowance:');
                if (!$('#id_baggage_allowance').val()) {
                    $('#id_baggage_allowance').val('15 kg Check-in + 7 kg Cabin Baggage per passenger');
                }
                $('label[for="id_destination_coach_partner"]').text('Destination Coach Partner (DMC):');
                $('#id_destination_coach_partner').attr('placeholder', 'e.g. Royal North Star Coaches Delhi (2 x 52-Seat Volvo)');
                $('label[for="id_destination_city"]').text('Destination City:');
                $('#id_destination_city').attr('placeholder', 'e.g. Delhi / Agra / Jaipur');

                var flightNotice = `
                    <div id="sg-transit-mode-notice" class="sg-transit-notice" data-transit-mode="flight_coach" style="margin-top:14px; margin-bottom:14px; background:#0f172a; border:1px solid #6366f1; border-left:5px solid #6366f1; border-radius:8px; padding:18px 22px;">
                        <div style="color:#818cf8; font-weight:700; font-size:14.5px; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                            <i class="fas fa-plane-departure" style="color:#38bdf8; font-size:18px;"></i>
                            <span>✈️ Fly-Bus Mode Active (Flight + Destination Coach)</span>
                            <span class="badge" style="background:#4338ca; color:#fff; font-size:11px; padding:3px 8px; border-radius:12px;">Airline Group PNR Required</span>
                        </div>
                        <div style="color:#cbd5e1; font-size:13px; line-height:1.65;">
                            Students &amp; faculty fly to destination airport and transfer to private luxury coaches stationed on-site.<br>
                            Enter group airline PNR, flight schedule, baggage allowance, and local destination coach partner details below.
                        </div>
                    </div>
                `;
                modeContainer.first().after(flightNotice);

            } else if (mode === 'train_coach') {
                // 3. TRAIN + DESTINATION COACH (RAIL-BUS)
                if (tabLink.length) {
                    tabLink.first().html('<i class="fas fa-train mr-1" style="color:#10b981;"></i> Rail & Train Logistics');
                }
                if (tabCardTitle.length) {
                    tabCardTitle.text('🚆 Rail-Bus Logistics: IRCTC Group PNR, train schedules, station coach pickup, and destination coach fleet partner.');
                }

                rowFlights.show();
                rowPnr.show();
                rowTerminal.show();
                rowCity.show();

                $('label[for="id_onward_transit_details"]').text('Onward Train Schedule:');
                $('#id_onward_transit_details').attr('placeholder', 'e.g. Train #12678 Kerala Express (CBE -> NDLS)');
                $('label[for="id_return_transit_details"]').text('Return Train Schedule:');
                $('#id_return_transit_details').attr('placeholder', 'e.g. Train #12677 Return Express');
                $('label[for="id_transit_pnr_or_booking_ref"]').text('IRCTC Group PNR:');
                $('#id_transit_pnr_or_booking_ref').attr('placeholder', 'e.g. 4521890321');
                $('label[for="id_reporting_terminal"]').text('Reporting Railway Station:');
                $('#id_reporting_terminal').attr('placeholder', 'e.g. Coimbatore Junction (CBE) - Platform 1');
                $('label[for="id_baggage_allowance"]').text('Rail Luggage Guidelines:');
                if (!$('#id_baggage_allowance').val()) {
                    $('#id_baggage_allowance').val('Standard Rail Coach Luggage (No weight surcharge)');
                }
                $('label[for="id_destination_coach_partner"]').text('Station Coach Pickup Partner:');
                $('#id_destination_coach_partner').attr('placeholder', 'e.g. Delhi Station Tourist Bus Fleet');
                $('label[for="id_destination_city"]').text('Destination City / Junction:');

                var trainNotice = `
                    <div id="sg-transit-mode-notice" class="sg-transit-notice" data-transit-mode="train_coach" style="margin-top:14px; margin-bottom:14px; background:#0f172a; border:1px solid #10b981; border-left:5px solid #10b981; border-radius:8px; padding:18px 22px;">
                        <div style="color:#34d399; font-weight:700; font-size:14.5px; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                            <i class="fas fa-train" style="color:#10b981; font-size:18px;"></i>
                            <span>🚆 Rail-Bus Mode Active (Train + Destination Coach)</span>
                            <span class="badge" style="background:#065f46; color:#fff; font-size:11px; padding:3px 8px; border-radius:12px;">IRCTC Group PNR</span>
                        </div>
                        <div style="color:#cbd5e1; font-size:13px; line-height:1.65;">
                            Group travels via Indian Railways. Station coach pickup and destination sightseeing will be executed by local coaches.
                        </div>
                    </div>
                `;
                modeContainer.first().after(trainNotice);

            } else if (mode === 'land_only') {
                // 4. LAND PACKAGE ONLY
                if (tabLink.length) {
                    tabLink.first().html('<i class="fas fa-map-marker-alt mr-1" style="color:#fbbf24;"></i> Destination Land Package');
                }
                if (tabCardTitle.length) {
                    tabCardTitle.text('📍 Destination Land Package: Local coach fleet and destination itinerary execution.');
                }

                rowFlights.hide();
                rowPnr.hide();
                rowTerminal.hide();
                rowCity.show();

                $('label[for="id_destination_coach_partner"]').text('Local Receiving Coach Provider:');
                $('#id_destination_coach_partner').attr('placeholder', 'e.g. Kerala Luxury Coach Travels');
                $('label[for="id_destination_city"]').text('Destination Receiving City:');

                var landNotice = `
                    <div id="sg-transit-mode-notice" class="sg-transit-notice" data-transit-mode="land_only" style="margin-top:14px; margin-bottom:14px; background:#0f172a; border:1px solid #f59e0b; border-left:5px solid #f59e0b; border-radius:8px; padding:18px 22px;">
                        <div style="color:#fbbf24; font-weight:700; font-size:14.5px; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                            <i class="fas fa-map-marker-alt" style="color:#fbbf24; font-size:18px;"></i>
                            <span>📍 Land Package Only (Ex-Destination)</span>
                        </div>
                        <div style="color:#cbd5e1; font-size:13px; line-height:1.65;">
                            Institution arranges their own transit to destination. Our operations begin upon receiving the group at destination airport/station.
                        </div>
                    </div>
                `;
                modeContainer.first().after(landNotice);
            }
        }

        // Bind transit mode changes to select change only
        var transitModeSelect = $('#id_transit_mode');
        if (transitModeSelect.length) {
            var transitDebounce = null;
            function onTransitModeTrigger() {
                if (transitDebounce) clearTimeout(transitDebounce);
                transitDebounce = setTimeout(function () {
                    var val = $('#id_transit_mode').val();
                    handleTransitModeChange(val, true);
                    var curPax = parseInt(totalPaxInput.val(), 10) || 0;
                    var curFac = parseInt(facultyInput.val(), 10) || 0;
                    updateLiveGroupQuotation(curPax, curFac);
                }, 50);
            }

            $(document).on('change select2:select', '#id_transit_mode', onTransitModeTrigger);

            // Re-apply once when user switches tabs
            $(document).on('shown.bs.tab', 'a[href*="transit"], a[href*="flight"], a[href*="logistics"]', function () {
                handleTransitModeChange($('#id_transit_mode').val(), false);
            });

            // Trigger on load
            handleTransitModeChange(transitModeSelect.val(), true);
            setTimeout(function () {
                handleTransitModeChange($('#id_transit_mode').val(), true);
            }, 100);
        }

        function onIVPackageChange() {
            var pkgId = ivPackageSelect.val();
            if (!pkgId) {
                cachedIVPkg = null;
                $('#iv-cost-badge').remove();
                return;
            }
            $.ajax({
                url: '/packages/api/package/' + pkgId + '/info/',
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    if (data.success) {
                        cachedIVPkg = data;
                        autoCalcIVEndDate(data.duration_days);
                        if (data.transit_mode) {
                            $('#id_transit_mode').val(data.transit_mode).trigger('change');
                            if (window.jQuery && window.jQuery('#id_transit_mode').data('select2')) {
                                window.jQuery('#id_transit_mode').trigger('change.select2');
                            }
                            handleTransitModeChange(data.transit_mode);
                        }
                        var curPax = parseInt(totalPaxInput.val(), 10) || 0;
                        var curFac = parseInt(facultyInput.val(), 10) || 0;
                        updateLiveGroupQuotation(curPax, curFac);
                    }
                }
            });
        }

        ivPackageSelect.on('change', onIVPackageChange);
        if (window.jQuery && window.jQuery('#id_package').length) {
            window.jQuery('#id_package').on('select2:select', onIVPackageChange);
        }

        ivStartDate.on('change input', function () {
            updateDateGap();
            if (cachedIVPkg && cachedIVPkg.duration_days) {
                autoCalcIVEndDate(cachedIVPkg.duration_days);
            }
        });

        // Trigger initial load if package is pre-selected on change form
        if (ivPackageSelect.val()) {
            onIVPackageChange();
        }

        function updateDateGap() {
            var start = ivStartDate.val(), end = ivEndDate.val();
            $('#iv-date-gap-badge').remove();
            if (start && end) {
                var diffDays = Math.round((new Date(end) - new Date(start)) / 86400000);
                if (diffDays < 0) {
                    ivEndDate.after('<span id="iv-date-gap-badge" class="sg-calc-pill sg-calc-red" style="margin-left:8px;">End date is BEFORE Start date!</span>');
                    ivEndDate.css('border', '2px solid #ef4444');
                } else {
                    ivEndDate.css('border', '');
                    ivEndDate.after('<span id="iv-date-gap-badge" class="sg-calc-pill sg-calc-blue" style="margin-left:8px;">' + diffDays + 'N / ' + (diffDays + 1) + 'D Trip</span>');
                }
            }
        }
        ivEndDate.on('change', updateDateGap);
        updateDateGap();

        // Detect if pre-existing record looks corporate or family to set initial mode
        var existingName = ($('#id_college_name').val() || '').toLowerCase();
        if (existingName.includes('corp') || existingName.includes('technologies') || existingName.includes('infotech') || existingName.includes('ltd') || existingName.includes('offsite')) {
            applyGroupMode('corporate');
        } else if (existingName.includes('school') || existingName.includes('vidyalaya') || existingName.includes('matriculation')) {
            applyGroupMode('school');
        } else if (existingName.includes('family') || existingName.includes('reunion') || existingName.includes('club')) {
            applyGroupMode('family');
        } else {
            applyGroupMode('college');
        }
    }

    // =========================================================================
    // 3. SUBMIT GUARDS
    // =========================================================================
    $('form').on('submit', function (e) {
        var start = ivStartDate.val(), end = ivEndDate.val();
        if (start && end && end < start) {
            e.preventDefault();
            alert('Cannot save: End Date is before Start Date!');
            return false;
        }
        var dep = departureDateInput.val(), ret = returnDateInput.val();
        if (dep && ret && ret < dep) {
            e.preventDefault();
            alert('Cannot save: Return Date is before Departure Date!');
            return false;
        }
    });

    // =========================================================================
    // 4. WHATSAPP EXPEDITION BRIEFING GENERATOR
    // =========================================================================
    var ivWhatsappModalHtml = `
        <div id="sg-iv-whatsapp-modal-overlay" class="sg-modal-overlay">
            <div class="sg-modal-dialog sg-whatsapp-dialog">
                <div class="sg-modal-header">
                    <div class="sg-modal-title">
                        <i class="fab fa-whatsapp text-success mr-2" style="font-size:18px;"></i> 1-Click WhatsApp Expedition Briefing
                    </div>
                    <button type="button" class="sg-btn-modal-close" id="sg-btn-close-iv-wa-modal" title="Close (Esc)">
                        &times;
                    </button>
                </div>
                <div class="sg-wa-tabs">
                    <button type="button" class="sg-wa-tab-btn active" data-tab="student">
                        <i class="fas fa-graduation-cap mr-1"></i> Student Briefing
                    </button>
                    <button type="button" class="sg-wa-tab-btn" data-tab="faculty">
                        <i class="fas fa-user-tie mr-1"></i> Faculty Dossier
                    </button>
                    <button type="button" class="sg-wa-tab-btn" data-tab="crew">
                        <i class="fas fa-bus mr-1"></i> Driver Dispatch
                    </button>
                </div>
                <div class="sg-wa-content">
                    <textarea id="sg-iv-wa-message-text" class="sg-wa-textarea" spellcheck="false"></textarea>
                    <div class="sg-wa-actions">
                        <button type="button" class="sg-btn-wa-copy" id="sg-btn-iv-wa-copy">
                            <i class="fas fa-copy mr-1"></i> Copy Message
                        </button>
                        <a href="#" target="_blank" class="sg-btn-wa-send" id="sg-btn-iv-wa-send">
                            <i class="fab fa-whatsapp mr-1"></i> Open in WhatsApp Web
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
    $('body').append(ivWhatsappModalHtml);

    var activeIvWaTab = 'student';

    function compileIvWhatsAppMessage(tabKey) {
        var collegeName = $('#id_college_name').val() || 'COLLEGE INDUSTRIAL VISIT';
        var deptName = $('#id_department_and_batch').val() || 'Student Batch';
        var facultyName = $('#id_faculty_incharge_name').val() || 'Faculty Coordinator';
        var facultyPhone = $('#id_faculty_incharge_phone').val() || '';
        var pkgName = $('#id_package option:selected').text() || 'Tour Package Circuit';
        var startDate = ivStartDate.val() || 'TBD';
        var endDate = ivEndDate.val() || 'TBD';
        var boys = maleInput.val() || '0';
        var girls = femaleInput.val() || '0';
        var faculty = facultyInput.val() || '0';
        var total = totalPaxInput.val() || '50';
        var buses = $('#id_bus_count').val() || '1';
        var tourManager = $('#id_tour_manager_assigned').val() || 'Rithik CA (+91 98425 33777)';

        var msg = '';
        if (tabKey === 'student') {
            msg = `🚌 *SIVA GAYATHRI TOURS & TRAVELS — STUDENT TRIP BRIEFING*\n` +
                  `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                  `🎓 *Institution:* ${collegeName}\n` +
                  `📚 *Department:* ${deptName}\n` +
                  `🚩 *Circuit:* ${pkgName}\n` +
                  `📅 *Travel Dates:* ${startDate} to ${endDate}\n` +
                  `🚍 *Convoy Fleet:* ${buses} Luxury Tourist Bus(es)\n` +
                  `👨‍🏫 *Faculty In-Charge:* ${facultyName} (${facultyPhone})\n\n` +
                  `🎒 *STUDENT TRAVEL CHECKLIST:*\n` +
                  `• Original College ID Card & Govt Aadhaar Card (Strictly mandatory for hotel check-in)\n` +
                  `• Formal / Semi-formal attire for scheduled industrial / factory visits\n` +
                  `• Warm jacket / sweater for night campfire & hill station weather\n` +
                  `• Mobile power bank, personal medicines & modest cash\n\n` +
                  `⚠️ *SAFETY & CODE OF CONDUCT:*\n` +
                  `• Full cooperation with Faculty In-Charge and Siva Gayathri Tour Managers.\n` +
                  `• Alcohol and contraband are strictly prohibited throughout the journey.\n` +
                  `• Be punctual at all assembly points so all scheduled spots can be covered.\n\n` +
                  `📞 *24x7 TOUR MANAGER HELPLINE:*\n` +
                  `• ${tourManager}\n` +
                  `✨ _Wish you a safe, memorable, and adventurous expedition!_`;
        } else if (tabKey === 'faculty') {
            msg = `🎓 *OFFICIAL EXPEDITION CONFIRMATION & FACULTY DOSSIER*\n` +
                  `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                  `🏢 *Institution:* ${collegeName}\n` +
                  `📚 *Batch:* ${deptName}\n` +
                  `👨‍🏫 *Faculty In-Charge:* ${facultyName} (${facultyPhone})\n` +
                  `📅 *Travel Dates:* ${startDate} to ${endDate}\n` +
                  `👥 *Headcount:* ${total} Pax (${boys} Male + ${girls} Female + ${faculty} Faculty Free Seats)\n` +
                  `🚍 *Buses Allocated:* ${buses} Luxury 2x2 Pushback Coach(es)\n\n` +
                  `🏨 *ROOMING & MEAL ARRANGEMENTS:*\n` +
                  `• Student Accommodation: Verified hotel/resort on 4-sharing basis.\n` +
                  `• Faculty Accommodation: Executive Twin-Sharing Rooms.\n` +
                  `• Meals: South Indian Buffet Breakfast, Lunch & Dinner.\n` +
                  `• Campfire with DJ Music night arranged.\n\n` +
                  `📞 *TOUR MANAGER CONTACT:*\n` +
                  `• ${tourManager} | Siva Gayathri Operations Desk`;
        } else if (tabKey === 'crew') {
            msg = `🚍 *SIVA GAYATHRI TOURS — CONVOY DRIVER TRIP DISPATCH*\n` +
                  `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                  `🚩 *Expedition:* ${collegeName} (${deptName})\n` +
                  `📅 *Duty Dates:* ${startDate} to ${endDate}\n` +
                  `👥 *Passenger Load:* ${total} Pax across ${buses} Bus(es)\n\n` +
                  `📋 *CREW INSTRUCTIONS:*\n` +
                  `1. Vehicle Inspection: Air suspension, AC cooling, mic & DJ lights verified.\n` +
                  `2. Reporting: Report to campus 45 minutes prior to scheduled departure.\n` +
                  `3. Safety: Speed limit max 80 km/h. Smooth driving with utmost safety for students.\n` +
                  `4. Permits: RTO border entry tax & highway toll receipts to be retained.\n\n` +
                  `📞 *OPS MANAGER HELPLINE:* +91 98425 33777`;
        }

        $('#sg-iv-wa-message-text').val(msg);
        var waEncoded = encodeURIComponent(msg);
        $('#sg-btn-iv-wa-send').attr('href', 'https://web.whatsapp.com/send?text=' + waEncoded);
    }

    $(document).on('click', '#sg-btn-iv-whatsapp', function (e) {
        e.preventDefault();
        compileIvWhatsAppMessage(activeIvWaTab);
        $('#sg-iv-whatsapp-modal-overlay').css('display', 'flex').hide().fadeIn(200);
    });

    $(document).on('click', '#sg-btn-close-iv-wa-modal', function () {
        $('#sg-iv-whatsapp-modal-overlay').fadeOut(150);
    });

    $(document).on('click', '#sg-iv-whatsapp-modal-overlay .sg-wa-tab-btn', function () {
        $('#sg-iv-whatsapp-modal-overlay .sg-wa-tab-btn').removeClass('active');
        $(this).addClass('active');
        activeIvWaTab = $(this).data('tab');
        compileIvWhatsAppMessage(activeIvWaTab);
    });

    $(document).on('click', '#sg-btn-iv-wa-copy', function () {
        var textarea = document.getElementById('sg-iv-wa-message-text');
        if (textarea) {
            textarea.select();
            document.execCommand('copy');
            var btn = $(this);
            var orig = btn.html();
            btn.html('<i class="fas fa-check text-success mr-1"></i> Copied!').css('background', '#065f46');
            setTimeout(function () {
                btn.html(orig).css('background', '#334155');
            }, 1800);
        }
    });

    $(document).on('click', '#sg-iv-whatsapp-modal-overlay', function (e) {
        if ($(e.target).is('#sg-iv-whatsapp-modal-overlay')) {
            $('#sg-btn-close-iv-wa-modal').trigger('click');
        }
    });

});
