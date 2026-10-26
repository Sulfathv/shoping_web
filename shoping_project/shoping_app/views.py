from decimal import Decimal
from datetime import date
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Sum, F
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseNotAllowed

from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .models import BusinessExpense, Category, Order, OrderItem, Product, ProductImage


@staff_member_required
def admin_dashboard(request):
    products = Product.objects.all()
    total_products = products.count()
    total_stock = products.aggregate(total=Sum('stock'))['total'] or 0
    in_stock = sum(1 for p in products if p.stock > p.low_stock_threshold)
    low_stock = sum(1 for p in products if 0 < p.stock <= p.low_stock_threshold)
    out_stock = sum(1 for p in products if p.stock == 0)
    delivered = Order.objects.filter(status=Order.Status.DELIVERED)
    revenue = Decimal('0.00')
    cogs = Decimal('0.00')
    for order in delivered.prefetch_related('items'):
        for item in order.items.all():
            revenue += item.unit_price * item.quantity
            cogs += item.unit_cost * item.quantity
    expenses = BusinessExpense.objects.all()
    expense_total = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    today = timezone.localdate()
    report = request.GET.get('period', 'month')
    days = {'day': 1, 'week': 7, 'month': 30}.get(report, 30)
    since = today - timedelta(days=days - 1)
    sales_by_day = []
    for offset in range(days):
        day = since + timedelta(days=offset)
        amount = Decimal('0.00')
        for order in delivered.filter(created_at__date=day).prefetch_related('items'):
            amount += sum((item.unit_price * item.quantity for item in order.items.all()), Decimal('0.00'))
        sales_by_day.append({'label': day.strftime('%d %b'), 'amount': amount})
    return render(request, 'shoping_app/admin/dashboard.html', {
        'total_products': total_products, 'total_stock': total_stock, 'in_stock': in_stock,
        'low_stock': low_stock, 'out_stock': out_stock, 'revenue': revenue, 'cogs': cogs,
        'gross_profit': revenue - cogs, 'expenses_total': expense_total,
        'net_profit': revenue - cogs - expense_total, 'sales_by_day': sales_by_day, 'period': report,
        'recent_orders': Order.objects.all()[:5], 'low_products': products.filter(stock__gt=0, stock__lte=F('low_stock_threshold'))[:5],
    })


@staff_member_required
def admin_products(request):
    if request.method == 'POST':
        action = request.POST.get('offer_action')
        if action in {'selected', 'all', 'clear'}:
            products = Product.objects.all() if action == 'all' else Product.objects.filter(pk__in=request.POST.getlist('product_ids'))
            if not products.exists():
                messages.error(request, 'Select at least one product first.')
                return redirect('admin_products')
            if action == 'clear':
                products.update(sale_price=None, offer_name='', offer_starts_at=None, offer_ends_at=None)
                messages.success(request, 'Offers cleared from the selected products.')
                return redirect('admin_products')
            try:
                percent = int(request.POST.get('offer_percent', ''))
                name = request.POST.get('offer_name', '').strip()
                starts_at = date.fromisoformat(request.POST.get('offer_starts_at', ''))
                ends_at = date.fromisoformat(request.POST.get('offer_ends_at', ''))
                if not 1 <= percent <= 99 or not name or ends_at < starts_at:
                    raise ValueError
            except (TypeError, ValueError):
                messages.error(request, 'Enter an offer name, a percentage from 1 to 99, and a valid start and end date.')
                return redirect('admin_products')
            with transaction.atomic():
                for product in products:
                    product.sale_price = (product.price * Decimal(100 - percent) / Decimal(100)).quantize(Decimal('0.01'))
                    product.offer_name, product.offer_starts_at, product.offer_ends_at = name, starts_at, ends_at
                    product.save(update_fields=['sale_price', 'offer_name', 'offer_starts_at', 'offer_ends_at'])
            messages.success(request, f'{name} ({percent}% off) applied to {products.count()} products.')
            return redirect('admin_products')
    products = Product.objects.select_related('category').prefetch_related('gallery_images')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', 'name')
    if q: products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if status == 'out': products = products.filter(stock=0)
    elif status == 'low': products = products.filter(stock__gt=0, stock__lte=F('low_stock_threshold'))
    elif status == 'in': products = products.filter(stock__gt=F('low_stock_threshold'))
    if sort in {'name', '-name', 'price', '-price', 'stock', '-stock'}: products = products.order_by(sort)
    return render(request, 'shoping_app/admin/products.html', {'page_obj': Paginator(products, 10).get_page(request.GET.get('page')), 'q': q, 'status': status, 'sort': sort})


@staff_member_required
def admin_product_form(request, product_id=None):
    product = get_object_or_404(Product, pk=product_id) if product_id else None
    if request.method == 'POST':
        data = request.POST
        name = data.get('name', '').strip()
        desc = data.get('description', '').strip()
        try:
            category = Category.objects.get(pk=int(data.get('category', '')))
            price = Decimal(data.get('price', ''))
            cost = Decimal(data.get('original_price', ''))
            offer_percent = int(data.get('offer_percent') or 0)
            if not 0 <= offer_percent <= 99: raise ValueError
            sale_price = (price * Decimal(100 - offer_percent) / Decimal(100)).quantize(Decimal('0.01')) if offer_percent else None
            offer_name = data.get('offer_name', '').strip() if offer_percent else ''
            starts_at = date.fromisoformat(data.get('offer_starts_at', '')) if offer_percent else None
            ends_at = date.fromisoformat(data.get('offer_ends_at', '')) if offer_percent else None
            if offer_percent and (not offer_name or not starts_at or not ends_at or ends_at < starts_at): raise ValueError
            threshold = int(data.get('low_stock_threshold', 4))
            if not name or not desc or price <= 0 or cost < 0 or threshold < 0 or (sale_price is not None and (sale_price <= 0 or sale_price > price)):
                raise ValueError
            sizes = [s for s in data.getlist('sizes') if s in {'S','L','XL','XXL','3XL'}]
            if not sizes: raise ValueError
            stocks = {s: int(data.get(f'stock_{s}', '0')) for s in sizes}
            if any(v < 0 for v in stocks.values()): raise ValueError
        except (Category.DoesNotExist, ValueError, TypeError, ArithmeticError):
            messages.error(request, 'Check the product details, prices, category, sizes, and stock quantities.')
            return redirect(request.path)
        product = product or Product()
        product.name, product.description, product.category = name, desc, category
        product.slug = slugify(name)[:45] or 'dress'
        if Product.objects.exclude(pk=product.pk).filter(slug=product.slug).exists(): product.slug = f'{product.slug}-{product.pk or "new"}'
        product.price, product.original_price, product.sale_price = price, cost, sale_price
        product.offer_name, product.offer_starts_at, product.offer_ends_at = offer_name, starts_at, ends_at
        product.sizes, product.size_stock = sizes, stocks
        product.stock = sum(stocks.values())
        product.low_stock_threshold = threshold
        product.is_available = data.get('is_available') == 'on'
        product.is_featured = data.get('is_featured') == 'on'
        if request.FILES.get('image'):
            try: get_image_dimensions(request.FILES['image'])
            except Exception:
                messages.error(request, 'The main upload must be a valid image.')
                return redirect(request.path)
            product.image = request.FILES['image']
        product.save()
        remove_ids = data.getlist('remove_images')
        if remove_ids: ProductImage.objects.filter(product=product, pk__in=remove_ids).delete()
        for image in request.FILES.getlist('images'):
            try: get_image_dimensions(image)
            except Exception: continue
            ProductImage.objects.create(product=product, image=image, alt_text=product.name, position=product.gallery_images.count())
        messages.success(request, 'Product saved.')
        return redirect('admin_products')
    return render(request, 'shoping_app/admin/product_form.html', {'product': product, 'categories': Category.objects.all(), 'sizes': ['S','L','XL','XXL','3XL']})


@staff_member_required
def admin_product_delete(request, product_id):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    try:
        get_object_or_404(Product, pk=product_id).delete()
        messages.success(request, 'Product deleted.')
    except ProtectedError:
        messages.error(request, 'This product belongs to an order and cannot be deleted. You can mark it unavailable instead.')
    return redirect('admin_products')


@staff_member_required
def admin_inventory(request):
    if request.method == 'POST':
        for product in Product.objects.all():
            threshold = request.POST.get(f'threshold_{product.pk}')
            if threshold is not None and threshold.isdigit(): product.low_stock_threshold = int(threshold)
            stocks = product.size_stock or {}
            for size in product.sizes or []:
                raw = request.POST.get(f'stock_{product.pk}_{size}')
                if raw is not None and raw.isdigit(): stocks[size] = int(raw)
            product.size_stock, product.stock = stocks, sum(stocks.values()) if stocks else product.stock
            product.save(update_fields=['size_stock','stock','low_stock_threshold'])
        return redirect('admin_inventory')
    return render(request, 'shoping_app/admin/inventory.html', {'products': Product.objects.all().order_by('stock')})


@staff_member_required
def admin_orders(request):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=request.POST.get('order_id'))
        new_status = request.POST.get('status')
        if new_status in Order.Status.values and order.status != Order.Status.CANCELLED:
            if new_status == Order.Status.CANCELLED and order.status != Order.Status.CANCELLED:
                for item in order.items.select_related('product'):
                    product = item.product
                    product.stock += item.quantity
                    product.save(update_fields=['stock'])
            order.status = new_status
            order.save(update_fields=['status'])
        return redirect('admin_orders')
    return render(request, 'shoping_app/admin/orders.html', {'orders': Order.objects.prefetch_related('items').all()})


@staff_member_required
def admin_expenses(request):
    if request.method == 'POST':
        expense_id = request.POST.get('expense_id')
        if request.POST.get('action') == 'delete':
            get_object_or_404(BusinessExpense, pk=expense_id).delete()
        else:
            try:
                amount = Decimal(request.POST.get('amount', ''))
                if amount <= 0: raise ValueError
                defaults = {
                    'name': request.POST.get('name','').strip(), 'category': request.POST.get('category','Other'),
                    'amount': amount, 'date': request.POST.get('date'), 'description': request.POST.get('description','').strip()}
                if not defaults['name'] or not defaults['date']:
                    raise ValueError
                if expense_id:
                    BusinessExpense.objects.filter(pk=expense_id).update(**defaults)
                else:
                    BusinessExpense.objects.create(**defaults)
            except Exception:
                messages.error(request, 'Enter a valid expense name, amount, and date.')
        return redirect('admin_expenses')
    entries = BusinessExpense.objects.all()
    editing = get_object_or_404(BusinessExpense, pk=request.GET.get('edit')) if request.GET.get('edit') else None
    start, end = request.GET.get('start'), request.GET.get('end')
    if start: entries = entries.filter(date__gte=start)
    if end: entries = entries.filter(date__lte=end)
    return render(request, 'shoping_app/admin/expenses.html', {'expenses': entries, 'expense_total': entries.aggregate(total=Sum('amount'))['total'] or 0, 'today': timezone.localdate(), 'editing': editing})


@staff_member_required
def admin_settings(request):
    if request.method == 'POST':
        threshold = request.POST.get('low_stock_threshold', '')
        if threshold.isdigit():
            Product.objects.all().update(low_stock_threshold=int(threshold))
            messages.success(request, 'Low stock threshold updated for all products.')
        else: messages.error(request, 'Enter a whole number of zero or greater.')
    threshold = Product.objects.values_list('low_stock_threshold', flat=True).first()
    return render(request, 'shoping_app/admin/settings.html', {'threshold': 4 if threshold is None else threshold})


def home(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True).select_related('category')
    category = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()
    if category:
        products = products.filter(category__slug=category)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'shoping_app/home.html', {
        'categories': categories,
        'products': products,
        'selected_category': category,
        'query': query,
        'cart_count': sum(request.session.get('cart', {}).values()),
        'favorites': request.session.get('favorites', []),
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category').prefetch_related('gallery_images'), slug=slug, is_available=True)
    gallery_images = [{'photo': product.photo, 'alt_text': product.name}] if product.photo else []
    gallery_images.extend(image for image in product.gallery_images.all() if image.photo)
    return render(request, 'shoping_app/product_detail.html', {
        'product': product,
        'similar_products': Product.objects.filter(category=product.category, is_available=True).exclude(pk=product.pk).select_related('category')[:4],
        'gallery_images': gallery_images,
        'is_favorite': str(product.pk) in request.session.get('favorites', []),
        'favorites': request.session.get('favorites', []),
        'cart_count': sum(request.session.get('cart', {}).values()),
    })


def favorites(request):
    favorites_ids = request.session.get('favorites', [])
    products_by_id = {
        str(product.pk): product
        for product in Product.objects.filter(pk__in=favorites_ids, is_available=True).select_related('category')
    }
    products = [products_by_id[product_id] for product_id in favorites_ids if product_id in products_by_id]
    return render(request, 'shoping_app/favorites.html', {
        'products': products,
        'favorites': favorites_ids,
        'cart_count': sum(request.session.get('cart', {}).values()),
    })


def next_page(request, fallback='home'):
    candidate = request.POST.get('next', '')
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}):
        return redirect(candidate)
    return redirect(fallback)


def add_to_cart(request, product_id):
    if request.method != 'POST':
        return redirect('home')
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    if product.stock < 1:
        messages.error(request, 'This lovely piece is sold out for now.')
        return next_page(request)
    cart = request.session.get('cart', {})
    key = str(product.pk)
    cart[key] = min(int(cart.get(key, 0)) + 1, product.stock, 20)
    request.session['cart'] = cart
    messages.success(request, f'{product.name} added to your bag.')
    return next_page(request)


def toggle_favorite(request, product_id):
    if request.method != 'POST':
        return redirect('home')
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    favorites = request.session.get('favorites', [])
    key = str(product.pk)
    if key in favorites:
        favorites.remove(key)
        messages.info(request, f'{product.name} removed from your favourites.')
    else:
        favorites.append(key)
        messages.success(request, f'{product.name} saved to your favourites.')
    request.session['favorites'] = favorites
    return next_page(request)


def buy_now(request, product_id):
    if request.method != 'POST':
        return redirect('home')
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    if product.stock < 1:
        messages.error(request, 'This lovely piece is sold out for now.')
        return next_page(request)
    request.session['cart'] = {str(product.pk): 1}
    return redirect('checkout')


def update_cart(request, product_id):
    if request.method != 'POST':
        return redirect('cart')
    product = get_object_or_404(Product, pk=product_id)
    cart_data = request.session.get('cart', {})
    key = str(product.pk)
    action = request.POST.get('action')
    quantity = int(cart_data.get(key, 0))
    if action == 'remove' or quantity <= 1 and action == 'decrease':
        cart_data.pop(key, None)
    elif action == 'decrease':
        cart_data[key] = quantity - 1
    elif action == 'increase':
        if quantity >= product.stock:
            messages.info(request, f'Only {product.stock} available right now.')
        else:
            cart_data[key] = min(quantity + 1, 20)
    request.session['cart'] = cart_data
    return redirect('cart')


def cart(request):
    cart_data = request.session.get('cart', {})
    items = []
    total = Decimal('0.00')
    can_checkout = True
    for product in Product.objects.filter(pk__in=cart_data.keys(), is_available=True):
        quantity = int(cart_data.get(str(product.pk), 0))
        if quantity > product.stock:
            can_checkout = False
        line_total = product.display_price * quantity
        items.append({'product': product, 'quantity': quantity, 'line_total': line_total})
        total += line_total
    return render(request, 'shoping_app/cart.html', {'items': items, 'total': total, 'can_checkout': can_checkout, 'cart_count': sum(cart_data.values())})


@transaction.atomic
def checkout(request):
    cart_data = request.session.get('cart', {})
    products = list(Product.objects.filter(pk__in=cart_data.keys(), is_available=True))
    if not products:
        messages.info(request, 'Your bag is empty. Find something lovely in the collection.')
        return redirect('home')
    total = sum((product.display_price * int(cart_data.get(str(product.pk), 0)) for product in products), Decimal('0.00'))
    if request.method == 'POST':
        if any(int(cart_data.get(str(product.pk), 0)) > product.stock for product in products):
            messages.error(request, 'Some items in your bag are no longer available in that quantity. Please review your bag.')
            return redirect('cart')
        required_fields = ('name', 'email', 'phone', 'address', 'city', 'postal_code')
        form_values = {field: request.POST.get(field, '').strip() for field in required_fields}
        if any(not value for value in form_values.values()):
            messages.error(request, 'Please fill in all your delivery details.')
            return redirect('checkout')
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(form_values['email'])
        except ValidationError:
            messages.error(request, 'Please enter a valid email address.')
            return redirect('checkout')
        order = Order.objects.create(
            customer_name=form_values['name'], email=form_values['email'], phone=form_values['phone'],
            address=form_values['address'], city=form_values['city'], postal_code=form_values['postal_code'], total=total,
        )
        for product in products:
            quantity = int(cart_data.get(str(product.pk), 0))
            OrderItem.objects.create(order=order, product=product, quantity=quantity, unit_price=product.display_price, unit_cost=product.original_price or Decimal('0.00'))
            product.stock -= quantity
            product.save(update_fields=['stock'])
        request.session['cart'] = {}
        return render(request, 'shoping_app/success.html', {'order': order})
    checkout_items = [{'product': product, 'quantity': int(cart_data.get(str(product.pk), 0)), 'line_total': product.display_price * int(cart_data.get(str(product.pk), 0))} for product in products]
    return render(request, 'shoping_app/checkout.html', {'checkout_items': checkout_items, 'total': total, 'cart_count': sum(cart_data.values())})

