"""
AthenaSubmission model -- append this class to models.py.

Destination: append to /home/coolzerohacks/projects/Pantheon/models.py
"""
# PASTE THIS CLASS AT THE BOTTOM OF models.py


class AthenaSubmission(db.Model):
    """Athena AI audit intake form submission and generated report.

    Lifecycle:
      pending     -> saved, background thread not yet started
      generating  -> Claude is writing the report
      done        -> report written, PDF emailed
      error       -> processing failed (check logs)
    """
    __tablename__ = "athena_submissions"
    id = db.Column(db.Integer, primary_key=True)
    # Business info
    business_name = db.Column(db.String(300), nullable=False)
    contact_name = db.Column(db.String(200))
    contact_email = db.Column(db.String(200))
    industry = db.Column(db.String(120))
    team_size = db.Column(db.String(64))
    # Intake questions
    current_bottlenecks = db.Column(db.Text)
    manual_processes = db.Column(db.Text)
    tools_in_use = db.Column(db.Text)
    goals_6_months = db.Column(db.Text)
    biggest_time_waste = db.Column(db.Text)
    ai_experience = db.Column(db.Text)
    budget_range = db.Column(db.String(64))
    # Generated AI report
    report_markdown = db.Column(db.Text)
    report_status = db.Column(db.String(32), default="pending")
    # CRM link
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="SET NULL"))
    # Email delivery
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    linked_client = db.relationship("Client", backref="athena_submissions")
