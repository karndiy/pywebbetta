from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from sqlalchemy import event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


db = SQLAlchemy()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), default=func.now(), onupdate=func.now()
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None]
    email: Mapped[str] = mapped_column(db.String(255), unique=True, index=True)
    phone: Mapped[str | None]
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="customer")

    addresses: Mapped[list[Address]] = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    carts: Mapped[list[Cart]] = relationship("Cart", back_populates="user")
    orders: Mapped[list[Order]] = relationship("Order", back_populates="user")

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_shipper(self) -> bool:
        return self.role == "shipper"


class Address(TimestampMixin, db.Model):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id", ondelete="CASCADE"))
    country: Mapped[str | None]
    province: Mapped[str | None]
    district: Mapped[str | None]
    postal_code: Mapped[str | None]
    line1: Mapped[str | None]
    line2: Mapped[str | None]
    is_default: Mapped[bool] = mapped_column(default=False)

    user: Mapped[User] = relationship("User", back_populates="addresses")


class Media(TimestampMixin, db.Model):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str]
    kind: Mapped[str] = mapped_column(db.CheckConstraint("kind IN ('image','video')"))
    alt_text: Mapped[str | None]
    width: Mapped[int | None]
    height: Mapped[int | None]
    duration: Mapped[float | None]

    products: Mapped[list[ProductMedia]] = relationship("ProductMedia", back_populates="media", cascade="all, delete-orphan")


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(unique=True, index=True)
    title_th: Mapped[str | None]
    title_en: Mapped[str | None]
    desc_th: Mapped[str | None]
    desc_en: Mapped[str | None]
    category: Mapped[str | None]
    is_unique: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(default="active")

    variants: Mapped[list[Variant]] = relationship("Variant", back_populates="product", cascade="all, delete-orphan")
    media: Mapped[list[ProductMedia]] = relationship("ProductMedia", back_populates="product", cascade="all, delete-orphan", order_by="ProductMedia.sort_order")
    tags: Mapped[list[ProductTag]] = relationship("ProductTag", back_populates="product", cascade="all, delete-orphan")

    def primary_variant(self) -> Variant | None:
        return self.variants[0] if self.variants else None

    def localized_title(self, locale: str) -> str:
        if locale == "en" and self.title_en:
            return self.title_en
        if locale == "th" and self.title_th:
            return self.title_th
        return self.title_en or self.title_th or self.sku


class Variant(TimestampMixin, db.Model):
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(db.ForeignKey("products.id", ondelete="CASCADE"))
    price: Mapped[float] = mapped_column(default=0)
    compare_at_price: Mapped[float | None]
    stock_qty: Mapped[int] = mapped_column(default=1)
    weight_grams: Mapped[int | None]
    attributes_json: Mapped[str | None]

    product: Mapped[Product] = relationship("Product", back_populates="variants")
    order_items: Mapped[list[OrderItem]] = relationship("OrderItem", back_populates="variant")

    @property
    def attributes(self) -> dict[str, Any]:
        if not self.attributes_json:
            return {}
        try:
            return json.loads(self.attributes_json)
        except json.JSONDecodeError:
            return {}

    @attributes.setter
    def attributes(self, value: dict[str, Any]) -> None:
        self.attributes_json = json.dumps(value, ensure_ascii=False)

    def is_available(self) -> bool:
        return self.stock_qty > 0


class ProductMedia(db.Model):
    __tablename__ = "product_media"

    product_id: Mapped[int] = mapped_column(db.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    media_id: Mapped[int] = mapped_column(db.ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    product: Mapped[Product] = relationship("Product", back_populates="media")
    media: Mapped[Media] = relationship("Media", back_populates="products")


class Tag(TimestampMixin, db.Model):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)

    products: Mapped[list[ProductTag]] = relationship("ProductTag", back_populates="tag", cascade="all, delete-orphan")


class ProductTag(db.Model):
    __tablename__ = "product_tags"

    product_id: Mapped[int] = mapped_column(db.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    product: Mapped[Product] = relationship("Product", back_populates="tags")
    tag: Mapped[Tag] = relationship("Tag", back_populates="products")


class Cart(TimestampMixin, db.Model):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id"))
    session_id: Mapped[str | None]

    user: Mapped[User | None] = relationship("User", back_populates="carts")
    items: Mapped[list[CartItem]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    def total(self) -> float:
        return sum(item.total_price for item in self.items)


class CartItem(TimestampMixin, db.Model):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(db.ForeignKey("carts.id", ondelete="CASCADE"))
    variant_id: Mapped[int] = mapped_column(db.ForeignKey("variants.id"))
    qty: Mapped[int] = mapped_column(default=1)
    price_at: Mapped[float]

    cart: Mapped[Cart] = relationship("Cart", back_populates="items")
    variant: Mapped[Variant] = relationship("Variant")

    @property
    def total_price(self) -> float:
        return self.price_at * self.qty


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id"))
    order_no: Mapped[str] = mapped_column(unique=True, index=True)
    status: Mapped[str] = mapped_column(default="pending")
    payment_method: Mapped[str | None]
    subtotal: Mapped[float] = mapped_column(default=0)
    shipping_fee: Mapped[float] = mapped_column(default=0)
    discount: Mapped[float] = mapped_column(default=0)
    grand_total: Mapped[float] = mapped_column(default=0)
    currency: Mapped[str] = mapped_column(default="THB")

    user: Mapped[User | None] = relationship("User", back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    shipment: Mapped[Shipment | None] = relationship("Shipment", back_populates="order", uselist=False, cascade="all, delete-orphan")

    def update_totals(self) -> None:
        self.subtotal = sum(item.total_price for item in self.items)
        self.grand_total = self.subtotal + (self.shipping_fee or 0) - (self.discount or 0)


class OrderItem(TimestampMixin, db.Model):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(db.ForeignKey("orders.id", ondelete="CASCADE"))
    variant_id: Mapped[int] = mapped_column(db.ForeignKey("variants.id"))
    title_snapshot: Mapped[str | None]
    attrs_snapshot: Mapped[str | None]
    qty: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float]
    total_price: Mapped[float]

    order: Mapped[Order] = relationship("Order", back_populates="items")
    variant: Mapped[Variant] = relationship("Variant", back_populates="order_items")


class Payment(TimestampMixin, db.Model):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(db.ForeignKey("orders.id", ondelete="CASCADE"))
    method: Mapped[str]
    ref: Mapped[str | None]
    amount: Mapped[float] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="init")
    paid_at: Mapped[datetime | None]
    slip_url: Mapped[str | None]

    order: Mapped[Order] = relationship("Order", back_populates="payments")


class Shipment(TimestampMixin, db.Model):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(db.ForeignKey("orders.id", ondelete="CASCADE"))
    carrier: Mapped[str | None]
    tracking_no: Mapped[str | None]
    label_url: Mapped[str | None]
    status: Mapped[str | None]
    shipped_at: Mapped[datetime | None]
    received_at: Mapped[datetime | None]

    order: Mapped[Order] = relationship("Order", back_populates="shipment")


class Coupon(TimestampMixin, db.Model):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    type: Mapped[str]
    value: Mapped[float] = mapped_column(default=0)
    min_subtotal: Mapped[float | None]
    max_uses: Mapped[int | None]
    used_count: Mapped[int] = mapped_column(default=0)
    start_at: Mapped[datetime | None]
    end_at: Mapped[datetime | None]
    is_active: Mapped[bool] = mapped_column(default=True)

    def is_valid(self, subtotal: float, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        if not self.is_active:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        if self.min_subtotal and subtotal < self.min_subtotal:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True

    def discount_amount(self, subtotal: float) -> float:
        if self.type == "percent":
            return subtotal * (self.value / 100)
        return min(self.value, subtotal)




class BlogPost(TimestampMixin, db.Model):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    slug: Mapped[str] = mapped_column(db.String(255), unique=True, index=True, nullable=False)
    content: Mapped[str] = mapped_column(db.Text, nullable=False)
    hero_image: Mapped[str | None]
    published_at: Mapped[datetime | None]
    is_published: Mapped[bool] = mapped_column(default=False)

    def publish(self) -> None:
        if not self.published_at:
            self.published_at = datetime.utcnow()
        self.is_published = True


class Setting(TimestampMixin, db.Model):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str | None]


def init_db() -> None:
    db.create_all()
    ensure_default_admin()



def ensure_default_admin() -> None:
    email = "karndiy@gmail.com"
    if User.query.filter_by(email=email).first():
        return
    admin = User(
        name="Default Admin",
        email=email,
        role="admin",
        password_hash=generate_password_hash("admin123"),
    )
    db.session.add(admin)
    db.session.commit()

def register_cli_commands(app):
    @app.cli.command("create-admin")
    def create_admin():
        """Create an admin user interactively."""
        import getpass
        from werkzeug.security import generate_password_hash

        email = input("Admin email: ")
        if User.query.filter_by(email=email).first():
            print("Admin already exists")
            return
        name = input("Name: ")
        phone = input("Phone: ")
        password = getpass.getpass("Password: ")
        admin = User(
            name=name,
            email=email,
            phone=phone,
            role="admin",
            password_hash=generate_password_hash(password),
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin created")

    @app.cli.command("seed-sample")
    def seed_sample():
        """Populate the database with sample betta fish products."""
        from werkzeug.security import generate_password_hash
        from slugify import slugify
        from random import choice, randint, uniform

        if User.query.count() == 0:
            demo_admin = User(
                name="Demo Admin",
                email="admin@bettashop.test",
                role="admin",
                password_hash=generate_password_hash("changeme"),
            )
            db.session.add(demo_admin)

        Media.query.delete()
        Product.query.delete()
        Variant.query.delete()
        Tag.query.delete()
        ProductTag.query.delete()

        tail_types = ["HM", "CT", "PK", "HMPK"]
        color_patterns = ["Koi", "Galaxy", "Nemo", "Copper", "Samurai"]
        grades = ["Show", "Breeder", "Pet"]
        sexes = ["M", "F"]

        base_media = []
        for idx in range(1, 6):
            media = Media(
                url=f"/static/uploads/sample_{idx}.jpg",
                kind="image",
                alt_text=f"Sample betta fish {idx}",
                width=1024,
                height=768,
            )
            db.session.add(media)
            base_media.append(media)

        db.session.flush()

        for i in range(1, 11):
            tail = choice(tail_types)
            color = choice(color_patterns)
            grade = choice(grades)
            sex = choice(sexes)
            sku = f"BETTA-{datetime.utcnow().strftime('%Y%m%d')}-{i:02d}"
            product = Product(
                sku=sku,
                title_th=f"ปลากัด {color} {tail} #{i:02d}",
                title_en=f"{color} {tail} Betta #{i:02d}",
                desc_th="ปลากัดสายประกวดสุขภาพดี พร้อมตู้ใหม่",
                desc_en="Show grade betta fish ready for shipping.",
                category="unique",
                is_unique=True,
            )
            variant = Variant(
                product=product,
                price=round(uniform(800, 2500), 2),
                stock_qty=1,
            )
            variant.attributes = {
                "tail": tail,
                "color": color,
                "sex": sex,
                "age_months": randint(4, 8),
                "grade": grade,
                "health": "Excellent",
                "lineage": {
                    "sire": f"Sire {color} {tail}",
                    "dam": f"Dam {color} {tail}",
                },
            }

            db.session.add(product)
            db.session.add(variant)

            for index, media in enumerate(base_media[:3]):
                db.session.add(
                    ProductMedia(
                        product=product,
                        media=media,
                        sort_order=index,
                    )
                )

            for label in (tail, color, grade):
                slug = slugify(label)
                tag = Tag.query.filter_by(slug=slug).one_or_none()
                if not tag:
                    tag = Tag(name=label, slug=slug)
                    db.session.add(tag)
                    db.session.flush()
                db.session.add(ProductTag(product=product, tag=tag))

        db.session.commit()
        print("Seed data inserted")


@event.listens_for(OrderItem, "after_insert")
def reduce_stock(mapper, connection, target):
    variant_table = Variant.__table__
    if target.qty:
        connection.execute(
            variant_table.update()
            .where(variant_table.c.id == target.variant_id)
            .values(stock_qty=variant_table.c.stock_qty - target.qty)
        )


@event.listens_for(OrderItem, "after_delete")
def restore_stock(mapper, connection, target):
    variant_table = Variant.__table__
    if target.qty:
        connection.execute(
            variant_table.update()
            .where(variant_table.c.id == target.variant_id)
            .values(stock_qty=variant_table.c.stock_qty + target.qty)
        )











