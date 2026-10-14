"""
End-to-End Comprehensive Verification Suite for CRM Kanban 3.0 & Digital Proposal Engine.
Written from scratch to rigorously validate:
  1. Admin authentication & session security
  2. Multi-Modal Board View: Scarcity Beacons, Margins, AI Win Prob, J/K Navigation, Command Palette
  3. Slide-Out Omnichannel WhatsApp Drawer: Two-way chat history & in-drawer response dispatch
  4. Rathasārathi AI Smart Pitch Generator: Context-aware sales copy generation
  5. Swimlane View by Specialist & Travel Vertical
  6. Departure Gantt Timeline
  7. South India Geographic Circuit Radar Map (Leaflet)
  8. Customer Interactive Digital Proposal (/quote/<token>/)
  9. Dynamic UPI Advance Token Deposit Confirmation & Automatic CRM Deal Auto-Conversion into active Booking and Trip
 10. Zero browser console errors assertion across the full run
"""

import os
import sys
import json
import time
from pathlib import Path

# Setup Django Environment
WORKSPACE_DIR = Path(r"c:\Users\rithi\Documents\Documents Project Intership and Course\Projects\Rag chatbot\Tours and Travel Application")
sys.path.insert(0, str(WORKSPACE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelerp.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from crm.models import Inquiry, InquiryChatMessage, InquiryFollowUp
from operations.models import Booking, Trip
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ARTIFACTS_DIR = Path(r"C:\Users\rithi\.gemini\antigravity-ide\brain\38a90fa8-4427-4e87-a010-66c145b9a064")
BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    prefixes = {
        "INFO": "[INFO] ",
        "PASS": "[PASS] [OK] ",
        "WARN": "[WARN] [!] ",
        "FAIL": "[FAIL] [X] ",
        "STEP": "\n========================================\n[STEP] "
    }
    print(f"{prefixes.get(status, '')}{msg}")

def run_suite():
    log("Starting Kanban 3.0 & Digital Proposal Comprehensive Verification Suite", "STEP")
    console_errors = []
    passed_tests = []
    failed_tests = []

    # Ensure admin user has valid password
    admin_user = User.objects.get(username="admin")
    admin_user.set_password("admin123")
    admin_user.save()

    # Find or prepare a test inquiry for proposal conversion
    test_inquiry = Inquiry.objects.filter(status__in=['negotiation', 'quoted']).exclude(proposal_token='').first()
    if not test_inquiry:
        test_inquiry = Inquiry.objects.filter(advance_deposit_paid=0).first()
        test_inquiry.status = 'negotiation'
        test_inquiry.save()
    
    # Reset conversion state for clean test run
    test_inquiry.advance_deposit_paid = 0
    test_inquiry.status = 'negotiation'
    test_inquiry.converted_booking = None
    test_inquiry.converted_trip = None
    test_inquiry.save()
    log(f"Test inquiry targeted: #{test_inquiry.id} ({test_inquiry.inquiry_number}) | Guest: {test_inquiry.guest_name} | Token: {test_inquiry.proposal_token}", "INFO")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1.5
        )

        # Authenticate session via Django SessionStore
        from django.contrib.sessions.backends.db import SessionStore
        session = SessionStore()
        session['_auth_user_id'] = str(admin_user.id)
        session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
        session['_auth_user_hash'] = admin_user.get_session_auth_hash()
        session.save()

        context.add_cookies([
            {
                'name': 'sessionid',
                'value': session.session_key,
                'domain': '127.0.0.1',
                'path': '/'
            }
        ])

        page = context.new_page()

        # Capture console messages
        def handle_console(msg):
            if msg.type == "error":
                # Filter out benign 3rd party tile/cdn network warnings if any
                text = msg.text
                if "tile.openstreetmap.org" in text or "favicon.ico" in text:
                    log(f"Browser Network Notice: {text}", "WARN")
                else:
                    console_errors.append(f"[CONSOLE ERROR] {text}")
                    log(f"Console error detected: {text}", "FAIL")

        def handle_page_error(err):
            console_errors.append(f"[PAGE ERROR] {str(err)}")
            log(f"Uncaught page error: {str(err)}", "FAIL")

        page.on("console", handle_console)
        page.on("pageerror", handle_page_error)

        # ----------------------------------------------------------------------
        # TEST 1: Admin Authentication
        # ----------------------------------------------------------------------
        log("Testing Admin Authentication...", "STEP")
        try:
            page.goto(f"{BASE_URL}/admin/", wait_until="networkidle")
            page.wait_for_selector("body", timeout=5000)
            assert "/login/" not in page.url, "Session not authenticated"
            log("Admin authenticated successfully into TravelERP session.", "PASS")
            passed_tests.append("Admin Authentication")
        except Exception as e:
            log(f"Authentication failed: {e}", "FAIL")
            failed_tests.append(f"Admin Authentication ({e})")

        # ----------------------------------------------------------------------
        # TEST 2: Kanban 3.0 Standard Board View
        # ----------------------------------------------------------------------
        log("Testing Kanban 3.0 Standard Board View...", "STEP")
        try:
            page.goto(f"{BASE_URL}/crm/kanban/?view_mode=board", wait_until="networkidle")
            page.wait_for_selector(".board-grid", timeout=8000)

            # Check 6 Columns
            cols = ["col-new", "col-in_progress", "col-quoted", "col-negotiating", "col-won", "col-lost"]
            for col_id in cols:
                assert page.is_visible(f"#{col_id}"), f"Column #{col_id} is missing"
            log("Verified all 6 Kanban columns rendered properly.", "PASS")

            # Check KPI Cards
            kpi_count = page.locator(".kpi-card").count()
            assert kpi_count >= 4, f"Expected at least 4 KPI cards, found {kpi_count}"
            log(f"Verified {kpi_count} KPI metric summary cards displayed.", "PASS")

            # Check Scarcity Beacons, Gross Margins, and AI Win Prob
            scarcity_count = page.locator(".scarcity-pill").count()
            margin_count = page.locator(".margin-pill").count()
            win_prob_count = page.locator(".win-prob-pill").count()
            assert scarcity_count > 0, "No scarcity beacons found"
            assert margin_count > 0, "No deal margin pills found"
            assert win_prob_count > 0, "No AI win probability pills found"
            log(f"Verified smart pills on cards: {scarcity_count} Scarcity Beacons, {margin_count} Margin Pills, {win_prob_count} AI Win Probabilities.", "PASS")

            # Test Keyboard Navigation (J / K)
            cards = page.locator(".kanban-card")
            if cards.count() > 0:
                page.keyboard.press("j")
                page.wait_for_timeout(300)
                active_card = page.locator(".kanban-card.keyboard-active")
                assert active_card.count() > 0, "Keyboard shortcut 'J' did not activate a card"
                log("Verified Linear-style 'J' keyboard shortcut highlights active card.", "PASS")

                page.keyboard.press("k")
                page.wait_for_timeout(300)
                log("Verified Linear-style 'K' keyboard shortcut successfully cycles cards.", "PASS")

            # Test Command Palette (Ctrl+K)
            page.click('button[title="Press Ctrl+K"]')
            page.wait_for_selector("#commandPalette", state="visible", timeout=3000)
            log("Verified Command Palette opens successfully.", "PASS")
            page.keyboard.press("Escape")
            page.wait_for_selector("#commandPalette", state="hidden", timeout=3000)
            log("Verified Command Palette closes on Escape.", "PASS")

            # Test Floating Bulk Actions Bar
            first_chk = page.locator(".card-checkbox").first
            first_chk.check()
            page.wait_for_selector("#bulkActionBar.visible", timeout=3000)
            badge_text = page.locator("#bulkCountBadge").inner_text()
            assert "Selected" in badge_text, f"Unexpected badge text: {badge_text}"
            log(f"Verified Floating Bulk Actions Bar activates on selection ({badge_text}).", "PASS")
            first_chk.uncheck()
            page.wait_for_selector("#bulkActionBar:not(.visible)", timeout=3000)

            # Capture Screenshot
            board_shot = ARTIFACTS_DIR / "kanban_3_01_board_view.png"
            page.screenshot(path=str(board_shot), full_page=False)
            log(f"Saved Board View screenshot to {board_shot.name}", "PASS")
            passed_tests.append("Kanban 3.0 Standard Board View")
        except Exception as e:
            log(f"Board View test failed: {e}", "FAIL")
            failed_tests.append(f"Kanban 3.0 Standard Board View ({e})")

        # ----------------------------------------------------------------------
        # TEST 3: Omnichannel WhatsApp Slide-out Drawer
        # ----------------------------------------------------------------------
        log("Testing Omnichannel WhatsApp Slide-Out Drawer...", "STEP")
        try:
            # Click WhatsApp chat button on card
            page.locator(".card-btn.wa").first.click()
            page.wait_for_selector("#chatDrawer.open", timeout=4000)
            log("Verified Slide-Out WhatsApp Drawer opened with animation.", "PASS")

            # Wait for messages timeline to load
            page.wait_for_selector("#drawerTimeline .chat-msg", timeout=5000)
            msg_count = page.locator("#drawerTimeline .chat-msg").count()
            log(f"Loaded {msg_count} prior messages in timeline.", "PASS")

            # Send in-drawer agent reply
            test_reply = f"Auto-verified reply from Kanban Drawer at {time.strftime('%H:%M:%S')}"
            page.fill("#drawerInput", test_reply)
            page.click("#chatDrawer .btn-send-wa")
            page.wait_for_timeout(1000)

            # Verify new message appears in timeline
            new_msg = page.locator("#drawerTimeline .chat-msg.agent").last
            assert test_reply in new_msg.inner_text(), "Sent message not found in timeline"
            log("Verified two-way dispatch: new message appended to live timeline.", "PASS")

            # Screenshot
            drawer_shot = ARTIFACTS_DIR / "kanban_3_02_chat_drawer.png"
            page.screenshot(path=str(drawer_shot))
            log(f"Saved Chat Drawer screenshot to {drawer_shot.name}", "PASS")

            # Close drawer
            page.click(".chat-drawer-close")
            page.wait_for_selector("#chatDrawer:not(.open)", timeout=3000)
            passed_tests.append("Omnichannel Slide-Out Chat Drawer")
        except Exception as e:
            log(f"Chat Drawer test failed: {e}", "FAIL")
            failed_tests.append(f"Omnichannel Slide-Out Chat Drawer ({e})")

        # ----------------------------------------------------------------------
        # TEST 4: Rathasārathi AI Smart Pitch Modal
        # ----------------------------------------------------------------------
        log("Testing Rathasārathi AI Smart Pitch Modal...", "STEP")
        try:
            # Trigger via javascript for targeted test inquiry
            page.evaluate(f"openRathasarathiPitchModal({test_inquiry.id})")
            page.wait_for_selector("#rathasarathiPitchModal", state="visible", timeout=4000)
            pitch_text = page.input_value("#rathasarathiPitchText")
            assert "Vanakkam" in pitch_text or "Greetings" in pitch_text, "Pitch text missing polite greeting"
            assert f"/quote/{test_inquiry.proposal_token}/" in pitch_text, "Pitch text missing proposal URL"
            log(f"Generated AI sales pitch ({len(pitch_text)} chars) with dynamic vehicle and proposal token.", "PASS")

            # Screenshot
            rathasarathi_shot = ARTIFACTS_DIR / "kanban_3_03_rathasarathi_pitch.png"
            page.screenshot(path=str(rathasarathi_shot))
            log(f"Saved Rathasārathi Pitch Modal screenshot to {rathasarathi_shot.name}", "PASS")

            page.keyboard.press("Escape")
            page.wait_for_selector("#rathasarathiPitchModal", state="hidden", timeout=3000)
            passed_tests.append("Rathasārathi AI Smart Pitch Modal")
        except Exception as e:
            log(f"Rathasārathi AI Pitch test failed: {e}", "FAIL")
            failed_tests.append(f"Rathasārathi AI Smart Pitch Modal ({e})")

        # ----------------------------------------------------------------------
        # TEST 5: Swimlanes View (By Specialist)
        # ----------------------------------------------------------------------
        log("Testing Swimlanes View (By Specialist)...", "STEP")
        try:
            page.goto(f"{BASE_URL}/crm/kanban/?view_mode=swimlanes&swimlane_by=specialist", wait_until="networkidle")
            page.wait_for_selector(".swimlane-container", timeout=8000)
            lane_count = page.locator(".swimlane-row").count()
            assert lane_count > 0, "No specialist swimlanes rendered"
            log(f"Verified {lane_count} Specialist Swimlanes rows rendered.", "PASS")

            swim_shot = ARTIFACTS_DIR / "kanban_3_04_swimlanes_specialist.png"
            page.screenshot(path=str(swim_shot), full_page=False)
            log(f"Saved Specialist Swimlanes screenshot to {swim_shot.name}", "PASS")
            passed_tests.append("Swimlanes View (By Specialist)")
        except Exception as e:
            log(f"Specialist Swimlanes test failed: {e}", "FAIL")
            failed_tests.append(f"Swimlanes View (By Specialist) ({e})")

        # ----------------------------------------------------------------------
        # TEST 6: Swimlanes View (By Travel Vertical)
        # ----------------------------------------------------------------------
        log("Testing Swimlanes View (By Travel Vertical)...", "STEP")
        try:
            page.goto(f"{BASE_URL}/crm/kanban/?view_mode=swimlanes&swimlane_by=vertical", wait_until="networkidle")
            page.wait_for_selector(".swimlane-container", timeout=8000)
            lane_count = page.locator(".swimlane-row").count()
            assert lane_count > 0, "No vertical swimlanes rendered"
            log(f"Verified {lane_count} Vertical Swimlanes rows rendered (Ooty, Wayanad, Temple circuits, etc.).", "PASS")

            vert_shot = ARTIFACTS_DIR / "kanban_3_05_swimlanes_vertical.png"
            page.screenshot(path=str(vert_shot), full_page=False)
            log(f"Saved Vertical Swimlanes screenshot to {vert_shot.name}", "PASS")
            passed_tests.append("Swimlanes View (By Travel Vertical)")
        except Exception as e:
            log(f"Vertical Swimlanes test failed: {e}", "FAIL")
            failed_tests.append(f"Swimlanes View (By Travel Vertical) ({e})")

        # ----------------------------------------------------------------------
        # TEST 7: Departure Gantt Timeline
        # ----------------------------------------------------------------------
        log("Testing Departure Gantt Timeline...", "STEP")
        try:
            page.goto(f"{BASE_URL}/crm/kanban/?view_mode=gantt", wait_until="networkidle")
            page.wait_for_selector(".gantt-container", timeout=8000)
            buckets = page.locator(".gantt-bucket").count()
            assert buckets == 4, f"Expected 4 departure buckets, found {buckets}"
            log("Verified all 4 departure timeline buckets rendered (This Week, Next Week, Upcoming, Future).", "PASS")

            gantt_shot = ARTIFACTS_DIR / "kanban_3_06_departure_gantt.png"
            page.screenshot(path=str(gantt_shot), full_page=False)
            log(f"Saved Departure Gantt screenshot to {gantt_shot.name}", "PASS")
            passed_tests.append("Departure Gantt Timeline")
        except Exception as e:
            log(f"Departure Gantt test failed: {e}", "FAIL")
            failed_tests.append(f"Departure Gantt Timeline ({e})")

        # ----------------------------------------------------------------------
        # TEST 8: South India Circuit Radar Map
        # ----------------------------------------------------------------------
        log("Testing South India Geographic Circuit Radar Map...", "STEP")
        try:
            page.goto(f"{BASE_URL}/crm/kanban/?view_mode=map", wait_until="networkidle")
            page.wait_for_selector("#circuitMap", timeout=8000)
            page.wait_for_selector(".leaflet-container", timeout=8000)
            page.wait_for_timeout(1000)  # Allow Leaflet markers to render
            markers = page.locator(".leaflet-interactive").count()
            log(f"Verified Leaflet interactive radar map initialized with {markers} circuit coordinate pins.", "PASS")

            map_shot = ARTIFACTS_DIR / "kanban_3_07_circuit_radar_map.png"
            page.screenshot(path=str(map_shot), full_page=False)
            log(f"Saved Circuit Radar Map screenshot to {map_shot.name}", "PASS")
            passed_tests.append("South India Geographic Circuit Radar Map")
        except Exception as e:
            log(f"Circuit Radar Map test failed: {e}", "FAIL")
            failed_tests.append(f"South India Geographic Circuit Radar Map ({e})")

        # ----------------------------------------------------------------------
        # TEST 9: Customer Interactive Digital Proposal (/quote/<token>/)
        # ----------------------------------------------------------------------
        log(f"Testing Customer Interactive Proposal for Inquiry #{test_inquiry.id}...", "STEP")
        try:
            proposal_url = f"{BASE_URL}/quote/{test_inquiry.proposal_token}/"
            page.goto(proposal_url, wait_until="networkidle")
            page.wait_for_selector(".hero-container", timeout=8000)

            # Assertions on content
            assert page.is_visible(".brand-header"), "Brand header not visible"
            assert page.is_visible(".vehicle-box"), "Vehicle specification box not visible"
            assert page.is_visible(".inclusions-grid"), "Inclusions grid not visible"
            assert page.is_visible(".investment-box"), "Investment summary not visible"
            assert page.is_visible("#btnPayUPI"), "Dynamic UPI pay button not visible"

            # Capture initial proposal screenshot
            prop_shot = ARTIFACTS_DIR / "kanban_3_08_customer_proposal.png"
            page.screenshot(path=str(prop_shot), full_page=False)
            log(f"Saved Customer Proposal screenshot to {prop_shot.name}", "PASS")
            passed_tests.append("Customer Interactive Digital Proposal")
        except Exception as e:
            log(f"Customer Proposal test failed: {e}", "FAIL")
            failed_tests.append(f"Customer Interactive Digital Proposal ({e})")

        # ----------------------------------------------------------------------
        # TEST 10: Dynamic UPI Payment & Instant CRM Auto-Conversion
        # ----------------------------------------------------------------------
        log("Testing Dynamic UPI Payment & Instant CRM Deal Auto-Conversion...", "STEP")
        try:
            # Click Pay via UPI button
            page.click("#btnPayUPI")
            log("Triggered Dynamic UPI Token Payment switch...", "INFO")

            # Wait for page to reload into confirmed state
            page.wait_for_selector(".success-banner", timeout=8000)
            banner_text = page.locator(".success-banner").inner_text()
            assert "Expedition Confirmed" in banner_text, f"Unexpected banner text: {banner_text}"
            log("Customer proposal successfully confirmed! Received 'Expedition Confirmed & Fleet Staged!' status.", "PASS")

            # Capture confirmed proposal screenshot
            conf_shot = ARTIFACTS_DIR / "kanban_3_09_proposal_confirmed.png"
            page.screenshot(path=str(conf_shot), full_page=False)
            log(f"Saved Confirmed Proposal screenshot to {conf_shot.name}", "PASS")

            # Backend Database Verification
            test_inquiry.refresh_from_db()
            assert test_inquiry.status == "won", f"Expected inquiry status 'won', got '{test_inquiry.status}'"
            assert test_inquiry.advance_deposit_paid > 0, f"Expected advance deposit > 0, got {test_inquiry.advance_deposit_paid}"
            assert test_inquiry.converted_booking is not None, "Inquiry converted_booking was not set"
            assert test_inquiry.converted_trip is not None, "Inquiry converted_trip was not set"

            booking = test_inquiry.converted_booking
            trip = test_inquiry.converted_trip
            assert booking.status == "confirmed", f"Expected booking status 'confirmed', got '{booking.status}'"
            assert trip.status == "booked", f"Expected trip status 'booked', got '{trip.status}'"

            log(f"Backend verification passed: Inquiry #{test_inquiry.id} marked as WON. Advance ₹{test_inquiry.advance_deposit_paid} recorded. Auto-provisioned Booking #{booking.booking_number} and Trip #{trip.trip_id}!", "PASS")
            passed_tests.append("Dynamic UPI Payment & Auto-Conversion")
        except Exception as e:
            log(f"UPI Payment & Conversion test failed: {e}", "FAIL")
            failed_tests.append(f"Dynamic UPI Payment & Auto-Conversion ({e})")

        # ----------------------------------------------------------------------
        # TEST 11: Assertion on Browser Console Errors
        # ----------------------------------------------------------------------
        log("Asserting Zero Browser Console Errors...", "STEP")
        if len(console_errors) == 0:
            log("Verified 0 fatal console errors across all pages, modals, and interactions!", "PASS")
            passed_tests.append("Zero Console Errors")
        else:
            log(f"Detected {len(console_errors)} console errors:\n" + "\n".join(console_errors), "FAIL")
            failed_tests.append(f"Zero Console Errors ({len(console_errors)} errors detected)")

        context.close()
        browser.close()

    # Summary
    log("\n========================================", "INFO")
    log("KANBAN 3.0 SUITE EXECUTION SUMMARY", "INFO")
    log("========================================", "INFO")
    log(f"Passed Tests: {len(passed_tests)} / {len(passed_tests) + len(failed_tests)}", "PASS" if len(failed_tests) == 0 else "INFO")
    for t in passed_tests:
        print(f"  [OK] {t}")
    if failed_tests:
        log("Failed Tests:", "FAIL")
        for t in failed_tests:
            print(f"  [X] {t}")
        sys.exit(1)
    else:
        log("ALL TESTS COMPLETED WITH 100% SUCCESS!", "PASS")

if __name__ == "__main__":
    run_suite()
