import datetime
import pytest
from database.connection import get_db_session, init_db
from database.models import User, Transaction, TransactionItem, SplitBill, SplitBillParticipant

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()

def test_user_and_transaction_crud():
    session = get_db_session()
    try:
        test_user_id = 999123456
        user = session.query(User).filter(User.id == test_user_id).first()
        if not user:
            user = User(id=test_user_id, username="testuser", first_name="Test", last_name="User")
            session.add(user)
            session.commit()

        assert user.id == test_user_id
        assert user.first_name == "Test"

        trans = Transaction(
            user_id=test_user_id,
            merchant="Solaria Resto",
            transaction_date=datetime.date.today(),
            total_amount=75000.0,
            category="Makanan & Minuman"
        )
        session.add(trans)
        session.flush()

        item1 = TransactionItem(transaction_id=trans.id, item_name="Nasi Goreng", qty=1, price=45000, subtotal=45000)
        item2 = TransactionItem(transaction_id=trans.id, item_name="Jus Alpukat", qty=1, price=30000, subtotal=30000)
        session.add_all([item1, item2])
        session.commit()

        db_trans = session.query(Transaction).filter(Transaction.id == trans.id).first()
        assert db_trans is not None
        assert db_trans.merchant == "Solaria Resto"
        assert float(db_trans.total_amount) == 75000.0
        assert len(db_trans.items) == 2

        session.delete(db_trans)
        session.commit()
    finally:
        session.close()

def test_split_bill_crud():
    session = get_db_session()
    try:
        test_user_id = 999123456
        user = session.query(User).filter(User.id == test_user_id).first()
        if not user:
            user = User(id=test_user_id, username="testuser", first_name="Test")
            session.add(user)
            session.commit()

        sb = SplitBill(
            creator_id=test_user_id,
            title="Makan Malam Ulang Tahun",
            total_amount=150000.0,
            tax_amount=15000.0,
            status="ACTIVE"
        )
        session.add(sb)
        session.flush()

        p1 = SplitBillParticipant(split_bill_id=sb.id, participant_name="Alice", allocated_amount=75000.0, is_paid=True)
        p2 = SplitBillParticipant(split_bill_id=sb.id, participant_name="Bob", allocated_amount=75000.0, is_paid=False)
        session.add_all([p1, p2])
        session.commit()

        db_sb = session.query(SplitBill).filter(SplitBill.id == sb.id).first()
        assert db_sb is not None
        assert len(db_sb.participants) == 2
        assert db_sb.participants[0].is_paid is True

        # Toggle Bob's payment status to True
        p2.is_paid = True
        p2.paid_at = datetime.datetime.now()
        
        # Check if all participants paid -> set status to SETTLED
        if all(p.is_paid for p in db_sb.participants):
            db_sb.status = "SETTLED"

        session.commit()

        db_sb_updated = session.query(SplitBill).filter(SplitBill.id == sb.id).first()
        assert db_sb_updated.status == "SETTLED"
        assert db_sb_updated.participants[1].is_paid is True
        assert db_sb_updated.participants[1].paid_at is not None

        session.delete(db_sb_updated)
        session.commit()
    finally:
        session.close()
