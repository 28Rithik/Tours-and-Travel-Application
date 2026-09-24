document.addEventListener("DOMContentLoaded", function () {
  const WHATSAPP_NUMBER = "919629808833";
  const SUPPORT_PHONE = "9629808833";
  const SUPPORT_EMAIL = "bharathiyartravels.cbe@gmail.com";

  const APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzlpmPSfv6bjWTRwYpEc8ICw6azs7pM6auSrm2phKCMmpZzLe4u7tagoJtj5USF6WfE/exec";

  const hourlyData = {
    "5H": {
      title: "5 Hours / 50 km Limit",
      slug: "5 Hours",
      kmLimit: 50,
      extraHour: {
        sedan: 250,
        ertiga: 300,
        innova: 400,
        crysta: 450
      },
      extraKm: {
        sedan: 12,
        ertiga: 15,
        innova: 17,
        crysta: 20
      },
      vehicles: [
        { key: "sedan", name: "SEDAN", type: "Etios, Dzire, Xcent", tariff: 1500 },
        { key: "ertiga", name: "ERTIGA", type: "6 - 7 Seater", tariff: 2000 },
        { key: "innova", name: "INNOVA", type: "7 Seater", tariff: 2500 },
        { key: "crysta", name: "CRYSTA", type: "Innova Crysta", tariff: 3000 }
      ]
    },

    "8H": {
      title: "8 Hours / 80 km Limit",
      slug: "8 Hours",
      kmLimit: 80,
      extraHour: {
        sedan: 250,
        ertiga: 300,
        innova: 400,
        crysta: 450
      },
      extraKm: {
        sedan: 12,
        ertiga: 15,
        innova: 17,
        crysta: 20
      },
      vehicles: [
        { key: "sedan", name: "SEDAN", type: "Etios, Dzire, Xcent", tariff: 2500 },
        { key: "ertiga", name: "ERTIGA", type: "6 - 7 Seater", tariff: 3350 },
        { key: "innova", name: "INNOVA", type: "7 Seater", tariff: 3500 },
        { key: "crysta", name: "CRYSTA", type: "Innova Crysta", tariff: 4300 }
      ]
    },

    "10H": {
      title: "10 Hours / 100 km Limit",
      slug: "10 Hours",
      kmLimit: 100,
      extraHour: {
        sedan: 250,
        ertiga: 300,
        innova: 400,
        crysta: 450
      },
      extraKm: {
        sedan: 12,
        ertiga: 15,
        innova: 17,
        crysta: 20
      },
      vehicles: [
        { key: "sedan", name: "SEDAN", type: "Etios, Dzire, Xcent", tariff: 3000 },
        { key: "ertiga", name: "ERTIGA", type: "6 - 7 Seater", tariff: 3800 },
        { key: "innova", name: "INNOVA", type: "7 Seater", tariff: 4000 },
        { key: "crysta", name: "CRYSTA", type: "Innova Crysta", tariff: 4700 }
      ]
    },

    "12H": {
      title: "12 Hours / 120 km Limit",
      slug: "12 Hours",
      kmLimit: 120,
      extraHour: {
        sedan: 250,
        ertiga: 300,
        innova: 400,
        crysta: 450
      },
      extraKm: {
        sedan: 12,
        ertiga: 15,
        innova: 17,
        crysta: 20
      },
      vehicles: [
        { key: "sedan", name: "SEDAN", type: "Etios, Dzire, Xcent", tariff: 3500 },
        { key: "ertiga", name: "ERTIGA", type: "6 - 7 Seater", tariff: 4300 },
        { key: "innova", name: "INNOVA", type: "7 Seater", tariff: 4500 },
        { key: "crysta", name: "CRYSTA", type: "Innova Crysta", tariff: 5300 }
      ]
    }
  };

  const packageSidebar = document.getElementById("packageSidebar");
  const tariffTableBody = document.getElementById("tariffTableBody");
  const packageHeading = document.getElementById("packageHeading");
  const packageSubheading = document.getElementById("packageSubheading");
  const routeLine = document.getElementById("routeLine");
  const extraChargesNote = document.getElementById("extraChargesNote");
  const tariffSection = document.getElementById("tariffSection");

  const bookingSummary = document.getElementById("bookingSummary");
  const bookingPopupForm = document.getElementById("bookingPopupForm");
  const bookingModalEl = document.getElementById("bookingModal");
  const bookingModal = bookingModalEl ? new bootstrap.Modal(bookingModalEl) : null;

  const paymentModalEl = document.getElementById("paymentModal");
  const paymentModal = paymentModalEl ? new bootstrap.Modal(paymentModalEl) : null;
  const paymentSummaryBox = document.getElementById("paymentSummaryBox");
  const paymentOptionNote = document.getElementById("paymentOptionNote");

  const enquireWhatsappBtn = document.getElementById("enquireWhatsappBtn");
  const bookNowZeroBtn = document.getElementById("bookNowZeroBtn");
  const payOnlineBtn = document.getElementById("payOnlineBtn");
  const advancePaymentBtn = document.getElementById("advancePaymentBtn");
  const fullPaymentBtn = document.getElementById("fullPaymentBtn");
  const backToBookingBtn = document.getElementById("backToBookingBtn");
  const floatingBtns = document.getElementById("floatingBtns");

  let activePackage = "5H";
  let selectedBooking = null;
  let customerFormData = null;
  let savedBookingId = "";

  function formatCurrency(value) {
    if (value === null || value === undefined || value === "") return "On Request";
    return "₹ " + Number(value).toLocaleString("en-IN");
  }

  function sanitizeText(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function setMinDateTime() {
    const dateInput = document.getElementById("customerDateTime");
    if (!dateInput) return;

    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    dateInput.min = now.toISOString().slice(0, 16);
  }

  function formatDateTimeAMPM(inputValue) {
    const d = new Date(inputValue);
    if (isNaN(d)) return inputValue;

    const day = String(d.getDate()).padStart(2, "0");
    const month = d.toLocaleString("en-GB", { month: "short" });
    const year = d.getFullYear();

    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;

    return `${day} ${month} ${year}, ${hours}:${minutes} ${ampm}`;
  }

  function getCurrentPackage() {
    return hourlyData[activePackage] || null;
  }

  function populatePackages(preferredPackage = "") {
    const keys = Object.keys(hourlyData);
    if (!keys.length) return;

    if (preferredPackage && hourlyData[preferredPackage]) {
      activePackage = preferredPackage;
    } else if (!hourlyData[activePackage]) {
      activePackage = keys[0];
    }

    packageSidebar.innerHTML = keys.map(key => {
      const pkg = hourlyData[key];
      const activeClass = key === activePackage ? "active" : "";
      return `
      <button type="button" class="tour-destination-btn hourly-package-btn ${activeClass}" data-package="${key}">
        ${sanitizeText(pkg.title)}
      </button>
    `;
    }).join("");

    packageSidebar.querySelectorAll(".tour-destination-btn").forEach(btn => {
      btn.addEventListener("click", function () {
        activePackage = this.dataset.package;
        populatePackages(activePackage);
        renderTariffTable();
        updatePageHeading();

        setTimeout(() => {
          if (tariffSection) {
            const y = tariffSection.getBoundingClientRect().top + window.scrollY - 90;
            window.scrollTo({ top: y, behavior: "smooth" });
          }
        }, 50);
      });
    });

    updatePageHeading();
  }

  function updatePageHeading() {
    const pkg = getCurrentPackage();
    if (!pkg) return;

    if (packageHeading) packageHeading.textContent = "Local Hourly Packages";
    if (packageSubheading) packageSubheading.textContent = "Select your package slab";
    if (routeLine) routeLine.textContent = pkg.title;

    if (extraChargesNote) {
      extraChargesNote.innerHTML = `
        <strong>Notes:</strong><br>
        Toll, parking and permit charges are extra.
      `;
    }
  }

  function renderTariffTable() {
    const pkg = getCurrentPackage();
    if (!pkg || !tariffTableBody) {
      tariffTableBody.innerHTML = `<tr><td colspan="3" class="text-center py-4">No tariffs available.</td></tr>`;
      return;
    }

    tariffTableBody.innerHTML = pkg.vehicles.map(vehicle => {
      const bookingData = {
        serviceType: "Local Hourly Package",
        packageTitle: "Local Hourly Packages",
        packageLabel: pkg.title,
        packageCode: activePackage,
        kmLimit: pkg.kmLimit,
        vehicleKey: vehicle.key,
        vehicle: vehicle.name,
        vehicleType: vehicle.type,
        tariff: vehicle.tariff,
        extraHour: pkg.extraHour[vehicle.key] || 0,
        extraKm: pkg.extraKm[vehicle.key] || 0
      };

      const encodedPayload = encodeURIComponent(JSON.stringify(bookingData));

      return `
        <tr>
          <td>
            <div class="vehicle-name">${sanitizeText(vehicle.name)}</div>
            <div class="vehicle-type">${sanitizeText(vehicle.type)}</div>
          </td>
          <td>
            <div class="dynamic-tariff base-rate">${formatCurrency(vehicle.tariff)}</div>
          </td>
          <td>
            <button type="button" class="btn-book-table" data-booking="${encodedPayload}">
              BOOK NOW
            </button>
          </td>
        </tr>
      `;
    }).join("");

    tariffTableBody.querySelectorAll(".btn-book-table").forEach(btn => {
      btn.addEventListener("click", function () {
        try {
          const payload = JSON.parse(decodeURIComponent(this.dataset.booking || ""));
          openBookingModal(payload);
        } catch {
          alert("Unable to open booking modal.");
        }
      });
    });
  }

  function openBookingModal(bookingData) {
    selectedBooking = bookingData;
    customerFormData = null;
    savedBookingId = "";

    if (!bookingSummary) return;

    bookingSummary.innerHTML = `
      <div><span>Service</span><span>${sanitizeText(selectedBooking.serviceType)}</span></div>
      <div><span>Package</span><span>${sanitizeText(selectedBooking.packageLabel)}</span></div>
      <div><span>Vehicle</span><span>${sanitizeText(selectedBooking.vehicle)}</span></div>
      <div><span>Type</span><span>${sanitizeText(selectedBooking.vehicleType)}</span></div>
      <div><span>Tariff</span><span>${formatCurrency(selectedBooking.tariff)}</span></div>
      <div><span>Extra Hour</span><span>${formatCurrency(selectedBooking.extraHour)}</span></div>
      <div><span>Extra KM</span><span>${formatCurrency(selectedBooking.extraKm)}</span></div>
    `;

    if (bookingPopupForm) bookingPopupForm.reset();
    setMinDateTime();

    if (bookingModal) bookingModal.show();
  }

  function validateCustomerForm() {
    const name = document.getElementById("customerName")?.value.trim();
    const phone = document.getElementById("customerPhone")?.value.trim();
    const dateTime = document.getElementById("customerDateTime")?.value;
    const pickup = document.getElementById("customerPickup")?.value.trim();
    const drop = document.getElementById("customerDrop")?.value.trim();

    if (!selectedBooking) {
      alert("Please select a booking first.");
      return null;
    }

    if (!name || !phone || !dateTime || !pickup || !drop) {
      alert("Please fill all required fields.");
      return null;
    }

    if (!/^[0-9]{10}$/.test(phone)) {
      alert("Please enter a valid 10-digit phone number.");
      return null;
    }

    const selectedDate = new Date(dateTime);
    if (selectedDate < new Date()) {
      alert("Old date and time cannot be selected.");
      return null;
    }

    return { name, phone, dateTime, pickup, drop };
  }

  async function postToAppsScript(action, payload) {
    const response = await fetch(APPS_SCRIPT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "text/plain;charset=utf-8"
      },
      body: JSON.stringify({ action, payload })
    });

    const text = await response.text();
    let data = {};

    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("Invalid server response");
    }

    if (data.status !== "success") {
      throw new Error(data.message || "Request failed");
    }

    return data;
  }

  async function saveBookingToSheet(paymentTypeValue = "") {
    if (!selectedBooking || !customerFormData) {
      throw new Error("Booking data missing");
    }

    const payload = {
      packageTitle: "Local Hourly Packages",
      packageLabel: selectedBooking.packageLabel,
      packageCode: selectedBooking.packageCode,
      vehicle: `${selectedBooking.vehicle} - ${selectedBooking.vehicleType}`,
      vehicleType: selectedBooking.vehicleType,
      tariff: selectedBooking.tariff,
      kmLimit: selectedBooking.kmLimit,
      extraHour: selectedBooking.extraHour,
      extraKm: selectedBooking.extraKm,
      customerName: customerFormData.name,
      customerPhone: customerFormData.phone,
      travelDate: formatDateTimeAMPM(customerFormData.dateTime),
      pickupLocation: customerFormData.pickup,
      dropLocation: customerFormData.drop,
      paymentType: paymentTypeValue,
      sourcePage: window.location.href
    };

    const result = await postToAppsScript("saveBooking", payload);
    savedBookingId = result.bookingId || "";
    return result;
  }

  function getAdvanceConfig() {
    return {
      type: "ADVANCE_10",
      label: "Pay Advance 10%",
      amount: Math.round(Number(selectedBooking?.tariff || 0) * 0.10)
    };
  }

  function fillPaymentSummary() {
    if (!paymentSummaryBox || !selectedBooking) return;

    const advance = getAdvanceConfig();
    const total = Number(selectedBooking.tariff || 0);

    paymentSummaryBox.innerHTML = `
      <div><span>Booking ID</span><span>${sanitizeText(savedBookingId || "-")}</span></div>
      <div><span>Service</span><span>Local Hourly Package</span></div>
      <div><span>Package</span><span>${sanitizeText(selectedBooking.packageLabel)}</span></div>
      <div><span>Vehicle</span><span>${sanitizeText(selectedBooking.vehicle)}</span></div>
      <div><span>Tariff</span><span>${formatCurrency(total)}</span></div>
      <div><span>Extra Hour</span><span>${formatCurrency(selectedBooking.extraHour)}</span></div>
      <div><span>Extra KM</span><span>${formatCurrency(selectedBooking.extraKm)}</span></div>
    `;

    if (paymentOptionNote) {
      paymentOptionNote.innerHTML = `
        <div><span>Advance</span><span>${formatCurrency(advance.amount)}</span></div>
        <div><span>Full Payment</span><span>${formatCurrency(total)}</span></div>
      `;
      paymentOptionNote.style.display = "block";
    }

    if (advancePaymentBtn) {
      advancePaymentBtn.textContent = `${advance.label} - ${formatCurrency(advance.amount)}`;
    }

    if (fullPaymentBtn) {
      fullPaymentBtn.textContent = `Pay Full - ${formatCurrency(total)}`;
    }
  }

  function buildWhatsAppBookingMessage(data) {
    const url = window.location.href;

    return `✨ *BHARATHIYAR TOURS & TRAVELS*
  ━━━━━━━━━━━━━━━━━
  🕒 *LOCAL HOURLY PACKAGE*

  📦 ${selectedBooking?.packageLabel || ""}
  🚘 ${selectedBooking?.vehicle || ""} (${selectedBooking?.vehicleType || ""})
  💰 ${formatCurrency(selectedBooking?.tariff || 0)}

  ➕ Extra: ${formatCurrency(selectedBooking?.extraHour || 0)}/hr | ${formatCurrency(selectedBooking?.extraKm || 0)}/km
  ⚠️ Toll, parking & permit extra

  ━━━━━━━━━━━━━━━━━
  👤 *CUSTOMER*
  🧑 ${data?.name || ""} | 📞 ${data?.phone || ""}
  🗓️ ${data?.dateTime ? formatDateTimeAMPM(data.dateTime) : ""}
  📍 Pickup: ${data?.pickup || ""}
  📌 Plan: ${data?.drop || ""}

  ━━━━━━━━━━━━━━━━━
  🙏 Kindly confirm availability.`;
  }

  function buildReceiptPayload(paymentInfo) {
    const total = Number(selectedBooking?.tariff || 0);
    const paid = Number(paymentInfo?.paidAmount || 0);

    return {
      receiptTitle: paymentInfo.paymentType === "FULL" ? "FULL PAYMENT RECEIPT" : "ADVANCE PAYMENT RECEIPT",
      paymentStatus: paymentInfo.paymentType === "FULL" ? "FULL PAYMENT RECEIVED" : "ADVANCE RECEIVED",
      quoteNo: savedBookingId,
      date: new Date().toLocaleDateString("en-GB"),
      customerName: customerFormData?.name,
      customerPhone: customerFormData?.phone,
      pickup: customerFormData?.pickup,
      drop: customerFormData?.drop,
      vehicle: `${selectedBooking?.vehicle} - ${selectedBooking?.vehicleType}`,
      packageTitle: "Local Hourly Packages",
      packageCode: selectedBooking?.packageCode,
      kmLimit: `${selectedBooking?.kmLimit || ""} km`,
      travelDate: formatDateTimeAMPM(customerFormData?.dateTime),
      totalTariff: total,
      paidAmount: paid,
      pendingAmount: total - paid,
      paymentId: paymentInfo.paymentId,
      paymentType: paymentInfo.paymentType,
      supportPhone: SUPPORT_PHONE,
      supportEmail: SUPPORT_EMAIL,
      terms: [
        `Package selected: ${selectedBooking?.packageLabel || ""}`,
        `Extra hour charge: ${formatCurrency(selectedBooking?.extraHour || 0)}`,
        `Extra km charge: ${formatCurrency(selectedBooking?.extraKm || 0)}`,
        "Toll, parking and permit charges are extra.",
        "Driver details will be assigned before journey."
      ]
    };
  }

  function goToReceiptPage(paymentInfo) {
    const data = buildReceiptPayload(paymentInfo);
    sessionStorage.setItem("btt_receipt_data", JSON.stringify(data));
    window.location.href = "receipt-success.html";
  }

  async function startPayment(paymentType) {
    if (!selectedBooking || !customerFormData || !savedBookingId) {
      throw new Error("Booking is incomplete");
    }

    const createOrderResult = await postToAppsScript("createOrder", {
      bookingId: savedBookingId,
      tariff: Number(selectedBooking.tariff || 0),
      withHotel: false,
      paymentType: paymentType
    });

    if (!createOrderResult.orderId) {
      throw new Error("Failed to create order");
    }

    const options = {
      key: createOrderResult.key,
      amount: Number(createOrderResult.amount || 0) * 100,
      currency: createOrderResult.currency || "INR",
      name: "BHARATHIYAR TOURS AND TRAVELS",
      description: `Local Hourly Package - ${selectedBooking.packageLabel}`,
      order_id: createOrderResult.orderId,
      handler: async function (response) {
        try {
          await postToAppsScript("verifyPayment", {
            bookingId: savedBookingId,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
            paymentType: paymentType,
            amount: Number(createOrderResult.amount || 0)
          });

          if (paymentModal) paymentModal.hide();
          if (bookingModal) bookingModal.hide();

          goToReceiptPage({
            paymentType: paymentType,
            paymentId: response.razorpay_payment_id,
            paidAmount: Number(createOrderResult.amount || 0)
          });

          resetPaymentButtons();
        } catch (err) {
          resetPaymentButtons();
          alert(err.message || "Payment verified, but redirect failed.");
        }
      },
      modal: {
        ondismiss: function () {
          resetPaymentButtons();
        }
      },
      prefill: {
        name: customerFormData?.name || "",
        contact: customerFormData?.phone || ""
      },
      theme: {
        color: "#111111"
      }
    };

    const rzp = new Razorpay(options);
    rzp.on("payment.failed", function (resp) {
      resetPaymentButtons();
      alert(resp?.error?.description || "Payment failed");
    });
    rzp.open();
  }

  function resetMainButtons() {
    if (enquireWhatsappBtn) {
      enquireWhatsappBtn.disabled = false;
      enquireWhatsappBtn.innerHTML = `<i class="bi bi-whatsapp me-2"></i>Enquire on WhatsApp`;
    }

    if (bookNowZeroBtn) {
      bookNowZeroBtn.disabled = false;
      bookNowZeroBtn.textContent = "Book Now @ ₹0";
    }

    if (payOnlineBtn) {
      payOnlineBtn.disabled = false;
      payOnlineBtn.innerHTML = `<i class="bi bi-credit-card me-2"></i>Pay Online`;
    }
  }

  function resetPaymentButtons() {
    if (!advancePaymentBtn || !fullPaymentBtn) return;

    advancePaymentBtn.disabled = false;
    fullPaymentBtn.disabled = false;

    const advance = getAdvanceConfig();
    const total = Number(selectedBooking?.tariff || 0);

    advancePaymentBtn.textContent = `${advance.label} - ${formatCurrency(advance.amount)}`;
    fullPaymentBtn.textContent = `Pay Full - ${formatCurrency(total)}`;
  }

  if (bookingPopupForm) {
    bookingPopupForm.addEventListener("submit", function (e) {
      e.preventDefault();
    });
  }

  if (enquireWhatsappBtn) {
    enquireWhatsappBtn.addEventListener("click", async function () {
      try {
        customerFormData = validateCustomerForm();
        if (!customerFormData) return;

        enquireWhatsappBtn.disabled = true;
        enquireWhatsappBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Please wait...`;

        const message = buildWhatsAppBookingMessage(customerFormData);
        const whatsappUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;

        window.open(whatsappUrl, "_blank");
        alert("Thanks for contacting Bharathiyar Tours and Travels. Our concern team will contact you.");
      } catch (err) {
        alert(err.message || "Failed to continue to WhatsApp");
      } finally {
        resetMainButtons();
      }
    });
  }

  if (bookNowZeroBtn) {
    bookNowZeroBtn.addEventListener("click", async function () {
      try {
        customerFormData = validateCustomerForm();
        if (!customerFormData) return;

        bookNowZeroBtn.disabled = true;
        bookNowZeroBtn.textContent = "Please wait...";

        await saveBookingToSheet("BOOK_NOW_ZERO");
        alert("Thanks for contacting Bharathiyar Tours and Travels. Our concern team will contact you.");

        if (bookingModal) bookingModal.hide();
        if (bookingPopupForm) bookingPopupForm.reset();
      } catch (err) {
        alert(err.message || "Failed to save booking");
      } finally {
        resetMainButtons();
      }
    });
  }

  if (payOnlineBtn) {
    payOnlineBtn.addEventListener("click", async function () {
      try {
        customerFormData = validateCustomerForm();
        if (!customerFormData) return;

        payOnlineBtn.disabled = true;
        payOnlineBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Please wait...`;

        await saveBookingToSheet("PAY_ONLINE");
        fillPaymentSummary();

        if (bookingModal) bookingModal.hide();
        if (paymentModal) paymentModal.show();
      } catch (err) {
        alert(err.message || "Failed to continue to payment");
      } finally {
        resetMainButtons();
      }
    });
  }

  if (backToBookingBtn) {
    backToBookingBtn.addEventListener("click", function () {
      if (paymentModal) paymentModal.hide();
      if (bookingModal) bookingModal.show();
    });
  }

  if (advancePaymentBtn) {
    advancePaymentBtn.addEventListener("click", async function () {
      try {
        advancePaymentBtn.disabled = true;
        fullPaymentBtn.disabled = true;
        advancePaymentBtn.textContent = "Please wait...";
        await startPayment(getAdvanceConfig().type);
      } catch (err) {
        alert(err.message || "Unable to start payment");
        resetPaymentButtons();
      }
    });
  }

  if (fullPaymentBtn) {
    fullPaymentBtn.addEventListener("click", async function () {
      try {
        advancePaymentBtn.disabled = true;
        fullPaymentBtn.disabled = true;
        fullPaymentBtn.textContent = "Please wait...";
        await startPayment("FULL");
      } catch (err) {
        alert(err.message || "Unable to start payment");
        resetPaymentButtons();
      }
    });
  }

  const phoneInput = document.getElementById("customerPhone");
  if (phoneInput) {
    phoneInput.addEventListener("input", function () {
      this.value = this.value.replace(/\D/g, "").slice(0, 10);
    });
  }

  function syncFloatingButtons(show) {
    if (!floatingBtns) return;
    floatingBtns.style.display = show ? "flex" : "none";
  }

  if (bookingModalEl) {
    bookingModalEl.addEventListener("shown.bs.modal", function () {
      document.body.classList.add("modal-open-custom");
      syncFloatingButtons(false);
    });

    bookingModalEl.addEventListener("hidden.bs.modal", function () {
      document.body.classList.remove("modal-open-custom");
      if (!paymentModalEl || !paymentModalEl.classList.contains("show")) {
        syncFloatingButtons(true);
      }
    });
  }

  if (paymentModalEl) {
    paymentModalEl.addEventListener("shown.bs.modal", function () {
      syncFloatingButtons(false);
    });

    paymentModalEl.addEventListener("hidden.bs.modal", function () {
      if (!bookingModalEl || !bookingModalEl.classList.contains("show")) {
        syncFloatingButtons(true);
      }
    });
  }

  setMinDateTime();
  populatePackages();
  renderTariffTable();
  updatePageHeading();
  syncFloatingButtons(true);
});
