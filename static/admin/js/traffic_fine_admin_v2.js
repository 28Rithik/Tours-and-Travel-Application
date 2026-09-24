/**
 * Traffic Fine Admin Dynamic JavaScript
 * - Selecting Trip auto-populates Vehicle, Driver, and Offence Date
 * - Violation Type auto-suggests Financial Responsibility with policy helper badge
 * - Resilient initialization for Django Head / Jazzmin Body loading
 */
(function() {
    'use strict';

    if (window.__trafficFineDynamicInitialized) {
        return;
    }

    var attempts = 0;
    function initTrafficFineDynamic() {
        if (window.__trafficFineDynamicInitialized) return;

        var $ = (typeof window.django !== 'undefined' && window.django.jQuery)
                ? window.django.jQuery
                : (window.jQuery || window.$);

        if (!$) {
            attempts++;
            if (attempts < 50) {
                setTimeout(initTrafficFineDynamic, 50);
            }
            return;
        }

        window.__trafficFineDynamicInitialized = true;

        $(function() {
            console.log("Travel ERP: Traffic Fine Admin Dynamic JS initialized.");

            const $tripSelect = $('#id_trip');
            const $vehicleSelect = $('#id_vehicle');
            const $driverSelect = $('#id_driver');
            const $dateOffence = $('#id_date_of_offence');
            const $violationSelect = $('#id_violation_type');
            const $responsibilitySelect = $('#id_financial_responsibility');

            // -------------------------------------------------------------
            // 1. Smart Responsibility Helper Box
            // -------------------------------------------------------------
            const $policyHelperBox = $(`
                <div id="traffic-fine-policy-box" style="margin-top: 10px; padding: 12px 16px; border-radius: 6px; background: #1e293b; border-left: 4px solid #f59e0b; color: #cbd5e1; font-size: 13px;">
                    <div style="font-weight: 700; margin-bottom: 4px; color: #f59e0b;" id="policy-box-title">
                        ⚖️ Financial Responsibility Policy
                    </div>
                    <div id="policy-box-desc">
                        Select a violation type to see standard ERP deduction and billing rules (Driver deduction, Customer invoice, or Supplier fleet charge).
                    </div>
                </div>
            `);

            function injectPolicyBox() {
                if ($('#id_financial_responsibility').length && !$('#traffic-fine-policy-box').length) {
                    const $row = $('#id_financial_responsibility').closest('.form-group');
                    if ($row.length) {
                        $row.append($policyHelperBox);
                    } else {
                        $('.field-financial_responsibility').first().append($policyHelperBox);
                    }
                }
            }

            injectPolicyBox();

            const policyRules = {
                'seatbelt_passenger': {
                    resp: 'customer',
                    title: '👤 Bill to Customer (+ On Invoice)',
                    desc: 'Passenger failed to wear seatbelt. Cost is legally and contractually passed onto the customer invoice.',
                    color: '#38bdf8',
                    bg: 'rgba(56, 189, 248, 0.1)'
                },
                'smoking': {
                    resp: 'customer',
                    title: '👤 Bill to Customer (+ On Invoice)',
                    desc: 'Passenger smoking inside vehicle violating transport guidelines. Fine is billed on final customer invoice.',
                    color: '#38bdf8',
                    bg: 'rgba(56, 189, 248, 0.1)'
                },
                'documents': {
                    resp: 'supplier',
                    title: '🏢 Deduct from Supplier (Fleet Owner)',
                    desc: 'Fitness/Permit/Pollution document expired on vehicle. If outsourced, deducted from supplier settlement.',
                    color: '#c084fc',
                    bg: 'rgba(192, 132, 252, 0.1)'
                },
                'speeding': {
                    resp: 'driver',
                    title: '🧑‍✈️ Deduct from Driver (Driver Settlement)',
                    desc: 'Speed limit violation caught by radar/camera. Deducted automatically from driver trip settlement.',
                    color: '#fb923c',
                    bg: 'rgba(251, 146, 60, 0.1)'
                },
                'signal_jumping': {
                    resp: 'driver',
                    title: '🧑‍✈️ Deduct from Driver (Driver Settlement)',
                    desc: 'Red light jumping violation. Deducted from driver trip settlement.',
                    color: '#fb923c',
                    bg: 'rgba(251, 146, 60, 0.1)'
                },
                'wrong_side': {
                    resp: 'driver',
                    title: '🧑‍✈️ Deduct from Driver (Driver Settlement)',
                    desc: 'Wrong-way or illegal overtaking violation. Handled as driver disciplinary deduction.',
                    color: '#fb923c',
                    bg: 'rgba(251, 146, 60, 0.1)'
                },
                'parking': {
                    resp: 'driver',
                    title: '🧑‍✈️ Driver or Company Discretion',
                    desc: 'Illegal or unauthorized parking. Default driver deduction unless customer requested no-parking wait.',
                    color: '#facc15',
                    bg: 'rgba(250, 204, 21, 0.1)'
                }
            };

            function updatePolicyNotice() {
                injectPolicyBox();
                const vType = $violationSelect.val();
                const rule = policyRules[vType];

                if (rule) {
                    $('#policy-box-title').text(rule.title).css('color', rule.color);
                    $('#policy-box-desc').text(rule.desc);
                    $('#traffic-fine-policy-box').css({
                        'border-left-color': rule.color,
                        'background': rule.bg
                    }).show();

                    if (!$responsibilitySelect.val() || $responsibilitySelect.val() === 'driver') {
                        $responsibilitySelect.val(rule.resp);
                    }
                } else {
                    $('#policy-box-title').text('⚖️ Financial Responsibility Policy').css('color', '#f59e0b');
                    $('#policy-box-desc').text('Select a violation type to see standard ERP deduction and billing rules (Driver deduction, Customer invoice, or Supplier fleet charge).');
                    $('#traffic-fine-policy-box').css({
                        'border-left-color': '#f59e0b',
                        'background': '#1e293b'
                    }).show();
                }
            }

            $violationSelect.on('change', updatePolicyNotice);

            // -------------------------------------------------------------
            // 2. Trip Selection Auto-Fill
            // -------------------------------------------------------------
            function handleTripChange() {
                const tripId = $tripSelect.val();
                if (!tripId) return;

                fetch(`/api/trips/${tripId}/`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.vehicle_id && $vehicleSelect.length && !$vehicleSelect.val()) {
                            if ($vehicleSelect.find(`option[value="${data.vehicle_id}"]`).length === 0) {
                                $vehicleSelect.append(new Option(data.vehicle_registration, data.vehicle_id, true, true));
                            }
                            $vehicleSelect.val(data.vehicle_id).trigger('change');
                        }

                        if (data.driver_id && $driverSelect.length && !$driverSelect.val()) {
                            if ($driverSelect.find(`option[value="${data.driver_id}"]`).length === 0) {
                                $driverSelect.append(new Option(data.driver_name, data.driver_id, true, true));
                            }
                            $driverSelect.val(data.driver_id).trigger('change');
                        }

                        if (data.start_date && $dateOffence.length && !$dateOffence.val()) {
                            $dateOffence.val(data.start_date);
                        }
                    })
                    .catch(err => console.error("Error fetching trip details for traffic fine:", err));
            }

            $tripSelect.on('change select2:select', handleTripChange);

            $(document).on('shown.bs.tab click', 'a[data-toggle="tab"], button[data-toggle="tab"], .nav-tabs a', function() {
                setTimeout(updatePolicyNotice, 50);
            });

            setTimeout(function() {
                injectPolicyBox();
                updatePolicyNotice();
            }, 100);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTrafficFineDynamic);
    } else {
        initTrafficFineDynamic();
    }
})();
