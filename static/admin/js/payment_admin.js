(function() {
    'use strict';

    // ============================================================
    // LEVEL 1: XHR-level patch — works regardless of which
    // jQuery instance or library Select2 uses internally.
    // ============================================================
    var _xhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        if (url &&
            url.indexOf('/admin/autocomplete/') !== -1 &&
            window._paymentPartyId)
        {
            var dependentPatterns = [
                'field_name=booking',
                'field_name=trip',
                'field_name=contract_trip',
                'field_name=statement'
            ];
            var needsFilter = dependentPatterns.some(function(p) {
                return url.indexOf(p) !== -1;
            });
            if (needsFilter) {
                var sep = url.indexOf('?') !== -1 ? '&' : '?';
                url = url + sep + 'party_id=' + encodeURIComponent(window._paymentPartyId);
            }
        }
        return _xhrOpen.apply(this, arguments);
    };

    // ============================================================
    // LEVEL 2: fetch()-level patch (belt-and-suspenders)
    // ============================================================
    if (window.fetch) {
        var _fetch = window.fetch;
        window.fetch = function(url, opts) {
            if (typeof url === 'string' &&
                url.indexOf('/admin/autocomplete/') !== -1 &&
                window._paymentPartyId)
            {
                var dependentPatterns = [
                    'field_name=booking', 'field_name=trip',
                    'field_name=contract_trip', 'field_name=statement'
                ];
                var needsFilter = dependentPatterns.some(function(p) {
                    return url.indexOf(p) !== -1;
                });
                if (needsFilter) {
                    var sep = url.indexOf('?') !== -1 ? '&' : '?';
                    url = url + sep + 'party_id=' + encodeURIComponent(window._paymentPartyId);
                }
            }
            return _fetch.apply(this, [url, opts]);
        };
    }

    // ============================================================
    // LEVEL 3: UI logic — party → clear dependents + auto-fill
    // ============================================================
    var dependentFields = ['booking', 'trip', 'contract_trip', 'statement'];

    function initPaymentForm($) {
        // Seed on page load (editing an existing payment)
        window._paymentPartyId = $('#id_party').val() || null;

        // Update whenever party changes
        $('#id_party').on('change select2:select select2:unselect', function() {
            window._paymentPartyId = $(this).val() || null;
            dependentFields.forEach(function(field) {
                var $f = $('#id_' + field);
                if ($f.length) {
                    $f.val(null).trigger('change');
                }
            });
        });

        // Auto-fill amount + payment type when a booking/trip is selected
        dependentFields.forEach(function(field) {
            var $el = $('#id_' + field);
            if (!$el.length) return;
            $el.on('change select2:select', function() {
                var id = $(this).val();
                if (!id) return;
                $.ajax({
                    url: '/api/payments/context/?' + field + '_id=' + id,
                    method: 'GET',
                    success: function(data) {
                        if (data.party_id && !$('#id_party').val()) {
                            $('#id_party').val(data.party_id).trigger('change');
                        }
                        if (data.balance && $('#id_amount').val() === '') {
                            $('#id_amount').val(data.balance);
                        }
                        var $type = $('#id_payment_type');
                        if ($type.length && !$type.val()) {
                            $type.val(field === 'booking' ? 'advance' : 'customer_receipt').trigger('change');
                        }
                    }
                });
            });
        });
    }

    function bootstrap() {
        var $ = (window.django && window.django.jQuery) || window.jQuery || window.$;
        if ($) {
            initPaymentForm($);
        } else {
            var attempts = 0;
            var interval = setInterval(function() {
                attempts++;
                var jq = (window.django && window.django.jQuery) || window.jQuery || window.$;
                if (jq) {
                    clearInterval(interval);
                    initPaymentForm(jq);
                } else if (attempts > 30) {
                    clearInterval(interval);
                }
            }, 100);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
        bootstrap();
    }

})();

