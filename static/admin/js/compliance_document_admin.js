document.addEventListener("DOMContentLoaded", function() {
    const documentTypeField = document.querySelector("#id_document_type");
    if (!documentTypeField) return;

    const insuranceFields = [
        document.querySelector(".field-insurance_provider"),
        document.querySelector(".field-premium_amount"),
        document.querySelector(".field-coverage_type")
    ];
    
    const permitFields = [
        document.querySelector(".field-permit_states")
    ];

    function updateFormVisibility() {
        const type = documentTypeField.value;
        
        insuranceFields.forEach(el => { if (el) el.style.display = 'none'; });
        permitFields.forEach(el => { if (el) el.style.display = 'none'; });
        
        if (type === 'insurance') {
            insuranceFields.forEach(el => { if (el) el.style.display = ''; });
        } else if (type === 'permit') {
            permitFields.forEach(el => { if (el) el.style.display = ''; });
        }
    }

    documentTypeField.addEventListener("change", updateFormVisibility);
    documentTypeField.addEventListener("input", updateFormVisibility);
    updateFormVisibility();

    var lastType = documentTypeField.value;
    setInterval(function() {
        if (documentTypeField.value !== lastType) {
            lastType = documentTypeField.value;
            updateFormVisibility();
        }
    }, 200);
});

