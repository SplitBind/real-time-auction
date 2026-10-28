# src/real_time_auction/services/auction_closer.py
from real_time_auction.models import db, Item, Bid
from real_time_auction.tasks.email_tasks import send_dispatch_email_task

def close_lot_and_notify(item_id: int):
    item = Item.query.get_or_404(item_id)
    
    if item.status == 'CLOSED' or not item.is_active:
        return # Already closed
        
    # Find the highest bid
    winning_bid = Bid.query.filter_by(item_id=item.id).order_by(Bid.amount.desc()).first()
    
    if winning_bid and winning_bid.user:
        recipient_email = winning_bid.user.email
        subject = f"Victory Confirmed: Lot #{item.id} - {item.title}"
        
        message = (
            f"Greetings,<br><br>"
            f"The auction for <strong>{item.title}</strong> (Lot #{item.id}) has officially concluded.<br>"
            f"You secured the winning bid at <strong>${item.current_price:.2f}</strong>.<br><br>"
            f"Please log into your control portal to complete your payment and finalize acquisition."
        )
        
        # Asynchronously trigger Celery task
        send_dispatch_email_task.delay(
            recipient=recipient_email,
            subject=subject,
            message=message
        )
        
    # Update Lot Status
    item.status = 'CLOSED'
    item.is_active = False
    db.session.commit()
