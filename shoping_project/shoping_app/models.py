from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=140)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=9, decimal_places=2)
    original_price = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    sale_price = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    offer_name = models.CharField(max_length=100, blank=True)
    offer_starts_at = models.DateField(blank=True, null=True)
    offer_ends_at = models.DateField(blank=True, null=True)
    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True)
    is_featured = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=10)
    low_stock_threshold = models.PositiveIntegerField(default=4)
    sizes = models.JSONField(default=list, blank=True)
    size_stock = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return self.name

    @property
    def photo(self):
        return self.image.url if self.image else self.image_url

    @property
    def stock_message(self):
        if self.stock <= 0:
            return 'Sold out'
        if self.stock <= self.low_stock_threshold:
            return f'Only {self.stock} left' if self.stock > 1 else 'Only 1 left'
        return ''

    @property
    def offer_percent(self):
        if self.has_active_offer:
            return round((self.price - self.sale_price) * 100 / self.price)
        if self.original_price and self.original_price > self.price:
            return round((self.original_price - self.price) * 100 / self.original_price)
        return 0

    @property
    def display_price(self):
        return self.sale_price if self.has_active_offer else self.price

    @property
    def offer_reference_price(self):
        return self.price if self.has_active_offer else self.original_price

    @property
    def configured_offer_percent(self):
        if self.sale_price and self.price > self.sale_price:
            return round((self.price - self.sale_price) * 100 / self.price)
        return 0

    @property
    def has_active_offer(self):
        if not self.sale_price or self.price <= self.sale_price:
            return False
        today = timezone.localdate()
        return ((self.offer_starts_at is None or self.offer_starts_at <= today)
                and (self.offer_ends_at is None or self.offer_ends_at >= today))


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='products/gallery/', blank=True)
    image_url = models.URLField(blank=True)
    alt_text = models.CharField(max_length=180, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.product.name} photo {self.position + 1}'

    @property
    def photo(self):
        return self.image.url if self.image else self.image_url


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        CONFIRMED = 'confirmed', 'Confirmed'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=12)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} · {self.customer_name}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=9, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.product.name} × {self.quantity}'


class BusinessExpense(models.Model):
    name = models.CharField(max_length=140)
    category = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.name} · {self.amount}'

