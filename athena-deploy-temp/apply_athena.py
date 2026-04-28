#!/usr/bin/env python3
"""
apply_athena.py -- Deploy the Athena intake pipeline to Pantheon.

Run this from the Pantheon project root:
  cd /home/coolzerohacks/projects/Pantheon
  python3 patches/apply_athena.py

What it does:
  1. Copies athena_pdf.py to the project root
  2. Appends AthenaSubmission class to models.py
  3. Adds required imports + routes to app.py
  4. Adds Athena nav entry to NAV_SECTIONS in app.py
  5. Updates base.html nav to include Athena route
  6. Copies all 4 Athena templates to templates/

After running, rebuild the container:
  docker stop pantheon
  docker rmi pantheon:latest
  cd /home/coolzerohacks/projects/Pantheon
  docker compose build --no-cache pantheon
  docker compose up -d pantheon

Then verify:
  docker logs pantheon --tail 50
  curl http://localhost:4200/athena/intake
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # /home/coolzerohacks/projects/Pantheon


def step(msg):
    print(f"\n[APPLY] {msg}")


def done(msg):
    print(f"  OK: {msg}")


def fail(msg):
    print(f"  ERROR: {msg}")
    sys.exit(1)


# -----------------------------------------------------------------------
# Step 1 -- Copy athena_pdf.py
# -----------------------------------------------------------------------
step("Copying athena_pdf.py")
src = os.path.join(HERE, "athena_pdf.py")
dst = os.path.join(ROOT, "athena_pdf.py")
if not os.path.exists(src):
    fail(f"Source not found: {src}")
shutil.copy2(src, dst)
done(dst)


# -----------------------------------------------------------------------
# Step 2 -- Append AthenaSubmission class to models.py
# -----------------------------------------------------------------------
step("Updating models.py")
models_path = os.path.join(ROOT, "models.py")
with open(models_path, "r") as f:
    models_content = f.read()

if "class AthenaSubmission" in models_content:
    done("AthenaSubmission already in models.py -- skipped")
else:
    addition_path = os.path.join(HERE, "athena_models_addition.py")
    with open(addition_path, "r") as f:
        addition = f.read()
    # Strip the docstring header (everything before '# PASTE THIS CLASS')
    marker = "# PASTE THIS CLASS AT THE BOTTOM OF models.py"
    if marker in addition:
        addition = addition[addition.index(marker) + len(marker):].strip()
    with open(models_path, "a") as f:
        f.write("\n\n" + addition + "\n")
    done("AthenaSubmission class appended to models.py")


# -----------------------------------------------------------------------
# Step 3 -- Update app.py: add imports, NAV_SECTIONS entry, append routes
# -----------------------------------------------------------------------
step("Updating app.py")
app_path = os.path.join(ROOT, "app.py")
with open(app_path, "r") as f:
    app_content = f.read()

changed = False

# 3a. Add AthenaSubmission to models import
OLD_IMPORT = "    Invoice, InvoiceLineItem, DeclinedContact, OutreachActivity, ProductDesign\n)"
NEW_IMPORT = "    Invoice, InvoiceLineItem, DeclinedContact, OutreachActivity, ProductDesign, AthenaSubmission\n)"
if "AthenaSubmission" not in app_content:
    if OLD_IMPORT in app_content:
        app_content = app_content.replace(OLD_IMPORT, NEW_IMPORT)
        done("Added AthenaSubmission to models import")
        changed = True
    else:
        print("  WARN: Could not find models import block -- add AthenaSubmission manually")
else:
    done("AthenaSubmission already in models import -- skipped")

# 3b. Add 'import threading' and 'import io' and 'import athena_pdf'
if "import threading" not in app_content:
    app_content = app_content.replace(
        "from decimal import Decimal\n",
        "from decimal import Decimal\nimport threading\nimport io\n"
    )
    done("Added threading + io imports")
    changed = True
else:
    done("threading already imported -- skipped")

if "import athena_pdf" not in app_content:
    app_content = app_content.replace(
        "import resend_client\n",
        "import resend_client\nimport athena_pdf\n"
    )
    done("Added athena_pdf import")
    changed = True
else:
    done("athena_pdf already imported -- skipped")

# 3c. Add Athena to NAV_SECTIONS
if '"athena"' not in app_content and "'athena'" not in app_content:
    # Insert after the agents entry
    app_content = app_content.replace(
        '    ("agents",          "Agents",           "\U0001f916"),',
        '    ("agents",          "Agents",           "\U0001f916"),\n    ("athena",          "Athena Audits",    "\U0001f3db️"),'
    )
    done("Added Athena to NAV_SECTIONS")
    changed = True
else:
    done("Athena already in NAV_SECTIONS -- skipped")

# 3d. Append Athena routes block
routes_path = os.path.join(HERE, "athena_app_routes.py")
with open(routes_path, "r") as f:
    routes_content = f.read()

# Strip the header docstring
marker = "# ======"
if marker in routes_content:
    routes_content = routes_content[routes_content.index(marker):]

if "def athena_intake" not in app_content:
    # Insert routes before the 'if __name__' block or at end
    if 'if __name__ == "__main__":' in app_content:
        app_content = app_content.replace(
            'if __name__ == "__main__":',
            routes_content + '\n\nif __name__ == "__main__":'
        )
    else:
        app_content = app_content + "\n\n" + routes_content
    done("Athena routes appended to app.py")
    changed = True
else:
    done("Athena routes already in app.py -- skipped")

if changed:
    with open(app_path, "w") as f:
        f.write(app_content)
    done("app.py written")


# -----------------------------------------------------------------------
# Step 4 -- Update base.html nav to include Athena route
# -----------------------------------------------------------------------
step("Updating base.html")
base_path = os.path.join(ROOT, "templates", "base.html")
with open(base_path, "r") as f:
    base_content = f.read()

if "athena_submissions" not in base_content:
    # Add Athena to the url_for chain in the nav
    base_content = base_content.replace(
        "else 'agents_page' if slug=='agents'",
        "else 'agents_page' if slug=='agents'\n             else 'athena_submissions' if slug=='athena'"
    )
    with open(base_path, "w") as f:
        f.write(base_content)
    done("base.html updated with Athena nav route")
else:
    done("base.html already has Athena route -- skipped")


# -----------------------------------------------------------------------
# Step 5 -- Copy templates
# -----------------------------------------------------------------------
step("Copying Athena templates")
tmpl_src = os.path.join(HERE, "templates")
tmpl_dst = os.path.join(ROOT, "templates")
for fname in [
    "athena_intake.html",
    "athena_thankyou.html",
    "athena_submissions.html",
    "athena_submission_detail.html",
]:
    src = os.path.join(tmpl_src, fname)
    dst = os.path.join(tmpl_dst, fname)
    if not os.path.exists(src):
        print(f"  WARN: Template not found: {src}")
        continue
    shutil.copy2(src, dst)
    done(f"Copied {fname}")


# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
print("\n[APPLY] All patches applied.")
print("[APPLY] Next: rebuild and verify.")
print()
print("  docker stop pantheon")
print("  docker rmi pantheon:latest")
print("  cd /home/coolzerohacks/projects/Pantheon")
print("  docker compose build --no-cache pantheon")
print("  docker compose up -d pantheon")
print()
print("  # Verify:")
print("  docker logs pantheon --tail 50")
print("  curl -s -o /dev/null -w '%{http_code}' http://localhost:4200/athena/intake")
print("  # Expected: 200")
