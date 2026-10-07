/**
 * Bulk Contract Admin Dynamic JavaScript
 * - Auto-fills agreed day rates from Vehicle Type defaults in the inline table
 * - Real-time contract duration calculator & date validation (start_date to end_date)
 * - Highlights contract billing model guidance
 */
document.addEventListener('DOMContentLoaded', function() {
    let vehicleRates = {};

    // 1. Fetch rates once on load
    fetch('/api/vehicle-types/')
        .then(response => response.json())
        .then(data => {
            vehicleRates = data;
        })
        .catch(err => console.error("Error fetching vehicle rates: ", err));

    // 2. Listen for changes on the inline vehicle rates forms
    const container = document.getElementById('vehicle_rates-group');
    if (container) {
        container.addEventListener('change', function(e) {
            if (e.target && e.target.tagName === 'SELECT' && e.target.id.includes('-vehicle_type')) {
                const selectedVehicleTypeId = e.target.value;
                if (selectedVehicleTypeId && vehicleRates[selectedVehicleTypeId]) {
                    const dayRate = vehicleRates[selectedVehicleTypeId].default_day_rate;
                    const rateInputId = e.target.id.replace('-vehicle_type', '-agreed_day_rate');
                    const rateInput = document.getElementById(rateInputId);
                    
                    if (rateInput && !rateInput.value) {
                        rateInput.value = dayRate;
                    }
                }
            }
        });
    }

    // 3. Contract Duration Calculator & Date Validation
    const startDateInput = document.getElementById('id_start_date');
    const endDateInput = document.getElementById('id_end_date');

    let durationBadge = document.getElementById('contract-duration-badge');
    if (!durationBadge && endDateInput) {
        durationBadge = document.createElement('div');
        durationBadge.id = 'contract-duration-badge';
        durationBadge.style.marginTop = '8px';
        durationBadge.style.fontSize = '13px';
        const parentEl = endDateInput.closest('.form-row, .field-end_date, [class*="field-end_date"]') || endDateInput.parentElement;
        if (parentEl) parentEl.appendChild(durationBadge);
    }

    function calculateContractDuration() {
        if (!startDateInput || !endDateInput || !durationBadge) return;
        const sVal = startDateInput.value;
        const eVal = endDateInput.value;

        if (sVal && eVal) {
            const sParts = sVal.split('-');
            const eParts = eVal.split('-');
            if (sParts.length === 3 && eParts.length === 3) {
                const s = new Date(parseInt(sParts[0], 10), parseInt(sParts[1], 10) - 1, parseInt(sParts[2], 10));
                const e = new Date(parseInt(eParts[0], 10), parseInt(eParts[1], 10) - 1, parseInt(eParts[2], 10));
                const diffTime = e.getTime() - s.getTime();
                const diffDays = Math.round(diffTime / (1000 * 3600 * 24)) + 1;

                if (diffDays < 1) {
                    durationBadge.innerHTML = `<span style="color: #ef4444; background: #450a0a; padding: 4px 10px; border-radius: 4px;">❌ Invalid Dates: End date cannot be before start date!</span>`;
                } else {
                    durationBadge.innerHTML = `<span style="color: #38bdf8; background: #0f172a; padding: 4px 10px; border-radius: 4px; border: 1px solid #1e293b;">📅 Total Duration: <strong>${diffDays} Operating Days</strong> (${sVal} to ${eVal})</span>`;
                }
            }
        } else {
            durationBadge.innerHTML = '';
        }
    }

    if (startDateInput) startDateInput.addEventListener('input', calculateContractDuration);
    if (endDateInput) endDateInput.addEventListener('input', calculateContractDuration);

    setTimeout(calculateContractDuration, 200);
});
