document.addEventListener('DOMContentLoaded', function() {
    const canDriveCheckbox = document.getElementById('id_can_drive');
    const licenseFieldset = Array.from(document.querySelectorAll('fieldset')).find(
        fs => fs.querySelector('h2') && fs.querySelector('h2').textContent.includes('License Details')
    );

    if (!canDriveCheckbox || !licenseFieldset) return;

    function toggleFields() {
        if (canDriveCheckbox.checked) {
            licenseFieldset.style.display = '';
        } else {
            licenseFieldset.style.display = 'none';
        }
    }

    toggleFields();
    canDriveCheckbox.addEventListener('change', toggleFields);
    canDriveCheckbox.addEventListener('input', toggleFields);

    var lastChecked = canDriveCheckbox.checked;
    setInterval(function() {
        if (canDriveCheckbox.checked !== lastChecked) {
            lastChecked = canDriveCheckbox.checked;
            toggleFields();
        }
    }, 200);
});

