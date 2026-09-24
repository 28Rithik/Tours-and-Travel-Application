(function() {
    function getCsrfToken() {
        var cookieVal = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var c = cookies[i].trim();
                if (c.substring(0, 10) === 'csrftoken=') {
                    cookieVal = decodeURIComponent(c.substring(10));
                    break;
                }
            }
        }
        if (!cookieVal) {
            var inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (inp) cookieVal = inp.value;
        }
        return cookieVal;
    }

    window.toggleVehicleStatus = function(vehicleId, checkboxElem) {
        var labelElem = document.getElementById('status-label-' + vehicleId);
        var originalChecked = !checkboxElem.checked;
        var token = getCsrfToken();

        checkboxElem.disabled = true;
        if (labelElem) {
            labelElem.style.opacity = '0.5';
            labelElem.textContent = 'Updating...';
        }

        fetch('/admin/core/vehicle/' + vehicleId + '/toggle-status/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': token
            }
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            checkboxElem.disabled = false;
            if (labelElem) labelElem.style.opacity = '1';

            if (data.success) {
                var isAvail = (data.status === 'available');
                checkboxElem.checked = isAvail;
                if (labelElem) {
                    labelElem.textContent = data.label;
                    if (isAvail) {
                        labelElem.className = 'vehicle-status-label text-success font-weight-bold';
                    } else {
                        labelElem.className = 'vehicle-status-label text-muted';
                    }
                }
            } else {
                // Revert
                checkboxElem.checked = originalChecked;
                if (labelElem) {
                    labelElem.textContent = originalChecked ? 'Available' : 'Not Available';
                    labelElem.className = originalChecked ? 'vehicle-status-label text-success font-weight-bold' : 'vehicle-status-label text-muted';
                }
                alert(data.error || 'Failed to update vehicle status.');
            }
        })
        .catch(function(err) {
            checkboxElem.disabled = false;
            checkboxElem.checked = originalChecked;
            if (labelElem) {
                labelElem.style.opacity = '1';
                labelElem.textContent = originalChecked ? 'Available' : 'Not Available';
            }
            console.error('Vehicle toggle error:', err);
            alert('Network error while updating vehicle status.');
        });
    };
})();
