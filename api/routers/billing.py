"""Stripe billing endpoints — checkout, webhooks, portal."""

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.middleware.user_auth import get_current_user
from api.models.db import User, PlanType
from api.models.schemas import CheckoutRequest, CheckoutResponse, PortalResponse
from api.config import get_settings

router = APIRouter(prefix="/billing", tags=["billing"])

PRICE_TO_PLAN = {}  # populated at startup


def init_stripe():
    """Initialize Stripe with API key and build price-to-plan mapping."""
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key
    global PRICE_TO_PLAN
    PRICE_TO_PLAN = {
        settings.stripe_price_pro: PlanType.pro,
        settings.stripe_price_business: PlanType.business,
        settings.stripe_price_enterprise: PlanType.enterprise,
    }


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for plan upgrade."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    init_stripe()

    # Create or reuse Stripe customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
        user.stripe_customer_id = customer.id
        await db.flush()

    success_url = body.success_url or f"{settings.api_base_url}/billing/success"
    cancel_url = body.cancel_url or f"{settings.api_base_url}/billing/cancel"

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": body.price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id)},
    )

    return CheckoutResponse(checkout_url=session.url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe customer portal session."""
    settings = get_settings()
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    init_stripe()
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.api_base_url}",
    )
    return PortalResponse(portal_url=session.url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events (subscription updates)."""
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        init_stripe()
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        # Look up user by Stripe customer ID
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user and subscription_id:
            user.stripe_subscription_id = subscription_id
            # Determine plan from line items
            sub = stripe.Subscription.retrieve(subscription_id)
            price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None
            if price_id and price_id in PRICE_TO_PLAN:
                user.plan = PRICE_TO_PLAN[price_id]

    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub = event["data"]["object"]
        customer_id = sub.get("customer")

        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user:
            if sub.get("status") in ("canceled", "unpaid", "past_due"):
                user.plan = PlanType.free
                user.stripe_subscription_id = None
            elif sub.get("status") == "active":
                price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None
                if price_id and price_id in PRICE_TO_PLAN:
                    user.plan = PRICE_TO_PLAN[price_id]

    return {"status": "ok"}
