import frappe


def cleanup_old_leopards_snapshots(days=30):
    """
    Delete delivered Leopards Shipment Tracking records
    older than N days (default: 30).

    Safe:
    - Does NOT touch Delivery Notes
    - Does NOT touch tracking history
    """

    frappe.db.sql(
        """
        DELETE FROM `tabLeopards Shipment Tracking`
        WHERE is_delivered = 1
          AND last_updated < DATE_SUB(NOW(), INTERVAL %s DAY)
        """,
        (int(days),),
    )

    frappe.db.commit()


def cleanup_old_leopards_tracking_history(days=30):
    """
    Delete Leopards Tracking Event records
    older than N days (default: 30).

    Safe:
    - Does NOT touch snapshots
    - Does NOT touch Delivery Notes
    - History-only cleanup
    """

    frappe.db.sql(
        """
        DELETE FROM `tabLeopards Tracking Event`
        WHERE event_time < DATE_SUB(NOW(), INTERVAL %s DAY)
        """,
        (int(days),),
    )

    frappe.db.commit()