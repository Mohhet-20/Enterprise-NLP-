"""
Capture README screenshots from a running stack.

    uvicorn backend.main:app --port 8000                 # terminal 1
    cd frontend && npm run build && npx vite preview --port 5173   # terminal 2
    python scripts/capture_screenshots.py

Requires `pip install playwright && playwright install chromium`.
Logs in with the dev-seeded admin account, exercises the Playground
(prediction + explanation, zero-shot, batch) and the Evaluations pages,
and writes PNGs to docs/images/.
"""

import argparse
import os

from playwright.sync_api import Page, sync_playwright

OUT = "docs/images"


def login(page: Page, base: str, username: str, password: str) -> None:
    page.goto(f"{base}/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_url(f"{base}/", timeout=20_000)


def pick_task(page: Page, label: str) -> None:
    page.get_by_role("combobox").first.click()
    page.get_by_role("option", name=label).click()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:5173")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="ChangeMe123!")
    parser.add_argument("--theme", choices=["light", "dark"], default="light")
    args = parser.parse_args()
    os.makedirs(OUT, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 1000}, device_scale_factor=2, color_scheme=args.theme
        )
        page = ctx.new_page()
        login(page, args.base, args.username, args.password)

        # Playground: sentiment + Integrated Gradients
        page.goto(f"{args.base}/playground")
        page.wait_for_selector("text=Predict")
        page.fill("textarea", "The plot was predictable and dull, but the acting was absolutely brilliant.")
        page.get_by_role("button", name="Run prediction").click()
        page.wait_for_selector("text=Result", timeout=120_000)
        page.get_by_role("button", name="Explain this prediction").click()
        page.wait_for_selector("[data-testid=attribution-text]", timeout=120_000)
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/playground-explain.png", full_page=True)

        # Zero-shot with request-time labels
        page.reload()
        page.wait_for_selector("text=Predict")
        pick_task(page, "Zero-shot Classification")
        page.fill("textarea", "I was charged twice for my order and still haven't received a refund.")
        page.get_by_role("button", name="Run prediction").click()
        page.wait_for_selector("text=Result", timeout=120_000)
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/playground-zero-shot.png", full_page=True)

        # Toxicity: multi-label output
        page.reload()
        page.wait_for_selector("text=Predict")
        pick_task(page, "Toxicity Detection")
        page.fill("textarea", "Shut up, you worthless idiot. Nobody wants you here.")
        page.get_by_role("button", name="Run prediction").click()
        page.wait_for_selector("text=multi-label", timeout=120_000)
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/playground-toxicity.png", full_page=True)

        # Evaluations list (runs created beforehand via the API)
        page.goto(f"{args.base}/evaluations")
        page.wait_for_selector("table", timeout=20_000)
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/evaluations.png", full_page=True)

        # Detail of the newest run
        page.locator("table a").first.click()
        page.wait_for_selector("text=Confusion", timeout=20_000)
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/evaluation-detail.png", full_page=True)

        page.goto(f"{args.base}/")
        page.wait_for_timeout(2500)
        page.screenshot(path=f"{OUT}/dashboard.png", full_page=True)

        browser.close()
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
