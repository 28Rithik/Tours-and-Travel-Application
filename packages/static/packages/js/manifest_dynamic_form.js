/**
 * Siva Gayathri Tours -- Passenger Manifest Dynamic Form Enhancements
 * 1. Passport/Visa fields visible only for International tours
 * 2. Category auto-smart (age > 55 -> Senior, age < 18 -> Child)
 * 3. Phone formatter  (+91 XXXXX XXXXX)
 * 4. Bus/Seat read-only info note (system auto-assigns)
 * 5. Passport 6-month expiry validator
 */

document.addEventListener('DOMContentLoaded', function () {
    var jq = window.django ? window.django.jQuery : (window.jQuery || null);
    if (!jq) return;
    var $ = jq;

    var departureSelect   = $('#id_departure');
    var ivExpSelect       = $('#id_iv_expedition');
    var categorySelect    = $('#id_category');
    var genderSelect      = $('#id_gender');
    var ageInput          = $('#id_age');
    var roomInput         = $('#id_room_sharing_number');
    var busInput          = $('#id_bus_assignment');
    var seatInput         = $('#id_seat_number');
    var seniorCb          = $('#id_senior_assistance_needed');
    var passportInput     = $('#id_passport_number');
    var passportExpiryInput = $('#id_passport_expiry_date');
    var visaInput         = $('#id_visa_number');
    var phoneInput        = $('#id_phone');

    var passportRow  = passportInput.closest('.form-row, .field-passport_number, [class*="field-passport_number"], .grp-row');
    var expiryRow    = passportExpiryInput.closest('.form-row, .field-passport_expiry_date, [class*="field-passport_expiry_date"], .grp-row');
    var visaRow      = visaInput.closest('.form-row, .field-visa_number, [class*="field-visa_number"], .grp-row');
    var intlFieldset = $('.grp-international-specs, fieldset:has(#id_passport_number)');

    // =========================================================================
    // 1. Passport & Visa visibility (International tours only)
    // =========================================================================
    function isInternational() {
        var depText = departureSelect.find('option:selected').text().toLowerCase();
        var ivText  = ivExpSelect.find('option:selected').text().toLowerCase();
        var intlKeywords = ['dubai', 'international', 'abu dhabi', 'singapore', 'malaysia', 'thailand', 'sri lanka', 'maldives', 'europe', 'evisa'];
        return intlKeywords.some(function (k) { return depText.includes(k) || ivText.includes(k); });
    }

    function syncInternationalFields() {
        if (isInternational()) {
            intlFieldset.slideDown(200);
            passportRow.show(); expiryRow.show(); visaRow.show();
            passportInput.attr('placeholder', 'Required for International Flights (e.g. V1234567)');
        } else {
            if (!passportInput.val() && !visaInput.val()) {
                intlFieldset.slideUp(200);
                passportRow.hide(); expiryRow.hide(); visaRow.hide();
            } else {
                intlFieldset.slideDown(200);
            }
        }
    }
    departureSelect.on('change', syncInternationalFields);
    ivExpSelect.on('change', syncInternationalFields);
    syncInternationalFields();

    // =========================================================================
    // 2. Bus/Seat info note -- system auto-assigns, user should not fill
    // =========================================================================
    if (busInput.length) {
        $('#sg-bus-note').remove();
        busInput.after(
            '<span id="sg-bus-note" style="display:block;font-size:11px;color:#94a3b8;margin-top:3px;">' +
            'Bus & Seat are AUTO-ASSIGNED by the system. Use the "Auto-Assign" action on the IV Expedition page.' +
            '</span>'
        );
        busInput.attr('readonly', false); // admin may need to override manually
    }

    // =========================================================================
    // 3. Age -> Category smart suggestion
    // =========================================================================
    ageInput.on('input change', function () {
        var age = parseInt($(this).val(), 10);
        if (isNaN(age)) return;
        $('#sg-age-hint').remove();
        var hint = '';
        if (age < 5) {
            hint = 'Infant (may need special fare)';
        } else if (age < 18) {
            hint = 'Minor / Child -- consider setting Category to Child';
            if (categorySelect.val() === 'adult') categorySelect.val('child');
        } else if (age >= 60) {
            hint = 'Senior Citizen -- consider setting Category to Senior';
            if (categorySelect.val() === 'adult') { categorySelect.val('senior'); seniorCb.prop('checked', true); }
        }
        if (hint) {
            ageInput.after('<span id="sg-age-hint" style="display:block;font-size:11px;color:#f59e0b;margin-top:3px;">' + hint + '</span>');
        }
    });

    // =========================================================================
    // 4. Category smart room default
    // =========================================================================
    categorySelect.on('change', function () {
        var cat = $(this).val();
        if (cat === 'student') {
            seniorCb.prop('checked', false);
        } else if (cat === 'faculty') {
            seniorCb.prop('checked', false);
        } else if (cat === 'senior') {
            seniorCb.prop('checked', true);
        }
    });

    // =========================================================================
    // 5. Phone number formatter: on blur, format as +91 XXXXX XXXXX
    // =========================================================================
    phoneInput.on('blur', function () {
        var raw = $(this).val().replace(/\D/g, '');
        if (raw.length === 10) {
            $(this).val('+91 ' + raw.substring(0, 5) + ' ' + raw.substring(5));
        } else if (raw.length === 12 && raw.startsWith('91')) {
            var num = raw.substring(2);
            $(this).val('+91 ' + num.substring(0, 5) + ' ' + num.substring(5));
        }
    });

    // =========================================================================
    // 6. Passport 6-month expiry validator
    // =========================================================================
    passportExpiryInput.on('change input', function () {
        var val = $(this).val();
        if (!val) return;
        var expDate = new Date(val);
        var now     = new Date();
        var sixMo   = new Date(); sixMo.setMonth(now.getMonth() + 6);
        $('#passport-valid-badge').remove();
        if (expDate < now) {
            $(this).after('<span id="passport-valid-badge" class="sg-calc-pill sg-calc-red" style="margin-left:8px;">Passport Expired!</span>');
        } else if (expDate < sixMo) {
            $(this).after('<span id="passport-valid-badge" class="sg-calc-pill sg-calc-red" style="margin-left:8px;">Less than 6 Months Validity! Airlines may reject.</span>');
        } else {
            $(this).after('<span id="passport-valid-badge" class="sg-calc-pill sg-calc-green" style="margin-left:8px;">Valid for Travel</span>');
        }
    });

});
