/**
 * Siva Gayathri Tours and Travels — Dynamic Category-Adaptive Package Automation
 * Provides category intelligence banners, 1-click presets, adaptive placeholders,
 * live tab filtering, and smart jump navigation.
 */

(function () {
    function initPackageForm() {
        const $ = window.django ? window.django.jQuery : (window.jQuery || null);
        if (!$) {
            setTimeout(initPackageForm, 40);
            return;
        }

        const categorySelect = $('#id_category');
    const isDevotionalCb = $('#id_is_devotional');
    const isIntlCb = $('#id_is_international');
    const pricingTypeSelect = $('#id_pricing_type');
    const durationDaysInput = $('#id_duration_days');
    const durationNightsInput = $('#id_duration_nights');
    const nameInput = $('#id_name');
    const destinationInput = $('#id_destination');

    const tabsContainer = $('#jazzy-tabs');
    const inclusionsField = $('#id_inclusions');
    const exclusionsField = $('#id_exclusions');
    const termsField = $('#id_terms_and_conditions');

    const apInput = $('#id_price_with_food');
    const epInput = $('#id_price_without_food');
    const baseInput = $('#id_base_price');
    const templateSelect = $('#id_template');
    const transitModeSelect = $('#id_transit_mode');
    const defaultVehicleSelect = $('#id_default_vehicle_type');
    const mealPlanSelect = $('#id_meal_plan');
    const roomSharingSelect = $('#id_room_sharing_type');
    const currencyCodeSelect = $('#id_currency_code');

    // Tab Links in Jazzmin navigation
    const devotionalTabLink = $('a[href*="devotional"], a[href*="temple-darshan"]').closest('.nav-item, li');
    const intlTabLink = $('a[href*="international"]').closest('.nav-item, li');
    const accommodationTabLink = $('a[href*="accommodation"]').closest('.nav-item, li');

    // Scoped Elements
    function getDevotionalElements() {
        return $('.grp-devotional-specs, #temple-darshan-slots-tab, #devotional-pilgrimage-specifications-tab, #temple_slots-group, [id*="temple_slots"], [id*="templedarshanslot"]');
    }
    function getIntlElements() {
        return $('.grp-international-specs, #international-tour-specifications-tab, #international-document-checklist-tab, #intl_documents-group, [id*="intl_documents"], [id*="internationaldocumentchecklist"]');
    }

    // =========================================================================
    // 1. Preset Toolbar Construction
    // =========================================================================
    const presetBarHtml = `
        <div class="sg-unified-toolbar">
            <div class="sg-toolbar-left">
                <span class="sg-preset-bar-title"><i class="fas fa-bolt text-warning mr-1"></i> Presets:</span>
                <button type="button" class="sg-btn-preset sg-btn-devotional" id="btn-preset-devotional">
                    <i class="fas fa-om"></i> Devotional
                </button>
                <button type="button" class="sg-btn-preset sg-btn-iv" id="btn-preset-iv">
                    <i class="fas fa-graduation-cap"></i> College IV
                </button>
                <button type="button" class="sg-btn-preset sg-btn-intl" id="btn-preset-intl">
                    <i class="fas fa-plane"></i> Intl Tour
                </button>
                <button type="button" class="sg-btn-preset sg-btn-holiday" id="btn-preset-holiday">
                    <i class="fas fa-mountain"></i> Hill Station
                </button>
                <button type="button" class="sg-btn-preset sg-btn-local" id="btn-preset-local">
                    <i class="fas fa-car"></i> 1-Day Local
                </button>
                <span id="sg-preset-toast" class="sg-preset-toast" style="display: none;"></span>
            </div>
            <div class="sg-toolbar-right">
                <span id="snap-name" style="color:#cbd5e1; font-weight:600; font-size:12px; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="Package Name">Tour Package</span>
                <span id="snap-duration" class="badge badge-info" style="font-size:11px;">0N / 1D</span>
                <span id="snap-price" class="sg-snap-price-pill">₹0</span>
                <button type="button" class="sg-btn-action sg-btn-proposal" id="sg-btn-open-preview" title="Live 5-page proposal PDF preview">
                    <i class="fas fa-eye mr-1"></i> Proposal
                </button>
                <button type="button" class="sg-btn-action sg-btn-wa" id="sg-btn-open-whatsapp" title="1-Click WhatsApp briefing generator">
                    <i class="fab fa-whatsapp mr-1"></i> WhatsApp
                </button>
            </div>
        </div>
        <div id="sg-category-intel-card" class="sg-category-intel-card" style="display: none;"></div>
    `;

        if ($('.sg-unified-toolbar').length === 0) {
            if (tabsContainer.length) {
                tabsContainer.before(presetBarHtml);
            } else if ($('#jazzy-tabs').length) {
                $('#jazzy-tabs').before(presetBarHtml);
            } else if ($('.nav-tabs').length) {
                $('.nav-tabs').first().before(presetBarHtml);
            } else if ($('#content-main').length) {
                $('#content-main').prepend(presetBarHtml);
            } else if (inclusionsField.length) {
                inclusionsField.closest('.form-row, .form-group').before(presetBarHtml);
            }
        }

    const intelCard = $('#sg-category-intel-card');
    const toast = $('#sg-preset-toast');

    function showToast(msg) {
        toast.html(msg).stop(true, true).fadeIn(200).delay(2800).fadeOut(400);
    }

    function setActivePresetButton(cat) {
        $('.sg-btn-preset').removeClass('sg-btn-active');
        if (cat === 'devotional') {
            $('#btn-preset-devotional').addClass('sg-btn-active');
        } else if (cat === 'college_iv' || cat === 'fixed_departure') {
            $('#btn-preset-iv').addClass('sg-btn-active');
        } else if (cat === 'international') {
            $('#btn-preset-intl').addClass('sg-btn-active');
        } else if (cat === 'hill_station' || cat === 'holiday' || cat === 'family_vacation' || cat === 'corporate_offsite') {
            $('#btn-preset-holiday').addClass('sg-btn-active');
        } else if (cat === 'local_tour') {
            $('#btn-preset-local').addClass('sg-btn-active');
        }
    }

    // =========================================================================
    // 2. Category Intelligence Configurations
    // =========================================================================
    const CATEGORY_DATA = {
        'college_iv': {
            badgeColor: '#f59e0b',
            title: '<i class="fas fa-graduation-cap text-warning mr-2"></i> College Industrial Visit (IV) Mode Active',
            badgeText: 'College IV Convoy',
            rules: [
                { icon: 'fas fa-users-cog text-warning', label: 'Faculty Ratio', val: 'Standard 1 Complimentary Faculty per 25–50 Students (Free Travel & AP Plan Food).' },
                { icon: 'fas fa-bed text-info', label: 'Room Sharing', val: 'Quad Sharing (4-Sharing) in verified student-friendly tourist hotels/resorts.' },
                { icon: 'fas fa-bus-alt text-success', label: 'Convoy Fleet', val: '54-Seater 2x2 luxury pushback coach convoy with DJ sound & laser lights.' },
                { icon: 'fas fa-file-contract text-danger', label: 'Permits & NOC', val: 'Factory visit clearance letter & Principal NOC required prior to departure.' },
                { icon: 'fas fa-coins text-warning', label: 'Dual Quotation', val: 'Dual rates enabled: Prints separate quotes for With Food (AP) vs Without Food (EP).' },
                { icon: 'fas fa-fire text-danger', label: 'Night Activities', val: 'Campfire party with music & off-road 4x4 Jeep safari included in circuit.' }
            ],
            jumps: [
                { target: 'headcount-dual-pricing', label: '2. Pricing & Staff' },
                { target: 'transit-coach-fleet', label: '3. Fleet & Transit' },
                { target: 'stay-dining-experiences', label: '4. Campfire & Activities' },
                { target: 'checklist-inclusions', label: '5. Inclusions' },
                { target: 'vehicle-wise-tariffs', label: 'Tariffs (4-60 Seats)' },
                { target: 'itinerary-days', label: 'Day-by-Day Itinerary' }
            ],
            namePlaceholder: 'e.g. 4 NIGHTS 5 DAYS KERALA COLLEGE IV (KOCHI-VARKALA-VAGAMON-ALLEPPEY)',
            destPlaceholder: 'e.g. Kochi, Varkala, Vagamon, Alleppey (Kerala)',
            highlightTabs: ['headcount-dual-pricing', 'transit-coach-fleet', 'stay-dining-experiences', 'checklist-inclusions']
        },
        'devotional': {
            badgeColor: '#8b5cf6',
            title: '<i class="fas fa-om mr-2" style="color: #a78bfa;"></i> Devotional & Spiritual Pilgrimage Yatra Mode Active',
            badgeText: 'Spiritual Yatra',
            rules: [
                { icon: 'fas fa-utensils text-success', label: 'Satvik Food', val: '100% Pure Vegetarian South Indian meals (No onion/garlic preparation on request).' },
                { icon: 'fas fa-user-shield text-info', label: 'Dress Code', val: 'Strict traditional attire mandatory (Dhoti/Kurta for Men, Saree/Chudidar for Women).' },
                { icon: 'fas fa-ticket-alt text-warning', label: 'Darshan Tokens', val: 'Special Entry Darshan tokens (₹300 fast track / Palani winch passes) configured.' },
                { icon: 'fas fa-wheelchair text-primary', label: 'Senior Citizen Care', val: 'Wheelchair assistance, ground-floor rooms & battery buggy car support.' },
                { icon: 'fas fa-place-of-worship text-danger', label: 'Darshan Timings', val: 'Darshan queues prioritized around morning & evening auspicious seva timings.' }
            ],
            jumps: [
                { target: 'stay-dining-experiences', label: '4. Darshan & Satvik Specs' },
                { target: 'temple-darshan', label: 'Temple Darshan Slots' },
                { target: 'transit-coach-fleet', label: '3. Coach & Hill Permits' },
                { target: 'checklist-inclusions', label: '5. Inclusions Checklist' }
            ],
            namePlaceholder: 'e.g. 4 NIGHTS 5 DAYS ARUPADAI VEEDU & NAVAGRAHA DEVOTIONAL YATRA',
            destPlaceholder: 'e.g. Palani, Madurai, Tiruchendur, Rameshwaram (Tamil Nadu)',
            highlightTabs: ['stay-dining-experiences', 'temple-darshan', 'transit-coach-fleet', 'checklist-inclusions']
        },
        'international': {
            badgeColor: '#0284c7',
            title: '<i class="fas fa-plane-departure text-info mr-2"></i> International Overseas Flight Tour Mode Active',
            badgeText: 'Overseas Tour',
            rules: [
                { icon: 'fas fa-passport text-danger', label: 'Passport Rule', val: 'Mandatory minimum 6 months passport validity from return flight departure date.' },
                { icon: 'fas fa-file-invoice text-info', label: 'Tourist eVisa', val: '30-Day tourist visa processing + comprehensive overseas medical travel insurance.' },
                { icon: 'fas fa-plane text-warning', label: 'Flight Tickets', val: 'Return economy airfares ex-Coimbatore/Chennai with check-in baggage included.' },
                { icon: 'fas fa-money-bill-wave text-success', label: 'Multi-Currency', val: 'Overseas quotations in foreign exchange (AED, SGD, MYR, THB, USD).' },
                { icon: 'fas fa-hotel text-primary', label: 'Accommodation', val: '4-Star luxury city hotel stay with daily buffet breakfasts & Indian dinners.' }
            ],
            jumps: [
                { target: 'stay-dining-experiences', label: '4. Visa & Overseas Specs' },
                { target: 'international-document', label: 'Document Checklist' },
                { target: 'transit-coach-fleet', label: '3. Flight & Coach' },
                { target: 'checklist-inclusions', label: '5. Overseas Terms' }
            ],
            namePlaceholder: 'e.g. 4 NIGHTS 5 DAYS DUBAI & ABU DHABI DESERT EXTRAVAGANZA',
            destPlaceholder: 'e.g. Dubai, Abu Dhabi (United Arab Emirates)',
            highlightTabs: ['stay-dining-experiences', 'international-document', 'transit-coach-fleet', 'checklist-inclusions']
        },
        'hill_station': {
            badgeColor: '#10b981',
            title: '<i class="fas fa-mountain text-success mr-2"></i> Hill Station Getaway Mode Active',
            badgeText: 'Hill Station Getaway',
            rules: [
                { icon: 'fas fa-tree text-success', label: 'Resort Stay', val: 'Deluxe hillside resort / tea estate cottage stay on Twin/Triple sharing basis.' },
                { icon: 'fas fa-concierge-bell text-warning', label: 'Meal Plan', val: 'MAP Plan standard (Daily Buffet Breakfast & Gourmet Dinner included).' },
                { icon: 'fas fa-jeep text-info', label: 'Sightseeing', val: 'Local sightseeing covering viewpoints, tea gardens, waterfalls & 4x4 Jeep Safari.' },
                { icon: 'fas fa-shield-alt text-primary', label: 'Hill Permits', val: 'Hill road green tax, interstate tourist permits, toll gates & driver hill bata.' }
            ],
            jumps: [
                { target: 'stay-dining-experiences', label: '4. Resort & Campfire' },
                { target: 'headcount-dual-pricing', label: '2. Pricing' },
                { target: 'transit-coach-fleet', label: '3. Coach Fleet' },
                { target: 'vehicle-wise-tariffs', label: 'Tariffs (4-60 Seats)' },
                { target: 'checklist-inclusions', label: '5. Inclusions' }
            ],
            namePlaceholder: 'e.g. 2 NIGHTS 3 DAYS OOTY-COONOOR-MUDUMALAI SCENIC ESCAPE',
            destPlaceholder: 'e.g. Ooty, Coonoor, Mudumalai (Tamil Nadu)',
            highlightTabs: ['stay-dining-experiences', 'headcount-dual-pricing', 'vehicle-wise-tariffs', 'checklist-inclusions']
        },
        'holiday': {
            badgeColor: '#14b8a6',
            title: '<i class="fas fa-umbrella-beach mr-2" style="color: #2dd4bf;"></i> Leisure & Beach Holiday Mode Active',
            badgeText: 'Leisure / Beach',
            rules: [
                { icon: 'fas fa-umbrella-beach text-info', label: 'Beach Resort', val: 'Scenic beach resort or heritage hotel stay on Twin Sharing basis.' },
                { icon: 'fas fa-concierge-bell text-warning', label: 'Meal Plan', val: 'MAP Plan standard (Daily Buffet Breakfast & Gourmet Dinner included).' },
                { icon: 'fas fa-ship text-success', label: 'Water Sports', val: 'Boating, beach recreation, island transfers & sightseeing included.' }
            ],
            jumps: [
                { target: 'stay-dining-experiences', label: '4. Beach Resort & Dining' },
                { target: 'headcount-dual-pricing', label: '2. Pricing' },
                { target: 'checklist-inclusions', label: '5. Inclusions' }
            ],
            namePlaceholder: 'e.g. 3 NIGHTS 4 DAYS GOA BEACH & HERITAGE ESCAPE',
            destPlaceholder: 'e.g. Goa / Pondicherry / Alleppey Backwaters',
            highlightTabs: ['stay-dining-experiences', 'headcount-dual-pricing', 'checklist-inclusions']
        },
        'local_tour': {
            badgeColor: '#0ea5e9',
            title: '<i class="fas fa-car text-info mr-2"></i> Local 1-Day City & Sightseeing Tour Mode Active',
            badgeText: '1-Day Local Tour',
            rules: [
                { icon: 'fas fa-clock text-warning', label: 'Package Hours', val: 'Fixed duration package (8 Hours / 80 KMs or 12 Hours / 120 KMs city limits).' },
                { icon: 'fas fa-tachometer-alt text-info', label: 'Extra KM / Hr', val: 'Clear overtime billing rates applied per extra kilometer and extra hour.' },
                { icon: 'fas fa-gas-pump text-success', label: 'Vehicle Inclusions', val: 'Fuel, driver bata, toll gates & commercial city parking charges included.' },
                { icon: 'fas fa-calendar-day text-primary', label: 'Single Day Run', val: 'Duration automatically configured to 1 Day / 0 Nights (No hotel stay).' }
            ],
            jumps: [
                { target: 'vehicle-wise-tariffs', label: 'Vehicle Rates (Sedan to Bus)' },
                { target: 'checklist-inclusions', label: '5. Inclusions & Exclusions' },
                { target: 'headcount-dual-pricing', label: '2. Package Rate' }
            ],
            namePlaceholder: 'e.g. 1-DAY COIMBATORE LOCAL SIGHTSEEING & MARUDHAMALAI TEMPLE TOUR',
            destPlaceholder: 'e.g. Coimbatore Local / Isha Yoga / Marudhamalai',
            highlightTabs: ['vehicle-wise-tariffs', 'checklist-inclusions', 'headcount-dual-pricing']
        },
        'family_vacation': {
            badgeColor: '#64748b',
            title: '<i class="fas fa-users text-primary mr-2"></i> Family & Custom Vacation Mode Active',
            badgeText: 'Family Vacation',
            rules: [
                { icon: 'fas fa-hotel text-info', label: 'Family Suite', val: 'Triple/Quad sharing cottages or interconnected family rooms.' },
                { icon: 'fas fa-utensils text-success', label: 'Kid Friendly', val: 'Customizable meal plans with mild spice options for kids & elders.' }
            ],
            jumps: [
                { target: 'stay-dining-experiences', label: '4. Family Resort & Dining' },
                { target: 'headcount-dual-pricing', label: '2. Pricing' }
            ],
            namePlaceholder: 'e.g. 2 NIGHTS 3 DAYS COORG & WAYANAD FAMILY RETREAT',
            destPlaceholder: 'e.g. Coorg / Wayanad / Chikmagalur',
            highlightTabs: ['stay-dining-experiences', 'headcount-dual-pricing']
        },
        'corporate_offsite': {
            badgeColor: '#3b82f6',
            title: '<i class="fas fa-building text-info mr-2"></i> Corporate Outing & Team Building Mode Active',
            badgeText: 'Corporate Outing',
            rules: [
                { icon: 'fas fa-chalkboard-teacher text-warning', label: 'Conference Hall', val: 'Projector, screen, sound system & team building activities included.' },
                { icon: 'fas fa-glass-cheers text-success', label: 'Gala Dinner', val: 'Evening DJ music, campfire BBQ & buffet dinner.' }
            ],
            jumps: [
                { target: 'stay-dining-experiences', label: '4. Resort & Conference' },
                { target: 'headcount-dual-pricing', label: '2. Pricing' }
            ],
            namePlaceholder: 'e.g. 1 NIGHT 2 DAYS YERCAUD CORPORATE RETREAT & TEAM OFFSITE',
            destPlaceholder: 'e.g. Yercaud / Kabini / Mysore',
            highlightTabs: ['stay-dining-experiences', 'headcount-dual-pricing']
        },
        'fixed_departure': {
            badgeColor: '#6366f1',
            title: '<i class="fas fa-bus text-warning mr-2"></i> Fixed Departure Group Bus Trip Active',
            badgeText: 'Fixed Departure',
            rules: [
                { icon: 'fas fa-ticket-alt text-success', label: 'Per-Seat Booking', val: 'Individual passenger seat allocation on luxury coach convoy.' }
            ],
            jumps: [
                { target: 'headcount-dual-pricing', label: '2. Per-Seat Pricing' }
            ],
            namePlaceholder: 'e.g. 2 NIGHTS 3 DAYS MUNNAR FIXED DEPARTURE BUS TRIP',
            destPlaceholder: 'e.g. Munnar / Kodaikanal',
            highlightTabs: ['headcount-dual-pricing', 'transit-coach-fleet']
        }
    };

    // =========================================================================
    // 3. Dynamic Intelligence Card & Tab Rendering
    // =========================================================================
    function renderCategoryIntelligence(cat) {
        const data = CATEGORY_DATA[cat] || CATEGORY_DATA['holiday'];
        setActivePresetButton(cat);

        // Update placeholders
        if (!nameInput.val()) {
            nameInput.attr('placeholder', data.namePlaceholder);
        }
        if (!destinationInput.val()) {
            destinationInput.attr('placeholder', data.destPlaceholder);
        }

        // Build Rules HTML
        let rulesHtml = '';
        data.rules.forEach(function (rule) {
            rulesHtml += `
                <div class="sg-rule-item">
                    <i class="${rule.icon} sg-rule-icon"></i>
                    <div>
                        <span class="sg-rule-label">${rule.label}:</span>
                        <span>${rule.val}</span>
                    </div>
                </div>
            `;
        });

        // Build Jumps HTML
        let jumpsHtml = '';
        data.jumps.forEach(function (jump) {
            jumpsHtml += `
                <a href="#" class="sg-jump-pill" data-target="${jump.target}">
                    <i class="fas fa-arrow-circle-right mr-1"></i> ${jump.label}
                </a>
            `;
        });

        const cardHtml = `
            <div class="sg-intel-header" id="sg-intel-header-toggle" style="cursor:pointer;" title="Click to expand/collapse category guidance">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="sg-intel-title">${data.title}</span>
                    <span class="sg-intel-badge" style="background-color: ${data.badgeColor}; color: #ffffff;">
                        ${data.badgeText}
                    </span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="sg-intel-toggle-pill"><i class="fas fa-chevron-down mr-1" id="sg-intel-caret"></i> Guidelines</span>
                </div>
            </div>
            <div id="sg-intel-collapsible-content" style="display:none; margin-top:8px;">
                <div class="sg-intel-rules-grid">
                    ${rulesHtml}
                </div>
                <div class="sg-intel-jumps">
                    <span class="sg-intel-jumps-title"><i class="fas fa-compass mr-1"></i> Quick Jump:</span>
                    ${jumpsHtml}
                </div>
            </div>
        `;

        intelCard.attr('class', 'sg-category-intel-card intel-' + cat).html(cardHtml).show();

        // Update Tab Highlights
        $('.nav-tabs .nav-link').removeClass('sg-tab-highlight');
        if (data.highlightTabs) {
            data.highlightTabs.forEach(function (t) {
                $(`a[href*="${t}"]`).addClass('sg-tab-highlight');
            });
        }
    }

    // =========================================================================
    // Universal Robust Tab Switcher for AdminLTE / Jazzmin Change Form Tabs
    // =========================================================================
    function activateTabByHref(href) {
        if (!href || href === '#' || !href.startsWith('#')) return;
        const targetId = href.substring(1);

        // 1. Update navigation tab active state
        $('#jazzy-tabs .nav-link').removeClass('active').attr('aria-selected', 'false');
        $(`#jazzy-tabs .nav-link[href="${href}"]`).addClass('active').attr('aria-selected', 'true');

        // 2. Locate target pane safely using getElementById (handles any ID)
        const targetPaneEl = document.getElementById(targetId);
        if (targetPaneEl) {
            $('.tab-content > .tab-pane').removeClass('show active').css('display', 'none');
            $(targetPaneEl).addClass('show active').css('display', 'block');

            // Dispatch resize event for Select2, layout elements
            window.dispatchEvent(new Event('resize'));
        }
    }

    // Direct click handler on all tab links in the tab bar
    $(document).on('click', '#jazzy-tabs .nav-link', function (e) {
        e.preventDefault();
        const href = $(this).attr('href');
        activateTabByHref(href);
    });

    // Click handler for Quick Jump buttons
    $(document).on('click', '.sg-jump-pill', function (e) {
        e.preventDefault();
        const target = $(this).data('target');
        const tabLink = $(`#jazzy-tabs a[href*="${target}"]`);
        if (tabLink.length) {
            const href = tabLink.attr('href');
            activateTabByHref(href);
            $('html, body').animate({
                scrollTop: tabLink.offset().top - 70
            }, 300);
        }
    });

    // Ensure initial active tab pane is explicitly displayed and others hidden
    setTimeout(function () {
        const currentActive = $('#jazzy-tabs .nav-link.active');
        if (currentActive.length) {
            activateTabByHref(currentActive.attr('href'));
        } else {
            const firstTab = $('#jazzy-tabs .nav-link').first();
            if (firstTab.length) {
                activateTabByHref(firstTab.attr('href'));
            }
        }
    }, 50);

    // Click handler to expand/collapse category intelligence card
    $(document).on('click', '#sg-intel-header-toggle', function () {
        const content = $('#sg-intel-collapsible-content');
        const caret = $('#sg-intel-caret');
        content.slideToggle(180);
        caret.toggleClass('fa-chevron-down fa-chevron-up');
    });

    // =========================================================================
    // 4. Robust Dropdown Reactive Engine & Synchronized State Adapters
    // =========================================================================

    // Helper: synchronize Select2 rendered container text so UI visibly updates immediately
    function syncSelect2Display(target) {
        const $el = $(target);
        if (!$el.length) return;
        const id = $el.attr('id');
        const val = $el.val();
        const opt = $el.find(`option[value="${val}"]`);
        const optText = opt.length ? opt.text() : '';
        if (optText) {
            if (id) {
                $(`#select2-${id}-container`).text(optText).attr('title', optText);
                if (window.jQuery) window.jQuery(`#select2-${id}-container`).text(optText).attr('title', optText);
            }
            const container = $el.closest('.fieldBox, .form-group, td').find('.select2-selection__rendered');
            if (container.length) {
                container.text(optText).attr('title', optText);
            }
            if (window.jQuery) {
                const s2 = window.jQuery(target).closest('.fieldBox, .form-group, td').find('.select2-selection__rendered');
                if (s2.length) s2.text(optText).attr('title', optText);
            }
        }
    }

    // Helper: provide clear visual feedback when a field auto-populates
    function flashField(selector) {
        const el = $(selector);
        if (el.length) {
            el.addClass('sg-field-flash');
            setTimeout(function () { el.removeClass('sg-field-flash'); }, 950);
        }
    }

    // Transit Mode Reactive Handler (Step 3)
    function onTransitModeChange() {
        const transitMode = $('#id_transit_mode').val() || 'road_coach';
        const flightGroup = $('.field-flight_estimate_per_pax').closest('.form-group');
        const trainGroup = $('.field-train_estimate_per_pax').closest('.form-group');
        const transitGroup = $('.field-transit_mode').closest('.form-group');

        $('#sg-transit-banner').remove();

        if (transitMode === 'flight_coach' || transitMode === 'fly_bus') {
            flightGroup.show();
            trainGroup.hide();
            const flightInput = $('#id_flight_estimate_per_pax');
            if (!flightInput.val() || parseFloat(flightInput.val()) === 0) {
                flightInput.val('8500.00');
            }
            $('#id_flight_inclusive').prop('checked', true);
            transitGroup.after(`
                <div id="sg-transit-banner" class="alert alert-info py-2 px-3 mb-2" style="background:#0c4a6e; border:1px solid #0284c7; color:#e0f2fe; font-size:12.5px; border-radius:6px;">
                    <i class="fas fa-plane mr-2 text-warning"></i><strong>✈️ Fly-Bus Mode Active:</strong> Destination coach is synchronized with flights. Flight airfare estimate is included in client quotations.
                </div>
            `);
            flashField('#id_flight_estimate_per_pax');
        } else if (transitMode === 'train_coach' || transitMode === 'rail_bus') {
            flightGroup.hide();
            trainGroup.show();
            const trainInput = $('#id_train_estimate_per_pax');
            if (!trainInput.val() || parseFloat(trainInput.val()) === 0) {
                trainInput.val('1800.00');
            }
            $('#id_flight_inclusive').prop('checked', false);
            transitGroup.after(`
                <div id="sg-transit-banner" class="alert alert-info py-2 px-3 mb-2" style="background:#1e3a8a; border:1px solid #3b82f6; color:#dbeafe; font-size:12.5px; border-radius:6px;">
                    <i class="fas fa-train mr-2 text-warning"></i><strong>🚆 Rail-Bus Mode Active:</strong> Destination coach meets passengers at railway station. Train fare estimate is included in client quotations.
                </div>
            `);
            flashField('#id_train_estimate_per_pax');
        } else if (transitMode === 'land_only') {
            flightGroup.hide();
            trainGroup.hide();
            $('#id_flight_inclusive').prop('checked', false);
            transitGroup.after(`
                <div id="sg-transit-banner" class="alert alert-secondary py-2 px-3 mb-2" style="background:#1e293b; border:1px solid #475569; color:#cbd5e1; font-size:12.5px; border-radius:6px;">
                    <i class="fas fa-map-pin mr-2 text-info"></i><strong>📍 Land Package Only:</strong> Client arranges own arrival transit to destination. Package covers local transfers, resort stay, sightseeing, and dining.
                </div>
            `);
        } else { // road_coach
            flightGroup.hide();
            trainGroup.hide();
            $('#id_flight_inclusive').prop('checked', false);
        }
        updateLiveSnapshot();
    }

    // Pricing Type Reactive Handler (Step 2)
    function onPricingTypeChange() {
        const pricingType = pricingTypeSelect.val() || 'per_person';
        const pricingFields = $('.field-price_with_food, .field-price_without_food').closest('.form-group');
        $('#sg-vehicle-rate-notice').remove();

        if (pricingType === 'vehicle_rate') {
            pricingFields.css({ 'opacity': '0.4', 'transition': 'opacity 0.2s' });
            pricingFields.before(`
                <div id="sg-vehicle-rate-notice" class="alert alert-secondary py-2 px-3 mb-2" style="background:#1e293b; border:1px solid #0284c7; color:#94a3b8; font-size:12.5px; border-radius:6px;">
                    <i class="fas fa-car mr-2 text-info"></i><strong>🚗 Vehicle Tariff Mode Active:</strong> Package rates are configured per vehicle in the <a href="#vehicle-wise-tariffs-4-to-60-seats-tab" class="text-primary font-weight-bold ml-1 sg-jump-tariffs">Vehicle-Wise Tariffs tab ➔</a>
                </div>
            `);
        } else if (pricingType === 'lump_sum') {
            pricingFields.css({ 'opacity': '0.4', 'transition': 'opacity 0.2s' });
            pricingFields.before(`
                <div id="sg-vehicle-rate-notice" class="alert alert-secondary py-2 px-3 mb-2" style="background:#1e293b; border:1px solid #f59e0b; color:#fef08a; font-size:12.5px; border-radius:6px;">
                    <i class="fas fa-file-contract mr-2 text-warning"></i><strong>📋 Lump Sum Contract Mode Active:</strong> Configure single total consolidated group package price in <strong>Base Price</strong>.
                </div>
            `);
        } else {
            pricingFields.css({ 'opacity': '1' });
        }
        updateLiveDualPricingPill();
    }

    // Default Vehicle Type Reactive Handler (Step 3)
    function onDefaultVehicleTypeChange() {
        const selText = $('#id_default_vehicle_type option:selected').text().toLowerCase();
        const seatingInput = $('#id_vehicle_seating_desc');
        const amenitiesInput = $('#id_bus_amenities_desc');
        let vehName = '';

        if (selText.includes('sedan') || selText.includes('dzire') || selText.includes('etios')) {
            vehName = '4-Seater AC Sedan';
            seatingInput.val('4-Seater AC Sedan with boot space');
            amenitiesInput.val('AC, Bottled Water, Bluetooth Audio, Professional Chauffeur, Fastag');
            if (!$('#id_min_pax').data('user-edited')) $('#id_min_pax').val(4).trigger('change');
        } else if (selText.includes('crysta') || selText.includes('innova') || selText.includes('ertiga')) {
            vehName = '7-Seater Luxury AC MPV';
            seatingInput.val('7-Seater Luxury AC MPV with Captain Seats');
            amenitiesInput.val('Dual AC, Reclining Leather Seats, Mobile Charging, Ice Box, Top Carrier');
            if (!$('#id_min_pax').data('user-edited')) $('#id_min_pax').val(7).trigger('change');
        } else if (selText.includes('urbania') || selText.includes('tempo') || selText.includes('tt')) {
            vehName = '17-Seater Luxury Pushback Coach';
            seatingInput.val('17-Seater Luxury Pushback Executive Coach');
            amenitiesInput.val('Individual AC Vents, Pushback Recliner Seats, Mobile USB Chargers, LED TV, Mic');
            if (!$('#id_min_pax').data('user-edited')) $('#id_min_pax').val(14).trigger('change');
        } else if (selText.includes('mini') || selText.includes('36') || selText.includes('40')) {
            vehName = '36-Seater Deluxe Mini Bus';
            seatingInput.val('36-Seater 2x2 Deluxe Tourist Mini Bus');
            amenitiesInput.val('2x2 Pushback, AC, PA Mic System, Stereo Audio, LED TV, Large Luggage Boot');
            if (!$('#id_min_pax').data('user-edited')) $('#id_min_pax').val(30).trigger('change');
        } else if (selText.includes('coach') || selText.includes('54') || selText.includes('52') || selText.includes('bus') || selText.includes('volvo')) {
            vehName = '54-Seater Luxury Coach Convoy';
            seatingInput.val('54-Seater 2x2 Pushback Luxury Coach Convoy');
            amenitiesInput.val('Laser Light & JBL DJ Sound System, LED TV, Recliner Pushback Seats, USB Chargers, First Aid Kit');
            if (!$('#id_min_pax').data('user-edited')) $('#id_min_pax').val(50).trigger('change');
        }

        if (vehName) {
            flashField('#id_vehicle_seating_desc');
            flashField('#id_bus_amenities_desc');
            showToast(`✨ Updated fleet seating & amenities for <strong>${vehName}</strong>`);
        }
    }

    // Meal Plan Reactive Handler (Step 4 & Step 2)
    function onMealPlanChange() {
        const mealPlan = $('#id_meal_plan').val() || 'AP';
        const mealText = $('#id_meal_plan option:selected').text();
        updateLiveDualPricingPill();
        showToast(`✨ Meal Plan updated to <strong>${mealText.split('(')[0].trim()}</strong>`);
    }

    // Room Sharing Type Reactive Handler (Step 4)
    function onRoomSharingTypeChange() {
        const sharingText = $('#id_room_sharing_type option:selected').text();
        showToast(`✨ Room sharing set to <strong>${sharingText.split('-')[0].trim()}</strong>`);
    }

    // Currency Code Reactive Handler (Step 4 International)
    function onCurrencyCodeChange() {
        const curr = $('#id_currency_code').val() || 'INR';
        const destCountryInput = $('#id_destination_country');
        if (!destCountryInput.val() || destCountryInput.val() === 'United Arab Emirates (UAE)') {
            if (curr === 'AED') destCountryInput.val('United Arab Emirates (Dubai & Abu Dhabi)');
            else if (curr === 'SGD') destCountryInput.val('Singapore');
            else if (curr === 'MYR') destCountryInput.val('Malaysia (Kuala Lumpur & Genting)');
            else if (curr === 'THB') destCountryInput.val('Thailand (Bangkok, Pattaya, Phuket)');
            else if (curr === 'EUR') destCountryInput.val('Europe (Schengen Circuit)');
            else if (curr === 'USD') destCountryInput.val('United States');
            else if (curr === 'INR') destCountryInput.val('India');
        }
        showToast(`✨ Currency updated to <strong>${curr}</strong>`);
    }

    // Inline Vehicle Tariff Row Handlers
    function onInlineTariffVehicleChange(selectEl) {
        const sel = $(selectEl);
        const selText = sel.find('option:selected').text().toLowerCase();
        const row = sel.closest('tr, .form-row, .inline-related');
        const seatingTierSel = row.find('select[id$="-seating_tier"], select[name$="-seating_tier"]');
        if (seatingTierSel.length) {
            if (selText.includes('sedan') || selText.includes('dzire')) seatingTierSel.val('4_sedan');
            else if (selText.includes('crysta') || selText.includes('innova')) seatingTierSel.val('7_crysta');
            else if (selText.includes('urbania') || selText.includes('tempo') || selText.includes('tt')) seatingTierSel.val('17_tt_urbania');
            else if (selText.includes('mini') || selText.includes('36')) seatingTierSel.val('36_mini_bus');
            else if (selText.includes('coach') || selText.includes('54') || selText.includes('bus')) seatingTierSel.val('54_luxury_coach');
            syncSelect2Display(seatingTierSel);
        }
    }

    function onInlineTariffRateTypeChange(selectEl) {
        const sel = $(selectEl);
        const rateType = sel.val();
        const row = sel.closest('tr, .form-row, .inline-related');
        const days = parseInt(durationDaysInput.val(), 10) || 3;
        if (rateType === 'local_1day') {
            const hoursInput = row.find('input[id$="-local_package_hours"]');
            const kmInput = row.find('input[id$="-included_km"]');
            if (hoursInput.length && (!hoursInput.val() || hoursInput.val() === '0')) hoursInput.val(8);
            if (kmInput.length && (!kmInput.val() || kmInput.val() === '0')) kmInput.val(80);
        } else if (rateType === 'outstation_multiday') {
            const kmInput = row.find('input[id$="-included_km"]');
            if (kmInput.length && (!kmInput.val() || kmInput.val() === '0' || kmInput.val() === '80')) {
                kmInput.val(days * 300);
            }
        }
    }

    // =========================================================================
    // 4. Unified Category & Preset Deep-Form Adaptation Engine
    // =========================================================================

    function applyCategoryDefaults(cat, isExplicitPresetClick) {
        if (!cat) return;

        // 1. Ensure select and Select2 container reflect category
        if (categorySelect.val() !== cat) {
            categorySelect.val(cat);
            if (window.jQuery) window.jQuery('#id_category').val(cat);
        }
        syncSelect2Display('#id_category');
        setActivePresetButton(cat);
        renderCategoryIntelligence(cat);

        // Check if pricing is empty or zero
        const currentAP = parseFloat(apInput.val()) || 0;
        const currentDays = parseInt(durationDaysInput.val(), 10) || 0;
        const isAddPage = window.location.href.indexOf('/add/') !== -1 || (!nameInput.val() && currentAP === 0);

        if (cat === 'devotional') {
            // Step 1: Duration
            if (isExplicitPresetClick || isAddPage || currentDays === 3 || currentDays === 1) {
                durationNightsInput.val(3);
                durationDaysInput.val(4);
            }
            // Step 2: Headcount & Pricing
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || $('#id_min_pax').val() === '50' || !$('#id_min_pax').val()) {
                $('#id_min_pax').val(35);
            }
            if (isExplicitPresetClick || isAddPage || $('#id_complementary_staff_count').val() === '2' || !$('#id_complementary_staff_count').val()) {
                $('#id_complementary_staff_count').val(1);
            }
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('4500.00');
                epInput.val('3200.00');
                baseInput.val('3200.00');
            }
            // Step 3: Transit & Fleet
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            $('#id_vehicle_seating_desc').val('36-Seater / 54-Seater Deluxe Tourist Coach with Pushback Seats');
            $('#id_bus_amenities_desc').val('AC, Devotional Audio & PA Mic System, Pushback Seats, Large Luggage Boot, First Aid Box');
            // Step 4: Stay & Dining
            isDevotionalCb.prop('checked', true);
            isIntlCb.prop('checked', false);
            $('#id_satvik_pure_veg_meals').prop('checked', true);
            $('#id_senior_citizen_friendly').prop('checked', true);
            $('#id_has_industrial_visit').prop('checked', false);
            $('#id_has_campfire_dj').prop('checked', false);
            $('#id_has_jeep_safari').prop('checked', false);
            $('#id_meal_plan').val('AP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('twin_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('Deluxe AC Pilgrim Hotel / Standard Temple Guest House');
            $('#id_temple_dress_code').val('Traditional attire mandatory: Dhoti/Kurta for Men, Saree/Chudidar for Women');
            $('#id_temple_darshan_info').val('Special Entry Darshan tokens / fast-track seva access arranged with morning & evening temple timings.');
            // Step 5: Checklist Inclusions
            if (isExplicitPresetClick || !inclusionsField.val() || inclusionsField.val().includes('Convoy Bus') || inclusionsField.val().includes('Airfare') || inclusionsField.val().includes('city 8 Hours')) {
                inclusionsField.val(
                    "Coimbatore roundtrip pushback luxury coach transportation.\n" +
                    "All toll gate, parking, and temple hill road permit charges.\n" +
                    "AC hotel / pilgrim cottage accommodation on twin/triple sharing.\n" +
                    "100% Satvik Pure Vegetarian South Indian Meals (Breakfast, Lunch, Dinner).\n" +
                    "Special Entry Darshan tokens / fast-track seva access at major shrines.\n" +
                    "Experienced Spiritual Tour Coordinator from Siva Gayathri Tours.\n" +
                    "Senior citizen boarding and wheelchair assistance."
                );
                exclusionsField.val(
                    "Personal archana tickets, tonsure charges, and special homams.\n" +
                    "Room service, tips, and personal expenses.\n" +
                    "Extra sightseeing not covered in the spiritual circuit."
                );
                termsField.val(
                    "Temple authorities reserve right of entry based on traditional dress code compliance.\n" +
                    "Darshan queue timings are subject to temple crowd and VIP movement.\n" +
                    "Payment: 50% advance while confirming the Yatra & rest 50% before departure."
                );
            }
        } else if (cat === 'college_iv') {
            // Step 1: Duration
            if (isExplicitPresetClick || isAddPage || currentDays === 3 || currentDays === 1) {
                durationNightsInput.val(4);
                durationDaysInput.val(5);
            }
            // Step 2: Headcount & Pricing
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || !$('#id_min_pax').val() || $('#id_min_pax').val() === '35' || $('#id_min_pax').val() === '4' || $('#id_min_pax').val() === '6') {
                $('#id_min_pax').val(50);
            }
            if (isExplicitPresetClick || isAddPage || !$('#id_complementary_staff_count').val() || $('#id_complementary_staff_count').val() === '0') {
                $('#id_complementary_staff_count').val(2);
            }
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('5700.00');
                epInput.val('4600.00');
                baseInput.val('4600.00');
            }
            // Step 3: Transit & Fleet
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            $('#id_vehicle_seating_desc').val('54-Seater 2x2 Pushback Luxury Coach Convoy');
            $('#id_bus_amenities_desc').val('Laser Light & JBL DJ Sound System, LED TV, Recliner Pushback Seats, USB Chargers, First Aid Kit');
            // Step 4: Stay & Dining
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', false);
            $('#id_satvik_pure_veg_meals').prop('checked', false);
            $('#id_senior_citizen_friendly').prop('checked', false);
            $('#id_has_industrial_visit').prop('checked', true);
            $('#id_has_campfire_dj').prop('checked', true);
            $('#id_has_jeep_safari').prop('checked', true);
            $('#id_meal_plan').val('AP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('4_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('Verified Student-Friendly Tourist Hotel / Resort');
            // Step 5: Inclusions & Terms
            if (isExplicitPresetClick || !inclusionsField.val() || inclusionsField.val().includes('Satvik') || inclusionsField.val().includes('Airfare') || inclusionsField.val().includes('city 8 Hours')) {
                inclusionsField.val(
                    "Tamilnadu-Karnataka-Kerala AC/Non-AC Luxury Convoy Bus.\n" +
                    "All parking, toll gate & inter-state permit charges.\n" +
                    "Accommodation on 4-sharing basis in verified tourist hotel/resort.\n" +
                    "All student transfers, factory visit access & sightseeing.\n" +
                    "Tour in-charge from Siva Gayathri Tours and Travels.\n" +
                    "Guide service & industrial clearance liaison.\n" +
                    "DJ with Campfire Night party.\n" +
                    "Off-road 4x4 Jeep Safari."
                );
                exclusionsField.val(
                    "Natural disturbances, roadblocks, or unexpected climate delays.\n" +
                    "Any damages caused by students to hotel/vehicle properties.\n" +
                    "Personal shopping and optional recreation."
                );
                termsField.val(
                    "College authorization letter and student identity cards are mandatory.\n" +
                    "Students are required to adhere to college discipline throughout the tour.\n" +
                    "Payment: 50% advance upon confirmation, balance 50% prior to convoy departure."
                );
            }
        } else if (cat === 'international') {
            // Step 1: Duration
            if (isExplicitPresetClick || isAddPage || currentDays === 3 || currentDays === 1) {
                durationNightsInput.val(4);
                durationDaysInput.val(5);
            }
            // Step 2: Headcount & Pricing
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || $('#id_min_pax').val() === '50') {
                $('#id_min_pax').val(20);
            }
            if (isExplicitPresetClick || isAddPage || $('#id_complementary_staff_count').val() === '2') {
                $('#id_complementary_staff_count').val(0);
            }
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('48500.00');
                epInput.val('42000.00');
                baseInput.val('42000.00');
            }
            // Step 3: Transit & Fleet
            $('#id_transit_mode').val('flight_coach');
            syncSelect2Display('#id_transit_mode');
            const flightEst = $('#id_flight_estimate_per_pax');
            if (isExplicitPresetClick || !flightEst.val() || parseFloat(flightEst.val()) === 0) {
                flightEst.val('18500.00');
            }
            $('#id_vehicle_seating_desc').val('Luxury Air-Conditioned Tourist Coach (Destination Transfers)');
            $('#id_bus_amenities_desc').val('AC, Chilled Mineral Water, Reclining Seats, Luggage Compartment, English-speaking Chauffeur');
            // Step 4: Stay & Dining
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', true);
            $('#id_visa_required').prop('checked', true);
            $('#id_flight_inclusive').prop('checked', true);
            $('#id_has_industrial_visit').prop('checked', false);
            $('#id_has_campfire_dj').prop('checked', false);
            $('#id_meal_plan').val('MAP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('twin_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('4-Star Luxury City Hotel');
            $('#id_passport_validity_months').val(6);
            $('#id_currency_code').val('AED');
            syncSelect2Display('#id_currency_code');
            if (!$('#id_destination_country').val()) $('#id_destination_country').val('United Arab Emirates (UAE)');
            if (!$('#id_visa_guidelines').val()) $('#id_visa_guidelines').val('Single entry 30-day tourist eVisa. Clear color passport scan and white background photo required 15 days in advance.');
            if (!$('#id_overseas_dmc_partner').val()) $('#id_overseas_dmc_partner').val('Licensed Local Destination Management Company (DMC)');
            // Step 5: Inclusions & Terms
            if (isExplicitPresetClick || !inclusionsField.val() || inclusionsField.val().includes('Satvik') || inclusionsField.val().includes('Convoy Bus') || inclusionsField.val().includes('city 8 Hours')) {
                inclusionsField.val(
                    "Return Economy Class Airfare Ex-Coimbatore / Chennai.\n" +
                    "30 Days Tourist eVisa with Comprehensive Overseas Travel Insurance.\n" +
                    "4-Star Luxury City Hotel accommodation on twin sharing basis.\n" +
                    "Daily Buffet Breakfast & Dinners at authentic Indian restaurants.\n" +
                    "Desert Safari with 4x4 Dune Bashing, BBQ Dinner & Live Cultural Shows.\n" +
                    "Burj Khalifa At The Top 124th Floor Entry Pass.\n" +
                    "Dhow Cruise Dinner at Dubai Marina.\n" +
                    "Full Day City Tour with English/Tamil Speaking Tour Escort.\n" +
                    "All airport and sightseeing transfers in Deluxe Luxury AC Tourist Coach."
                );
                exclusionsField.val(
                    "Tourism Dirham Fee payable directly at hotel check-in.\n" +
                    "Lunches unless specified in the day itinerary.\n" +
                    "Excess baggage fees and personal tips."
                );
                termsField.val(
                    "Original Passport must have at least 6 months validity from return date.\n" +
                    "Visa processing requires clear scanned passport and 35x45mm white background photo.\n" +
                    "Payment: 30% advance on confirmation, 50% on visa approval, 20% before flight departure."
                );
            }
        } else if (cat === 'hill_station') {
            // Step 1: Duration
            if (isExplicitPresetClick || isAddPage || currentDays === 1 || currentDays === 5) {
                durationNightsInput.val(2);
                durationDaysInput.val(3);
            }
            // Step 2: Headcount & Pricing
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || $('#id_min_pax').val() === '50' || !$('#id_min_pax').val()) {
                $('#id_min_pax').val(6);
            }
            if (isExplicitPresetClick || isAddPage || $('#id_complementary_staff_count').val() === '2') {
                $('#id_complementary_staff_count').val(0);
            }
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('4200.00');
                epInput.val('3100.00');
                baseInput.val('3100.00');
            }
            // Step 3: Transit & Fleet
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            $('#id_vehicle_seating_desc').val('7-Seater Luxury AC Innova Crysta / 17-Seater Urbania');
            $('#id_bus_amenities_desc').val('Dual AC, Pushback Seats, Mobile USB Chargers, Music System, Hill-experienced Chauffeur');
            // Step 4: Stay & Dining
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', false);
            $('#id_has_industrial_visit').prop('checked', false);
            $('#id_has_campfire_dj').prop('checked', true);
            $('#id_has_jeep_safari').prop('checked', true);
            $('#id_has_boating').prop('checked', true);
            $('#id_satvik_pure_veg_meals').prop('checked', false);
            $('#id_senior_citizen_friendly').prop('checked', false);
            $('#id_meal_plan').val('MAP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('twin_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('Deluxe Hillside Resort / Tea Estate Cottage');
            // Step 5: Inclusions & Terms
            if (isExplicitPresetClick || !inclusionsField.val() || inclusionsField.val().includes('Satvik') || inclusionsField.val().includes('Airfare') || inclusionsField.val().includes('city 8 Hours')) {
                inclusionsField.val(
                    "Coimbatore roundtrip private tourist vehicle with fuel & driver bata.\n" +
                    "Hill station green tax, parking, and toll gate charges.\n" +
                    "Resort / Deluxe Hotel stay with scenic views.\n" +
                    "Daily breakfast and dinner (MAP Plan).\n" +
                    "Local sightseeing covering viewpoint, waterfalls, tea gardens & boating.\n" +
                    "Campfire evening at resort."
                );
                exclusionsField.val(
                    "Boating tickets, botanical garden entrance tickets, and camera fees.\n" +
                    "Lunch and personal laundry/food orders."
                );
                termsField.val(
                    "Sightseeing sequence is subject to hill weather and forest road permissions.\n" +
                    "Check-in 12:00 PM / Check-out 11:00 AM standard resort timings.\n" +
                    "Payment: 50% advance while booking & 50% before vehicle start."
                );
            }
        } else if (cat === 'local_tour') {
            // Step 1: Duration
            durationDaysInput.val(1);
            durationNightsInput.val(0);
            // Step 2: Headcount & Pricing
            $('#id_pricing_type').val('vehicle_rate');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || $('#id_min_pax').val() === '50' || !$('#id_min_pax').val()) {
                $('#id_min_pax').val(4);
            }
            $('#id_complementary_staff_count').val(0);
            if (isExplicitPresetClick || currentAP === 0 || baseInput.val() === '0') {
                baseInput.val('2400.00');
                apInput.val('0.00');
                epInput.val('0.00');
            }
            // Step 3: Transit & Fleet
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            $('#id_vehicle_seating_desc').val('4-Seater AC Sedan (Swift Dzire / Toyota Etios)');
            $('#id_bus_amenities_desc').val('AC, Bottled Water, Bluetooth Audio, Professional Chauffeur, Fastag');
            // Step 4: Stay & Dining
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', false);
            $('#id_has_industrial_visit').prop('checked', false);
            $('#id_has_campfire_dj').prop('checked', false);
            $('#id_has_jeep_safari').prop('checked', false);
            $('#id_has_boating').prop('checked', false);
            $('#id_meal_plan').val('EP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('single');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('Day Package / No Hotel Stay');
            // Step 5: Inclusions & Terms
            if (isExplicitPresetClick || !inclusionsField.val() || inclusionsField.val().includes('Satvik') || inclusionsField.val().includes('Airfare') || inclusionsField.val().includes('Convoy Bus')) {
                inclusionsField.val(
                    "Coimbatore city 8 Hours / 80 KMs (or 12 Hours / 120 KMs) local package.\n" +
                    "Dedicated private AC tourist vehicle with professional chauffeur.\n" +
                    "Vehicle fuel charges included in base package.\n" +
                    "Driver day bata included.\n" +
                    "All city toll gate & commercial parking charges."
                );
                exclusionsField.val(
                    "Extra kilometers beyond package limit (billed per km at vehicle tariff rate).\n" +
                    "Extra hours beyond package limit (billed per hour at vehicle tariff rate).\n" +
                    "Temple entrance tickets, special pooja tickets & passenger food."
                );
                termsField.val(
                    "Package kilometers and hours calculate from garage departure to garage reporting.\n" +
                    "Overtime charges: Extra km rates (Sedan ₹14/km, Crysta ₹20/km, Urbania ₹26/km, Bus ₹40/km).\n" +
                    "Night driving allowance applicable if journey extends beyond 10:00 PM."
                );
            }
        } else if (cat === 'holiday') {
            if (isExplicitPresetClick || isAddPage || currentDays === 1) {
                durationNightsInput.val(3);
                durationDaysInput.val(4);
            }
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || $('#id_min_pax').val() === '50' || !$('#id_min_pax').val()) {
                $('#id_min_pax').val(6);
            }
            $('#id_complementary_staff_count').val(0);
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('4800.00');
                epInput.val('3600.00');
                baseInput.val('3600.00');
            }
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            $('#id_vehicle_seating_desc').val('7-Seater Luxury AC Innova Crysta / AC Coach');
            $('#id_bus_amenities_desc').val('Dual AC, Reclining Seats, Music System, Mobile USB Charging');
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', false);
            $('#id_has_campfire_dj').prop('checked', true);
            $('#id_has_boating').prop('checked', true);
            $('#id_meal_plan').val('MAP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('twin_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('Deluxe Beach Resort / Heritage Hotel');
        } else if (cat === 'family_vacation') {
            if (isExplicitPresetClick || isAddPage || !durationDaysInput.val()) {
                durationNightsInput.val(2);
                durationDaysInput.val(3);
            }
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || $('#id_min_pax').val() === '50' || !$('#id_min_pax').val()) {
                $('#id_min_pax').val(4);
            }
            $('#id_complementary_staff_count').val(0);
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('3800.00');
                epInput.val('2800.00');
                baseInput.val('2800.00');
            }
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', false);
            $('#id_meal_plan').val('MAP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('3_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('Family Resort / Private Cottage Suite');
        } else if (cat === 'corporate_offsite') {
            if (isExplicitPresetClick || isAddPage || !durationDaysInput.val()) {
                durationNightsInput.val(1);
                durationDaysInput.val(2);
            }
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || $('#id_min_pax').val() === '50' || !$('#id_min_pax').val()) {
                $('#id_min_pax').val(30);
            }
            $('#id_complementary_staff_count').val(0);
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('4200.00');
                epInput.val('3200.00');
                baseInput.val('3200.00');
            }
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', false);
            $('#id_has_campfire_dj').prop('checked', true);
            $('#id_meal_plan').val('AP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('twin_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('4-Star Luxury Business Resort with Conference Hall');
        } else if (cat === 'fixed_departure') {
            if (isExplicitPresetClick || isAddPage || !durationDaysInput.val()) {
                durationNightsInput.val(2);
                durationDaysInput.val(3);
            }
            $('#id_pricing_type').val('per_person');
            syncSelect2Display('#id_pricing_type');
            if (isExplicitPresetClick || isAddPage || !$('#id_min_pax').val()) {
                $('#id_min_pax').val(40);
            }
            $('#id_complementary_staff_count').val(1);
            if (isExplicitPresetClick || currentAP === 0) {
                apInput.val('3500.00');
                epInput.val('2600.00');
                baseInput.val('2600.00');
            }
            $('#id_transit_mode').val('road_coach');
            syncSelect2Display('#id_transit_mode');
            isDevotionalCb.prop('checked', false);
            isIntlCb.prop('checked', false);
            $('#id_meal_plan').val('AP');
            syncSelect2Display('#id_meal_plan');
            $('#id_room_sharing_type').val('twin_sharing');
            syncSelect2Display('#id_room_sharing_type');
            $('#id_hotel_star_category').val('Tourist Class AC Hotel');
        }

        // Post-adaptation updates
        autoGenPackageCode();
        syncVerticalVisibility();
        updateLiveDualPricingPill();
        updateLiveSnapshot();
        calculateProfitMargin();

        // Visual flash indicators on adapted fields
        flashField('#id_duration_days');
        flashField('#id_duration_nights');
        flashField('#id_pricing_type');
        flashField('#id_min_pax');
        flashField('#id_price_with_food');
        flashField('#id_meal_plan');
        flashField('#id_room_sharing_type');
    }

    // Category Change Delegator
    function onCategoryChange() {
        const val = categorySelect.val() || 'hill_station';
        applyCategoryDefaults(val, false);
    }

    // Helper to synchronize both native select and Jazzmin Select2 container
    function setCategoryValue(val, isExplicitPresetClick = false) {
        if (!val) return;
        categorySelect.val(val);
        if (window.jQuery) window.jQuery('#id_category').val(val);

        const opt = categorySelect.find(`option[value="${val}"]`);
        const optText = opt.length ? opt.text() : val;
        $('#select2-id_category-container').text(optText).attr('title', optText);
        if (window.jQuery) window.jQuery('#select2-id_category-container').text(optText).attr('title', optText);

        syncSelect2Display(categorySelect);
        categorySelect.trigger('change.select2');
        if (window.jQuery) window.jQuery('#id_category').trigger('change.select2');

        applyCategoryDefaults(val, isExplicitPresetClick);
    }

    // Template change handler
    function onTemplateChange() {
        const tmplSelect = $('#id_template');
        if (!tmplSelect.length) return;
        const tmplId = tmplSelect.val();
        if (!tmplId) return;

        $.ajax({
            url: `/packages/api/template/${tmplId}/info/`,
            method: 'GET',
            dataType: 'json',
            success: function (res) {
                if (res && res.success) {
                    if (res.category) {
                        setCategoryValue(res.category);
                    }
                    if (res.destination && !destinationInput.val()) {
                        destinationInput.val(res.destination);
                    }
                    if (res.duration_days) {
                        durationDaysInput.val(res.duration_days).trigger('input').trigger('change');
                    }
                    if (res.duration_nights !== undefined) {
                        durationNightsInput.val(res.duration_nights).trigger('input').trigger('change');
                    }
                    if (res.base_price && (!baseInput.val() || parseFloat(baseInput.val()) === 0)) {
                        baseInput.val(res.base_price).trigger('input').trigger('change');
                    }
                    if (res.description && !$('#id_description').val()) {
                        $('#id_description').val(res.description);
                    }
                    updateLiveSnapshot();
                    showToast(`✨ Loaded template defaults: <strong>${res.name}</strong>`);
                }
            },
            error: function () {
                // Silently ignore if template endpoint unavailable
            }
        });
    }

    // Synchronize Vertical Visibility of Contextual Inlines and Fields
    function syncVerticalVisibility() {
        const cat = categorySelect.val() || 'hill_station';
        const isDevotional = (isDevotionalCb.is(':checked') || cat === 'devotional');
        const isIntl = (isIntlCb.is(':checked') || cat === 'international');

        // Dynamically query tabs for inlines
        const curDevotionalInlineTab = $('a[href*="temple-darshan"], a[href*="temple_slots"]').closest('.nav-item, li');
        const curIntlInlineTab = $('a[href*="international-document"], a[href*="intl_documents"]').closest('.nav-item, li');

        // Contextual Devotional Rows inside Step 4
        const devRows = $('.field-is_devotional, .field-satvik_pure_veg_meals, .field-senior_citizen_friendly, .field-temple_dress_code, .field-temple_darshan_info').closest('.form-group, .form-row');
        if (isDevotional) {
            curDevotionalInlineTab.show();
            devRows.show();
        } else {
            curDevotionalInlineTab.hide();
            devRows.hide();
        }

        // Contextual International Rows inside Step 4
        const intlRows = $('.field-is_international, .field-destination_country, .field-currency_code, .field-visa_required, .field-passport_validity_months, .field-flight_inclusive, .field-visa_guidelines, .field-overseas_dmc_partner, .field-flight_details_note').closest('.form-group, .form-row');
        if (isIntl) {
            curIntlInlineTab.show();
            intlRows.show();
        } else {
            curIntlInlineTab.hide();
            intlRows.hide();
        }

        onTransitModeChange();
        onPricingTypeChange();
        updateLiveSnapshot();
    }

    // Hotel Star Category Auto-Suggestions
    const hotelInput = $('#id_hotel_star_category');
    if (hotelInput.length && !$('#hotel_star_options').length) {
        $('body').append(`
            <datalist id="hotel_star_options">
                <option value="Star Category Hotel & Resort">
                <option value="3-Star Deluxe Hotel & Resort">
                <option value="4-Star Luxury City Hotel">
                <option value="5-Star Premium Luxury Resort">
                <option value="Deluxe AC Hotel / Premium Resort">
                <option value="Pilgrim Guest House / Standard Lodge">
                <option value="Hillside Tea Estate Resort / Cottage">
                <option value="Heritage Palace / Jungle Resort">
            </datalist>
        `);
        hotelInput.attr('list', 'hotel_star_options');
        hotelInput.on('input change', function () {
            calculateProfitMargin();
        });
    }

    // Master Dropdown Change Handler
    function handleDropdownChange(el) {
        const id = el.id || $(el).attr('id');
        if (!id) return;

        if (id === 'id_category') {
            onCategoryChange();
        } else if (id === 'id_transit_mode') {
            onTransitModeChange();
        } else if (id === 'id_pricing_type') {
            onPricingTypeChange();
        } else if (id === 'id_default_vehicle_type') {
            onDefaultVehicleTypeChange();
        } else if (id === 'id_meal_plan') {
            onMealPlanChange();
        } else if (id === 'id_room_sharing_type') {
            onRoomSharingTypeChange();
        } else if (id === 'id_currency_code') {
            onCurrencyCodeChange();
        } else if (id === 'id_template') {
            onTemplateChange();
        } else if (id.includes('vehicle_tariffs') && id.endsWith('vehicle_type')) {
            onInlineTariffVehicleChange(el);
        } else if (id.includes('vehicle_tariffs') && id.endsWith('rate_type')) {
            onInlineTariffRateTypeChange(el);
        }

        syncVerticalVisibility();
        calculateProfitMargin();
        updateLiveSnapshot();
    }

    // 3-Tier Multi-Framework Event Delegation for Select2 & Native Selects
    if (window.django && window.django.jQuery) {
        window.django.jQuery(document).off('.sgDropdowns').on('change.sgDropdowns select2:select.sgDropdowns select2:clear.sgDropdowns', 'select', function () {
            handleDropdownChange(this);
        });
    }
    if (window.jQuery) {
        window.jQuery(document).off('.sgDropdowns').on('change.sgDropdowns select2:select.sgDropdowns select2:clear.sgDropdowns', 'select', function () {
            handleDropdownChange(this);
        });
    }
    document.addEventListener('change', function (e) {
        if (e.target && e.target.tagName === 'SELECT') {
            handleDropdownChange(e.target);
        }
    }, true);

    $(document).on('change', '#id_is_devotional, #id_is_international, #id_flight_inclusive, #id_visa_required', function () {
        syncVerticalVisibility();
    });

    $(document).on('click', '.sg-jump-tariffs', function (e) {
        e.preventDefault();
        const tabLink = $(`#jazzy-tabs a[href*="vehicle-wise-tariffs"]`);
        if (tabLink.length) {
            activateTabByHref(tabLink.attr('href'));
        }
    });

    // Initial state check & Category synchronization
    const initialCat = categorySelect.val() || 'college_iv';
    onCategoryChange();
    setActivePresetButton(initialCat);
    renderCategoryIntelligence(initialCat);
    syncVerticalVisibility();
    updateLiveSnapshot();

    // =========================================================================
    // 5. Smart Duration Calculator & Package Code Generator
    // =========================================================================
    function autoGenPackageCode() {
        const codeInput = $('#id_package_code');
        if (codeInput.val() && codeInput.data('user-customized')) return;

        const name = nameInput.val() || '';
        const dest = destinationInput.val() || '';
        const nights = durationNightsInput.val() || '0';
        const days = durationDaysInput.val() || '1';

        const source = dest || name;
        if (!source) return;

        const words = source.replace(/[^a-zA-Z0-9\s]/g, '').trim().split(/\s+/);
        let prefix = '';
        if (words.length >= 2) {
            prefix = (words[0].slice(0, 2) + words[1].slice(0, 2)).toUpperCase();
        } else if (words.length === 1) {
            prefix = words[0].slice(0, 3).toUpperCase();
        }
        prefix = prefix || 'TRIP';

        const genCode = `PKG-${prefix}-${nights}N${days}D`;
        codeInput.val(genCode).data('user-customized', false);
    }

    // When Nights is entered, automatically set Days = Nights + 1
    durationNightsInput.on('input change', function () {
        const nights = parseInt($(this).val(), 10);
        if (!isNaN(nights) && nights >= 0) {
            durationDaysInput.val(nights + 1);
            autoGenPackageCode();
        }
    });

    // When Days is entered, ensure nights is valid
    durationDaysInput.on('input change', function () {
        const days = parseInt($(this).val(), 10);
        if (!isNaN(days) && days > 0) {
            const currentNights = parseInt(durationNightsInput.val(), 10);
            if (isNaN(currentNights) || currentNights === 0 || currentNights === days) {
                durationNightsInput.val(Math.max(0, days - 1));
            }
            autoGenPackageCode();
        }
    });

    nameInput.on('input change', autoGenPackageCode);
    destinationInput.on('input change', autoGenPackageCode);
    $('#id_package_code').on('input change', function () {
        if ($(this).val()) {
            $(this).data('user-customized', true);
        }
    });

    // =========================================================================
    // 6. One-Click Inclusions Quick Presets (5 Verticals)
    // =========================================================================

    // 1. Devotional Preset
    $(document).on('click', '#btn-preset-devotional', function (e) {
        e.preventDefault();
        setCategoryValue('devotional', true);
        showToast("✨ Applied <strong>Devotional Yatra Mode</strong> across all 5 steps!");
    });

    // 2. College IV Preset
    $(document).on('click', '#btn-preset-iv', function (e) {
        e.preventDefault();
        setCategoryValue('college_iv', true);
        showToast("✨ Applied <strong>College IV Mode</strong> across all 5 steps!");
    });

    // 3. International Preset
    $(document).on('click', '#btn-preset-intl', function (e) {
        e.preventDefault();
        setCategoryValue('international', true);
        showToast("✨ Applied <strong>International Tour Mode</strong> across all 5 steps!");
    });

    // 4. Hill Station Preset
    $(document).on('click', '#btn-preset-holiday', function (e) {
        e.preventDefault();
        setCategoryValue('hill_station', true);
        showToast("✨ Applied <strong>Hill Station Getaway Mode</strong> across all 5 steps!");
    });

    // 5. Local 1-Day Preset
    $(document).on('click', '#btn-preset-local', function (e) {
        e.preventDefault();
        setCategoryValue('local_tour', true);
        showToast("✨ Applied <strong>Local 1-Day Mode</strong> across all 5 steps!");
    });

    // =========================================================================
    // 7. Step 5 Quick-Fill Inclusions & Exclusions Chips Toolbar
    // =========================================================================
    const inclusionChipsHtml = `
        <div class="sg-inclusion-chips-toolbar" style="margin-bottom:12px; background:#1e293b; padding:10px 14px; border-radius:6px; border:1px solid #334155; display:flex; flex-wrap:wrap; align-items:center; gap:8px;">
            <span style="font-size:11.5px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">
                <i class="fas fa-magic text-warning mr-1"></i> Quick-Fill Checklist:
            </span>
            <button type="button" class="sg-chip-btn sg-chip-iv" data-template="iv">
                <i class="fas fa-graduation-cap"></i> College IV Plan
            </button>
            <button type="button" class="sg-chip-btn sg-chip-holiday" data-template="holiday">
                <i class="fas fa-mountain"></i> Hill Station Resort
            </button>
            <button type="button" class="sg-chip-btn sg-chip-devotional" data-template="devotional">
                <i class="fas fa-om"></i> Devotional Satvik
            </button>
            <button type="button" class="sg-chip-btn sg-chip-flight" data-template="flight">
                <i class="fas fa-plane"></i> Fly-Bus Flight Plan
            </button>
            <button type="button" class="sg-chip-btn sg-chip-corporate" data-template="corporate">
                <i class="fas fa-briefcase"></i> Corporate Outbound
            </button>
        </div>
    `;

    if (inclusionsField.length) {
        inclusionsField.closest('.form-group, .form-row').before(inclusionChipsHtml);
    }

    const TEMPLATE_INCLUSIONS = {
        'iv': {
            inc: "Tamilnadu-Karnataka-Kerala AC/Non-AC Luxury Convoy Bus.\nAll parking, toll gate & inter-state permit charges.\nAccommodation on 4-sharing basis in verified tourist hotel/resort.\nAll student transfers, factory visit access & sightseeing.\nTour in-charge from Siva Gayathri Tours and Travels.\nGuide service & industrial clearance liaison.\nDJ with Campfire Night party.\nOff-road 4x4 Jeep Safari.",
            exc: "Natural disturbances, roadblocks, or unexpected climate delays.\nAny damages caused by students to hotel/vehicle properties.\nPersonal shopping and optional recreation.",
            terms: "College authorization letter and student identity cards are mandatory.\nStudents are required to adhere to college discipline throughout the tour.\nPayment: 50% advance upon confirmation, balance 50% prior to convoy departure."
        },
        'holiday': {
            inc: "Coimbatore roundtrip private tourist vehicle with fuel & driver bata.\nHill station green tax, parking, and toll gate charges.\nResort / Deluxe Hotel stay with scenic views.\nDaily breakfast and dinner (MAP Plan).\nLocal sightseeing covering viewpoint, waterfalls, tea gardens & boating.\nCampfire evening at resort.",
            exc: "Boating tickets, botanical garden entrance tickets, and camera fees.\nLunch and personal laundry/food orders.",
            terms: "Sightseeing sequence is subject to hill weather and forest road permissions.\nCheck-in 12:00 PM / Check-out 11:00 AM standard resort timings.\nPayment: 50% advance while booking & 50% before vehicle start."
        },
        'devotional': {
            inc: "Coimbatore roundtrip pushback luxury coach transportation.\nAll toll gate, parking, and temple hill road permit charges.\nAC hotel / pilgrim cottage accommodation on twin/triple sharing.\n100% Satvik Pure Vegetarian South Indian Meals (Breakfast, Lunch, Dinner).\nSpecial Entry Darshan tokens / fast-track seva access at major shrines.\nExperienced Spiritual Tour Coordinator from Siva Gayathri Tours.\nSenior citizen boarding and wheelchair assistance.",
            exc: "Personal archana tickets, tonsure charges, and special homams.\nRoom service, tips, and personal expenses.\nExtra sightseeing not covered in the spiritual circuit.",
            terms: "Temple authorities reserve right of entry based on traditional dress code compliance.\nDarshan queue timings are subject to temple crowd and VIP movement.\nPayment: 50% advance while confirming the Yatra & rest 50% before departure."
        },
        'flight': {
            inc: "Return Economy Class Airfare with 15 kg Check-in + 7 kg Cabin Baggage.\nDestination Airport Pickup and Sightseeing in Private Luxury AC Coach.\n3-Star / 4-Star Deluxe Hotel Accommodation.\nDaily Breakfast & Buffet Dinners.\nAll Interstate Border Road Taxes, Tolls & Parking Fees in destination state.\nDedicated Tour Manager escorting the group from arrival to departure.",
            exc: "Airline excess baggage fees beyond 15 kg check-in allowance.\nCamera tickets and monument monument entry fees.\nPersonal laundry, room telephone calls, and personal tips.",
            terms: "Govt Photo ID / Aadhaar card is strictly mandatory for airport check-in.\nAirline tickets are non-refundable once issued per airline group PNR policy.\nPayment: 50% advance on confirmation to block airline seats, balance before travel."
        },
        'corporate': {
            inc: "Dedicated Executive Luxury Coach Transfer (2x2 Pushback / AC Coach).\n4-Star Resort stay on Twin Sharing accommodation basis.\nFull Board Buffet Meals (Breakfast, Executive Buffet Lunch & Gala Dinner).\nConference Hall facility with Projector, Screen & Audio System for half-day.\nOutdoor Team Building Activities & Ice-breaker games with facilitator.\nEvening DJ Music & Campfire Barbeque Dinner.",
            exc: "Alcoholic beverages, personal laundry, and spa services.\nAny additional conference hours beyond package agreement.",
            terms: "Company Purchase Order (PO) required with GSTIN details for corporate billing.\nFinal delegate headcount to be confirmed 7 days prior to arrival.\nPayment: 50% on PO issuance, balance within 7 days of event completion."
        }
    };

    $(document).on('click', '.sg-chip-btn', function (e) {
        e.preventDefault();
        const tmplKey = $(this).data('template');
        const tmpl = TEMPLATE_INCLUSIONS[tmplKey];
        if (tmpl) {
            inclusionsField.val(tmpl.inc);
            exclusionsField.val(tmpl.exc);
            termsField.val(tmpl.terms);
            showToast("✨ Applied <strong>" + $(this).text().trim() + "</strong> checklist!");
        }
    });

    // =========================================================================
    // 8. Live Dual Pricing & Food Deduction Calculator (Step 2)
    // =========================================================================

    function updateLiveDualPricingPill() {
        const apVal = parseFloat(apInput.val()) || 0;
        const epVal = parseFloat(epInput.val()) || 0;
        const days = parseInt(durationDaysInput.val(), 10) || 1;

        $('#sg-food-calc-pill').remove();
        $('#sg-auto-ep-btn').remove();

        if (apVal > 0) {
            let pillText = '';
            if (epVal > 0) {
                const foodDiff = Math.max(0, apVal - epVal);
                const foodPerDay = days > 0 ? Math.round(foodDiff / days) : 0;
                pillText = `🍛 Food Component: ₹${foodDiff.toLocaleString('en-IN')} (~₹${foodPerDay}/day) | AP (Food): ₹${apVal.toLocaleString('en-IN')} | EP (No-Food): ₹${epVal.toLocaleString('en-IN')}`;
            } else {
                pillText = `AP Rate: ₹${apVal.toLocaleString('en-IN')} / head`;
            }

            apInput.after(`<span id="sg-food-calc-pill" class="sg-calc-pill sg-calc-green" style="margin-left:8px; font-size:12px;"><i class="fas fa-utensils mr-1"></i> ${pillText}</span>`);

            // If EP is empty or 0, offer 1-click auto-computation button
            if (!epVal || epVal === 0) {
                const suggestedDeduction = days * 350;
                const suggestedEP = Math.max(0, apVal - suggestedDeduction);
                const epBtnHtml = `<button type="button" id="sg-auto-ep-btn" class="sg-calc-pill sg-calc-blue" style="margin-left:8px; border:none; cursor:pointer;" data-ep="${suggestedEP}" title="Auto-deduct standard ₹350/day food cost"><i class="fas fa-calculator mr-1"></i> Auto-Compute EP Rate (-₹350/day = ₹${suggestedEP.toLocaleString('en-IN')})</button>`;
                epInput.after(epBtnHtml);
            }
        }
    }

    $(document).on('click', '#sg-auto-ep-btn', function (e) {
        e.preventDefault();
        const suggestedEP = $(this).data('ep');
        if (suggestedEP) {
            epInput.val(suggestedEP);
            if (!baseInput.val() || parseFloat(baseInput.val()) === 0) {
                baseInput.val(suggestedEP);
            }
            updateLiveDualPricingPill();
            showToast("✨ Auto-calculated Without-Food (EP) Rate: ₹" + suggestedEP.toLocaleString('en-IN'));
        }
    });

    apInput.on('input change', updateLiveDualPricingPill);
    epInput.on('input change', updateLiveDualPricingPill);
    durationDaysInput.on('input change', updateLiveDualPricingPill);
    updateLiveDualPricingPill();

    // =========================================================================
    // 9. Synchronize Live Unified Toolbar Snapshot
    // =========================================================================
    function updateLiveSnapshot() {
        const name = nameInput.val() || 'New Tour Package';
        const nights = durationNightsInput.val() || '0';
        const days = durationDaysInput.val() || '1';
        const price = apInput.val() || baseInput.val() || '0';

        $('#snap-name').text(name.length > 32 ? name.substring(0, 30) + '...' : name).attr('title', name);
        $('#snap-duration').text(`${nights}N / ${days}D`);
        $('#snap-price').text(parseFloat(price) > 0 ? `₹${parseFloat(price).toLocaleString('en-IN')}` : '₹0');
    }

    nameInput.on('input change', updateLiveSnapshot);
    durationNightsInput.on('input change', updateLiveSnapshot);
    durationDaysInput.on('input change', updateLiveSnapshot);
    $('#id_transit_mode, #id_meal_plan').on('change', updateLiveSnapshot);
    apInput.on('input change', updateLiveSnapshot);
    baseInput.on('input change', updateLiveSnapshot);
    updateLiveSnapshot();

    // =========================================================================
    // 10. 1-Click Day-by-Day Circuit / Itinerary Builder
    // =========================================================================
    const itineraryGroup = $('#itinerary_days-group');

    const CIRCUIT_TEMPLATES = {
        'kerala_iv_5d': {
            name: "Kerala College IV (Kochi - Alleppey - Vagamon - Athirappilly)",
            category: "college_iv",
            nights: 4,
            days: 5,
            daysData: [
                {
                    day_number: 1,
                    title: "Arrival Kochi - InfoPark IT Hub - Marine Drive & Fort Kochi",
                    route_segment: "Coimbatore to Kochi by 54-Seater Luxury Pushback Coach",
                    night_stay_location: "Hotel / Resort in Kochi",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Departure from campus, highway breakfast, arrival in Kochi and hotel check-in.",
                    sightseeing_spots: "Kochi InfoPark IT Corridor, Marine Drive Walkway, Fort Kochi Chinese Fishing Nets, St. Francis Church & Dutch Palace.",
                    evening_night_activity: "Sunset boating cruise at Marine Drive Kochi, South Indian dinner and group briefing.",
                    activities: "Industrial liaison visit, harbor sightseeing and waterfront exploration."
                },
                {
                    day_number: 2,
                    title: "Proceed to Alleppey - Backwater Houseboat Cruise & Beach",
                    route_segment: "Kochi to Alleppey (Vembanad Lake backwater corridor)",
                    night_stay_location: "Resort / Hotel in Alleppey / Changanassery",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Early breakfast, checkout, scenic drive to Alleppey Punnamada Jetty.",
                    sightseeing_spots: "Punnamada Lake, Vembanad Backwaters, Alleppey Beach, Light House & Coir Museum.",
                    evening_night_activity: "Exclusive Day Houseboat Cruise with traditional Kerala Sadhya lunch on board, evening beach stroll and resort dinner.",
                    activities: "Houseboat cruise across narrow canals, coir industrial process inspection."
                },
                {
                    day_number: 3,
                    title: "Proceed to Vagamon Hills - Pine Forest & Off-Road Jeep Safari",
                    route_segment: "Alleppey to Vagamon Western Ghats Hill Route",
                    night_stay_location: "Hilltop Nature Resort in Vagamon",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Breakfast, hill climb through rubber and tea plantations to misty Vagamon.",
                    sightseeing_spots: "Vagamon Pine Forest, Kurisumala Ashram, Suicide Point, Vagamon Lake & Meadows.",
                    evening_night_activity: "Thrilling 4x4 Off-Road Jeep Safari to deep valley viewpoints, followed by grand DJ Music party with Campfire at resort.",
                    activities: "Off-road extreme terrain safari, mountain photography, and student campfire dance."
                },
                {
                    day_number: 4,
                    title: "Athirappilly & Vazhachal Waterfalls - Return Transit",
                    route_segment: "Vagamon to Athirappilly - Chalakudy corridor",
                    night_stay_location: "Overnight Coach Journey / Campus",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Checkout after breakfast, descent towards the majestic Athirappilly waterfalls.",
                    sightseeing_spots: "Athirappilly 'Niagara of India' Waterfalls, Vazhachal Forest Waterfalls & Charpa Falls.",
                    evening_night_activity: "Dinner at highway restaurant, boarding coach for comfortable overnight return journey.",
                    activities: "Forest nature walk, waterfall viewpoints, photography and departure transit."
                },
                {
                    day_number: 5,
                    title: "Safe Campus Arrival & Tour Completion",
                    route_segment: "Highway to College Campus",
                    night_stay_location: "Home / Campus",
                    meals_included: "Morning Refreshment",
                    morning_activity: "Early morning arrival at college campus gates with cherished memories.",
                    sightseeing_spots: "Campus reporting and luggage de-boarding.",
                    evening_night_activity: "Tour conclusion.",
                    activities: "Safe dispersal of students and faculty."
                }
            ]
        },
        'mysore_coorg_4d': {
            name: "Mysore - Coorg - Chikmagalur (3N / 4D)",
            category: "college_iv",
            nights: 3,
            days: 4,
            daysData: [
                {
                    day_number: 1,
                    title: "Arrive Mysore - Palace Grandeur, Chamundi Hills & Brindavan Gardens",
                    route_segment: "Coimbatore to Mysore by Luxury Coach",
                    night_stay_location: "Hotel in Mysore",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Morning departure, cross Nilgiri forest corridor, arrive Mysore and check in.",
                    sightseeing_spots: "Mysore Maharaja Palace, Chamundi Hills Temple, St. Philomena's Church, KRS Dam & Brindavan Musical Gardens.",
                    evening_night_activity: "Illuminated Mysore Palace exterior view, Brindavan musical fountain show, dinner at Mysore hotel.",
                    activities: "Heritage palace visit, silk and sandalwood showroom tour, evening leisure."
                },
                {
                    day_number: 2,
                    title: "Proceed Coorg - Golden Temple Bylakuppe & Dubare Elephant Camp",
                    route_segment: "Mysore to Kushalnagar / Madikeri (Coorg)",
                    night_stay_location: "Coffee Plantation Resort in Coorg",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Breakfast, proceed towards misty Kodagu (Coorg).",
                    sightseeing_spots: "Tibetan Golden Temple (Namdroling Monastery), Dubare Elephant Camp, Kaveri Nisargadhama & Raja's Seat.",
                    evening_night_activity: "Sunset view at Raja's Seat, followed by DJ Campfire Night Party with music at resort.",
                    activities: "Tibetan cultural exposure, elephant interaction, coffee estate walk, and campfire."
                },
                {
                    day_number: 3,
                    title: "Proceed Chikmagalur - Mullayanagiri Peak 4x4 Safari & Tea Estate",
                    route_segment: "Madikeri to Chikmagalur via Hassan corridor",
                    night_stay_location: "Resort / Hotel in Chikmagalur",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Scenic hill road drive to the coffee land of Chikmagalur.",
                    sightseeing_spots: "Mullayanagiri (Highest Peak in Karnataka), Baba Budangiri, Z Point & Tea Estate.",
                    evening_night_activity: "Thrilling 4x4 Jeep Safari ride through steep hill slopes, campfire evening at resort.",
                    activities: "Off-road 4x4 mountain safari, peak trekking, and tea processing explanation."
                },
                {
                    day_number: 4,
                    title: "Belur & Halebidu Hoysala Architecture - Return Journey",
                    route_segment: "Chikmagalur to Campus via Hassan-Bangalore highway",
                    night_stay_location: "Campus / Home",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Checkout, proceed to world-famous UNESCO Hoysala temple heritage sites.",
                    sightseeing_spots: "Belur Chennakesava Temple, Halebidu Hoysaleswara Temple intricate rock carvings.",
                    evening_night_activity: "Highway dinner break, non-stop coach transit to campus.",
                    activities: "Historical architecture appreciation and return travel."
                }
            ]
        },
        'ooty_coonoor_3d': {
            name: "Ooty - Coonoor - Mudumalai Hills (2N / 3D)",
            category: "holiday",
            nights: 2,
            days: 3,
            daysData: [
                {
                    day_number: 1,
                    title: "Ascend Nilgiris - Botanical Gardens, Rose Garden & Ooty Lake Boating",
                    route_segment: "Coimbatore / Mettupalayam to Ooty via Kallar Ghat Road",
                    night_stay_location: "Resort / Deluxe Hotel in Ooty",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Scenic hill climb through 36 hairpin bends with viewpoint photography stops.",
                    sightseeing_spots: "Government Botanical Garden, Rose Garden, Ooty Lake & Boating, Doddabetta Peak.",
                    evening_night_activity: "Shopping at Tibetan market and Commercial Road, resort dinner with warm bonfire.",
                    activities: "Boating in Ooty Lake, garden walks, scenic tea estate photography."
                },
                {
                    day_number: 2,
                    title: "Coonoor Heritage Sightseeing, Sims Park, Tea Factory & Campfire",
                    route_segment: "Ooty to Coonoor scenic mountain stretch",
                    night_stay_location: "Resort in Ooty / Coonoor",
                    meals_included: "Breakfast, Lunch, Dinner",
                    morning_activity: "Breakfast, scenic drive to Coonoor valley (optional Nilgiri Mountain Toy Train ride).",
                    sightseeing_spots: "Sim's Park, Dolphin's Nose Viewpoint, Lamb's Rock, Highfield Tea Factory & Chocolate Museum.",
                    evening_night_activity: "Tea tasting session, factory chocolate buying, and resort DJ Campfire evening.",
                    activities: "Tea manufacturing process demonstration, mountain valley photography."
                },
                {
                    day_number: 3,
                    title: "Mudumalai Tiger Reserve Safari & Pykara Falls - Return Descent",
                    route_segment: "Ooty - Gudalur - Mudumalai - Coimbatore descent",
                    night_stay_location: "Home / Origin",
                    meals_included: "Breakfast, Lunch",
                    morning_activity: "Checkout after breakfast, proceed to Mudumalai National Park wildlife belt.",
                    sightseeing_spots: "Pykara Waterfalls, Pykara Speed Boating, Mudumalai Tiger Reserve Jungle Jeep Safari.",
                    evening_night_activity: "Descent down Nilgiris, drop back at pickup points.",
                    activities: "Wild elephant/deer spotting, speed boating, safe return trip."
                }
            ]
        },
        'devotional_yatra_5d': {
            name: "Arupadai Veedu & Navagraha Pilgrimage Yatra (4N / 5D)",
            category: "devotional",
            nights: 4,
            days: 5,
            daysData: [
                {
                    day_number: 1,
                    title: "Palani Dhandayuthapani Swamy Darshan - Winch Car Seva",
                    route_segment: "Coimbatore to Palani - Dindigul highway",
                    night_stay_location: "Pilgrim Hotel in Palani / Madurai",
                    meals_included: "Satvik Breakfast, Lunch, Dinner",
                    morning_activity: "Early morning spiritual departure, reach foothills of Palani Murugan temple.",
                    sightseeing_spots: "Palani Foothills Giri Veedhi, Hilltop Lord Murugan Temple, Winch Car Seva.",
                    evening_night_activity: "Evening Sayarakshai pooja darshan, Panchamirtham prasad collection, Satvik dinner.",
                    activities: "Hilltop temple darshan, tonsure seva support, spiritual bhajans."
                },
                {
                    day_number: 2,
                    title: "Madurai Meenakshi Amman Temple & Thirupparankundram Shrine",
                    route_segment: "Palani to Madurai cultural corridor",
                    night_stay_location: "Hotel in Madurai",
                    meals_included: "Satvik Breakfast, Lunch, Dinner",
                    morning_activity: "Proceed to ancient temple city of Madurai, hotel check-in.",
                    sightseeing_spots: "Thirupparankundram (1st Arupadai Veedu), Sri Meenakshi Sundareswarar Temple, Golden Lotus Tank.",
                    evening_night_activity: "Special Entry Darshan at Meenakshi Amman temple, Puttu Chokkanathar temple, Satvik dinner.",
                    activities: "Temple architecture tour, sacred theertham immersion, spiritual chanting."
                },
                {
                    day_number: 3,
                    title: "Tiruchendur Subramanya Swamy Beach Temple & Special Abhishekam",
                    route_segment: "Madurai to Tiruchendur sea coast",
                    night_stay_location: "Hotel / Cottage in Tiruchendur / Tirunelveli",
                    meals_included: "Satvik Breakfast, Lunch, Dinner",
                    morning_activity: "Early morning start to the seashore shrine of Lord Murugan (2nd Arupadai Veedu).",
                    sightseeing_spots: "Tiruchendur Bay of Bengal Beach, Nazhikinaru Sacred Well, Valli Cave Temple.",
                    evening_night_activity: "Sea bath, sacred holy dip in Nazhikinaru spring, evening Shanmuga Vilasam deeparadhana.",
                    activities: "Special entry beach temple darshan, spiritual vows."
                },
                {
                    day_number: 4,
                    title: "Rameshwaram Holy 22 Theerthams Snanam & Ramanathaswamy Darshan",
                    route_segment: "Tirunelveli to Rameshwaram Island via Pamban Bridge",
                    night_stay_location: "Hotel in Rameshwaram",
                    meals_included: "Satvik Breakfast, Lunch, Dinner",
                    morning_activity: "Cross scenic Pamban Bridge over the ocean, arrive Rameshwaram island.",
                    sightseeing_spots: "Agnitheertham Sea Snanam, 22 Sacred Wells inside Ramanathaswamy Temple, 1212 Pillars Corridor.",
                    evening_night_activity: "Spaniard darshan of Spatika Lingam, visit Dhanushkodi ocean border and Ram Setu point.",
                    activities: "Complete 22 theerthams snanam guided by Siva Gayathri coordinator, Pamban bridge photos."
                },
                {
                    day_number: 5,
                    title: "Thanjavur Brihadeeswarar Big Temple, Srirangam & Return",
                    route_segment: "Rameshwaram to Thanjavur - Trichy - Return",
                    night_stay_location: "Home Arrival",
                    meals_included: "Satvik Breakfast, Lunch, Dinner",
                    morning_activity: "Checkout, drive through fertile Kaveri delta.",
                    sightseeing_spots: "Thanjavur UNESCO Brihadeeswarar Temple (Big Temple), Srirangam Sri Ranganathaswamy Temple.",
                    evening_night_activity: "Final blessing darshan, highway dinner, return drop at home.",
                    activities: "Chola architecture wonder, Vishnu divyadesam darshan, safe return."
                }
            ]
        },
        'dubai_intl_5d': {
            name: "Dubai & Abu Dhabi International Flight Extravaganza (4N / 5D)",
            category: "international",
            nights: 4,
            days: 5,
            daysData: [
                {
                    day_number: 1,
                    title: "Flight Arrival Dubai - 4-Star Hotel Check-In & Marina Dhow Cruise",
                    route_segment: "Coimbatore / Chennai to Dubai International (DXB) by Flight",
                    night_stay_location: "4-Star Luxury City Hotel in Dubai",
                    meals_included: "Buffet Dinner",
                    morning_activity: "Airport arrival, eVisa clearance, luxury coach transfer to 4-star hotel.",
                    sightseeing_spots: "Dubai Marina Skyline, JBR Beach Promenade, Traditional Wooden Dhow Cruise.",
                    evening_night_activity: "2-Hour Dhow Cruise dinner with live Tanoura dance show & international buffet.",
                    activities: "Arrival orientation, overseas sim setup, evening leisure cruise."
                },
                {
                    day_number: 2,
                    title: "Dubai Panoramic City Tour, Burj Khalifa (124th Flr) & Dubai Mall",
                    route_segment: "Dubai Luxury Coach Sightseeing Circuit",
                    night_stay_location: "4-Star Luxury City Hotel in Dubai",
                    meals_included: "Buffet Breakfast, Indian Dinner",
                    morning_activity: "Buffet breakfast, guided city tour covering modern and historic landmarks.",
                    sightseeing_spots: "Palm Jumeirah, Atlantis Hotel Photo Stop, Burj Al Arab, Burj Khalifa 124th Floor, Dubai Mall & Musical Fountain.",
                    evening_night_activity: "At The Top Burj Khalifa observation deck view, spectacular Dubai Fountain evening show.",
                    activities: "Skyscraper sightseeing, mega mall shopping, skyline photography."
                },
                {
                    day_number: 3,
                    title: "Desert Safari, 4x4 Dune Bashing, Camel Ride & BBQ Gala Dinner",
                    route_segment: "Hotel to Lahbab Red Dunes Desert Camp by 4x4 Land Cruiser",
                    night_stay_location: "4-Star Luxury City Hotel in Dubai",
                    meals_included: "Buffet Breakfast, Desert BBQ Dinner",
                    morning_activity: "Morning leisure for pool / nearby shopping.",
                    sightseeing_spots: "Red Dunes Desert, Camel Farm, Bedouin Desert Camp, Sandboarding Slopes.",
                    evening_night_activity: "Thrilling 4x4 Dune Bashing, sunset photo stop, Henna painting, live Fire show, Belly dance & BBQ dinner.",
                    activities: "Desert safari adventure, cultural entertainment, dune photography."
                },
                {
                    day_number: 4,
                    title: "Abu Dhabi Day Tour - Sheikh Zayed Grand Mosque & Ferrari World",
                    route_segment: "Dubai to Abu Dhabi Capital Highway Corridor",
                    night_stay_location: "4-Star Luxury City Hotel in Dubai",
                    meals_included: "Buffet Breakfast, Dinner",
                    morning_activity: "Breakfast, luxury coach drive to the capital emirate of Abu Dhabi.",
                    sightseeing_spots: "Sheikh Zayed Grand Mosque (World's largest marble mosque), Abu Dhabi Corniche, Emirates Palace & Ferrari World.",
                    evening_night_activity: "Yas Island photo stop, return coach drive to Dubai hotel for dinner.",
                    activities: "Grand Mosque cultural etiquette tour, luxury architecture views."
                },
                {
                    day_number: 5,
                    title: "Dubai Frame, Miracle Garden, Gold Souk & Departure Flight",
                    route_segment: "Dubai Hotel to DXB Airport",
                    night_stay_location: "Flight Return to India",
                    meals_included: "Buffet Breakfast",
                    morning_activity: "Checkout after breakfast, visit remaining iconic attractions.",
                    sightseeing_spots: "Dubai Frame Sky Glass Bridge, Miracle Garden (150M flowers), Deira Gold Souk & Spice Market.",
                    evening_night_activity: "Airport drop 3 hours prior to flight departure, boarding return flight.",
                    activities: "Last-minute duty-free shopping, departure flight transit."
                }
            ]
        }
    };

    // Helper: Ensure inline formset has at least targetCount rows
    function ensureInlineRowCount(groupSelector, prefix, targetCount) {
        const group = $(groupSelector);
        if (!group.length) return [];

        let totalFormsInput = $(`#id_${prefix}-TOTAL_FORMS`);
        if (!totalFormsInput.length) {
            totalFormsInput = group.find(`input[name="${prefix}-TOTAL_FORMS"]`);
        }

        let currentTotal = parseInt(totalFormsInput.val(), 10) || 0;

        // Try clicking Django's add button
        const addBtn = group.find('.add-row a');
        while (currentTotal < targetCount && addBtn.length) {
            addBtn.trigger('click');
            const newTotal = parseInt(totalFormsInput.val(), 10) || (currentTotal + 1);
            if (newTotal === currentTotal) break;
            currentTotal = newTotal;
        }

        // Fallback: manually clone empty form
        const emptyTemplate = $(`#${prefix}-empty`);
        while (currentTotal < targetCount && emptyTemplate.length) {
            const newRowHtml = emptyTemplate.prop('outerHTML')
                .replace(new RegExp(`${prefix}-empty`, 'g'), `${prefix}-${currentTotal}`)
                .replace(new RegExp(`${prefix}-__prefix__`, 'g'), `${prefix}-${currentTotal}`)
                .replace(new RegExp(`__prefix__`, 'g'), currentTotal);

            const newRow = $(newRowHtml);
            newRow.removeClass('empty-form').show();
            emptyTemplate.before(newRow);
            currentTotal++;
            totalFormsInput.val(currentTotal);
        }

        const indices = [];
        for (let i = 0; i < targetCount; i++) {
            indices.push(i);
        }
        return indices;
    }

    function setItineraryField(index, field, value) {
        const el = $(`#id_itinerary_days-${index}-${field}, [name="itinerary_days-${index}-${field}"]`);
        if (el.length) {
            el.val(value).trigger('change');
        }
    }

    // Inject Itinerary Circuit Builder Toolbar
    if (itineraryGroup.length) {
        const circuitToolbarHtml = `
            <div class="sg-itinerary-builder-toolbar" id="sg-itinerary-builder-toolbar">
                <div class="sg-toolbar-title">
                    <i class="fas fa-route text-info"></i> 1-Click Circuit Itinerary Builder:
                </div>
                <div style="display:flex; flex-wrap:wrap; align-items:center; gap:10px;">
                    <select id="sg-circuit-selector" class="sg-circuit-select">
                        <option value="kerala_iv_5d">🎓 Kerala College IV (Kochi-Alleppey-Vagamon-Athirappilly) [4N / 5D]</option>
                        <option value="mysore_coorg_4d">🎓 Mysore - Coorg - Chikmagalur IV [3N / 4D]</option>
                        <option value="ooty_coonoor_3d">⛰️ Ooty - Coonoor - Mudumalai Hills [2N / 3D]</option>
                        <option value="devotional_yatra_5d">🕉️ Arupadai Veedu & Navagraha Pilgrimage [4N / 5D]</option>
                        <option value="dubai_intl_5d">✈️ Dubai & Abu Dhabi Flight Extravaganza [4N / 5D]</option>
                    </select>
                    <button type="button" class="sg-btn-builder-action" id="sg-btn-build-circuit">
                        <i class="fas fa-bolt text-warning mr-1"></i> Auto-Generate Day Cards
                    </button>
                    <button type="button" class="sg-btn-builder-clear" id="sg-btn-clear-circuit" title="Clear all day descriptions">
                        <i class="fas fa-eraser mr-1"></i> Clear Days
                    </button>
                </div>
            </div>
        `;
        itineraryGroup.before(circuitToolbarHtml);
    }

    // Event Handler: Generate Circuit Days
    $(document).on('click', '#sg-btn-build-circuit', function (e) {
        e.preventDefault();
        const selectedKey = $('#sg-circuit-selector').val();
        const circuit = CIRCUIT_TEMPLATES[selectedKey];
        if (!circuit) return;

        // Auto-update duration nights and days in main form
        durationNightsInput.val(circuit.nights).trigger('change');
        durationDaysInput.val(circuit.days).trigger('change');

        // Ensure rows exist
        ensureInlineRowCount('#itinerary_days-group', 'itinerary_days', circuit.daysData.length);

        // Populate rows
        circuit.daysData.forEach(function (day, idx) {
            setItineraryField(idx, 'day_number', day.day_number);
            setItineraryField(idx, 'title', day.title);
            setItineraryField(idx, 'route_segment', day.route_segment);
            setItineraryField(idx, 'night_stay_location', day.night_stay_location);
            setItineraryField(idx, 'meals_included', day.meals_included);
            setItineraryField(idx, 'morning_activity', day.morning_activity);
            setItineraryField(idx, 'sightseeing_spots', day.sightseeing_spots);
            setItineraryField(idx, 'evening_night_activity', day.evening_night_activity);
            setItineraryField(idx, 'activities', day.activities);

            // Visual feedback flash
            const rowCard = $(`#itinerary_days-${idx}`);
            if (rowCard.length) {
                rowCard.addClass('sg-row-flash');
                setTimeout(function () { rowCard.removeClass('sg-row-flash'); }, 1200);
            }
        });

        // Set package name placeholder/suggestion if empty
        if (!nameInput.val()) {
            nameInput.val(`${circuit.nights} NIGHTS ${circuit.days} DAYS ${circuit.name.toUpperCase()}`).trigger('input');
        }

        updateLiveSnapshot();
        showToast(`✨ Generated <strong>${circuit.name}</strong> (${circuit.daysData.length} Day Cards) with full sightseeing routes and meals!`);

        // Smooth scroll to itinerary section
        const firstCard = $('#itinerary_days-0');
        if (firstCard.length) {
            $('html, body').animate({ scrollTop: firstCard.offset().top - 80 }, 400);
        }
    });

    // Event Handler: Clear Days
    $(document).on('click', '#sg-btn-clear-circuit', function (e) {
        e.preventDefault();
        const totalForms = parseInt($('#id_itinerary_days-TOTAL_FORMS').val(), 10) || 1;
        for (let idx = 0; idx < totalForms; idx++) {
            setItineraryField(idx, 'title', '');
            setItineraryField(idx, 'route_segment', '');
            setItineraryField(idx, 'night_stay_location', '');
            setItineraryField(idx, 'meals_included', '');
            setItineraryField(idx, 'morning_activity', '');
            setItineraryField(idx, 'sightseeing_spots', '');
            setItineraryField(idx, 'evening_night_activity', '');
            setItineraryField(idx, 'activities', '');
        }
        showToast("🧹 Cleared itinerary day cards.");
    });

    // =========================================================================
    // 11. 1-Click Fleet Tariff Slabs Auto-Fill (Sedan to 54-Seat Bus)
    // =========================================================================
    const tariffGroup = $('#vehicle_tariffs-group');

    const FLEET_SLAB_TIERS = [
        {
            name: "Swift Dzire / Etios Sedan",
            tier: "4_sedan",
            seats: 4,
            regex: /sedan|dzire|etios/i,
            kmRate: 14.0,
            driverBata: 500.0,
            localPackageHours: 8,
            localIncludedKm: 80,
            localRate: 2200.0,
            extraHourRate: 150.0
        },
        {
            name: "Innova Crysta MPV",
            tier: "7_crysta",
            seats: 7,
            regex: /crysta|innova/i,
            kmRate: 20.0,
            driverBata: 600.0,
            localPackageHours: 8,
            localIncludedKm: 80,
            localRate: 3500.0,
            extraHourRate: 250.0
        },
        {
            name: "Force Urbania / Executive TT",
            tier: "17_tt_urbania",
            seats: 17,
            regex: /urbania|tempo traveller|17.*tt/i,
            kmRate: 26.0,
            driverBata: 800.0,
            localPackageHours: 8,
            localIncludedKm: 80,
            localRate: 5500.0,
            extraHourRate: 350.0
        },
        {
            name: "Deluxe Mini Bus",
            tier: "36_mini_bus",
            seats: 36,
            regex: /36|mini.*bus|40.*seater/i,
            kmRate: 35.0,
            driverBata: 1000.0,
            localPackageHours: 8,
            localIncludedKm: 80,
            localRate: 8500.0,
            extraHourRate: 500.0
        },
        {
            name: "54-Seater Luxury Tour Coach",
            tier: "54_luxury_coach",
            seats: 54,
            regex: /54|luxury.*coach|52.*volvo|coach/i,
            kmRate: 45.0,
            driverBata: 1200.0,
            localPackageHours: 8,
            localIncludedKm: 80,
            localRate: 12000.0,
            extraHourRate: 700.0
        }
    ];

    function setTariffField(index, field, value) {
        const el = $(`#id_vehicle_tariffs-${index}-${field}, [name="vehicle_tariffs-${index}-${field}"]`);
        if (el.length) {
            if (el.is(':checkbox')) {
                el.prop('checked', !!value).trigger('change');
            } else {
                el.val(value).trigger('change');
            }
        }
    }

    function setVehicleTypeOption(index, regexKeyword) {
        const sel = $(`#id_vehicle_tariffs-${index}-vehicle_type, [name="vehicle_tariffs-${index}-vehicle_type"]`);
        if (!sel.length) return;

        let matchedVal = null;
        sel.find('option').each(function () {
            const val = $(this).val();
            const text = $(this).text();
            if (val && regexKeyword.test(text)) {
                matchedVal = val;
                return false;
            }
        });

        if (!matchedVal) {
            const validOptions = sel.find('option').filter(function () { return !!$(this).val(); });
            if (validOptions.length > index) {
                matchedVal = validOptions.eq(index).val();
            } else if (validOptions.length > 0) {
                matchedVal = validOptions.first().val();
            }
        }

        if (matchedVal) {
            sel.val(matchedVal).trigger('change.select2').trigger('change');
            const optText = sel.find(`option[value="${matchedVal}"]`).text();
            const s2Container = sel.closest('td, .form-group').find('.select2-selection__rendered');
            if (s2Container.length && optText) {
                s2Container.text(optText).attr('title', optText);
            }
        }
    }

    // Inject Tariff Toolbar
    if (tariffGroup.length) {
        const tariffToolbarHtml = `
            <div class="sg-tariff-builder-toolbar" id="sg-tariff-builder-toolbar">
                <div class="sg-toolbar-title">
                    <i class="fas fa-bus-alt text-success"></i> 1-Click Fleet Tariff Slabs (4 to 54 Seats):
                </div>
                <div style="display:flex; flex-wrap:wrap; align-items:center; gap:10px;">
                    <button type="button" class="sg-btn-tariff-action" id="sg-btn-build-tariffs">
                        <i class="fas fa-magic text-warning mr-1"></i> Auto-Populate Standard Fleet Tariffs (4 to 54 Seats)
                    </button>
                    <button type="button" class="sg-btn-builder-clear" id="sg-btn-clear-tariffs" title="Reset all tariff rows">
                        <i class="fas fa-eraser mr-1"></i> Reset Tariffs
                    </button>
                </div>
            </div>
        `;
        tariffGroup.before(tariffToolbarHtml);
    }

    // Event Handler: Populate Tariffs
    $(document).on('click', '#sg-btn-build-tariffs', function (e) {
        e.preventDefault();
        const days = parseInt(durationDaysInput.val(), 10) || 3;
        const cat = categorySelect.val() || 'holiday';
        const isLocal = (cat === 'local_tour' || days === 1);

        ensureInlineRowCount('#vehicle_tariffs-group', 'vehicle_tariffs', FLEET_SLAB_TIERS.length);

        FLEET_SLAB_TIERS.forEach(function (tier, idx) {
            setVehicleTypeOption(idx, tier.regex);
            setTariffField(idx, 'seating_tier', tier.tier);

            if (isLocal) {
                setTariffField(idx, 'rate_type', 'local_1day');
                setTariffField(idx, 'package_rate', tier.localRate);
                setTariffField(idx, 'per_day_rate', tier.localRate);
                setTariffField(idx, 'included_km', tier.localIncludedKm);
                setTariffField(idx, 'extra_km_rate', tier.kmRate);
                setTariffField(idx, 'local_package_hours', tier.localPackageHours);
                setTariffField(idx, 'extra_hour_rate', tier.extraHourRate);
                setTariffField(idx, 'driver_bata_per_day', tier.driverBata);
                setTariffField(idx, 'driver_bata_included', true);
                setTariffField(idx, 'toll_parking_included', true);
            } else {
                const totalKm = days * 300;
                const perDay = (300 * tier.kmRate) + tier.driverBata;
                const pkgRate = days * perDay;

                setTariffField(idx, 'rate_type', 'outstation_multiday');
                setTariffField(idx, 'package_rate', pkgRate);
                setTariffField(idx, 'per_day_rate', perDay);
                setTariffField(idx, 'included_km', totalKm);
                setTariffField(idx, 'extra_km_rate', tier.kmRate);
                setTariffField(idx, 'driver_bata_per_day', tier.driverBata);
                setTariffField(idx, 'driver_bata_included', true);
                setTariffField(idx, 'toll_parking_included', true);
            }

            const rowTr = $(`#vehicle_tariffs-${idx}`);
            if (rowTr.length) {
                rowTr.addClass('sg-row-flash');
                setTimeout(function () { rowTr.removeClass('sg-row-flash'); }, 1200);
            }
        });

        showToast(`✨ Generated <strong>5-Tier Fleet Tariffs</strong> (Dzire, Crysta, Urbania, Mini Bus, 54-Coach) for <strong>${days} Days</strong>!`);

        const firstTariff = $('#vehicle_tariffs-0');
        if (firstTariff.length) {
            $('html, body').animate({ scrollTop: firstTariff.offset().top - 80 }, 400);
        }
    });

    // Event Handler: Reset Tariffs
    $(document).on('click', '#sg-btn-clear-tariffs', function (e) {
        e.preventDefault();
        const totalForms = parseInt($('#id_vehicle_tariffs-TOTAL_FORMS').val(), 10) || 1;
        for (let idx = 0; idx < totalForms; idx++) {
            setTariffField(idx, 'package_rate', 0);
            setTariffField(idx, 'per_day_rate', 0);
            setTariffField(idx, 'included_km', 0);
        }
        showToast("🧹 Reset vehicle tariff values.");
    });

    // =========================================================================
    // 12. Live Proposal Modal Preview
    // =========================================================================
    const proposalModalHtml = `
        <div id="sg-proposal-modal-overlay" class="sg-modal-overlay">
            <div class="sg-modal-dialog">
                <div class="sg-modal-header">
                    <div class="sg-modal-title">
                        <i class="fas fa-file-pdf text-danger mr-2"></i> Official Proposal Quotation Preview (Siva Gayathri Tours)
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <button type="button" class="sg-btn-modal-print" id="sg-btn-modal-print-action">
                            <i class="fas fa-print mr-1"></i> Print / PDF
                        </button>
                        <a id="sg-modal-newtab-link" href="#" target="_blank" class="sg-btn-modal-newtab">
                            <i class="fas fa-external-link-alt mr-1"></i> Open in New Tab
                        </a>
                        <button type="button" class="sg-btn-modal-close" id="sg-btn-close-modal" title="Close Preview (Esc)">
                            &times;
                        </button>
                    </div>
                </div>
                <div class="sg-modal-body">
                    <iframe id="sg-proposal-iframe" src="about:blank" frameborder="0" style="width:100%; height:100%; border:none;"></iframe>
                </div>
            </div>
        </div>
    `;
    $('body').append(proposalModalHtml);

    function getPackageIdFromUrl() {
        const match = window.location.pathname.match(/\/package\/(\d+)\/change/);
        return match ? match[1] : null;
    }

    $(document).on('click', '#sg-btn-open-preview', function (e) {
        e.preventDefault();
        const pkgId = getPackageIdFromUrl();
        let previewUrl = '';

        if (pkgId) {
            previewUrl = `/packages/quote/${pkgId}/?modal=1`;
        } else {
            const params = new URLSearchParams({
                modal: '1',
                name: nameInput.val() || 'Tour Package Proposal',
                nights: durationNightsInput.val() || '4',
                days: durationDaysInput.val() || '5',
                category: categorySelect.val() || 'college_iv',
                destination: destinationInput.val() || 'Tour Destination Circuit',
                price_with_food: apInput.val() || '6850',
                price_without_food: epInput.val() || '4750',
                base_price: baseInput.val() || '4800',
                meal_plan: $('#id_meal_plan').val() || 'AP',
                room_sharing: $('#id_room_sharing_type').val() || '4_sharing',
                inclusions: inclusionsField.val() || '',
                exclusions: exclusionsField.val() || '',
                terms: termsField.val() || '',
            });
            previewUrl = `/packages/quote/preview/?${params.toString()}`;
        }

        $('#sg-proposal-iframe').attr('src', previewUrl);
        $('#sg-modal-newtab-link').attr('href', previewUrl.replace('modal=1', 'modal=0'));
        $('#sg-proposal-modal-overlay').css('display', 'flex').hide().fadeIn(200);
    });

    $(document).on('click', '#sg-btn-close-modal', function () {
        $('#sg-proposal-modal-overlay').fadeOut(150, function () {
            $('#sg-proposal-iframe').attr('src', 'about:blank');
        });
    });

    $(document).on('click', '#sg-btn-modal-print-action', function () {
        const iframe = document.getElementById('sg-proposal-iframe');
        if (iframe && iframe.contentWindow) {
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
        }
    });

    $(document).on('click', '#sg-proposal-modal-overlay', function (e) {
        if ($(e.target).is('#sg-proposal-modal-overlay')) {
            $('#sg-btn-close-modal').trigger('click');
        }
    });
    $(document).on('keydown', function (e) {
        if (e.key === 'Escape' && $('#sg-proposal-modal-overlay').is(':visible')) {
            $('#sg-btn-close-modal').trigger('click');
        }
    });

    // =========================================================================
    // 13. Live Profit Margin & Cost Breakeven Sheet
    // =========================================================================
    const marginSheetHtml = `
        <div id="sg-margin-sheet-card" class="sg-margin-sheet-card">
            <div class="sg-margin-header" id="sg-margin-header-toggle" title="Click to show/hide Profit Margin & Breakeven Calculator">
                <div class="sg-margin-title">
                    <i class="fas fa-calculator text-warning mr-2"></i> Live Profit Margin & Cost Breakeven Calculator
                    <i class="fas fa-chevron-down text-muted ml-2" id="sg-margin-caret" style="font-size:11px;"></i>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <button type="button" class="sg-btn-builder-clear" id="sg-btn-auto-costs" style="padding:4px 8px; font-size:11px;" title="Auto-estimate costs based on headcount & days">
                        <i class="fas fa-magic text-warning mr-1"></i> Auto-Estimate Costs
                    </button>
                    <span id="sg-margin-status-badge" class="sg-margin-badge badge-green">
                        <i class="fas fa-check-circle mr-1"></i> 22.4% Margin
                    </span>
                </div>
            </div>
            <div class="sg-margin-body" id="sg-margin-body" style="display:none;">
                <div class="sg-margin-grid">
                    <!-- Col 1: Trip Parameters & Revenue -->
                    <div class="sg-margin-col">
                        <div class="sg-col-title"><i class="fas fa-users text-info mr-1"></i> Revenue Parameters</div>
                        <div class="sg-metric-row">
                            <span>Quoted Rate (AP / head):</span>
                            <strong id="margin-rev-rate" style="color:#38bdf8;">₹0</strong>
                        </div>
                        <div class="sg-metric-row">
                            <span>Paying Headcount:</span>
                            <input type="number" id="sg-calc-pax" value="50" min="1" class="sg-mini-input" style="width:75px;">
                        </div>
                        <div class="sg-metric-row">
                            <span>Complimentary Staff:</span>
                            <span id="margin-free-staff" style="color:#94a3b8;">2 Staff</span>
                        </div>
                        <div class="sg-metric-row sg-metric-highlight">
                            <span>Total Trip Revenue:</span>
                            <strong id="margin-total-revenue" style="color:#34d399; font-size:14.5px;">₹0</strong>
                        </div>
                    </div>

                    <!-- Col 2: Operating Expenses (Editable) -->
                    <div class="sg-margin-col">
                        <div class="sg-col-title"><i class="fas fa-receipt text-danger mr-1"></i> Operating Expenses</div>
                        <div class="sg-metric-row">
                            <span>Bus Convoy Fleet:</span>
                            <input type="number" id="sg-cost-bus" value="44000" step="500" class="sg-mini-input" style="width:90px;">
                        </div>
                        <div class="sg-metric-row">
                            <span>Hotel Accommodation:</span>
                            <input type="number" id="sg-cost-hotel" value="46800" step="500" class="sg-mini-input" style="width:90px;">
                        </div>
                        <div class="sg-metric-row">
                            <span>Food Expenses:</span>
                            <input type="number" id="sg-cost-food" value="87500" step="500" class="sg-mini-input" style="width:90px;">
                        </div>
                        <div class="sg-metric-row">
                            <span>DJ, Permits, Tolls & Misc:</span>
                            <input type="number" id="sg-cost-misc" value="23000" step="500" class="sg-mini-input" style="width:90px;">
                        </div>
                        <div class="sg-metric-row sg-metric-highlight">
                            <span>Total Operating Cost:</span>
                            <strong id="margin-total-cost" style="color:#f87171; font-size:14.5px;">₹0</strong>
                        </div>
                    </div>

                    <!-- Col 3: Profit & Breakeven Analysis -->
                    <div class="sg-margin-col">
                        <div class="sg-col-title"><i class="fas fa-chart-line text-success mr-1"></i> Net Profit & Breakeven</div>
                        <div class="sg-kpi-box">
                            <span class="sg-kpi-label">Estimated Net Profit</span>
                            <span class="sg-kpi-val" id="margin-net-profit" style="color:#34d399;">₹0</span>
                        </div>
                        <div class="sg-kpi-box" style="margin-top:6px; padding:6px;">
                            <span class="sg-kpi-label">Profit Margin %</span>
                            <span class="sg-kpi-val" id="margin-percentage" style="color:#38bdf8; font-size:17px;">0.0%</span>
                        </div>
                        <div class="sg-kpi-breakeven">
                            <i class="fas fa-balance-scale mr-1 text-warning"></i> Breakeven Rate: 
                            <strong id="margin-breakeven-rate">₹0 / head</strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (!$('#sg-margin-sheet-card').length) {
        const pricingCardBody = $('[id*="headcount-dual-pricing"] .card-body, .grp-pricing-dual .card-body');
        if (pricingCardBody.length) {
            pricingCardBody.first().append(marginSheetHtml);
        } else {
            $('.field-price_with_food').closest('.form-group, .form-row').after(marginSheetHtml);
        }
    }

    function autoEstimateTripCosts(force) {
        const pax = parseInt($('#sg-calc-pax').val(), 10) || parseInt($('#id_min_pax').val(), 10) || 50;
        const days = parseInt(durationDaysInput.val(), 10) || 3;
        const nights = parseInt(durationNightsInput.val(), 10) || (days > 1 ? days - 1 : 0);

        // 1. Bus Convoy Fleet Cost
        if (force || !$('#sg-cost-bus').data('user-edited')) {
            const vehText = $('#id_default_vehicle_type option:selected').text().toLowerCase();
            let dailyBus = 14000;
            let cap = 50;
            if (vehText.includes('sedan') || vehText.includes('dzire') || vehText.includes('etios')) {
                dailyBus = 2200; cap = 4;
            } else if (vehText.includes('crysta') || vehText.includes('innova') || vehText.includes('ertiga')) {
                dailyBus = 3500; cap = 7;
            } else if (vehText.includes('urbania') || vehText.includes('tempo') || vehText.includes('tt')) {
                dailyBus = 5500; cap = 17;
            } else if (vehText.includes('mini') || vehText.includes('36') || vehText.includes('40')) {
                dailyBus = 8500; cap = 36;
            } else {
                dailyBus = 14000; cap = 50;
            }
            const busCount = Math.max(1, Math.ceil(pax / cap));
            $('#sg-cost-bus').val(busCount * days * dailyBus);
        }

        // 2. Hotel Accommodation Cost
        if (force || !$('#sg-cost-hotel').data('user-edited')) {
            const sharing = $('#id_room_sharing_type').val() || '4_sharing';
            let divisor = 4;
            if (sharing === 'single') divisor = 1;
            else if (sharing === 'twin_sharing') divisor = 2;
            else if (sharing === '3_sharing') divisor = 3;
            else if (sharing === '4_sharing') divisor = 4;
            else if (sharing === '6_sharing') divisor = 6;
            else if (sharing === '8_sharing') divisor = 8;
            else if (sharing === 'dormitory') divisor = 10;

            const rooms = Math.ceil(pax / divisor);
            const hotelText = ($('#id_hotel_star_category').val() || '').toLowerCase();
            let roomRate = 1200;
            if (hotelText.includes('5-star') || hotelText.includes('5 star')) roomRate = 5500;
            else if (hotelText.includes('4-star') || hotelText.includes('4 star')) roomRate = 3200;
            else if (hotelText.includes('3-star') || hotelText.includes('3 star')) roomRate = 1800;
            else if (hotelText.includes('pilgrim') || hotelText.includes('lodge')) roomRate = 1000;

            $('#sg-cost-hotel').val(rooms * nights * roomRate);
        }

        // 3. Food Cost
        if (force || !$('#sg-cost-food').data('user-edited')) {
            const mealPlan = $('#id_meal_plan').val() || 'AP';
            const cat = categorySelect.val() || 'college_iv';
            let dailyFood = 350;
            if (mealPlan === 'EP') dailyFood = 0;
            else if (mealPlan === 'CP') dailyFood = 100;
            else if (mealPlan === 'MAP') dailyFood = 220;
            else if (mealPlan === 'AP') {
                dailyFood = (cat === 'devotional' || cat === 'pilgrimage') ? 400 : 350;
            }
            $('#sg-cost-food').val(pax * days * dailyFood);
        }

        // 4. Misc & Tolls
        if (force || !$('#sg-cost-misc').data('user-edited')) {
            let misc = 15000;
            if (days <= 1) misc = 3000;
            else if (days <= 3) misc = 12000;
            else misc = 22000;
            $('#sg-cost-misc').val(misc);
        }
    }

    function calculateProfitMargin() {
        const pax = parseInt($('#sg-calc-pax').val(), 10) || parseInt($('#id_min_pax').val(), 10) || 50;
        const freeStaff = $('#id_complementary_staff_count').val() || '2';
        $('#margin-free-staff').text(`${freeStaff} Staff`);

        const rate = parseFloat(apInput.val()) || parseFloat(baseInput.val()) || 0;
        $('#margin-rev-rate').text(rate > 0 ? `₹${rate.toLocaleString('en-IN')}` : '₹0');

        const totalRevenue = pax * rate;
        $('#margin-total-revenue').text(`₹${totalRevenue.toLocaleString('en-IN')}`);

        autoEstimateTripCosts(false);

        const busCost = parseFloat($('#sg-cost-bus').val()) || 0;
        const hotelCost = parseFloat($('#sg-cost-hotel').val()) || 0;
        const foodCost = parseFloat($('#sg-cost-food').val()) || 0;
        const miscCost = parseFloat($('#sg-cost-misc').val()) || 0;

        const totalCost = busCost + hotelCost + foodCost + miscCost;
        $('#margin-total-cost').text(`₹${totalCost.toLocaleString('en-IN')}`);

        const netProfit = totalRevenue - totalCost;
        $('#margin-net-profit').text(`₹${netProfit.toLocaleString('en-IN')}`);
        if (netProfit >= 0) {
            $('#margin-net-profit').css('color', '#34d399');
        } else {
            $('#margin-net-profit').css('color', '#f87171');
        }

        const marginPercent = totalRevenue > 0 ? ((netProfit / totalRevenue) * 100).toFixed(1) : 0;
        $('#margin-percentage').text(`${marginPercent}%`);

        const breakeven = pax > 0 ? Math.ceil(totalCost / pax) : 0;
        $('#margin-breakeven-rate').text(`₹${breakeven.toLocaleString('en-IN')} / head`);

        const badge = $('#sg-margin-status-badge');
        if (marginPercent >= 18) {
            badge.attr('class', 'sg-margin-badge badge-green').html(`<i class="fas fa-check-circle mr-1"></i> ${marginPercent}% Margin (High Profit)`);
        } else if (marginPercent >= 10) {
            badge.attr('class', 'sg-margin-badge badge-yellow').html(`<i class="fas fa-exclamation-circle mr-1"></i> ${marginPercent}% Margin (Healthy)`);
        } else {
            badge.attr('class', 'sg-margin-badge badge-red').html(`<i class="fas fa-exclamation-triangle mr-1"></i> ${marginPercent}% Margin (Low Margin)`);
        }
    }

    $(document).on('input change', '#sg-calc-pax, #sg-cost-bus, #sg-cost-hotel, #sg-cost-food, #sg-cost-misc', function () {
        $(this).data('user-edited', true);
        calculateProfitMargin();
    });
    apInput.on('input change', calculateProfitMargin);
    baseInput.on('input change', calculateProfitMargin);
    $('#id_min_pax, #id_complementary_staff_count').on('input change', function () {
        if ($('#id_min_pax').val() && !$('#sg-calc-pax').data('user-edited')) {
            $('#sg-calc-pax').val($('#id_min_pax').val());
        }
        calculateProfitMargin();
    });

    $(document).on('click', '#sg-btn-auto-costs', function (e) {
        e.preventDefault();
        $('#sg-cost-bus, #sg-cost-hotel, #sg-cost-food, #sg-cost-misc').removeData('user-edited');
        autoEstimateTripCosts(true);
        calculateProfitMargin();
        const pax = parseInt($('#sg-calc-pax').val(), 10) || 50;
        const days = parseInt(durationDaysInput.val(), 10) || 3;
        showToast("✨ Auto-estimated trip expenses for " + pax + " Pax & " + days + " Days!");
    });

    calculateProfitMargin();

    $(document).on('click', '#sg-margin-header-toggle', function (e) {
        if ($(e.target).closest('#sg-btn-auto-costs').length) return;
        const body = $('#sg-margin-body');
        const caret = $('#sg-margin-caret');
        body.slideToggle(180);
        caret.toggleClass('fa-chevron-down fa-chevron-up');
    });

    // =========================================================================
    // 14. 1-Click WhatsApp Trip Briefing Generator
    // =========================================================================
    const whatsappModalHtml = `
        <div id="sg-whatsapp-modal-overlay" class="sg-modal-overlay">
            <div class="sg-modal-dialog sg-whatsapp-dialog">
                <div class="sg-modal-header">
                    <div class="sg-modal-title">
                        <i class="fab fa-whatsapp text-success mr-2" style="font-size:18px;"></i> 1-Click WhatsApp Trip Briefing Generator
                    </div>
                    <button type="button" class="sg-btn-modal-close" id="sg-btn-close-wa-modal" title="Close (Esc)">
                        &times;
                    </button>
                </div>
                <div class="sg-wa-tabs">
                    <button type="button" class="sg-wa-tab-btn active" data-tab="student">
                        <i class="fas fa-graduation-cap mr-1"></i> Student Briefing
                    </button>
                    <button type="button" class="sg-wa-tab-btn" data-tab="faculty">
                        <i class="fas fa-user-tie mr-1"></i> Faculty Dossier
                    </button>
                    <button type="button" class="sg-wa-tab-btn" data-tab="crew">
                        <i class="fas fa-bus mr-1"></i> Driver Dispatch
                    </button>
                </div>
                <div class="sg-wa-content">
                    <textarea id="sg-wa-message-text" class="sg-wa-textarea" spellcheck="false"></textarea>
                    <div class="sg-wa-actions">
                        <button type="button" class="sg-btn-wa-copy" id="sg-btn-wa-copy">
                            <i class="fas fa-copy mr-1"></i> Copy Message
                        </button>
                        <a href="#" target="_blank" class="sg-btn-wa-send" id="sg-btn-wa-send">
                            <i class="fab fa-whatsapp mr-1"></i> Open in WhatsApp Web
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
    $('body').append(whatsappModalHtml);

    let activeWaTab = 'student';

    function compileWhatsAppMessage(tabKey) {
        const name = nameInput.val() || 'COLLEGE INDUSTRIAL VISIT EXPEDITION';
        const nights = durationNightsInput.val() || '4';
        const days = durationDaysInput.val() || '5';
        const dest = destinationInput.val() || 'Kochi, Vagamon, Alleppey';
        const meal = $('#id_meal_plan option:selected').text() || 'AP Plan (Full Board)';
        const sharing = $('#id_room_sharing_type option:selected').text() || '4-Sharing';
        const contacts = $('#id_contact_persons_footer').val() || 'Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)';

        let msg = '';
        if (tabKey === 'student') {
            msg = `🚌 *SIVA GAYATHRI TOURS & TRAVELS — STUDENT TRIP BRIEFING*\n` +
                  `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                  `🎓 *Tour:* ${name}\n` +
                  `📅 *Duration:* ${nights} Nights / ${days} Days\n` +
                  `📍 *Circuit:* ${dest}\n` +
                  `🍽️ *Food:* ${meal}\n` +
                  `🏨 *Stay:* Deluxe Resort (${sharing})\n\n` +
                  `🎒 *MANDATORY PACKING CHECKLIST:*\n` +
                  `• College Identity Card & Govt Aadhaar Card (Must have original)\n` +
                  `• Formal / Semi-formal attire for scheduled industrial / factory visits\n` +
                  `• Modest traditional wear for temple entries if covered in circuit\n` +
                  `• Warm jacket / sweater for hill station night campfire\n` +
                  `• Mobile power bank, personal medicines & modest spending cash\n\n` +
                  `⚠️ *SAFETY & CODE OF CONDUCT:*\n` +
                  `• Strict adherence to college discipline under Faculty In-Charge supervision.\n` +
                  `• Punctuality at all assembly points is required to complete all sightseeing.\n` +
                  `• Consuming alcohol / contraband is strictly prohibited throughout the tour.\n\n` +
                  `📞 *24x7 TOUR COORDINATOR CONTACTS:*\n` +
                  `• ${contacts}\n` +
                  `✨ _Wishing all students a memorable, adventurous, and safe expedition!_`;
        } else if (tabKey === 'faculty') {
            msg = `🎓 *SIVA GAYATHRI TOURS & TRAVELS — FACULTY IN-CHARGE DOSSIER*\n` +
                  `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                  `🏢 *Trip Dossier:* ${name}\n` +
                  `📅 *Duration:* ${nights} Nights / ${days} Days\n` +
                  `📍 *Destination Corridor:* ${dest}\n\n` +
                  `🏨 *HOSPITALITY & ROOMING ARRANGEMENTS:*\n` +
                  `• Student Accommodation: Verified hotel/resort on ${sharing} basis.\n` +
                  `• Faculty Accommodation: Dedicated Executive Twin-Sharing Rooms.\n` +
                  `• Meal Plan: ${meal} (South Indian Buffet Breakfast, Lunch & Dinner).\n` +
                  `• DJ with Campfire Night party arranged with professional sound & lighting.\n\n` +
                  `🚍 *CONVOY & LOGISTICS:*\n` +
                  `• Dedicated 2x2 luxury pushback tourist coach convoy.\n` +
                  `• Interstate RTO border taxes, commercial permits & toll charges included.\n` +
                  `• Industry visit clearance liaison escort provided.\n\n` +
                  `📞 *DIRECT OPS CONTROL DESK:*\n` +
                  `• ${contacts}`;
        } else if (tabKey === 'crew') {
            msg = `🚍 *SIVA GAYATHRI TOURS — DRIVER & CREW DISPATCH ORDER*\n` +
                  `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                  `🚩 *Tour Run:* ${name}\n` +
                  `📅 *Schedule:* ${days} Days / ${nights} Nights\n` +
                  `🛣️ *Circuit Route:* ${dest}\n\n` +
                  `📋 *MANDATORY DRIVER PROTOCOLS:*\n` +
                  `1. Pre-Trip: Check tyre pressure, spare stepney, diesel level & AC cooling.\n` +
                  `2. Documents: Carry Vehicle Fitness, Insurance, Pollution & Interstate Tourist Permit.\n` +
                  `3. Safety: Maximum 80 km/h speed limit. No rash overtaking or night-time over-speeding.\n` +
                  `4. Reporting: Report to campus pickup terminal 45 minutes prior to scheduled departure.\n\n` +
                  `⛽ *EXPENSES & BATA:*\n` +
                  `• Daily Driver Bata allowance credited per roster agreement.\n` +
                  `• Commercial parking & highway toll receipts must be submitted at garage return.\n\n` +
                  `📞 *OPS MANAGER HELPLINE:* +91 98425 33777`;
        }

        $('#sg-wa-message-text').val(msg);
        const waEncoded = encodeURIComponent(msg);
        $('#sg-btn-wa-send').attr('href', `https://web.whatsapp.com/send?text=${waEncoded}`);
    }

    $(document).on('click', '#sg-btn-open-whatsapp', function (e) {
        e.preventDefault();
        compileWhatsAppMessage(activeWaTab);
        $('#sg-whatsapp-modal-overlay').css('display', 'flex').hide().fadeIn(200);
    });

    $(document).on('click', '#sg-btn-close-wa-modal', function () {
        $('#sg-whatsapp-modal-overlay').fadeOut(150);
    });

    $(document).on('click', '.sg-wa-tab-btn', function () {
        $('.sg-wa-tab-btn').removeClass('active');
        $(this).addClass('active');
        activeWaTab = $(this).data('tab');
        compileWhatsAppMessage(activeWaTab);
    });

    $(document).on('click', '#sg-btn-wa-copy', function () {
        const textarea = document.getElementById('sg-wa-message-text');
        if (textarea) {
            textarea.select();
            document.execCommand('copy');
            const btn = $(this);
            const orig = btn.html();
            btn.html('<i class="fas fa-check text-success mr-1"></i> Copied!').css('background', '#065f46');
            setTimeout(function () {
                btn.html(orig).css('background', '#334155');
            }, 1800);
            showToast("📋 WhatsApp briefing copied to clipboard!");
        }
    });

    $(document).on('click', '#sg-whatsapp-modal-overlay', function (e) {
        if ($(e.target).is('#sg-whatsapp-modal-overlay')) {
            $('#sg-btn-close-wa-modal').trigger('click');
        }
    });

    // =========================================================================
    // 15. Streamline Field Help Texts & Tooltips
    // =========================================================================
    function streamlineFieldHelpTexts() {
        $('.form-row').each(function () {
            const row = $(this);
            const helpEl = row.find('.help-block, .help, span.helptext, p.help');
            if (helpEl.length) {
                const text = helpEl.text().trim();
                const input = row.find('input[type="text"], input[type="number"], textarea');

                // If input doesn't have a placeholder or has an empty placeholder
                if (input.length && (!input.attr('placeholder') || input.attr('placeholder').startsWith('e.g.'))) {
                    if (text.includes('e.g.') || text.includes('Format:') || text.length < 50) {
                        input.attr('placeholder', text);
                    }
                }

                // Attach subtle info tooltip badge next to label if not already present
                const label = row.find('label');
                if (label.length && !label.find('.sg-tooltip-badge').length && text.length > 0) {
                    label.append(`<span class="sg-tooltip-badge" title="${text.replace(/"/g, '&quot;')}"><i class="fas fa-info"></i></span>`);
                }

                // Hide the sprawling raw help block to eliminate vertical clutter
                helpEl.addClass('sg-help-hidden');
            }
        });
    }
    streamlineFieldHelpTexts();

    // =========================================================================
    // 16. Smart Package Code & Duration Detection from Title
    // =========================================================================
    const codeInput = $('#id_package_code');
    const STOPWORDS = new Set(['TOUR', 'PACKAGE', 'TRIP', 'DAYS', 'NIGHTS', 'DAY', 'NIGHT', 'AND', 'FOR', 'WITH', 'TO', 'FROM', 'THE', 'A', 'AN', 'OF', 'IN', 'ON', 'AT']);

    function autoGenSmartPackageCode(title) {
        if (!title || !codeInput.length) return;
        if (codeInput.data('user-manually-edited')) return;

        const words = title.toUpperCase().replace(/[^A-Z0-9\s]/g, ' ').split(/\s+/).filter(function (w) {
            return w.length > 1 && !STOPWORDS.has(w);
        });
        const parts = ['SGT'];
        for (let i = 0; i < Math.min(2, words.length); i++) {
            parts.push(words[i].substring(0, 4));
        }
        const days = durationDaysInput.val() || '3';
        parts.push(String(days).padStart(2, '0') + 'D');
        codeInput.val(parts.join('-'));
    }

    function autoDetectDurationFromName(title) {
        if (!title) return;
        // Match "XN/YD" or "X N / Y D" or "X NIGHTS Y DAYS"
        const n_d_match = title.match(/(\d+)\s*(?:N|NIGHTS?)\s*[\/\-&]?\s*(\d+)\s*(?:D|DAYS?)/i);
        if (n_d_match) {
            const nights = parseInt(n_d_match[1], 10);
            const days = parseInt(n_d_match[2], 10);
            if (!durationNightsInput.data('user-manually-edited')) durationNightsInput.val(nights).trigger('change');
            if (!durationDaysInput.data('user-manually-edited')) durationDaysInput.val(days).trigger('change');
            return;
        }
        // Match "XD/XN"
        const d_n_match = title.match(/(\d+)\s*(?:D|DAYS?)\s*[\/\-&]?\s*(\d+)\s*(?:N|NIGHTS?)/i);
        if (d_n_match) {
            const days = parseInt(d_n_match[1], 10);
            const nights = parseInt(d_n_match[2], 10);
            if (!durationDaysInput.data('user-manually-edited')) durationDaysInput.val(days).trigger('change');
            if (!durationNightsInput.data('user-manually-edited')) durationNightsInput.val(nights).trigger('change');
            return;
        }
        // Match "1 DAY" or "1-DAY"
        if (/\b1[\s\-]DAY\b/i.test(title)) {
            if (!durationDaysInput.data('user-manually-edited')) durationDaysInput.val(1).trigger('change');
            if (!durationNightsInput.data('user-manually-edited')) durationNightsInput.val(0).trigger('change');
        }
    }

    if (codeInput.length) {
        codeInput.on('input', function () {
            $(this).data('user-manually-edited', true);
        });
    }
    durationNightsInput.on('input', function () {
        $(this).data('user-manually-edited', true);
    });
    durationDaysInput.on('input', function () {
        $(this).data('user-manually-edited', true);
    });

    nameInput.on('input change', function () {
        const title = $(this).val();
        autoDetectDurationFromName(title);
        autoGenSmartPackageCode(title);
    });

    // =========================================================================
    // 17. 1-Click Template Auto-Population
    // =========================================================================
    if (templateSelect.length) {
        templateSelect.on('change', onTemplateChange);
    }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPackageForm);
    } else {
        initPackageForm();
    }
})();




