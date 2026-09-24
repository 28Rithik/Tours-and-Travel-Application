document.addEventListener('DOMContentLoaded', function() {
    const vehicleSelect = document.getElementById('id_vehicle');
    const vehicleTypeInput = document.getElementById('id_vehicle_type');

    if (!vehicleSelect || !vehicleTypeInput) return;

    function handleVehicleChange() {
        if (vehicleSelect.value) {
            vehicleTypeInput.readOnly = true;
            vehicleTypeInput.parentElement.style.opacity = '0.5';
            vehicleTypeInput.title = 'Vehicle type is auto-synced with the selected vehicle';
        } else {
            vehicleTypeInput.readOnly = false;
            vehicleTypeInput.parentElement.style.opacity = '1';
            vehicleTypeInput.title = '';
        }
    }

    handleVehicleChange();
    vehicleSelect.addEventListener('change', handleVehicleChange);
});
