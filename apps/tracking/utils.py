from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

channel_layer = get_channel_layer()


def broadcast_location_update(order_id, latitude, longitude, status):
    """
    Called from AgentLocationUpdateView after saving new coordinates.
    Broadcasts to all WebSocket clients tracking this order.

    ── Why async_to_sync? ────────────────────────────────────────────────
    channel_layer.group_send() is async.
    AgentLocationUpdateView is a sync Django view.
    async_to_sync() bridges the gap — runs async code from sync context.
    """
    async_to_sync(channel_layer.group_send)( #type:ignore
        f"order_{order_id}",      # group name — matches consumer's group_name
        {
            # ── type maps to consumer method ──────────────────────────────
            # "location.update" → consumer.location_update()
            # dot notation → underscore method name
            "type":      "location.update",
            "latitude":  str(latitude),
            "longitude": str(longitude),
            "status":    status,
            "timestamp": timezone.now().isoformat(),
        }
    )


def broadcast_order_status(order_id, status, message=""):
    """
    Called from OrderStatusUpdateView after every status transition.
    Customer sees real-time status updates without polling.

    Example messages:
        ACCEPTED  → "Restaurant accepted your order!"
        PREPARING → "Your food is being prepared"
        READY     → "Order ready for pickup"
        PICKED_UP → "Agent is on the way"
        DELIVERED → "Order delivered. Enjoy your meal!"
    """
    STATUS_MESSAGES = {
        "ACCEPTED":  "Restaurant accepted your order.",
        "PREPARING": "Your food is being prepared.",
        "READY":     "Order is ready for pickup.",
        "PICKED_UP": "Your order is on the way.",
        "DELIVERED": "Order delivered. Enjoy your meal!",
        "CANCELLED": "Your order has been cancelled.",
    }

    async_to_sync(channel_layer.group_send)( #type:ignore
        f"order_{order_id}",
        {
            "type":    "order.status.update",
            "status":  status,
            "message": message or STATUS_MESSAGES.get(status, ""),
        }
    )