/**
 * Booking Form Dynamic JavaScript
 * - Dynamic Package -> PackageInventory (Departure Batches) linkage
 * - Real-time seat availability indicators & batch quick-selector
 * - Auto-fill pickup/drop dates from departure batch & package duration
 * - Live Financial Quote & Balance Calculator (Pax * Price + GST - Advance)
 * - Date validation & warning
 * - Resilient initialization for Django Head / Jazzmin Body loading
 */
(function() {
    'use strict';

    if (window.__bookingDynamicInitialized) {
        return;
    }

    var attempts = 0;
    function initBookingDynamic() {
        if (window.__bookingDynamicInitialized) return;

        var $ = (typeof window.django !== 'undefined' && window.django.jQuery)
                ? window.django.jQuery
                : (window.jQuery || window.$);

        if (!$) {
            attempts++;
            if (attempts < 50) {
                setTimeout(initBookingDynamic, 50);
            }
            return;
        }

        window.__bookingDynamicInitialized = true;

        $(function() {
            console.log("Travel ERP: Booking Form Dynamic JS starting...");

            const $packageSelect = $('#id_package');
            const $inventorySelect = $('#id_package_inventory');
            const $pickupDate = $('#id_pickup_date');
            const $dropDate = $('#id_drop_date');
            const $paxCount = $('#id_pax_count');
            const $quotedPrice = $('#id_quoted_price');
            const $gstRate = $('#id_gst_rate');
            const $billingType = $('#id_billing_type');

            let currentPackageData = null;
            let currentInventoryData = null;

            // -------------------------------------------------------------
            // 1. UI Elements Creation
            // -------------------------------------------------------------
            const $packageContextCard = $(`
                <div id="package-context-card" style="display:none; margin: 12px 0 16px; padding: 14px 18px; border-radius: 8px; background: #1e293b; color: #f8fafc; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 10px;">
                        <div>
                            <span id="pkg-card-title" style="font-size: 15px; font-weight: 700; color: #38bdf8;"></span>
                            <span id="pkg-card-badge" style="margin-left: 8px; font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #0284c7; color: white;"></span>
                        </div>
                        <div id="pkg-card-pricing" style="font-size: 13px; font-weight: 600; color: #4ade80;"></div>
                    </div>
                    <div id="pkg-card-details" style="font-size: 12px; color: #94a3b8; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; margin-bottom: 10px;"></div>
                    <div id="pkg-batches-container" style="border-top: 1px dashed #475569; padding-top: 8px;">
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 6px; font-weight: 600;">
                            🚌 Available Departure Batches (Click to Select):
                        </div>
                        <div id="pkg-batches-list" style="display: flex; flex-wrap: wrap; gap: 6px;"></div>
                    </div>
                </div>
            `);

            const $quoteSummaryBox = $(`
                <div id="quote-live-summary" style="margin: 14px 0 18px; padding: 16px 20px; border-radius: 8px; background: #0f172a; border: 1px solid #1e293b; color: #e2e8f0; display: flex; flex-wrap: wrap; gap: 20px; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);">
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Base Estimation</div>
                        <div id="calc-base-quote" style="font-size: 17px; font-weight: 700; color: #f8fafc;">₹0.00</div>
                        <div id="calc-pax-formula" style="font-size: 11px; color: #94a3b8;">0 pax × ₹0.00</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">GST (<span id="calc-gst-pct">0%</span>)</div>
                        <div id="calc-gst-amount" style="font-size: 17px; font-weight: 700; color: #cbd5e1;">₹0.00</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Total Quoted Value</div>
                        <div id="calc-total-quote" style="font-size: 20px; font-weight: 800; color: #38bdf8;">₹0.00</div>
                    </div>
                    <div style="border-left: 2px solid #334155; padding-left: 20px;">
                        <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Advance Paid / Balance</div>
                        <div id="calc-balance-due" style="font-size: 17px; font-weight: 700; color: #f87171;">₹0.00</div>
                    </div>
                </div>
            `);

            function injectCards() {
                if ($('#id_package').length && !$('#package-context-card').length) {
                    const $pkgRow = $('#id_package').closest('.form-group, .form-row, tr, div');
                    $pkgRow.after($packageContextCard);
                }

                if ($('#id_gst_rate').length && !$('#quote-live-summary').length) {
                    const $gstRow = $('#id_gst_rate').closest('.form-group, .form-row, tr, div');
                    $gstRow.after($quoteSummaryBox);
                }
            }

            injectCards();

            // -------------------------------------------------------------
            // 2. Helper: Date calculations
            // -------------------------------------------------------------
            function addDaysToDate(dateStr, days) {
                if (!dateStr || !days) return null;
                const parts = dateStr.split('-');
                if (parts.length !== 3) return null;
                const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
                d.setDate(d.getDate() + parseInt(days, 10));
                const y = d.getFullYear();
                const m = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                return `${y}-${m}-${day}`;
            }

            // -------------------------------------------------------------
            // 3. Live Quote & Balance Calculation
            // -------------------------------------------------------------
            function updateLiveQuote() {
                injectCards();
                const pax = parseFloat($paxCount.val()) || 0;
                const price = parseFloat($quotedPrice.val()) || 0;
                const gst = parseFloat($gstRate.val()) || 0;
                const billing = $billingType.val() || 'package';

                let baseTotal = 0;
                let formulaText = "";

                if (billing === 'package' && pax > 0 && price > 0) {
                    baseTotal = pax * price;
                    formulaText = `${pax} Pax × ₹${price.toLocaleString('en-IN')}`;
                } else {
                    baseTotal = price;
                    formulaText = price > 0 ? `Fixed Quoted: ₹${price.toLocaleString('en-IN')}` : "Enter price";
                }

                const gstAmount = (baseTotal * gst) / 100;
                const totalQuoted = baseTotal + gstAmount;

                let advance = 0;
                $('input[id$="-amount"]').each(function() {
                    const val = parseFloat($(this).val());
                    if (!isNaN(val)) {
                        advance += val;
                    }
                });

                const existingAdvance = parseFloat($('.field-advance_received .readonly').text().replace(/[^\d.]/g, '')) || 0;
                const totalAdvance = Math.max(advance, existingAdvance);
                const balance = Math.max(0, totalQuoted - totalAdvance);

                $('#calc-base-quote').text(`₹${baseTotal.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`);
                $('#calc-pax-formula').text(formulaText);
                $('#calc-gst-pct').text(`${gst}%`);
                $('#calc-gst-amount').text(`₹${gstAmount.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`);
                $('#calc-total-quote').text(`₹${totalQuoted.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`);

                if (balance === 0 && totalQuoted > 0) {
                    $('#calc-balance-due').html('<span style="color:#4ade80;">✅ Fully Paid</span>');
                } else {
                    $('#calc-balance-due').html(`<span style="color:#f87171;">Due: ₹${balance.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span> <small style="color:#94a3b8; font-size:11px;">(Paid: ₹${totalAdvance.toLocaleString('en-IN')})</small>`);
                }
            }

            $paxCount.on('input change', updateLiveQuote);
            $quotedPrice.on('input change', updateLiveQuote);
            $gstRate.on('input change', updateLiveQuote);
            $billingType.on('change', updateLiveQuote);
            $(document).on('input change', 'input[id$="-amount"]', updateLiveQuote);

            // -------------------------------------------------------------
            // 4. Package Selection Handler
            // -------------------------------------------------------------
            function onPackageChanged() {
                injectCards();
                const packageId = $packageSelect.val();
                if (!packageId) {
                    $('#package-context-card').slideUp(200);
                    currentPackageData = null;
                    return;
                }

                fetch(`/api/packages/${packageId}/inventory/`)
                    .then(r => r.json())
                    .then(data => {
                        currentPackageData = data;
                        const pkg = data.package;
                        const batches = data.inventories;

                        $('#pkg-card-title').text(pkg.name);
                        $('#pkg-card-badge').text(`${pkg.duration_nights}N / ${pkg.duration_days}D • ${pkg.destination || 'Tour'}`);
                        
                        const withFoodPrice = parseFloat(pkg.price_with_food) || 0;
                        const withoutFoodPrice = parseFloat(pkg.price_without_food) || 0;
                        let priceHtml = '';
                        if (withFoodPrice > 0) {
                            priceHtml += `₹${withFoodPrice.toLocaleString('en-IN')}/head <span style="font-size:10px; color:#94a3b8;">(with food)</span>`;
                        } else if (parseFloat(pkg.base_price) > 0) {
                            priceHtml += `₹${parseFloat(pkg.base_price).toLocaleString('en-IN')} <span style="font-size:10px; color:#94a3b8;">(base)</span>`;
                        }
                        $('#pkg-card-pricing').html(priceHtml);

                        $('#pkg-card-details').html(`
                            <div>📍 Destination: <strong style="color:#e2e8f0;">${pkg.destination || '-'}</strong></div>
                            <div>⏱️ Duration: <strong style="color:#e2e8f0;">${pkg.duration_days} Days / ${pkg.duration_nights} Nights</strong></div>
                            <div>🍽️ Without Food: <strong style="color:#e2e8f0;">₹${withoutFoodPrice.toLocaleString('en-IN')}</strong></div>
                        `);

                        const $batchesList = $('#pkg-batches-list');
                        $batchesList.empty();

                        if (!batches || batches.length === 0) {
                            $batchesList.html('<span style="color: #f59e0b; font-size: 12px;">⚠️ No active departure batches scheduled for this package. You can create one in Tour Bus Departures.</span>');
                        } else {
                            batches.forEach(b => {
                                const statusIcon = b.available_seats > 5 ? '🟢' : (b.available_seats > 0 ? '🟡' : '🔴');
                                const isSelected = $inventorySelect.val() == b.id;
                                const activeBorder = isSelected ? 'border: 2px solid #38bdf8; background: #0369a1;' : 'border: 1px solid #475569; background: #334155;';

                                const $batchBtn = $(`
                                    <button type="button" class="batch-select-btn" data-id="${b.id}" style="cursor: pointer; ${activeBorder} color: white; padding: 5px 10px; border-radius: 6px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s;">
                                        <span>${statusIcon} <strong>${b.departure_date}</strong></span>
                                        <span style="background: rgba(0,0,0,0.3); padding: 1px 6px; border-radius: 4px; font-size: 11px;">${b.available_seats}/${b.total_seats} seats</span>
                                        <span style="color: #4ade80; font-weight: 600;">₹${parseFloat(b.price).toLocaleString('en-IN')}</span>
                                    </button>
                                `);

                                $batchBtn.on('click', function(e) {
                                    e.preventDefault();
                                    selectBatch(b);
                                });

                                $batchesList.append($batchBtn);
                            });
                        }

                        $('#package-context-card').slideDown(250);

                        if (!$quotedPrice.val() || parseFloat($quotedPrice.val()) === 0) {
                            const defaultPrice = withFoodPrice > 0 ? withFoodPrice : (parseFloat(pkg.base_price) || 0);
                            if (defaultPrice > 0) {
                                $quotedPrice.val(defaultPrice).trigger('input');
                            }
                        }

                        updateLiveQuote();
                    })
                    .catch(err => console.error("Error fetching package inventory:", err));
            }

            // -------------------------------------------------------------
            // 5. Batch Selection Handler
            // -------------------------------------------------------------
            function selectBatch(batch) {
                currentInventoryData = batch;

                if ($inventorySelect.is('select')) {
                    if ($inventorySelect.find(`option[value="${batch.id}"]`).length === 0) {
                        const newOption = new Option(batch.label, batch.id, true, true);
                        $inventorySelect.append(newOption);
                    }
                    $inventorySelect.val(batch.id).trigger('change');
                }

                $('.batch-select-btn').each(function() {
                    if ($(this).data('id') == batch.id) {
                        $(this).css({ 'border': '2px solid #38bdf8', 'background': '#0369a1' });
                    } else {
                        $(this).css({ 'border': '1px solid #475569', 'background': '#334155' });
                    }
                });

                if (batch.departure_date) {
                    $pickupDate.val(batch.departure_date).trigger('change');

                    if (batch.return_date) {
                        $dropDate.val(batch.return_date).trigger('change');
                    } else if (currentPackageData && currentPackageData.package && currentPackageData.package.duration_nights) {
                        const calculatedDrop = addDaysToDate(batch.departure_date, currentPackageData.package.duration_nights);
                        if (calculatedDrop) {
                            $dropDate.val(calculatedDrop).trigger('change');
                        }
                    }
                }

                if (batch.price && parseFloat(batch.price) > 0) {
                    $quotedPrice.val(parseFloat(batch.price)).trigger('input');
                }

                checkSeatAvailability(batch);
            }

            function checkSeatAvailability(batch) {
                const pax = parseInt($paxCount.val(), 10) || 0;
                $('#seat-warning-box').remove();

                if (batch && pax > batch.available_seats) {
                    const warnBox = $(`
                        <div id="seat-warning-box" style="margin-top: 8px; padding: 8px 12px; border-radius: 6px; background: #7f1d1d; border: 1px solid #dc2626; color: #fecaca; font-size: 12px;">
                            ⚠️ <strong>Seat Capacity Warning:</strong> Booking is for ${pax} pax, but only <strong>${batch.available_seats} seats</strong> remain on this departure batch (${batch.departure_date})!
                        </div>
                    `);
                    $('#id_package_inventory').closest('.form-group, .form-row, tr, div').append(warnBox);
                }
            }

            $paxCount.on('input change', function() {
                if (currentInventoryData) {
                    checkSeatAvailability(currentInventoryData);
                }
            });

            // -------------------------------------------------------------
            // 6. Inventory dropdown change handler
            // -------------------------------------------------------------
            $inventorySelect.on('change select2:select', function() {
                const invId = $(this).val();
                if (!invId) {
                    currentInventoryData = null;
                    $('#seat-warning-box').remove();
                    return;
                }

                fetch(`/api/package-inventory/${invId}/`)
                    .then(r => r.json())
                    .then(data => {
                        currentInventoryData = data;
                        if (data.package_id && (!$packageSelect.val() || $packageSelect.val() != data.package_id)) {
                            if ($packageSelect.find(`option[value="${data.package_id}"]`).length === 0) {
                                $packageSelect.append(new Option(data.package_name, data.package_id, true, true));
                            }
                            $packageSelect.val(data.package_id).trigger('change');
                        }
                        if (data.departure_date && (!$pickupDate.val() || $pickupDate.val() !== data.departure_date)) {
                            $pickupDate.val(data.departure_date);
                        }
                        if (data.return_date && (!$dropDate.val() || $dropDate.val() !== data.return_date)) {
                            $dropDate.val(data.return_date);
                        } else if (data.duration_nights && data.departure_date) {
                            const calculatedDrop = addDaysToDate(data.departure_date, data.duration_nights);
                            if (calculatedDrop) $dropDate.val(calculatedDrop);
                        }
                        checkSeatAvailability(data);
                    })
                    .catch(err => console.error("Error fetching inventory detail:", err));
            });

            $packageSelect.on('change select2:select select2:clear', onPackageChanged);

            // -------------------------------------------------------------
            // 7. Date Validation
            // -------------------------------------------------------------
            function validateDates() {
                const pickup = $pickupDate.val();
                const drop = $dropDate.val();
                $('#date-validation-warning').remove();

                if (pickup && drop && drop < pickup) {
                    const warn = $(`
                        <div id="date-validation-warning" style="margin-top: 6px; padding: 6px 10px; border-radius: 4px; background: #450a0a; border: 1px solid #ef4444; color: #fca5a5; font-size: 12px; font-weight: 600;">
                            ❌ Invalid Dates: Drop date (${drop}) cannot be earlier than pickup date (${pickup})!
                        </div>
                    `);
                    $('#id_drop_date').closest('.form-group, .form-row, tr, div').append(warn);
                }
            }

            $pickupDate.on('change input', validateDates);
            $dropDate.on('change input', validateDates);

            // Jazzmin tab switch re-inject & re-calculate
            var bookingTabTimer = null;
            $(document).on('shown.bs.tab', function() {
                if (bookingTabTimer) clearTimeout(bookingTabTimer);
                bookingTabTimer = setTimeout(function() {
                    injectCards();
                    updateLiveQuote();
                }, 60);
            });

            // Initial trigger
            setTimeout(function() {
                injectCards();
                if ($packageSelect.val()) {
                    onPackageChanged();
                }
                updateLiveQuote();
                validateDates();
            }, 100);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBookingDynamic);
    } else {
        initBookingDynamic();
    }
})();
