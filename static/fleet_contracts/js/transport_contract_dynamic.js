/**
 * Transport Contracts Dynamic Admin Engine
 * - Interactive Vertical Category Presets (Corporate ETS, School Bus, Factory, Hospital, Govt)
 * - Adaptive Vertical-Specific Operational & Compliance Specification Panels (Step 2)
 * - Universal Tab Switcher & Step Navigation Controls
 * - Billing Model Commercial Estimator & Dynamic Rate Labels
 * - Fuel Escalation Clause Visualizer
 * - Date Term Duration & Dedicated Fleet Redundancy Gauges
 */

(function () {
    'use strict';

    const PRESETS = {
        corporate: {
            name: 'Corporate / IT / BPO (Staff Commute)',
            billing_model: 'per_trip',
            billing_cycle: 'calendar_month',
            default_rate: '2400.00',
            committed_vehicle_count: 4,
            standby_vehicle_count: 1,
            payment_credit_days: 30,
            fuel_escalation_enabled: true,
            base_diesel_price: '92.50',
            fuel_revision_factor: '0.2500',
            sla_penalty_cap_pct: '10.00',
            guidance: '🏢 Corporate IT / BPO Employee Transport Service (ETS). Female security escort mandatory on drops between 20:00 - 06:00. Live GPS telematics & speed monitoring enforced.',
            tags: ['24x7 ETS Commute', 'Female Escort SLA', 'GPS Telematics', 'Per-Trip Billing'],
            notes: 'Corporate Commute Norms:\n1. Dedicated fleet assigned exclusively to corporate facility.\n2. Security escort mandatory on rostered night drops for female commuters.\n3. Fuel revision benchmarked on 1st of every month via IOCL commercial rates.',
            specs: {
                night_escort_mandatory: true,
                escort_timing_window: '20:00 - 06:00',
                safe_drop_confirmation: 'otp_sms',
                max_in_transit_minutes: 60,
                pickup_grace_minutes: 10,
                gps_telematics_portal: 'https://telematics.sivagayathiritravels.com/live/client-omr',
                roster_cutoff_hours: 4,
                panic_button_installed: true
            }
        },
        school: {
            name: 'School / College Student Transport',
            billing_model: 'fixed_monthly',
            billing_cycle: 'calendar_month',
            default_rate: '185000.00',
            committed_vehicle_count: 3,
            standby_vehicle_count: 1,
            payment_credit_days: 15,
            fuel_escalation_enabled: false,
            base_diesel_price: '0.00',
            fuel_revision_factor: '0.0000',
            sla_penalty_cap_pct: '5.00',
            guidance: '🎒 Institutional Student Transit. Speed governors strictly capped at 40 km/h. Female bus attendant mandatory on all student pickup routes. Valid Yellow Board & Fitness required.',
            tags: ['Speed Governor (40 km/h)', 'Female Attendant', 'Yellow Board PSV', 'Fixed Monthly'],
            notes: 'School Transport Compliance:\n1. Dedicated school buses with active Fitness Certificate (FC) and commercial insurance.\n2. First aid kit and certified fire extinguishers on all boarding vehicles.\n3. Drivers must possess minimum 5 years verified commercial driving record.',
            specs: {
                speed_governor_certified: true,
                speed_limit_kmh: 40,
                female_attendant_name: 'Kavitha M.',
                female_attendant_phone: '+91 98401 23456',
                child_safety_grills_verified: true,
                parent_alerts_enabled: true,
                vacation_excluded_months: 'May (Summer Vacation 0-Fee)',
                yellow_board_rto_verified: true,
                first_aid_fire_extinguisher: true
            }
        },
        factory: {
            name: 'Manufacturing / Factory Shift Shuttle',
            billing_model: 'per_trip',
            billing_cycle: 'calendar_month',
            default_rate: '2800.00',
            committed_vehicle_count: 6,
            standby_vehicle_count: 2,
            payment_credit_days: 45,
            fuel_escalation_enabled: true,
            base_diesel_price: '92.50',
            fuel_revision_factor: '0.3000',
            sla_penalty_cap_pct: '15.00',
            guidance: '🏭 Industrial Plant Shift Transport. Covers 3 rotatory shifts (Shift A 06:00, Shift B 14:00, Shift C 22:00). Biometric punch-in punctuality strictly enforced.',
            tags: ['3 Rotatory Shifts', 'Gate Siren Cutoff', 'High Capacity Coaches', 'Fuel Escalation'],
            notes: 'Industrial Logistics Clauses:\n1. Vehicles must arrive at factory security gate at least 15 minutes prior to shift change.\n2. Punctuality SLA applies if workers miss line start or gate biometric punch.',
            specs: {
                shift_a_timing: '06:00 AM - 02:00 PM',
                shift_b_timing: '02:00 PM - 10:00 PM',
                shift_c_timing: '10:00 PM - 06:00 AM',
                gate_siren_buffer_minutes: 15,
                assembly_downtime_penalty_rate: 5000,
                highway_toll_allocation: 'Sriperumbudur - Oragadam Industrial Corridor Fastag',
                min_bus_seating_capacity: 40,
                worker_union_safety_charter: true
            }
        },
        hospital: {
            name: 'Hospital / Healthcare Staff Shuttle',
            billing_model: 'fixed_monthly',
            billing_cycle: 'calendar_month',
            default_rate: '210000.00',
            committed_vehicle_count: 2,
            standby_vehicle_count: 1,
            payment_credit_days: 30,
            fuel_escalation_enabled: false,
            base_diesel_price: '0.00',
            fuel_revision_factor: '0.0000',
            sla_penalty_cap_pct: '10.00',
            guidance: '🏥 Healthcare & Hospital Staff Transit. 24/7 on-call emergency roster readiness. Daily vehicle cabin sanitization & climate-control reliability mandatory.',
            tags: ['24/7 Emergency Roster', 'Sanitization SLA', 'Doctors/Nurses Shuttle', 'Fixed Monthly'],
            notes: 'Hospital Transit Guidelines:\n1. 24/7 on-call availability for medical shifts and emergency recalls.\n2. Daily cabin sanitization log verified by hospital facilities supervisor.',
            specs: {
                emergency_recall_minutes: 30,
                cabin_sanitization_protocol: 'Daily post-shift fumigation with hospital-grade disinfectant',
                ac_reliability_sla: true,
                doctor_priority_dispatch: true,
                hospital_emergency_desk: 'Apollo Main Casualty Desk: 044-28290200',
                dual_crew_driver_rotation: true
            }
        },
        government: {
            name: 'Government / PSU Official Duty',
            billing_model: 'per_km',
            billing_cycle: 'calendar_month',
            default_rate: '28.50',
            committed_vehicle_count: 2,
            standby_vehicle_count: 1,
            payment_credit_days: 60,
            fuel_escalation_enabled: true,
            base_diesel_price: '92.50',
            fuel_revision_factor: '0.2000',
            sla_penalty_cap_pct: '5.00',
            guidance: '🏛️ Government & PSU VIP Protocol Movement. Uniformed chauffeur with verified security clearance. Formal trip logbook signed for each official conveyance.',
            tags: ['VIP Chauffeur Protocol', 'Logbook Signoff', 'PSU Credit (60 Days)', 'Per-KM Rate'],
            notes: 'Government Conveyance Standards:\n1. Professional chauffeur in clean white uniform with identity badge.\n2. Official duty slip and odometer readings endorsed by authorized government signatory.',
            specs: {
                police_verification_verified: true,
                uniform_protocol_mandatory: true,
                govt_movement_order_ref: 'TN-POL-SEC-2026/088',
                km_billing_clause: 'office_to_office',
                psu_tds_credit_terms: '60 Days Credit with Form 16A TDS Certificate',
                protocol_officer_name: 'Thiru. S. Ramanathan, Deputy Protocol Officer'
            }
        }
    };

    function initDynamicTransportForm() {
        const $ = window.jQuery || window.$;
        if (!$) return;

        // 1. Universal Tab Switcher
        function activateTab(href) {
            if (!href || !href.startsWith('#')) return;
            const targetId = href.substring(1);
            $('#jazzy-tabs .nav-link').removeClass('active').attr('aria-selected', 'false');
            $(`#jazzy-tabs .nav-link[href="${href}"]`).addClass('active').attr('aria-selected', 'true');

            $('.tab-content > .tab-pane').removeClass('show active').css('display', 'none');
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                $(targetEl).addClass('show active').css('display', 'block');
                window.dispatchEvent(new Event('resize'));
            }
        }

        $(document).on('click', '#jazzy-tabs .nav-link', function (e) {
            e.preventDefault();
            activateTab($(this).attr('href'));
        });

        // 2. Inject Preset Bar into Step 1
        const step1Pane = $('#step-1-classification-client-organization-tab');
        if (step1Pane.length && !$('#tc-preset-bar').length) {
            const presetHtml = `
                <div id="tc-preset-bar" class="tc-preset-wrapper">
                    <div class="tc-preset-header">
                        <div class="tc-preset-title">
                            <span>⚡ Institutional Vertical Presets</span>
                        </div>
                        <div class="tc-preset-subtitle">
                            Click a preset to auto-populate standard commercial rates, fleet buffer, and SLA norms
                        </div>
                    </div>
                    <div class="tc-preset-chips">
                        <button type="button" class="tc-preset-chip" data-category="corporate">🏢 Corporate ETS</button>
                        <button type="button" class="tc-preset-chip" data-category="school">🎒 School / College Bus</button>
                        <button type="button" class="tc-preset-chip" data-category="factory">🏭 Factory 3-Shift</button>
                        <button type="button" class="tc-preset-chip" data-category="hospital">🏥 Hospital 24/7</button>
                        <button type="button" class="tc-preset-chip" data-category="government">🏛️ Govt / PSU VIP</button>
                    </div>
                    <div id="tc-guidance-container"></div>
                </div>
            `;
            step1Pane.find('.card-body').first().prepend(presetHtml);
        }

        // 3. Category Preset Click Handler
        $(document).on('click', '.tc-preset-chip', function () {
            const cat = $(this).data('category');
            applyPreset(cat);
        });

        function applyPreset(cat) {
            const p = PRESETS[cat];
            if (!p) return;

            // Highlight chip
            $('.tc-preset-chip').removeClass('active');
            $(`.tc-preset-chip[data-category="${cat}"]`).addClass('active');

            // Set Category
            const catField = $('#id_contract_category');
            if (catField.length && catField.val() !== cat) {
                catField.val(cat).trigger('change');
            }

            // Set Billing Model & Rates
            $('#id_billing_model').val(p.billing_model).trigger('change');
            $('#id_billing_cycle').val(p.billing_cycle);
            $('#id_default_rate').val(p.default_rate).trigger('input');

            // Set Fleet Commitments
            $('#id_committed_vehicle_count').val(p.committed_vehicle_count).trigger('input');
            $('#id_standby_vehicle_count').val(p.standby_vehicle_count).trigger('input');
            $('#id_payment_credit_days').val(p.payment_credit_days);

            // Set Fuel Escalation
            const fuelCheck = $('#id_fuel_escalation_enabled');
            if (fuelCheck.length) {
                fuelCheck.prop('checked', p.fuel_escalation_enabled).trigger('change');
            }
            $('#id_base_diesel_price').val(p.base_diesel_price);
            $('#id_fuel_revision_factor').val(p.fuel_revision_factor);
            $('#id_sla_penalty_cap_pct').val(p.sla_penalty_cap_pct);

            // Populate Notes if empty
            const notesField = $('#id_notes');
            if (notesField.length && (!notesField.val() || notesField.val().trim() === '')) {
                notesField.val(p.notes);
            }

            // Update specifications JSON
            if (p.specs) {
                setSpecifications(p.specs);
            }

            renderGuidance(cat);
            renderVerticalSpecPanel(cat);
            updateCommercialEstimator();
            updateFuelFormula();
            updateRedundancy();
        }

        // Render Category Guidance Card
        function renderGuidance(cat) {
            const p = PRESETS[cat];
            const container = $('#tc-guidance-container');
            if (!p || !container.length) return;

            const tagsHtml = p.tags.map(t => `<span class="tc-guidance-tag">${t}</span>`).join('');
            container.html(`
                <div class="tc-guidance-card">
                    <div><strong>Operational Guidance:</strong> ${p.guidance}</div>
                    <div class="tc-guidance-tags">${tagsHtml}</div>
                </div>
            `);
        }

        // Helper to read specifications JSON
        function getSpecifications() {
            const raw = $('#id_category_specifications').val();
            if (!raw) return {};
            try {
                return JSON.parse(raw);
            } catch (e) {
                return {};
            }
        }

        // Helper to write specifications JSON
        function setSpecifications(specsObj) {
            $('#id_category_specifications').val(JSON.stringify(specsObj, null, 2));
        }

        // Update single spec property and save
        function updateSpecProp(key, value) {
            const specs = getSpecifications();
            specs[key] = value;
            setSpecifications(specs);
        }

        // 4. Render Adaptive Vertical Specification Panel (Step 2)
        function renderVerticalSpecPanel(cat) {
            const step2Pane = $('#step-2-operational-compliance-specifications-tab');
            if (!step2Pane.length) return;

            const cardBody = step2Pane.find('.card-body').first();
            $('#tc-adaptive-spec-panel').remove();

            let specs = getSpecifications();
            if ($.isEmptyObject(specs) && PRESETS[cat] && PRESETS[cat].specs) {
                specs = $.extend({}, PRESETS[cat].specs);
                setSpecifications(specs);
            }

            let panelHtml = '';

            if (cat === 'corporate') {
                panelHtml = `
                    <div id="tc-adaptive-spec-panel" class="tc-spec-panel tc-spec-panel-corporate">
                        <div class="tc-spec-header">
                            <div class="tc-spec-title">
                                <span>🏢 Corporate ETS Operational & Night Escort Charter</span>
                            </div>
                            <span class="tc-spec-badge tc-spec-badge-corporate">Corporate BPO / IT ETS</span>
                        </div>
                        <div class="tc-spec-grid">
                            <div class="tc-spec-field">
                                <label>Night Escort Timing Window</label>
                                <input type="text" class="tc-spec-input" data-spec-key="escort_timing_window" value="${specs.escort_timing_window || '20:00 - 06:00'}" placeholder="e.g. 20:00 - 06:00">
                                <div class="tc-spec-help">Window during which female employees require security escort</div>
                            </div>
                            <div class="tc-spec-field">
                                <label>Safe Drop Confirmation Protocol</label>
                                <select class="tc-spec-input" data-spec-key="safe_drop_confirmation">
                                    <option value="otp_sms" ${specs.safe_drop_confirmation === 'otp_sms' ? 'selected' : ''}>📱 Commuter Mobile OTP / SMS Confirmation</option>
                                    <option value="security_call" ${specs.safe_drop_confirmation === 'security_call' ? 'selected' : ''}>📞 Dedicated ETS Desk Voice Confirmation</option>
                                    <option value="guard_handover" ${specs.safe_drop_confirmation === 'guard_handover' ? 'selected' : ''}>🛡️ Physical Guard / Attendant Handover</option>
                                </select>
                            </div>
                            <div class="tc-spec-field">
                                <label>Max In-Transit Duration SLA (Minutes)</label>
                                <input type="number" class="tc-spec-input" data-spec-key="max_in_transit_minutes" value="${specs.max_in_transit_minutes || 60}" placeholder="60">
                                <div class="tc-spec-help">Maximum permissible commute time per employee from pickup to drop</div>
                            </div>
                            <div class="tc-spec-field">
                                <label>Max Pickup Window Arrival Margin (Minutes)</label>
                                <input type="number" class="tc-spec-input" data-spec-key="pickup_grace_minutes" value="${specs.pickup_grace_minutes || 10}" placeholder="10">
                                <div class="tc-spec-help">Permissible pickup arrival deviation (± mins)</div>
                            </div>
                            <div class="tc-spec-field" style="grid-column: 1 / -1;">
                                <label>Live GPS Telematics Portal / Tracking URL</label>
                                <input type="text" class="tc-spec-input" data-spec-key="gps_telematics_portal" value="${specs.gps_telematics_portal || 'https://telematics.sivagayathiritravels.com/live/client-omr'}" placeholder="https://telematics.domain.com/live/...">
                                <div class="tc-spec-help">Customer transport desk live fleet monitoring link</div>
                            </div>
                            <div class="tc-spec-field">
                                <label>Roster Cutoff Window (Hours before shift)</label>
                                <input type="number" class="tc-spec-input" data-spec-key="roster_cutoff_hours" value="${specs.roster_cutoff_hours || 4}" placeholder="4">
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_night_escort_mandatory" data-spec-key="night_escort_mandatory" ${specs.night_escort_mandatory !== false ? 'checked' : ''}>
                                <label for="spec_night_escort_mandatory">Mandatory Female Security Escort Guard</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_panic_button_installed" data-spec-key="panic_button_installed" ${specs.panic_button_installed !== false ? 'checked' : ''}>
                                <label for="spec_panic_button_installed">In-Cabin SOS Panic Button & Alarm Fitted</label>
                            </div>
                        </div>
                    </div>
                `;
            } else if (cat === 'school') {
                panelHtml = `
                    <div id="tc-adaptive-spec-panel" class="tc-spec-panel tc-spec-panel-school">
                        <div class="tc-spec-header">
                            <div class="tc-spec-title">
                                <span>🎒 Institutional Student Safety & RTO Regulatory Panel</span>
                            </div>
                            <span class="tc-spec-badge tc-spec-badge-school">School & College Bus</span>
                        </div>
                        <div class="tc-spec-grid">
                            <div class="tc-spec-field">
                                <label>RTO Speed Limit (km/h)</label>
                                <input type="number" class="tc-spec-input" data-spec-key="speed_limit_kmh" value="${specs.speed_limit_kmh || 40}" placeholder="40">
                                <div class="tc-spec-help">State RTO certified speed governor maximum ceiling</div>
                            </div>
                            <div class="tc-spec-field">
                                <label>Designated Female Bus Attendant Name</label>
                                <input type="text" class="tc-spec-input" data-spec-key="female_attendant_name" value="${specs.female_attendant_name || 'Kavitha M.'}" placeholder="Attendant Full Name">
                            </div>
                            <div class="tc-spec-field">
                                <label>Female Attendant Mobile Contact</label>
                                <input type="text" class="tc-spec-input" data-spec-key="female_attendant_phone" value="${specs.female_attendant_phone || '+91 98401 23456'}" placeholder="+91 98401 23456">
                            </div>
                            <div class="tc-spec-field">
                                <label>Summer Vacation Excluded Billing Months</label>
                                <input type="text" class="tc-spec-input" data-spec-key="vacation_excluded_months" value="${specs.vacation_excluded_months || 'May (Summer Vacation 0-Fee)'}" placeholder="e.g. May">
                                <div class="tc-spec-help">Months when school is closed and zero fee applies</div>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_speed_governor_certified" data-spec-key="speed_governor_certified" ${specs.speed_governor_certified !== false ? 'checked' : ''}>
                                <label for="spec_speed_governor_certified">Speed Governor Certificate Verified (40 km/h)</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_child_safety_grills_verified" data-spec-key="child_safety_grills_verified" ${specs.child_safety_grills_verified !== false ? 'checked' : ''}>
                                <label for="spec_child_safety_grills_verified">Child-Safety Grills & Emergency Doors Inspected</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_parent_alerts_enabled" data-spec-key="parent_alerts_enabled" ${specs.parent_alerts_enabled !== false ? 'checked' : ''}>
                                <label for="spec_parent_alerts_enabled">Parent Real-Time SMS/WhatsApp Gateway Active</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_yellow_board_rto_verified" data-spec-key="yellow_board_rto_verified" ${specs.yellow_board_rto_verified !== false ? 'checked' : ''}>
                                <label for="spec_yellow_board_rto_verified">Yellow Board Commercial PSV & Valid FC</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_first_aid_fire_extinguisher" data-spec-key="first_aid_fire_extinguisher" ${specs.first_aid_fire_extinguisher !== false ? 'checked' : ''}>
                                <label for="spec_first_aid_fire_extinguisher">In-Cabin First Aid Kit & Fire Extinguisher</label>
                            </div>
                        </div>
                    </div>
                `;
            } else if (cat === 'factory') {
                panelHtml = `
                    <div id="tc-adaptive-spec-panel" class="tc-spec-panel tc-spec-panel-factory">
                        <div class="tc-spec-header">
                            <div class="tc-spec-title">
                                <span>🏭 Manufacturing Industrial Plant Shift Transit Panel</span>
                            </div>
                            <span class="tc-spec-badge tc-spec-badge-factory">Factory Shift Logistics</span>
                        </div>
                        <div class="tc-spec-grid">
                            <div class="tc-spec-field">
                                <label>Shift A (Morning Shift) Timetable</label>
                                <input type="text" class="tc-spec-input" data-spec-key="shift_a_timing" value="${specs.shift_a_timing || '06:00 AM - 02:00 PM'}" placeholder="06:00 AM - 02:00 PM">
                            </div>
                            <div class="tc-spec-field">
                                <label>Shift B (Evening Shift) Timetable</label>
                                <input type="text" class="tc-spec-input" data-spec-key="shift_b_timing" value="${specs.shift_b_timing || '02:00 PM - 10:00 PM'}" placeholder="02:00 PM - 10:00 PM">
                            </div>
                            <div class="tc-spec-field">
                                <label>Shift C (Night Shift) Timetable</label>
                                <input type="text" class="tc-spec-input" data-spec-key="shift_c_timing" value="${specs.shift_c_timing || '10:00 PM - 06:00 AM'}" placeholder="10:00 PM - 06:00 AM">
                            </div>
                            <div class="tc-spec-field">
                                <label>Gate Siren Arrival Buffer (Minutes)</label>
                                <input type="number" class="tc-spec-input" data-spec-key="gate_siren_buffer_minutes" value="${specs.gate_siren_buffer_minutes || 15}" placeholder="15">
                                <div class="tc-spec-help">Arrival margin required prior to plant biometric punch cutoff</div>
                            </div>
                            <div class="tc-spec-field">
                                <label>Assembly Line Downtime Penalty Rate (₹/hr)</label>
                                <input type="number" class="tc-spec-input" data-spec-key="assembly_downtime_penalty_rate" value="${specs.assembly_downtime_penalty_rate || 5000}" placeholder="5000">
                                <div class="tc-spec-help">Penalty deducted if bus delay causes line downtime</div>
                            </div>
                            <div class="tc-spec-field">
                                <label>Minimum Bus Seating Capacity</label>
                                <input type="number" class="tc-spec-input" data-spec-key="min_bus_seating_capacity" value="${specs.min_bus_seating_capacity || 40}" placeholder="40">
                            </div>
                            <div class="tc-spec-field" style="grid-column: 1 / -1;">
                                <label>Industrial Highway Toll / Fastag Route Plan</label>
                                <input type="text" class="tc-spec-input" data-spec-key="highway_toll_allocation" value="${specs.highway_toll_allocation || 'Sriperumbudur - Oragadam Industrial Corridor Fastag'}" placeholder="Corridor Highway Plan">
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_worker_union_safety_charter" data-spec-key="worker_union_safety_charter" ${specs.worker_union_safety_charter !== false ? 'checked' : ''}>
                                <label for="spec_worker_union_safety_charter">Factory Worker Union Safety Charter Complied</label>
                            </div>
                        </div>
                    </div>
                `;
            } else if (cat === 'hospital') {
                panelHtml = `
                    <div id="tc-adaptive-spec-panel" class="tc-spec-panel tc-spec-panel-hospital">
                        <div class="tc-spec-header">
                            <div class="tc-spec-title">
                                <span>🏥 Healthcare Critical Staff Transit & Hygiene Panel</span>
                            </div>
                            <span class="tc-spec-badge tc-spec-badge-hospital">Hospital 24/7 Shuttle</span>
                        </div>
                        <div class="tc-spec-grid">
                            <div class="tc-spec-field">
                                <label>24/7 On-Call Emergency Recall Time Limit (Minutes)</label>
                                <input type="number" class="tc-spec-input" data-spec-key="emergency_recall_minutes" value="${specs.emergency_recall_minutes || 30}" placeholder="30">
                                <div class="tc-spec-help">Maximum response time to mobilize standby vehicle for trauma recall</div>
                            </div>
                            <div class="tc-spec-field">
                                <label>Hospital Emergency Transport Desk Contact</label>
                                <input type="text" class="tc-spec-input" data-spec-key="hospital_emergency_desk" value="${specs.hospital_emergency_desk || 'Apollo Main Casualty Desk: 044-28290200'}" placeholder="Casualty Transport Desk">
                            </div>
                            <div class="tc-spec-field" style="grid-column: 1 / -1;">
                                <label>Vehicle Cabin Fumigation & Daily Sanitization Protocol</label>
                                <input type="text" class="tc-spec-input" data-spec-key="cabin_sanitization_protocol" value="${specs.cabin_sanitization_protocol || 'Daily post-shift fumigation with hospital-grade disinfectant'}" placeholder="Sanitization SLA">
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_ac_reliability_sla" data-spec-key="ac_reliability_sla" ${specs.ac_reliability_sla !== false ? 'checked' : ''}>
                                <label for="spec_ac_reliability_sla">100% Climate Control / AC Uptime SLA (Zero Failure)</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_doctor_priority_dispatch" data-spec-key="doctor_priority_dispatch" ${specs.doctor_priority_dispatch !== false ? 'checked' : ''}>
                                <label for="spec_doctor_priority_dispatch">Emergency Priority Dispatch for Surgeons & Anesthesiologists</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_dual_crew_driver_rotation" data-spec-key="dual_crew_driver_rotation" ${specs.dual_crew_driver_rotation !== false ? 'checked' : ''}>
                                <label for="spec_dual_crew_driver_rotation">24/7 Dual-Crew Shift Rotation (Zero Fatigue Policy)</label>
                            </div>
                        </div>
                    </div>
                `;
            } else if (cat === 'government') {
                panelHtml = `
                    <div id="tc-adaptive-spec-panel" class="tc-spec-panel tc-spec-panel-government">
                        <div class="tc-spec-header">
                            <div class="tc-spec-title">
                                <span>🏛️ Government & PSU VIP Protocol Movement Panel</span>
                            </div>
                            <span class="tc-spec-badge tc-spec-badge-government">Govt / PSU Protocol</span>
                        </div>
                        <div class="tc-spec-grid">
                            <div class="tc-spec-field">
                                <label>Government Movement Order / Indent Reference No.</label>
                                <input type="text" class="tc-spec-input" data-spec-key="govt_movement_order_ref" value="${specs.govt_movement_order_ref || 'TN-POL-SEC-2026/088'}" placeholder="Movement Order Ref">
                            </div>
                            <div class="tc-spec-field">
                                <label>Authorized Protocol / Liaison Officer Name</label>
                                <input type="text" class="tc-spec-input" data-spec-key="protocol_officer_name" value="${specs.protocol_officer_name || 'Thiru. S. Ramanathan, Deputy Protocol Officer'}" placeholder="Protocol Officer">
                            </div>
                            <div class="tc-spec-field">
                                <label>Kilometre & Toll Billing Reconciliation Policy</label>
                                <select class="tc-spec-input" data-spec-key="km_billing_clause">
                                    <option value="office_to_office" ${specs.km_billing_clause === 'office_to_office' ? 'selected' : ''}>🏢 Office-to-Office Actual Mileage (No Dead KM)</option>
                                    <option value="garage_to_garage" ${specs.km_billing_clause === 'garage_to_garage' ? 'selected' : ''}>🚗 Garage-to-Garage Mileage with 10 KM Buffer</option>
                                </select>
                            </div>
                            <div class="tc-spec-field">
                                <label>PSU Settlement & TDS Credit Schedule</label>
                                <input type="text" class="tc-spec-input" data-spec-key="psu_tds_credit_terms" value="${specs.psu_tds_credit_terms || '60 Days Credit with Form 16A TDS Certificate'}" placeholder="Credit terms">
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_police_verification_verified" data-spec-key="police_verification_verified" ${specs.police_verification_verified !== false ? 'checked' : ''}>
                                <label for="spec_police_verification_verified">Special Branch Police Background Clearance & PSV Badge</label>
                            </div>
                            <div class="tc-spec-checkbox-group">
                                <input type="checkbox" id="spec_uniform_protocol_mandatory" data-spec-key="uniform_protocol_mandatory" ${specs.uniform_protocol_mandatory !== false ? 'checked' : ''}>
                                <label for="spec_uniform_protocol_mandatory">Crisp White Safari Suit & Name Badge Mandatory</label>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                panelHtml = `
                    <div id="tc-adaptive-spec-panel" class="tc-spec-panel" style="border: 1px solid rgba(148, 163, 184, 0.3); border-top: 4px solid #64748b;">
                        <div class="tc-spec-header">
                            <div class="tc-spec-title">
                                <span>📋 General Bulk Commercial Agreement Specifications</span>
                            </div>
                            <span class="tc-spec-badge" style="background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid #64748b;">General Fleet</span>
                        </div>
                        <div class="tc-spec-help">Standard commercial fleet terms and SLA thresholds apply for this contract category.</div>
                    </div>
                `;
            }

            cardBody.prepend(panelHtml);
        }

        // Handle changes in vertical specification inputs
        $(document).on('change input', '.tc-spec-input', function () {
            const key = $(this).data('spec-key');
            const val = $(this).val();
            updateSpecProp(key, val);
        });

        $(document).on('change', '.tc-spec-checkbox-group input[type="checkbox"]', function () {
            const key = $(this).data('spec-key');
            const val = $(this).is(':checked');
            updateSpecProp(key, val);
        });

        // Listen for direct change on contract_category dropdown
        $(document).on('change', '#id_contract_category', function () {
            const val = $(this).val();
            $('.tc-preset-chip').removeClass('active');
            $(`.tc-preset-chip[data-category="${val}"]`).addClass('active');
            renderGuidance(val);
            renderVerticalSpecPanel(val);
        });

        // 5. Billing Model & Dynamic Rate Context
        function updateBillingModelUi() {
            const model = $('#id_billing_model').val();
            const rateLabel = $('label[for="id_default_rate"]');

            if (model === 'per_trip') {
                rateLabel.html('Base Rate per Trip (₹) <span class="text-danger">*</span>');
            } else if (model === 'per_km') {
                rateLabel.html('Base Rate per KM (₹/km) <span class="text-danger">*</span>');
            } else if (model === 'fixed_monthly') {
                rateLabel.html('Fixed Monthly Lump Sum (₹) <span class="text-danger">*</span>');
            }

            updateCommercialEstimator();
        }

        $(document).on('change', '#id_billing_model', updateBillingModelUi);

        // 6. Commercial Estimator Card in Step 5
        function updateCommercialEstimator() {
            const model = $('#id_billing_model').val();
            const rate = parseFloat($('#id_default_rate').val()) || 0;
            const committed = parseInt($('#id_committed_vehicle_count').val(), 10) || 1;

            let estMonthly = 0;
            let formulaDesc = '';

            if (model === 'fixed_monthly') {
                estMonthly = rate;
                formulaDesc = `Fixed contract lump-sum: ₹${rate.toLocaleString('en-IN')}/month`;
            } else if (model === 'per_trip') {
                const totalTrips = committed * 44;
                estMonthly = totalTrips * rate;
                formulaDesc = `${committed} Vehicles × 44 Trips/mo = ~${totalTrips} trips @ ₹${rate.toLocaleString('en-IN')}/trip`;
            } else if (model === 'per_km') {
                const totalKm = committed * 2200;
                estMonthly = totalKm * rate;
                formulaDesc = `${committed} Vehicles × 2,200 km/mo = ~${totalKm.toLocaleString('en-IN')} KM @ ₹${rate}/km`;
            }

            const step5Pane = $('#step-5-billing-structure-commercial-rates-tab');
            let estimatorEl = $('#tc-commercial-estimator');
            if (!estimatorEl.length && step5Pane.length) {
                estimatorEl = $(`
                    <div id="tc-commercial-estimator" class="tc-estimator-card">
                        <div>
                            <div style="font-weight:700; color:#34d399; margin-bottom:2px;">📊 Projected Monthly Contract Volume</div>
                            <div id="tc-est-formula" style="font-size:0.78rem; color:#94a3b8;">${formulaDesc}</div>
                        </div>
                        <div class="tc-estimator-val" id="tc-est-val">₹${Math.round(estMonthly).toLocaleString('en-IN')} / mo</div>
                    </div>
                `);
                step5Pane.find('.card-body').first().append(estimatorEl);
            } else if (estimatorEl.length) {
                $('#tc-est-formula').text(formulaDesc);
                $('#tc-est-val').text(`₹${Math.round(estMonthly).toLocaleString('en-IN')} / mo`);
            }
        }

        $(document).on('input change', '#id_default_rate, #id_committed_vehicle_count', updateCommercialEstimator);

        // 7. Fuel Escalation Clause Visualizer
        function updateFuelFormula() {
            const enabled = $('#id_fuel_escalation_enabled').is(':checked');
            const basePrice = parseFloat($('#id_base_diesel_price').val()) || 92.50;
            const factor = parseFloat($('#id_fuel_revision_factor').val()) || 0.25;

            const step6Pane = $('#step-6-fuel-escalation-clause-sla-caps-tab');
            let fuelEl = $('#tc-fuel-formula-box');

            if (!fuelEl.length && step6Pane.length) {
                fuelEl = $(`
                    <div id="tc-fuel-formula-box" class="tc-fuel-card"></div>
                `);
                step6Pane.find('.card-body').first().append(fuelEl);
            }

            if (fuelEl.length) {
                if (enabled) {
                    const sampleDiff = 4.0;
                    const sampleAdj = (sampleDiff * factor).toFixed(2);
                    fuelEl.html(`
                        <div style="font-weight:700; margin-bottom:4px;">⛽ Active Fuel Price Adjustment Formula</div>
                        <div style="color:#e2e8f0; font-family:monospace; background:rgba(0,0,0,0.25); padding:6px 10px; border-radius:6px; margin:4px 0;">
                            Billing Adjustment = (Current Diesel Price - Base Diesel Price ₹${basePrice.toFixed(2)}) × Factor ₹${factor.toFixed(4)}/km
                        </div>
                        <div style="font-size:0.78rem; color:#fde68a; margin-top:4px;">
                            💡 Example: If diesel rises to ₹${(basePrice + sampleDiff).toFixed(2)} (+₹${sampleDiff.toFixed(2)}), additional surcharge billed is <strong>+₹${sampleAdj} per KM</strong>.
                        </div>
                    `).show();
                } else {
                    fuelEl.html(`
                        <div style="font-weight:600; color:#94a3b8;">
                            🔒 Fixed Fuel Agreement: Fuel escalation is disabled. Fixed tariff applies regardless of diesel fluctuations.
                        </div>
                    `).show();
                }
            }
        }

        $(document).on('change', '#id_fuel_escalation_enabled', updateFuelFormula);
        $(document).on('input change', '#id_base_diesel_price, #id_fuel_revision_factor', updateFuelFormula);

        // 8. Term Duration Calculator
        function updateTermDuration() {
            const startStr = $('#id_start_date').val();
            const endStr = $('#id_end_date').val();
            const container = $('#id_end_date').closest('.form-group');

            $('.tc-term-badge').remove();

            if (startStr && endStr && container.length) {
                const start = new Date(startStr);
                const end = new Date(endStr);
                const diffTime = end - start;
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                let badgeHtml = '';
                if (diffDays <= 0) {
                    badgeHtml = `<div id="tc-term-indicator" class="tc-term-badge tc-term-invalid">⚠️ End date must be strictly after start date!</div>`;
                } else {
                    const months = (diffDays / 30.4).toFixed(1);
                    badgeHtml = `<div id="tc-term-indicator" class="tc-term-badge tc-term-valid">📅 Contract Term: ${diffDays} Days (~${months} Months)</div>`;
                }
                container.append(badgeHtml);
            }
        }

        $(document).on('change input', '#id_start_date, #id_end_date', updateTermDuration);

        // 9. Fleet Redundancy Gauge
        function updateRedundancy() {
            const committed = parseInt($('#id_committed_vehicle_count').val(), 10) || 1;
            const standby = parseInt($('#id_standby_vehicle_count').val(), 10) || 0;
            const container = $('#id_standby_vehicle_count').closest('.form-group');

            $('.tc-redundancy-badge').remove();

            if (!container.length) return;

            const pct = Math.round((standby / committed) * 100);
            let badgeClass = 'tc-red-healthy';
            let icon = '🛡️';
            let text = `${pct}% Standby Buffer (${committed} Primary + ${standby} Spare) - Optimal Reliability`;

            if (standby === 0) {
                badgeClass = 'tc-red-warning';
                icon = '⚠️';
                text = `0% Standby Buffer (High risk of SLA penalties on vehicle breakdown)`;
            } else if (pct < 15) {
                badgeClass = 'tc-red-warning';
                icon = '⚠️';
                text = `${pct}% Standby Buffer - Lean redundancy`;
            }

            const badgeHtml = `<div id="tc-redundancy-indicator" class="tc-redundancy-badge ${badgeClass}">${icon} ${text}</div>`;
            container.append(badgeHtml);
        }

        $(document).on('input change', '#id_committed_vehicle_count, #id_standby_vehicle_count', updateRedundancy);

        // 10. Add Step Navigation Buttons (Prev / Next) to each pane
        function setupStepNavButtons() {
            const tabLinks = $('#jazzy-tabs .nav-link');
            const panes = $('.tab-content > .tab-pane');

            panes.each(function (idx) {
                const pane = $(this);
                if (pane.find('.tc-step-footer').length) return;

                const prevTab = idx > 0 ? tabLinks.eq(idx - 1) : null;
                const nextTab = idx < tabLinks.length - 1 ? tabLinks.eq(idx + 1) : null;

                let footerHtml = '<div class="tc-step-footer">';
                if (prevTab && prevTab.length) {
                    footerHtml += `<button type="button" class="tc-btn-step tc-btn-step-prev" data-target="${prevTab.attr('href')}">← Previous: ${prevTab.text().trim()}</button>`;
                } else {
                    footerHtml += '<div></div>';
                }

                if (nextTab && nextTab.length) {
                    footerHtml += `<button type="button" class="tc-btn-step tc-btn-step-next" data-target="${nextTab.attr('href')}">Next: ${nextTab.text().trim()} →</button>`;
                } else {
                    footerHtml += '<div></div>';
                }
                footerHtml += '</div>';

                pane.find('.card-body').last().append(footerHtml);
            });
        }

        $(document).on('click', '.tc-btn-step', function (e) {
            e.preventDefault();
            const target = $(this).data('target');
            activateTab(target);
            $('html, body').animate({
                scrollTop: $('#jazzy-tabs').offset().top - 80
            }, 250);
        });

        // Initialize on page ready
        setupStepNavButtons();
        updateBillingModelUi();
        updateFuelFormula();
        updateTermDuration();
        updateRedundancy();

        const initCat = $('#id_contract_category').val() || 'corporate';
        $(`.tc-preset-chip[data-category="${initCat}"]`).addClass('active');
        renderGuidance(initCat);
        renderVerticalSpecPanel(initCat);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDynamicTransportForm);
    } else {
        initDynamicTransportForm();
    }
})();
