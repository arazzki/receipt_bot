import datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer,
    Numeric, String, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram User ID
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    split_bills: Mapped[List["SplitBill"]] = relationship(
        "SplitBill", back_populates="creator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    merchant: Mapped[str] = mapped_column(String(128), nullable=False, default="Unknown Merchant")
    transaction_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, default=datetime.date.today)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="Lain-lain")
    raw_ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="transactions")
    items: Mapped[List["TransactionItem"]] = relationship(
        "TransactionItem", back_populates="transaction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, merchant='{self.merchant}', total={self.total_amount})>"


class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(128), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)

    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="items")

    def __repr__(self) -> str:
        return f"<TransactionItem(name='{self.item_name}', qty={self.qty}, subtotal={self.subtotal})>"


class SplitBill(Base):
    __tablename__ = "split_bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="Split Bill")
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    service_charge: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE") # DRAFT, ACTIVE, SETTLED
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    creator: Mapped["User"] = relationship("User", back_populates="split_bills")
    items: Mapped[List["SplitBillItem"]] = relationship(
        "SplitBillItem", back_populates="split_bill", cascade="all, delete-orphan"
    )
    participants: Mapped[List["SplitBillParticipant"]] = relationship(
        "SplitBillParticipant", back_populates="split_bill", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SplitBill(id={self.id}, title='{self.title}', total={self.total_amount})>"


class SplitBillItem(Base):
    __tablename__ = "split_bill_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    split_bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("split_bills.id"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(128), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)

    split_bill: Mapped["SplitBill"] = relationship("SplitBill", back_populates="items")
    assignments: Mapped[List["SplitBillItemAssignment"]] = relationship(
        "SplitBillItemAssignment", back_populates="split_bill_item", cascade="all, delete-orphan"
    )


class SplitBillParticipant(Base):
    __tablename__ = "split_bill_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    split_bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("split_bills.id"), nullable=False)
    participant_name: Mapped[str] = mapped_column(String(128), nullable=False)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    allocated_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    split_bill: Mapped["SplitBill"] = relationship("SplitBill", back_populates="participants")
    assignments: Mapped[List["SplitBillItemAssignment"]] = relationship(
        "SplitBillItemAssignment", back_populates="participant", cascade="all, delete-orphan"
    )


class SplitBillItemAssignment(Base):
    __tablename__ = "split_bill_item_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    split_bill_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("split_bill_items.id"), nullable=False)
    participant_id: Mapped[int] = mapped_column(Integer, ForeignKey("split_bill_participants.id"), nullable=False)
    share_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # e.g., 1.0 = 100% of item cost, 0.5 = half

    split_bill_item: Mapped["SplitBillItem"] = relationship("SplitBillItem", back_populates="assignments")
    participant: Mapped["SplitBillParticipant"] = relationship("SplitBillParticipant", back_populates="assignments")
