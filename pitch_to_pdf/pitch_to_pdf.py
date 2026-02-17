#!/usr/bin/env python3
"""Scrape a pitch.com presentation and export it as a PDF."""

import argparse
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export a pitch.com slide deck to PDF."
    )
    parser.add_argument("url", help="Full pitch.com presentation URL")
    parser.add_argument(
        "-o",
        "--output",
        default="output.pdf",
        help="Output PDF filename (default: output.pdf)",
    )
    parser.add_argument(
        "-e",
        "--email",
        default=None,
        help="Email address for protected presentations",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run browser in headed mode for debugging",
    )
    return parser.parse_args()


def handle_email_prompt(page, email):
    """Handle email-gated presentations."""
    email_selectors = [
        'input[type="email"]',
        '[data-testid*="email"]',
        'input[name*="email"]',
        'input[placeholder*="email" i]',
    ]

    for sel in email_selectors:
        try:
            input_el = page.query_selector(sel)
            if input_el and input_el.is_visible():
                if email is None:
                    print(
                        "Error: This presentation requires an email address. "
                        "Please provide one with -e/--email.",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                print("Email prompt detected, entering email...")
                input_el.fill(email)

                # Try to submit the email form
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Enter")',
                    'button:has-text("View")',
                ]
                submitted = False
                for submit_sel in submit_selectors:
                    try:
                        submit_btn = page.query_selector(submit_sel)
                        if submit_btn and submit_btn.is_visible():
                            submit_btn.click()
                            submitted = True
                            break
                    except Exception:
                        pass

                if not submitted:
                    # Fallback: press Enter to submit
                    input_el.press("Enter")

                # Wait for page to load after email submission
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                time.sleep(1)
                print("Email submitted.")

                # Handle the "Can we share details" popup
                try:
                    agree_btn = page.wait_for_selector(
                        'button:has-text("Agree")',
                        timeout=5000,
                    )
                    if agree_btn and agree_btn.is_visible():
                        agree_btn.click()
                        print("Clicked 'Agree' on sharing popup.")
                        time.sleep(1)
                except Exception:
                    pass

                # Handle the "Want to make a presentation" popup
                # The X button doesn't work, so click "Create a presentation" then go back
                try:
                    # Use get_by_role for better button detection, with partial text match
                    create_btn = page.get_by_role("link", name="Create a presentation").or_(
                        page.get_by_role("button", name="Create a presentation")
                    ).or_(
                        page.locator('a:has-text("Create a presentation")')
                    ).or_(
                        page.locator('button:has-text("Create a presentation")')
                    )
                    create_btn.wait_for(timeout=5000)
                    if create_btn.is_visible():
                        print("Found 'Create a presentation' button, clicking to dismiss popup...")
                        create_btn.click()
                        time.sleep(2)
                        page.go_back()
                        page.wait_for_load_state("networkidle", timeout=10000)
                        print("Dismissed 'Want to make a presentation' popup.")
                        time.sleep(1)
                except Exception as e:
                    print(f"Could not dismiss presentation popup: {e}")
                return
        except Exception:
            pass


def detect_slide_count(page):
    """Try to detect total slide count from pitch.com UI elements."""

    # pitch.com shows a "current / total" counter in presentation mode
    # Try common selectors for the slide counter
    selectors = [
        '[data-testid="slide-count"]',
        '[class*="slideCount"]',
        '[class*="SlideCount"]',
        '[class*="page-number"]',
        '[class*="slide-number"]',
    ]
    for sel in selectors:
        el = page.query_selector(sel)
        if el:
            text = el.inner_text()
            # Expect something like "1 / 12" or "1/12"
            if "/" in text:
                parts = text.split("/")
                try:
                    return int(parts[-1].strip())
                except ValueError:
                    pass

    # Fallback: look for any text matching "N / M" pattern on the page
    body_text = page.inner_text("body")
    import re

    match = re.search(r"(\d+)\s*/\s*(\d+)", body_text)
    if match:
        return int(match.group(2))

    # Another fallback: look for navigation dots / thumbnail indicators
    dots = page.query_selector_all('[class*="dot"], [class*="thumbnail"], [class*="Thumbnail"]')
    if len(dots) > 1:
        return len(dots)

    return None


def wait_for_slide_transition(page, wait_time=0.5):
    """Wait for a slide transition to complete."""
    time.sleep(wait_time)
    # Also wait for network to be mostly idle
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        pass


def find_slide_element(page):
    """Find the slide/canvas element for clipped screenshots."""
    # Common selectors for the slide container in pitch.com
    selectors = [
        '[data-testid*="slide" i]',
        '[class*="slideContainer" i]',
        '[class*="slide-container" i]',
        '[class*="presentationSlide" i]',
        '[class*="SlideView" i]',
        'canvas',
        '[class*="player" i] [class*="slide" i]',
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                box = el.bounding_box()
                if box and box["width"] > 100 and box["height"] > 100:
                    return el
        except Exception:
            pass
    return None


def capture_slides(page, total_slides=None):
    """Capture each slide as a PNG screenshot, returns list of image paths."""
    screenshots = []
    slide_index = 0
    max_slides = total_slides or 200  # safety cap
    prev_screenshot = None

    # In fullscreen mode, the viewport IS the slide - no need to find element
    print("Capturing full viewport (fullscreen mode).")
    slide_el = None  # Force viewport capture for cleaner fullscreen shots

    while slide_index < max_slides:
        # Take screenshot (clipped to slide element if found, otherwise full viewport)
        if slide_el:
            try:
                img_bytes = slide_el.screenshot(type="png")
            except Exception:
                # Element may have changed, try to find it again
                slide_el = find_slide_element(page)
                if slide_el:
                    img_bytes = slide_el.screenshot(type="png")
                else:
                    img_bytes = page.screenshot(type="png")
        else:
            img_bytes = page.screenshot(type="png")

        # Duplicate detection: stop if screenshot is identical to previous
        if prev_screenshot is not None and img_bytes == prev_screenshot:
            # Press right one more time and check again to be sure
            page.keyboard.press("ArrowRight")
            wait_for_slide_transition(page)
            verify_bytes = page.screenshot(type="png")
            if verify_bytes == prev_screenshot:
                print(f"  Detected end of deck (duplicate slide at index {slide_index}).")
                break
            else:
                # There was actually a new slide, save the verify screenshot
                img_bytes = verify_bytes

        prev_screenshot = img_bytes
        slide_index += 1
        print(f"  Captured slide {slide_index}" + (f" / {total_slides}" if total_slides else ""))
        screenshots.append(img_bytes)

        if total_slides and slide_index >= total_slides:
            break

        # Advance to next slide
        page.keyboard.press("ArrowRight")
        wait_for_slide_transition(page)

    return screenshots


def screenshots_to_pdf(screenshots, output_path):
    """Combine PNG screenshot bytes into a single PDF."""
    if not screenshots:
        print("No slides captured, nothing to save.")
        sys.exit(1)

    images = []
    for data in screenshots:
        from io import BytesIO

        img = Image.open(BytesIO(data)).convert("RGB")
        images.append(img)

    first, *rest = images
    first.save(output_path, "PDF", save_all=True, append_images=rest, resolution=150)
    print(f"Saved {len(images)} slides to {output_path}")


def main():
    args = parse_args()
    url = args.url
    output = args.output

    if "pitch.com" not in url:
        print("Warning: URL does not appear to be a pitch.com link.", file=sys.stderr)

    print(f"Opening {url} ...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.debug)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
        )
        page = context.new_page()

        # Navigate to the deck
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Handle email-gated presentations
        handle_email_prompt(page, args.email)

        # Wait for page to stabilize
        time.sleep(2)

        # Debug pause to allow inspection BEFORE entering fullscreen
        if args.debug:
            input("Debug mode: Press Enter to continue (inspect the page now)...")

        # Detect slide count before going fullscreen (easier to find in normal view)
        total = detect_slide_count(page)
        if total:
            print(f"Detected {total} slides.")
        else:
            print("Could not detect slide count; will use duplicate detection to find the end.")

        # Click on the slide area to give it focus
        page.mouse.click(960, 540)
        time.sleep(0.5)

        # Enter fullscreen presentation mode by pressing 'f'
        print("Entering fullscreen presentation mode...")
        page.keyboard.press("f")
        time.sleep(2)  # Wait for fullscreen transition

        # Forcibly remove any popups/modals via JavaScript
        page.evaluate("""
            () => {
                // Remove elements that look like popups/modals
                const selectors = [
                    '[role="dialog"]',
                    '[class*="modal" i]',
                    '[class*="Modal"]',
                    '[class*="popup" i]',
                    '[class*="Popup"]',
                    '[class*="Popover"]',
                    '[class*="popover"]',
                    '[class*="tooltip" i]',
                    '[class*="Tooltip"]',
                    '[class*="drawer" i]',
                    '[class*="Drawer"]',
                ];
                for (const sel of selectors) {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                }
                // Also remove any fixed/absolute positioned elements that might be overlays
                document.querySelectorAll('*').forEach(el => {
                    const style = window.getComputedStyle(el);
                    if ((style.position === 'fixed' || style.position === 'absolute') &&
                        style.zIndex > 100 &&
                        !el.closest('canvas') &&
                        !el.closest('[class*="slide" i]') &&
                        !el.closest('[class*="player" i]')) {
                        // Check if it looks like a popup (small-ish, not full screen)
                        const rect = el.getBoundingClientRect();
                        if (rect.width < window.innerWidth * 0.5 && rect.height < window.innerHeight * 0.5) {
                            el.remove();
                        }
                    }
                });
            }
        """)
        time.sleep(0.5)

        # Hide cursor from captures by moving it off-screen
        page.mouse.move(0, 0)
        time.sleep(0.3)

        # Capture all slides
        print("Capturing slides...")
        screenshots = capture_slides(page, total_slides=total)

        browser.close()

    # Build PDF
    screenshots_to_pdf(screenshots, output)
    print("Done.")


if __name__ == "__main__":
    main()
