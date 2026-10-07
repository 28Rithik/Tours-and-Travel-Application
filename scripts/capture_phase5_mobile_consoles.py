import os
import sys
import asyncio

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import django
from playwright.async_api import async_playwright

def setup_trip():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
    django.setup()
    from operations.models import Trip, Booking
    from core.models import Vehicle, Driver
    
    trip = Trip.objects.first()
    if trip:
        if not trip.vehicle:
            trip.vehicle = Vehicle.objects.first()
        if not trip.driver:
            trip.driver = Driver.objects.first()
        trip.driver_handover_status = 'pending'
        trip.current_milestone = 'driver_reached'
        trip.pickup_pin = '4821'
        trip.save()
        return trip.pk
    return 1

async def main(trip_pk):
    artifact_dir = r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d"
    os.makedirs(artifact_dir, exist_ok=True)
    handover_img = os.path.join(artifact_dir, "driver_handover_portal.png")
    lifecycle_img = os.path.join(artifact_dir, "tour_lifecycle_portal.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        
        # 1. Capture Mobile Handover Portal (Mobile Viewport)
        context_mobile = await browser.new_context(
            viewport={'width': 440, 'height': 950},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page_handover = await context_mobile.new_page()
        await page_handover.goto(f"http://127.0.0.1:8000/trip/{trip_pk}/handover/")
        await page_handover.wait_for_timeout(1500)
        await page_handover.screenshot(path=handover_img, full_page=True)
        print(f"Handover screenshot saved: {handover_img}")
        await context_mobile.close()

        # 2. Capture 7-Milestone Tour Lifecycle Cockpit (Desktop/Tablet Viewport)
        context_lifecycle = await browser.new_context(viewport={'width': 800, 'height': 1100})
        page_lifecycle = await context_lifecycle.new_page()
        await page_lifecycle.goto(f"http://127.0.0.1:8000/trip/{trip_pk}/lifecycle/")
        await page_lifecycle.wait_for_timeout(1500)
        await page_lifecycle.screenshot(path=lifecycle_img, full_page=True)
        print(f"Lifecycle screenshot saved: {lifecycle_img}")
        await context_lifecycle.close()

        await browser.close()

if __name__ == "__main__":
    trip_id = setup_trip()
    asyncio.run(main(trip_id))
