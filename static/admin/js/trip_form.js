/**
 * Trip Form Dynamic JavaScript (Jazzmin custom_js)
 * - Dynamic booking context box and party field locking
 * - Context-aware billing model toggling (fixed, day, km, day_km, custom)
 * - Auto-calculate days count from start_date and end_date
 * - Live Trip Execution P&L & Profit Margin Calculator
 * - Live odometer distance & Extra KM alert
 */
(function() {
    'use strict';

    function initTripForm() {
        var $ = (typeof window.django !== 'undefined' && window.django.jQuery)
                ? window.django.jQuery
                : (window.jQuery || window.$);

        if (!$) {
            setTimeout(initTripForm, 50);
            return;
        }

        $(function() {
            console.log("Travel ERP: Trip Form Dynamic JS active.");

            const $bookingSelect = $('#id_booking');
            const $billingModelSelect = $('#id_billing_model');
            const $partySelect = $('#id_party');
            const $startDate = $('#id_start_date');
            const $endDate = $('#id_end_date');
            const $daysCount = $('#id_days_count');
            const $dayRate = $('#id_day_rate');
            const $kmRate = $('#id_km_rate');
            const $fixedAmount = $('#id_fixed_amount');
            const $driverBata = $('#id_driver_bata');
            const $openingKm = $('#id_opening_km');
            const $closingKm = $('#id_closing_km');

            window.currentBookingExpectedKm = 0;

            // -------------------------------------------------------------
            // 1. Context-Aware Billing Fields
            // -------------------------------------------------------------
            function getBillingRows() {
                return {
                    'day_rate': $('.form-group.field-day_rate'),
                    'km_rate': $('.form-group.field-km_rate'),
                    'fixed_amount': $('.form-group.field-fixed_amount'),
                    'days_count': $('.form-group.field-days_count')
                };
            }

            function updateBillingFields() {
                if (!$billingModelSelect.length) return;
                const model = $billingModelSelect.val();
                const rows = getBillingRows();

                Object.values(rows).forEach($f => {
                    if ($f.length) $f.hide();
                });

                if (model === 'km') {
                    if (rows['km_rate'].length) rows['km_rate'].show();
                } else if (model === 'day') {
                    if (rows['day_rate'].length) rows['day_rate'].show();
                    if (rows['days_count'].length) rows['days_count'].show();
                } else if (model === 'day_km') {
                    if (rows['day_rate'].length) rows['day_rate'].show();
                    if (rows['km_rate'].length) rows['km_rate'].show();
                    if (rows['days_count'].length) rows['days_count'].show();
                } else if (model === 'fixed') {
                    if (rows['fixed_amount'].length) rows['fixed_amount'].show();
                } else if (model === 'custom') {
                    Object.values(rows).forEach($f => {
                        if ($f.length) $f.show();
                    });
                }

                updateLivePnL();
            }

            if ($billingModelSelect.length) {
                $billingModelSelect.on('change', updateBillingFields);
            }

            // -------------------------------------------------------------
            // 2. Auto-calculate Days Count from Dates
            // -------------------------------------------------------------
            function calculateDays() {
                const startVal = $startDate.val();
                const endVal = $endDate.val();

                if (startVal && endVal) {
                    const sParts = startVal.split('-');
                    const eParts = endVal.split('-');
                    if (sParts.length === 3 && eParts.length === 3) {
                        const s = new Date(parseInt(sParts[0], 10), parseInt(sParts[1], 10) - 1, parseInt(sParts[2], 10));
                        const e = new Date(parseInt(eParts[0], 10), parseInt(eParts[1], 10) - 1, parseInt(eParts[2], 10));
                        const diffTime = e.getTime() - s.getTime();
                        const diffDays = Math.round(diffTime / (1000 * 3600 * 24)) + 1;

                        if (diffDays >= 1) {
                            $daysCount.val(diffDays);
                        }
                    }
                }
                updateLivePnL();
            }

            $startDate.on('change input', calculateDays);
            $endDate.on('change input', calculateDays);

            // -------------------------------------------------------------
            // 3. Live Trip P&L and Estimated Revenue Calculator
            // -------------------------------------------------------------
            const $pnlDashboard = $(`
                <div id="trip-live-pnl" style="margin: 14px 0 18px; padding: 16px 20px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-bottom: 10px;">
                        <span style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8;">
                            📊 Live Trip Execution P&L Estimate
                        </span>
                        <span id="pnl-status-badge" style="padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 700;"></span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; text-align: left;">
                        <div>
                            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Est. Revenue</div>
                            <div id="pnl-est-revenue" style="font-size: 17px; font-weight: 800; color: #38bdf8;">₹0.00</div>
                            <div id="pnl-revenue-formula" style="font-size: 11px; color: #94a3b8;">-</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Direct Operating Cost</div>
                            <div id="pnl-est-cost" style="font-size: 17px; font-weight: 800; color: #f87171;">₹0.00</div>
                            <div id="pnl-cost-formula" style="font-size: 11px; color: #94a3b8;">Bata + Fuel + Exp + Supplier</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Est. Gross Profit</div>
                            <div id="pnl-est-profit" style="font-size: 18px; font-weight: 800; color: #4ade80;">₹0.00</div>
                            <div id="pnl-margin-pct" style="font-size: 11px; color: #94a3b8;">Margin: 0%</div>
                        </div>
                    </div>
                </div>
            `);

            function injectPnL() {
                if ($('#id_billing_model').length && !$('#trip-live-pnl').length) {
                    const $row = $('#id_billing_model').closest('.form-group');
                    if ($row.length) {
                        $row.before($pnlDashboard);
                    } else {
                        $('.field-billing_model').first().before($pnlDashboard);
                    }
                }
            }

            injectPnL();

            function updateLivePnL() {
                injectPnL();
                const model = $billingModelSelect.val() || 'day_km';
                const days = parseFloat($daysCount.val()) || 1;
                const dayRate = parseFloat($dayRate.val()) || 0;
                const kmRate = parseFloat($kmRate.val()) || 0;
                const fixedAmt = parseFloat($fixedAmount.val()) || 0;
                const bata = parseFloat($driverBata.val()) || 0;

                const opening = parseFloat($openingKm.val()) || 0;
                const closing = parseFloat($closingKm.val()) || 0;
                const usedKm = (closing > opening) ? (closing - opening) : 0;

                let revenue = 0;
                let revFormula = "";

                if (model === 'fixed') {
                    revenue = fixedAmt;
                    revFormula = `Fixed: ₹${fixedAmt.toLocaleString('en-IN')}`;
                } else if (model === 'day') {
                    revenue = days * dayRate;
                    revFormula = `${days} days × ₹${dayRate.toLocaleString('en-IN')}`;
                } else if (model === 'km') {
                    revenue = usedKm * kmRate;
                    revFormula = `${usedKm} km × ₹${kmRate.toLocaleString('en-IN')}`;
                } else if (model === 'day_km') {
                    revenue = (days * dayRate) + (usedKm * kmRate);
                    revFormula = `(${days}d × ₹${dayRate}) + (${usedKm}km × ₹${kmRate})`;
                } else {
                    revenue = fixedAmt || (days * dayRate) || 0;
                    revFormula = "Custom model";
                }

                let fuelTotal = 0;
                $('input[id*="fuelrecord"][id$="-amount"], input[id*="fuel_records"][id$="-amount"]').each(function() {
                    const v = parseFloat($(this).val());
                    if (!isNaN(v)) fuelTotal += v;
                });

                let expTotal = 0;
                $('input[id*="tripexpense"][id$="-amount"], input[id*="trip_expenses"][id$="-amount"]').each(function() {
                    const v = parseFloat($(this).val());
                    if (!isNaN(v)) expTotal += v;
                });

                let supplierTotal = 0;
                $('input[id*="suppliertripcost"][id$="-agreed_rate"], input[id*="supplier_trip_cost"][id$="-agreed_rate"]').each(function() {
                    const v = parseFloat($(this).val());
                    if (!isNaN(v)) supplierTotal += v;
                });

                const totalCost = bata + fuelTotal + expTotal + supplierTotal;
                const profit = revenue - totalCost;
                const marginPct = (revenue > 0) ? Math.round((profit / revenue) * 100) : 0;

                $('#pnl-est-revenue').text(`₹${revenue.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`);
                $('#pnl-revenue-formula').text(revFormula);

                $('#pnl-est-cost').text(`₹${totalCost.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`);
                $('#pnl-cost-formula').text(`Bata: ₹${bata} | Fuel: ₹${fuelTotal} | Exp: ₹${expTotal + supplierTotal}`);

                $('#pnl-est-profit').text(`₹${profit.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`);
                $('#pnl-margin-pct').text(`Profit Margin: ${marginPct}%`);

                if (profit > 0 && marginPct >= 15) {
                    $('#pnl-status-badge').css({'background': '#166534', 'color': '#bbf7d0'}).text(`🟢 Healthy Margin (${marginPct}%)`);
                    $('#pnl-est-profit').css('color', '#4ade80');
                } else if (profit > 0) {
                    $('#pnl-status-badge').css({'background': '#854d0e', 'color': '#fef08a'}).text(`🟡 Low Margin (${marginPct}%)`);
                    $('#pnl-est-profit').css('color', '#facc15');
                } else if (revenue > 0) {
                    $('#pnl-status-badge').css({'background': '#991b1b', 'color': '#fecaca'}).text(`🔴 Operating at a Loss!`);
                    $('#pnl-est-profit').css('color', '#f87171');
                } else {
                    $('#pnl-status-badge').css({'background': '#334155', 'color': '#94a3b8'}).text(`⚪ Pending Rates`);
                }
            }

            $dayRate.on('input change', updateLivePnL);
            $kmRate.on('input change', updateLivePnL);
            $fixedAmount.on('input change', updateLivePnL);
            $driverBata.on('input change', updateLivePnL);
            $daysCount.on('input change', updateLivePnL);
            $(document).on('input change', 'input[id*="amount"], input[id*="agreed_rate"]', updateLivePnL);

            // -------------------------------------------------------------
            // 4. Live Odometer & Extra KM Calculation
            // -------------------------------------------------------------
            function calculateOdometer() {
                const opening = parseFloat($openingKm.val());
                const closing = parseFloat($closingKm.val());
                const $distDisplay = $('.field-total_distance .readonly');
                const $extraDisplay = $('.field-extra_km .readonly');

                if (!isNaN(opening) && !isNaN(closing) && closing >= opening) {
                    const distance = closing - opening;
                    if ($distDisplay.length) {
                        $distDisplay.html(`<span style="color: #4ade80; font-weight: 700; font-size: 1.1em;">${distance} KM</span>`);
                    }

                    if ($extraDisplay.length && window.currentBookingExpectedKm > 0) {
                        if (distance > window.currentBookingExpectedKm) {
                            const extra = distance - window.currentBookingExpectedKm;
                            $extraDisplay.html(`
                                <span style="color: #ef4444; font-weight: 800; background: #450a0a; padding: 2px 8px; border-radius: 4px;">
                                    ⚠️ +${extra} Extra KM (Cap: ${window.currentBookingExpectedKm} KM)
                                </span>
                            `);
                        } else {
                            $extraDisplay.html(`<span style="color: #94a3b8;">0 KM (Within limit)</span>`);
                        }
                    }
                } else if (!isNaN(opening) && !isNaN(closing) && closing < opening) {
                    if ($distDisplay.length) {
                        $distDisplay.html(`<span style="color: #ef4444; font-weight: 600;">❌ Closing KM cannot be less than Opening KM</span>`);
                    }
                }
                updateLivePnL();
            }

            $openingKm.on('input change', calculateOdometer);
            $closingKm.on('input change', calculateOdometer);

            // -------------------------------------------------------------
            // 5. Booking Context Box
            // -------------------------------------------------------------
            const $bookingContextBox = $(`
                <div id="booking-context-info-box" style="display:none; margin-top: 12px; padding: 14px; border-radius: 6px; background: rgba(56, 189, 248, 0.08); border-left: 4px solid #38bdf8; color: #e2e8f0; font-size: 13px;">
                    <div style="font-weight: 700; color: #38bdf8; margin-bottom: 8px;">
                        ℹ️ Linked Booking Context
                    </div>
                    <div id="booking-context-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px;"></div>
                    <div id="booking-context-notes" style="margin-top: 8px; font-style: italic; color: #cbd5e1;"></div>
                </div>
            `);

            function injectBookingContext() {
                if ($('#id_booking').length && !$('#booking-context-info-box').length) {
                    const $row = $('#id_booking').closest('.form-group');
                    if ($row.length) {
                        $row.append($bookingContextBox);
                    } else {
                        $('.field-booking').first().append($bookingContextBox);
                    }
                }
            }

            injectBookingContext();

            function lockPartyField() {
                if ($bookingSelect.val()) {
                    $partySelect.css({ 'pointer-events': 'none', 'opacity': '0.75' });
                } else {
                    $partySelect.css({ 'pointer-events': 'auto', 'opacity': '1' });
                }
            }

            function handleBookingChange() {
                lockPartyField();
                injectBookingContext();
                const bookingId = $bookingSelect.val();
                if (!bookingId) {
                    $('#booking-context-info-box').slideUp(150);
                    window.currentBookingExpectedKm = 0;
                    return;
                }

                fetch(`/api/bookings/${bookingId}/`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.party_id && $partySelect.val() != data.party_id) {
                            $partySelect.val(data.party_id).trigger('change');
                        }

                        const $pkgSelect = $('#id_package');
                        if (data.package_id && $pkgSelect.length && !$pkgSelect.val()) {
                            if ($pkgSelect.find(`option[value="${data.package_id}"]`).length === 0) {
                                $pkgSelect.append(new Option(data.package_name, data.package_id, true, true));
                            }
                            $pkgSelect.val(data.package_id).trigger('change');
                        }

                        const $invSelect = $('#id_package_inventory');
                        if (data.package_inventory_id && $invSelect.length && !$invSelect.val()) {
                            if ($invSelect.find(`option[value="${data.package_inventory_id}"]`).length === 0) {
                                $invSelect.append(new Option(data.package_inventory_name, data.package_inventory_id, true, true));
                            }
                            $invSelect.val(data.package_inventory_id).trigger('change');
                        }

                        const fieldMap = [
                            { $el: $('#id_guest_name'), val: data.guest_name },
                            { $el: $('#id_travel_pnr'), val: data.travel_pnr },
                            { $el: $('#id_pax_count'), val: data.pax_count },
                            { $el: $('#id_luggage_count'), val: data.luggage_count },
                            { $el: $('#id_start_date'), val: data.start_date },
                            { $el: $('#id_end_date'), val: data.end_date },
                            { $el: $('#id_start_time'), val: data.start_time }
                        ];

                        fieldMap.forEach(item => {
                            if (item.$el.length && (!item.$el.val() || item.$el.val() === '')) {
                                item.$el.val(item.val);
                            }
                        });

                        if (data.billing_model && $billingModelSelect.length && !$billingModelSelect.val()) {
                            $billingModelSelect.val(data.billing_model).trigger('change');
                        }

                        if (data.fixed_amount && parseFloat(data.fixed_amount) > 0 && $fixedAmount.length && parseFloat($fixedAmount.val() || 0) === 0) {
                            $fixedAmount.val(data.fixed_amount);
                        }

                        if (data.expected_km) {
                            window.currentBookingExpectedKm = parseFloat(data.expected_km);
                        }

                        $('#booking-context-grid').html(`
                            <div>📍 <strong>Pickup:</strong> ${data.pickup_location || '-'}</div>
                            <div>🏁 <strong>Drop:</strong> ${data.destination || '-'}</div>
                            <div>🚗 <strong>Vehicle Req:</strong> ${data.vehicle_type || '-'}</div>
                            <div>🛣️ <strong>Journey:</strong> ${data.journey_type || '-'}</div>
                            <div>📦 <strong>Package:</strong> ${data.package_name || 'Standard Hire'}</div>
                            <div>🎯 <strong>Expected Cap:</strong> ${data.expected_km ? data.expected_km + ' KM' : 'Unlimited / Daily'}</div>
                        `);

                        if (data.special_requirements || data.notes) {
                            $('#booking-context-notes').html(`<strong>Notes / Special Reqs:</strong> ${data.special_requirements || data.notes}`);
                        } else {
                            $('#booking-context-notes').empty();
                        }

                        $('#booking-context-info-box').slideDown(200);
                        calculateDays();
                        calculateOdometer();
                        updateLivePnL();
                    })
                    .catch(err => console.error("Error fetching booking details in trip admin:", err));
            }

            $bookingSelect.on('change select2:select select2:clear', handleBookingChange);

            $(document).on('shown.bs.tab click', 'a[data-toggle="tab"], button[data-toggle="tab"], .nav-tabs a', function() {
                setTimeout(function() {
                    injectPnL();
                    injectBookingContext();
                    updateBillingFields();
                    updateLivePnL();
                }, 80);
            });

            setTimeout(function() {
                injectPnL();
                injectBookingContext();
                updateBillingFields();
                lockPartyField();
                if ($bookingSelect.val()) {
                    fetch(`/api/bookings/${$bookingSelect.val()}/`)
                        .then(r => r.json())
                        .then(data => {
                            if (data.expected_km) window.currentBookingExpectedKm = parseFloat(data.expected_km);
                            $('#booking-context-grid').html(`
                                <div>📍 <strong>Pickup:</strong> ${data.pickup_location || '-'}</div>
                                <div>🏁 <strong>Drop:</strong> ${data.destination || '-'}</div>
                                <div>🚗 <strong>Vehicle Req:</strong> ${data.vehicle_type || '-'}</div>
                                <div>🛣️ <strong>Journey:</strong> ${data.journey_type || '-'}</div>
                                <div>📦 <strong>Package:</strong> ${data.package_name || 'Standard Hire'}</div>
                                <div>🎯 <strong>Expected Cap:</strong> ${data.expected_km ? data.expected_km + ' KM' : 'Unlimited / Daily'}</div>
                            `);
                            $('#booking-context-info-box').show();
                            calculateOdometer();
                            updateLivePnL();
                        });
                } else {
                    calculateOdometer();
                    updateLivePnL();
                }
            }, 100);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTripForm);
    } else {
        initTripForm();
    }
})();
