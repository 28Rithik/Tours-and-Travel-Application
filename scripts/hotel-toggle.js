document.addEventListener("DOMContentLoaded", function () {
  const accommodationSelect = document.getElementById("accommodationSelect");
  const hotelFields = document.querySelectorAll(".hotel-field");

  function toggleHotelFields() {
    if (!accommodationSelect) return;

    if (accommodationSelect.value === "hotel") {
      hotelFields.forEach(field => field.classList.add("show-hotel-field"));
    } else {
      hotelFields.forEach(field => field.classList.remove("show-hotel-field"));
    }
  }

  toggleHotelFields();

  if (accommodationSelect) {
    accommodationSelect.addEventListener("change", toggleHotelFields);
  }
});
