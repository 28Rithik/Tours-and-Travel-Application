document.addEventListener('DOMContentLoaded', function() {
    const partyTypeSelect = document.getElementById('id_party_type');
    const billingFieldset = document.querySelector('fieldset.b2b-corporate-billing');
    
    function toggleBillingFields() {
        if (!partyTypeSelect || !billingFieldset) return;
        
        const type = partyTypeSelect.value;
        if (type === 'individual') {
            billingFieldset.style.display = 'none';
        } else {
            billingFieldset.style.display = 'block';
        }
    }
    
    // Initial toggle
    toggleBillingFields();
    
    // Toggle on change
    if (partyTypeSelect) {
        partyTypeSelect.addEventListener('change', toggleBillingFields);
    }
});
