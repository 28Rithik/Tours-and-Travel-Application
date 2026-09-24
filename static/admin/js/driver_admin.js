document.addEventListener('DOMContentLoaded', function() {
    const driverTypeSelect = document.querySelector('#id_driver_type');
    if (!driverTypeSelect) return;

    function toggleFields() {
        const type = driverTypeSelect.value;
        
        // Define elements
        const aadharRow = document.querySelector('.field-aadhar_number');
        const employerRow = document.querySelector('.field-employer_party');
        const joiningDateRow = document.querySelector('.field-joining_date');
        const bankAccountRow = document.querySelector('.field-bank_account_number');
        const ifscRow = document.querySelector('.field-ifsc_code');
        const bankNameRow = document.querySelector('.field-bank_name');
        const upiRow = document.querySelector('.field-upi_id');
        const bloodGroupRow = document.querySelector('.field-blood_group');

        // Helper function to show/hide
        function toggleRow(row, show) {
            if (row) {
                row.style.display = show ? 'block' : 'none';
            }
        }

        if (type === 'owned') {
            toggleRow(aadharRow, true);
            toggleRow(employerRow, false);
            toggleRow(joiningDateRow, true);
            toggleRow(bankAccountRow, true);
            toggleRow(ifscRow, true);
            toggleRow(bankNameRow, true);
            toggleRow(upiRow, true);
            toggleRow(bloodGroupRow, true);
        } else if (type === 'supplier') {
            toggleRow(aadharRow, false);
            toggleRow(employerRow, true);
            toggleRow(joiningDateRow, false);
            toggleRow(bankAccountRow, false);
            toggleRow(ifscRow, false);
            toggleRow(bankNameRow, false);
            toggleRow(upiRow, false); 
            toggleRow(bloodGroupRow, true);
        } else if (type === 'temporary') {
            toggleRow(aadharRow, false);
            toggleRow(employerRow, false);
            toggleRow(joiningDateRow, false);
            toggleRow(bankAccountRow, false);
            toggleRow(ifscRow, false);
            toggleRow(bankNameRow, false);
            toggleRow(upiRow, true); 
            toggleRow(bloodGroupRow, false);
        }
    }

    // Run on load
    toggleFields();

    // Run on change
    driverTypeSelect.addEventListener('change', toggleFields);
});
