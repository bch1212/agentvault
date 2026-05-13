"""SendGrid email alerts for budget warnings and rotation events."""

import os
from api.config import get_settings


async def send_alert(to_email: str, subject: str, body_html: str):
    """Send an email alert via SendGrid."""
    settings = get_settings()
    if not settings.sendgrid_api_key:
        return  # silently skip in dev

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=settings.sendgrid_from_email,
            to_emails=to_email,
            subject=subject,
            html_content=body_html,
        )
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        sg.send(message)
    except Exception as e:
        # Log but don't crash — alerts are best-effort
        print(f"[ALERT] Failed to send email to {to_email}: {e}")


async def send_budget_warning(to_email: str, agent_name: str, period: str, used: float, limit: float):
    """Alert when an agent hits 80% of budget."""
    pct = (used / limit * 100) if limit > 0 else 0
    await send_alert(
        to_email=to_email,
        subject=f"[AgentVault] Budget warning: {agent_name} at {pct:.0f}% of {period} limit",
        body_html=f"""
        <h2>Budget Warning</h2>
        <p>Agent <strong>{agent_name}</strong> has used <strong>${used:.2f}</strong>
        of its <strong>${limit:.2f}</strong> {period} budget ({pct:.0f}%).</p>
        <p>The agent will be blocked from accessing credentials once the limit is reached.</p>
        <p><a href="{get_settings().api_base_url}">Open AgentVault Dashboard</a></p>
        """,
    )


async def send_rotation_alert(to_email: str, credential_name: str, provider: str | None, success: bool):
    """Alert when a credential is rotated (or rotation fails)."""
    status = "succeeded" if success else "FAILED"
    await send_alert(
        to_email=to_email,
        subject=f"[AgentVault] Credential rotation {status}: {credential_name}",
        body_html=f"""
        <h2>Credential Rotation {status.title()}</h2>
        <p>Credential <strong>{credential_name}</strong>
        {f'(provider: {provider})' if provider else ''}
        was {'successfully rotated' if success else 'scheduled for rotation but the rotation failed'}.</p>
        {'<p style="color:red;">Please check the credential and rotate it manually if needed.</p>' if not success else ''}
        <p><a href="{get_settings().api_base_url}">Open AgentVault Dashboard</a></p>
        """,
    )
