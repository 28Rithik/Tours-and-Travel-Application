/**
 * Bulk Contract Day Admin Dynamic JavaScript
 * - Contract Context Banner (Customer, Duration, Status, Agreed Rates)
 * - Real-Time Date Range Validation against Parent Contract
 * - Live Requirements vs Scheduled Trips Fulfillment Gauge
 * - Inline Rate Auto-populate & Guidance
 */
(function() {
    'use strict';

    if (window.__bulkContractDayDynamicInitialized) {
        return;
    }

    var attempts = 0;
    function initBulkContractDayDynamic() {
        if (window.__bulkContractDayDynamicInitialized) return;

        var $ = (typeof window.django !== 'undefined' && window.django.jQuery)
                ? window.django.jQuery
                : (window.jQuery || window.$);

        if (!$) {
            attempts++;
            if (attempts < 50) {
                setTimeout(initBulkContractDayDynamic, 50);
            }
            return;
        }

        window.__bulkContractDayDynamicInitialized = true;

        $(function() {
            console.log("Travel ERP: Bulk Contract Day Admin Dynamic JS starting...");

            const $contractSelect = $('#id_contract');
            const $dateInput = $('#id_date');

            let currentContractData = null;

            // -------------------------------------------------------------
            // 1. UI Elements: Contract Context Card & Fulfillment Dashboard
            // -------------------------------------------------------------
            const $contractCard = $(`
                <div id="contract-context-banner" style="display:none; margin: 12px 0 16px; padding: 14px 18px; border-radius: 8px; background: #1e293b; color: #f8fafc; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 10px;">
                        <div>
                            <span id="contract-card-name" style="font-size: 15px; font-weight: 700; color: #38bdf8;"></span>
                            <span id="contract-card-type" style="margin-left: 8px; font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #0284c7; color: white;"></span>
                        </div>
                        <div id="contract-card-customer" style="font-size: 13px; font-weight: 600; color: #cbd5e1;"></div>
                    </div>
                    <div id="contract-card-details" style="font-size: 12px; color: #94a3b8; display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 10px;"></div>
                    <div id="contract-rates-container" style="border-top: 1px dashed #475569; padding-top: 8px;">
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 6px; font-weight: 600;">
                            💰 Agreed Vehicle Day Rates Under This Contract:
                        </div>
                        <div id="contract-rates-list" style="display: flex; flex-wrap: wrap; gap: 8px;"></div>
                    </div>
                </div>
            `);

            const $fulfillmentWidget = $(`
                <div id="day-fulfillment-widget" style="margin: 14px 0 18px; padding: 16px 20px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-bottom: 12px;">
                        <span style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8;">
                            📋 Operating Day Fleet Dispatch Fulfillment
                        </span>
                        <span id="fulfillment-status-badge" style="padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 700;"></span>
                    </div>
                    <div id="fulfillment-stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 10px;">
                        <div>
                            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Vehicles Demanded</div>
                            <div id="fl-total-demanded" style="font-size: 18px; font-weight: 800; color: #f8fafc;">0</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Trips Scheduled</div>
                            <div id="fl-total-scheduled" style="font-size: 18px; font-weight: 800; color: #38bdf8;">0</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Pending Allocation</div>
                            <div id="fl-total-pending" style="font-size: 18px; font-weight: 800; color: #f87171;">0</div>
                        </div>
                    </div>
                    <div id="fulfillment-breakdown" style="border-top: 1px solid #1e293b; padding-top: 8px; font-size: 12px; color: #cbd5e1;"></div>
                </div>
            `);

            function injectElements() {
                if ($('#id_contract').length && !$('#contract-context-banner').length) {
                    const $cRow = $('#id_contract').closest('.form-group, .form-row, tr, div');
                    $cRow.after($contractCard);
                }

                if ($('#id_date').length && !$('#day-fulfillment-widget').length) {
                    const $dRow = $('#id_date').closest('.form-group, .form-row, tr, div');
                    $dRow.after($fulfillmentWidget);
                }
            }

            injectElements();

            // -------------------------------------------------------------
            // 2. Date Range Validation against Parent Contract
            // -------------------------------------------------------------
            function validateContractDate() {
                $('#contract-date-warning').remove();
                if (!currentContractData || !$dateInput.val()) return;

                const dayDate = $dateInput.val();
                const startDate = currentContractData.start_date;
                const endDate = currentContractData.end_date;

                if (dayDate < startDate || dayDate > endDate) {
                    const $warn = $(`
                        <div id="contract-date-warning" style="margin-top: 6px; padding: 8px 12px; border-radius: 4px; background: #450a0a; border: 1px solid #ef4444; color: #fca5a5; font-size: 12px; font-weight: 600;">
                            ❌ Out-of-Bounds: Operating date (${dayDate}) does not fall inside Contract duration (${startDate} to ${endDate})!
                        </div>
                    `);
                    $dateInput.closest('.form-group, .form-row, tr, div').append($warn);
                }
            }

            $dateInput.on('input change', validateContractDate);

            // -------------------------------------------------------------
            // 3. Contract Change Handler & API Fetch
            // -------------------------------------------------------------
            function onContractChanged() {
                injectElements();
                const contractId = $contractSelect.val();
                if (!contractId) {
                    $('#contract-context-banner').slideUp(200);
                    currentContractData = null;
                    validateContractDate();
                    return;
                }

                fetch(`/api/bulk-contracts/${contractId}/`)
                    .then(r => r.json())
                    .then(data => {
                        currentContractData = data;
                        $('#contract-card-name').text(data.name);
                        $('#contract-card-type').text(data.contract_type_display);
                        $('#contract-card-customer').text(`👤 Client: ${data.customer_name}`);

                        $('#contract-card-details').html(`
                            <div>📅 Contract Range: <strong style="color:#e2e8f0;">${data.start_date} to ${data.end_date}</strong></div>
                            <div>💳 Billing Model: <strong style="color:#e2e8f0;">${data.billing_model}</strong></div>
                            <div>⚡ Status: <strong style="color:#38bdf8; text-transform:capitalize;">${data.status}</strong></div>
                        `);

                        const $ratesList = $('#contract-rates-list');
                        $ratesList.empty();

                        if (!data.rates || data.rates.length === 0) {
                            $ratesList.html('<span style="color: #94a3b8; font-size: 12px;">No specific agreed vehicle rates defined for this contract.</span>');
                        } else {
                            data.rates.forEach(r => {
                                $ratesList.append(`
                                    <span style="background: #334155; border: 1px solid #475569; padding: 4px 10px; border-radius: 6px; font-size: 12px; color: #f8fafc;">
                                        🚗 <strong>${r.vehicle_type_name}</strong>: <span style="color: #4ade80; font-weight: 700;">₹${parseFloat(r.agreed_day_rate).toLocaleString('en-IN')}/day</span>
                                    </span>
                                `);
                            });
                        }

                        $('#contract-context-banner').slideDown(250);
                        validateContractDate();
                        updateFulfillment();
                    })
                    .catch(err => console.error("Error fetching bulk contract context:", err));
            }

            $contractSelect.on('change select2:select', onContractChanged);

            // -------------------------------------------------------------
            // 4. Live Fulfillment Calculator
            // -------------------------------------------------------------
            function updateFulfillment() {
                injectElements();

                // 1. Calculate required quantities from requirements inline
                let totalDemanded = 0;
                const demandMap = {}; // vehicle_type_text -> count

                $('input[id*="requirements-"][id$="-quantity"]').each(function() {
                    const $qtyInput = $(this);
                    const qty = parseInt($qtyInput.val(), 10) || 0;
                    if (qty > 0) {
                        const rowId = $qtyInput.attr('id').replace('-quantity', '');
                        const $vTypeSelect = $(`#${rowId}-vehicle_type`);
                        const typeText = $vTypeSelect.find('option:selected').text() || 'Vehicle';
                        totalDemanded += qty;
                        demandMap[typeText] = (demandMap[typeText] || 0) + qty;
                    }
                });

                // 2. Calculate scheduled trips from trips inline
                let totalScheduled = 0;
                $('select[id*="trips-"][id$="-vehicle"], select[id*="trips-"][id$="-driver"]').each(function() {
                    // Count unique non-empty trip rows
                    if ($(this).attr('id').endsWith('-vehicle')) {
                        if ($(this).val()) {
                            totalScheduled++;
                        }
                    }
                });

                // Also count any trip rows in change view
                const existingTripRows = $('#trips-group .tabular tbody tr:not(.empty-form)').length;
                const effectiveScheduled = Math.max(totalScheduled, existingTripRows);

                const pending = Math.max(0, totalDemanded - effectiveScheduled);

                $('#fl-total-demanded').text(totalDemanded);
                $('#fl-total-scheduled').text(effectiveScheduled);
                $('#fl-total-pending').text(pending);

                let statusBadgeHtml = '';
                if (totalDemanded === 0) {
                    statusBadgeHtml = '<span style="background: #334155; color: #94a3b8;">⚪ No Requirements Set</span>';
                } else if (pending === 0 && effectiveScheduled >= totalDemanded) {
                    statusBadgeHtml = '<span style="background: #166534; color: #bbf7d0;">🟢 100% Fulfilled & Ready</span>';
                } else if (effectiveScheduled > 0) {
                    statusBadgeHtml = `<span style="background: #854d0e; color: #fef08a;">🟡 Partially Assigned (${pending} Remaining)</span>`;
                } else {
                    statusBadgeHtml = `<span style="background: #991b1b; color: #fecaca;">🔴 0/${totalDemanded} Assigned (Action Required)</span>`;
                }

                $('#fulfillment-status-badge').html(statusBadgeHtml);

                // Summary text
                const demandItems = Object.keys(demandMap).map(k => `${demandMap[k]}x ${k}`);
                if (demandItems.length > 0) {
                    $('#fulfillment-breakdown').html(`
                        <strong>Requested Fleet:</strong> ${demandItems.join(', ')} • 
                        <span style="color:#38bdf8;">Tip: Use the admin action <em>"Generate Scheduled Trips from Vehicle Requirements"</em> to automatically spawn all missing trip records!</span>
                    `);
                } else {
                    $('#fulfillment-breakdown').html('<span style="color:#94a3b8;">Add vehicle requirements in the table below to set fleet demand for this operating day.</span>');
                }
            }

            $(document).on('input change', 'input[id*="requirements-"], select[id*="requirements-"], select[id*="trips-"]', updateFulfillment);

            // Tab switch re-check
            var tabTimer = null;
            $(document).on('shown.bs.tab', function() {
                if (tabTimer) clearTimeout(tabTimer);
                tabTimer = setTimeout(function() {
                    injectElements();
                    validateContractDate();
                    updateFulfillment();
                }, 60);
            });

            // Initial trigger
            setTimeout(function() {
                injectElements();
                if ($contractSelect.val()) {
                    onContractChanged();
                }
                updateFulfillment();
            }, 100);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBulkContractDayDynamic);
    } else {
        initBulkContractDayDynamic();
    }
})();
