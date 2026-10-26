from django.contrib import admin
from .models import Category, Order, OrderItem, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2
    fields = ('image', 'image_url', 'alt_text', 'position')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'original_price', 'offer_percent', 'stock', 'stock_message', 'is_available')
    list_filter = ('category', 'is_featured', 'is_available')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'original_price', 'stock', 'is_available')
    inlines = [ProductImageInline]

    @admin.display(description='Offer')
    def offer_percent(self, obj):
        return f'{obj.offer_percent}% off' if obj.offer_percent else '—'

    @admin.display(description='Stock status')
    def stock_message(self, obj):
        return obj.stock_message or 'In stock'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'email', 'phone')
    inlines = (OrderItemInline,)
