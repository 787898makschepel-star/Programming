import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .connection import Base


class ProductType(str, enum.Enum):
    DIGITAL_ITEM = "digital_item"  # Построчный цифровой товар (аккаунты, ключи)
    FILE = "file"                  # Неизменяемый файл (архив, мануал, прошивка)
    SERVICE = "service"            # Услуга / ручная выдача администратором


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    city: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    district: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    referrer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    referral_earnings: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    used_promos: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    referrer: Mapped[Optional["User"]] = relationship("User", remote_side=[id], back_populates="referrals")
    referrals: Mapped[List["User"]] = relationship("User", back_populates="referrer")

    def __repr__(self) -> str:
        return f"<User tg_id={self.tg_id} username={self.username} balance={self.balance}>"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subcategories: Mapped[List["Category"]] = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    parent: Mapped[Optional["Category"]] = relationship("Category", back_populates="subcategories", remote_side=[id])
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name='{self.name}' parent_id={self.parent_id}>"

class ShowcaseProduct(Base):
    """Товар витрины с карточкой из клиентского каталога."""
    __tablename__ = "showcase_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(8), default="шт.", nullable=False)
    start_quantity: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    image_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    category: Mapped[Optional["Category"]] = relationship("Category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    product_type: Mapped[ProductType] = mapped_column(
        Enum(ProductType, native_enum=False),
        default=ProductType.DIGITAL_ITEM,
        nullable=False
    )
    file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    items: Mapped[List["ProductItem"]] = relationship("ProductItem", back_populates="product", cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} title='{self.title}' price={self.price}>"


class ProductItem(Base):
    """
    Склад единиц цифрового товара (ключи, строки вида login:password, ссылки).
    Выдаются атомарно при каждой покупке.
    """
    __tablename__ = "product_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="items")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="items")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), default="balance")
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False),
        default=OrderStatus.COMPLETED,
        nullable=False
    )
    delivered_data: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="orders")
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    items: Mapped[List["ProductItem"]] = relationship("ProductItem", back_populates="order")
    referral_reward: Mapped[Optional["ReferralReward"]] = relationship("ReferralReward", back_populates="order", uselist=False, cascade="all, delete-orphan")


class ReferralReward(Base):
    """Однократное вознаграждение рефереру за заказ."""
    __tablename__ = "referral_rewards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    referrer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship("Order", back_populates="referral_reward")
    referrer: Mapped["User"] = relationship("User", foreign_keys=[referrer_id])


class Transaction(Base):
    """История пополнений баланса."""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_system: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False),
        default=PaymentStatus.PENDING,
        nullable=False
    )
    invoice_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="transactions")
