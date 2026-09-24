function formatRouteName(destinationName) {
  if (!destinationName) return "Coimbatore - Destination - Coimbatore";

  const cleanDestination = String(destinationName)
    .replace(/>/g, " - ")   // only convert > to -
    .trim();

  return `Route: Coimbatore - ${cleanDestination} - Coimbatore`;
}

function updateDynamicTitles() {
  const destinationName = document.getElementById("destinationSelect")?.value || "";
  const routeTitle = formatRouteName(destinationName);

  const subheading = document.getElementById("packageSubheading");
  const itineraryTitle = document.getElementById("itineraryTitle");

  if (subheading) subheading.textContent = routeTitle;
  if (itineraryTitle) itineraryTitle.textContent = `Route: ${routeTitle}`;
}
