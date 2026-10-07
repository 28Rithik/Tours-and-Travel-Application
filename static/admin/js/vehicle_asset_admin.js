document.addEventListener("DOMContentLoaded", function() {
    const assetTypeField = document.querySelector("#id_asset_type");
    const positionField = document.querySelector("#id_position");

    if (!assetTypeField || !positionField) return;

    function updatePositionOptions() {
        const type = assetTypeField.value;
        const options = positionField.options;
        
        for (let i = 0; i < options.length; i++) {
            const val = options[i].value;
            if (!val) continue; // Skip the empty choice

            if (type === 'battery') {
                if (val === 'engine_bay') {
                    options[i].style.display = '';
                } else {
                    options[i].style.display = 'none';
                    if (positionField.value === val) {
                        positionField.value = ''; // Reset if invalid selected
                    }
                }
            } else if (type === 'tyre') {
                if (val === 'engine_bay') {
                    options[i].style.display = 'none';
                    if (positionField.value === val) {
                        positionField.value = '';
                    }
                } else {
                    options[i].style.display = '';
                }
            } else {
                options[i].style.display = ''; // Show all if nothing selected
            }
        }
    }

    assetTypeField.addEventListener("change", updatePositionOptions);
    assetTypeField.addEventListener("input", updatePositionOptions);
    updatePositionOptions();

    var lastType = assetTypeField.value;
    setInterval(function() {
        if (assetTypeField.value !== lastType) {
            lastType = assetTypeField.value;
            updatePositionOptions();
        }
    }, 200);
});

