"""
Athena pipeline routes and helpers -- append this entire block to app.py.

BEFORE appending:
  1. Add 'AthenaSubmission' to the 'from models import (...)' block in app.py
  2. Add 'import threading' near the top imports in app.py
  3. Add 'import io' near the top imports in app.py
  4. Add 'import athena_pdf' near the top imports in app.py
  5. Add ("athena", "Athena Audits", chr(0x1F3DB)) to NAV_SECTIONS list in app.py
  6. Add 'else athena_submissions if slug==athena' to the url_for chain in base.html nav

APPEND everything below the '# ====' marker to the END of app.py
(before the 'if __name__ == "__main__":' line)
"""

# ======================================================================
# ATHENA INTAKE PIPELINE
# ======================================================================

_ATHENA_SYSTEM = (
    "You are an expert AI business consultant generating an Athena audit report "
    "for Cognito Coding. Your report must be clear, practical, and specific to the "
    "client's actual answers. No corporate waffle. Straight-talking.\n\n"
    "Structure your report exactly as follows (use these headings):\n\n"
    "# Athena AI Audit Report\n\n"
    "## Executive Summary\n"
    "2-3 sentences: current state, biggest single AI opportunity, expected impact.\n\n"
    "## Current State Assessment\n"
    "Honest analysis of their workflows, bottlenecks, and tech stack. "
    "Name specific pain points from their answers.\n\n"
    "## AI Opportunity Map\n"
    "3-5 specific automation opportunities ranked by ROI. For each:\n"
    "- **Opportunity**: what it is\n"
    "- **Current pain**: time/money being wasted\n"
    "- **AI solution**: what gets automated\n"
    "- **Expected saving**: realistic estimate\n"
    "- **Priority**: High / Medium / Low\n\n"
    "## Recommended Implementation Roadmap\n\n"
    "**Phase 1 -- Quick Wins (0-30 days)**\n"
    "2-3 low-effort, high-impact things they can do immediately.\n\n"
    "**Phase 2 -- Core Automation (1-3 months)**\n"
    "2-3 specific projects with expected outcomes.\n\n"
    "**Phase 3 -- Advanced AI (3-6 months)**\n"
    "More complex automations worth building once Phase 2 is stable.\n\n"
    "## Why Athena Fits\n"
    "2-3 sentences explaining how Cognito Coding's Athena service (750 GBP/month: "
    "full workflow review + 2-3 configured AI agents + 60-min debrief) directly "
    "addresses their goals. Name specific agents that would serve them "
    "(e.g. CMO agent for content, Scout agent for leads, Ops agent for admin).\n\n"
    "Be specific. Use their actual answers. No padding."
)


def _build_athena_prompt(sub) -> str:
    lines = [
        f"Business Name: {sub.business_name}",
        f"Industry: {sub.industry or 'Not specified'}",
        f"Team Size: {sub.team_size or 'Not specified'}",
        f"Contact: {sub.contact_name or 'Not specified'}",
        "",
        "INTAKE ANSWERS:",
        "",
        f"Current Bottlenecks:\n{sub.current_bottlenecks or 'Not answered'}",
        "",
        f"Manual Processes:\n{sub.manual_processes or 'Not answered'}",
        "",
        f"Tools Currently in Use:\n{sub.tools_in_use or 'Not answered'}",
        "",
        f"Goals for Next 6 Months:\n{sub.goals_6_months or 'Not answered'}",
        "",
        f"Biggest Time Waste:\n{sub.biggest_time_waste or 'Not answered'}",
        "",
        f"AI/Automation Experience:\n{sub.ai_experience or 'Not answered'}",
        "",
        f"Budget Range: {sub.budget_range or 'Not specified'}",
        "",
        "Generate a structured, practical Athena audit report in markdown format.",
    ]
    return "\n".join(lines)


def _athena_email_html(sub) -> str:
    import html as _html
    name = _html.escape(sub.contact_name or sub.business_name)
    biz = _html.escape(sub.business_name)
    return (
        '<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'
        'padding:20px;background:#fafafa;">'
        '<div style="background:#000;padding:24px;border-radius:8px 8px 0 0;">'
        '<h1 style="color:#FF6600;margin:0;font-size:22px;">Cognito Coding</h1>'
        '<p style="color:#FFB347;margin:4px 0 0;">Automate the Boring. Focus on What Matters.</p>'
        '</div>'
        '<div style="background:#fff;padding:24px;border-radius:0 0 8px 8px;'
        'border:1px solid #e5e5e5;border-top:none;">'
        f'<p>Hi {name},</p>'
        '<p>Thank you for completing your <strong>Athena AI Audit</strong>. '
        'Your personalised report is attached as a PDF.</p>'
        '<p>Your report covers:</p>'
        '<ul>'
        f'<li>Current state assessment of {biz}</li>'
        '<li>Your AI opportunity map -- where automation saves the most time</li>'
        '<li>A phased implementation roadmap</li>'
        '<li>How Athena specifically fits your goals</li>'
        '</ul>'
        '<p>We would love to walk you through the findings on a 60-minute debrief call. '
        'Reply to this email to book a time.</p>'
        '<p style="margin:24px 0 0;padding:12px 24px;background:#FF6600;border-radius:6px;'
        'display:inline-block;">'
        '<a href="mailto:info@cognitocoding.com" style="color:#fff;text-decoration:none;'
        'font-weight:bold;">Reply to Book Your Debrief</a></p>'
        '<hr style="margin:24px 0;border:none;border-top:1px solid #e5e5e5;">'
        '<p style="font-size:12px;color:#999;">'
        'Cognito Coding &middot; info@cognitocoding.com &middot; cognitocoding.com<br>'
        'Athena &mdash; &pound;750/month. Full workflow review, AI opportunity map, '
        '2-3 configured agents, and 60-min debrief. Everything included.</p>'
        '</div></body></html>'
    )


def _process_athena_bg(app_ref, submission_id: int):
    """Background thread: Claude report -> PDF -> CRM client -> email."""
    with app_ref.app_context():
        sub = AthenaSubmission.query.get(submission_id)
        if not sub:
            return
        try:
            # 1. Mark generating
            sub.report_status = "generating"
            db.session.commit()

            # 2. Generate report via Claude CLI (subscription billing, not API)
            result = agent_runner._call_cli(
                prompt=_build_athena_prompt(sub),
                system=_ATHENA_SYSTEM,
                model="claude-sonnet-4-6",
                max_tokens=4096,
                timeout=300,
                agent_slug="athena",
            )
            sub.report_markdown = result.get("text", "")
            sub.report_status = "done"
            db.session.commit()

            # 3. Create CRM client record if email provided and not already linked
            if sub.contact_email and not sub.client_id:
                existing_contact = Contact.query.filter_by(email=sub.contact_email).first()
                if existing_contact:
                    sub.client_id = existing_contact.client_id
                else:
                    cl = Client(
                        company_name=sub.business_name,
                        industry=sub.industry,
                        lifecycle_stage="prospect",
                        is_active=True,
                        notes=f"Athena audit submission #{sub.id}. Contact: {sub.contact_name}.",
                    )
                    db.session.add(cl)
                    db.session.flush()
                    ct = Contact(
                        client_id=cl.id,
                        name=sub.contact_name or sub.business_name,
                        email=sub.contact_email,
                        is_primary=True,
                    )
                    db.session.add(ct)
                    sub.client_id = cl.id
                db.session.commit()

            # 4. Generate PDF
            import athena_pdf as _athena_pdf
            pdf_bytes = _athena_pdf.render(sub)

            # 5. Send email with PDF attachment
            if sub.contact_email:
                safe_name = sub.business_name.replace(" ", "_").replace("/", "_")
                email_result = resend_client.send_email(
                    to=sub.contact_email,
                    subject=f"Your Athena AI Audit Report -- {sub.business_name}",
                    html=_athena_email_html(sub),
                    from_addr="Cognito Coding <noreply@cognitocoding.com>",
                    reply_to="info@cognitocoding.com",
                    attachments=[{
                        "filename": f"Athena_Audit_{safe_name}.pdf",
                        "content": pdf_bytes,
                    }],
                )
                if email_result.get("ok"):
                    sub.email_sent = True
                    sub.email_sent_at = datetime.utcnow()
                    db.session.commit()
                else:
                    log.warning("Athena email failed for submission %s: %s",
                                submission_id, email_result)

        except Exception:
            log.exception("Athena processing failed for submission %s", submission_id)
            try:
                sub.report_status = "error"
                db.session.commit()
            except Exception:
                db.session.rollback()


# ---- Public routes (no login required) ----

@app.route("/athena/intake", methods=["GET", "POST"])
def athena_intake():
    """Public-facing intake form -- no login required."""
    if request.method == "POST":
        business_name = (request.form.get("business_name") or "").strip()
        if not business_name:
            flash("Business name is required.", "error")
            return redirect(url_for("athena_intake"))

        sub = AthenaSubmission(
            business_name=business_name,
            contact_name=(request.form.get("contact_name") or "").strip(),
            contact_email=(request.form.get("contact_email") or "").strip(),
            industry=(request.form.get("industry") or "").strip(),
            team_size=request.form.get("team_size") or "",
            current_bottlenecks=(request.form.get("current_bottlenecks") or "").strip(),
            manual_processes=(request.form.get("manual_processes") or "").strip(),
            tools_in_use=(request.form.get("tools_in_use") or "").strip(),
            goals_6_months=(request.form.get("goals_6_months") or "").strip(),
            biggest_time_waste=(request.form.get("biggest_time_waste") or "").strip(),
            ai_experience=(request.form.get("ai_experience") or "").strip(),
            budget_range=request.form.get("budget_range") or "",
            report_status="pending",
        )
        db.session.add(sub)
        db.session.commit()

        # Fire background processing (daemon so container can still shut down cleanly)
        import threading as _threading
        t = _threading.Thread(target=_process_athena_bg, args=(app, sub.id), daemon=True)
        t.start()

        return redirect(url_for("athena_thankyou", sid=sub.id))

    return render_template("athena_intake.html")


@app.route("/athena/thankyou")
def athena_thankyou():
    """Thank-you page shown after intake submission."""
    sid = request.args.get("sid", type=int)
    sub = AthenaSubmission.query.get(sid) if sid else None
    return render_template("athena_thankyou.html", sub=sub)


@app.route("/athena/<int:sid>/status")
def athena_submission_status(sid):
    """JSON status poll -- PUBLIC. Called by thank-you page and detail page."""
    sub = AthenaSubmission.query.get_or_404(sid)
    return jsonify(status=sub.report_status, email_sent=sub.email_sent)


# ---- Admin views (login required) ----

@app.route("/athena")
@login_required
def athena_submissions():
    g.section = "athena"
    rows = AthenaSubmission.query.order_by(AthenaSubmission.created_at.desc()).all()
    total = len(rows)
    pending = sum(1 for r in rows if r.report_status in ("pending", "generating"))
    done = sum(1 for r in rows if r.report_status == "done")
    errors = sum(1 for r in rows if r.report_status == "error")
    return render_template("athena_submissions.html",
                           rows=rows, total=total, pending=pending,
                           done=done, errors=errors)


@app.route("/athena/<int:sid>")
@login_required
def athena_submission_detail(sid):
    g.section = "athena"
    sub = AthenaSubmission.query.get_or_404(sid)
    return render_template("athena_submission_detail.html", sub=sub)


@app.route("/athena/<int:sid>/pdf")
@login_required
def athena_submission_pdf(sid):
    sub = AthenaSubmission.query.get_or_404(sid)
    if not sub.report_markdown:
        flash("No report generated yet.", "error")
        return redirect(url_for("athena_submission_detail", sid=sid))
    import athena_pdf as _athena_pdf
    from flask import send_file
    import io as _io
    pdf_bytes = _athena_pdf.render(sub)
    buf = _io.BytesIO(pdf_bytes)
    safe_name = sub.business_name.replace(" ", "_").replace("/", "_")
    fname = f"Athena_Audit_{safe_name}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=fname)


@app.route("/athena/<int:sid>/regenerate", methods=["POST"])
@login_required
def athena_regenerate(sid):
    sub = AthenaSubmission.query.get_or_404(sid)
    sub.report_status = "pending"
    sub.report_markdown = None
    sub.email_sent = False
    sub.email_sent_at = None
    db.session.commit()
    import threading as _threading
    t = _threading.Thread(target=_process_athena_bg, args=(app, sub.id), daemon=True)
    t.start()
    flash("Report regeneration started.", "success")
    return redirect(url_for("athena_submission_detail", sid=sid))
