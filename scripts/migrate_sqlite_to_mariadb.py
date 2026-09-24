import sys
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import pymysql
from database.connection import init_db, get_db_session, engine
from database.models import User, Transaction, TransactionItem, SplitBill, SplitBillItem, SplitBillParticipant

def migrate():
    print("=== 1. Checking MariaDB Connection ===")
    from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
    conn_m = pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn_m.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    conn_m.commit()
    cursor.close()
    conn_m.close()
    print(f"MariaDB Database '{DB_NAME}' created/verified successfully!")

    print("=== 2. Initializing MariaDB Tables ===")
    init_db()

    sqlite_path = BASE_DIR / "receipt_bot.db"
    if not sqlite_path.exists():
        print("No SQLite database found to migrate.")
        return

    print("=== 3. Migrating Data from SQLite to MariaDB ===")
    sq_conn = sqlite3.connect(sqlite_path)
    sq_cursor = sq_conn.cursor()

    session = get_db_session()
    try:
        # Migrate Users
        sq_cursor.execute("SELECT id, username, first_name, last_name, created_at FROM users;")
        for u in sq_cursor.fetchall():
            if not session.query(User).filter(User.id == u[0]).first():
                session.add(User(id=u[0], username=u[1], first_name=u[2], last_name=u[3]))
        session.commit()
        print("Migrated Users.")

        # Migrate Transactions
        sq_cursor.execute("SELECT id, user_id, merchant, transaction_date, total_amount, category, raw_ocr_text, image_path FROM transactions;")
        for t in sq_cursor.fetchall():
            if not session.query(Transaction).filter(Transaction.id == t[0]).first():
                session.add(Transaction(
                    id=t[0], user_id=t[1], merchant=t[2], transaction_date=t[3],
                    total_amount=t[4], category=t[5], raw_ocr_text=t[6], image_path=t[7]
                ))
        session.commit()

        # Migrate Transaction Items
        sq_cursor.execute("SELECT id, transaction_id, item_name, qty, price, subtotal FROM transaction_items;")
        for ti in sq_cursor.fetchall():
            if not session.query(TransactionItem).filter(TransactionItem.id == ti[0]).first():
                session.add(TransactionItem(
                    id=ti[0], transaction_id=ti[1], item_name=ti[2], qty=ti[3], price=ti[4], subtotal=ti[5]
                ))
        session.commit()
        print("Migrated Transactions & Items.")

        # Migrate SplitBills
        sq_cursor.execute("SELECT id, creator_id, title, total_amount, tax_amount, service_charge, discount_amount, status FROM split_bills;")
        for sb in sq_cursor.fetchall():
            if not session.query(SplitBill).filter(SplitBill.id == sb[0]).first():
                session.add(SplitBill(
                    id=sb[0], creator_id=sb[1], title=sb[2], total_amount=sb[3],
                    tax_amount=sb[4], service_charge=sb[5], discount_amount=sb[6], status=sb[7]
                ))
        session.commit()

        # Migrate SplitBillItems
        sq_cursor.execute("SELECT id, split_bill_id, item_name, qty, price, subtotal FROM split_bill_items;")
        for sbi in sq_cursor.fetchall():
            if not session.query(SplitBillItem).filter(SplitBillItem.id == sbi[0]).first():
                session.add(SplitBillItem(
                    id=sbi[0], split_bill_id=sbi[1], item_name=sbi[2], qty=sbi[3], price=sbi[4], subtotal=sbi[5]
                ))
        session.commit()

        # Migrate SplitBillParticipants
        sq_cursor.execute("SELECT id, split_bill_id, participant_name, telegram_id, allocated_amount, is_paid FROM split_bill_participants;")
        for sbp in sq_cursor.fetchall():
            if not session.query(SplitBillParticipant).filter(SplitBillParticipant.id == sbp[0]).first():
                session.add(SplitBillParticipant(
                    id=sbp[0], split_bill_id=sbp[1], participant_name=sbp[2],
                    telegram_id=sbp[3], allocated_amount=sbp[4], is_paid=bool(sbp[5])
                ))
        session.commit()
        print("Migrated Split Bills, Items & Participants.")

        print("=== MIGRATION TO MARIADB COMPLETE! ===")

        # Verify MariaDB contents
        print("\n=== Verification of MariaDB Tables ===")
        print("Users count:", session.query(User).count())
        print("SplitBills count:", session.query(SplitBill).count())
        for sb in session.query(SplitBill).all():
            print(f"  SplitBill #{sb.id}: '{sb.title}' (Total: Rp {sb.total_amount:,.0f})")
            print(f"  Participants ({len(sb.participants)}): {[p.participant_name for p in sb.participants]}")

    except Exception as e:
        session.rollback()
        print("Migration Error:", e)
    finally:
        session.close()
        sq_conn.close()

if __name__ == "__main__":
    migrate()
