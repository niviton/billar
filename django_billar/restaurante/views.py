from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal, InvalidOperation
import json
import socket

from .models import User, Category, Product, Order, OrderItem, AppSettings, Ingredient, ProductIngredient
from .forms import (
    LoginForm, UserForm, CategoryForm, ProductForm, 
    OrderForm, DeliveryOrderForm, PaymentForm, AppSettingsForm, IngredientForm
)


def enrich_delivery_order_display(order):
    """Extrai plataforma de delivery das observações para exibição em badge."""
    order.platform_name = ''
    order.display_observacoes = order.observacoes

    if order.order_type != 'delivery' or not order.observacoes:
        return

    prefix = 'Plataforma:'
    raw_observacoes = order.observacoes.strip()
    if not raw_observacoes.startswith(prefix):
        return

    after_prefix = raw_observacoes[len(prefix):].strip()
    if '|' in after_prefix:
        platform, remaining_obs = after_prefix.split('|', 1)
        order.platform_name = platform.strip()
        order.display_observacoes = remaining_obs.strip()
    else:
        order.platform_name = after_prefix.strip()
        order.display_observacoes = ''


def cart_qty_for_product(cart, product_id):
    for item in cart:
        if item['id'] == product_id:
            return item['qty']
    return 0


def validate_cart_ingredient_stock(cart):
    products = Product.objects.filter(id__in=[item['id'] for item in cart]).prefetch_related('recipe_items__ingredient')
    products_by_id = {product.id: product for product in products}

    for cart_item in cart:
        product = products_by_id.get(cart_item['id'])
        if not product:
            return f"Produto inválido no carrinho: ID {cart_item['id']}"
        if not product.can_make(cart_item['qty']):
            return f'Estoque insuficiente para {product.name}.'
    return None


def save_product_recipe_from_request(product, request):
    if not product.use_ingredient_stock:
        return 0

    ingredient_ids = request.POST.getlist('recipe_ingredient[]')
    quantities = request.POST.getlist('recipe_quantity[]')

    ProductIngredient.objects.filter(product=product).delete()

    recipe_rows = []
    for ingredient_id, quantity_raw in zip(ingredient_ids, quantities):
        ingredient_id = str(ingredient_id).strip()
        quantity_raw = str(quantity_raw).strip()
        if not ingredient_id or not quantity_raw:
            continue

        try:
            quantity = Decimal(quantity_raw)
        except InvalidOperation:
            continue

        if quantity <= 0:
            continue

        recipe_rows.append((int(ingredient_id), quantity))

    if not recipe_rows:
        return 0

    ingredients_map = {
        ingredient.id: ingredient
        for ingredient in Ingredient.objects.filter(id__in=[row[0] for row in recipe_rows], is_active=True)
    }

    created_ingredient_ids = set()
    for ingredient_id, quantity in recipe_rows:
        if ingredient_id in created_ingredient_ids:
            continue
        ingredient = ingredients_map.get(ingredient_id)
        if not ingredient:
            continue
        ProductIngredient.objects.create(
            product=product,
            ingredient=ingredient,
            quantity=quantity,
        )
        created_ingredient_ids.add(ingredient_id)

    return len(created_ingredient_ids)


@never_cache
def login_view(request):
    """View de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuário ou senha incorretos')
    else:
        form = LoginForm()
    
    return render(request, 'restaurante/login.html', {'form': form})


def logout_view(request):
    """View de logout"""
    logout(request)
    messages.info(request, 'Você saiu do sistema.')
    return redirect('login')


@login_required
def dashboard(request):
    """Dashboard principal - redireciona baseado no role do usuário"""
    user = request.user
    if user.role == 'gerente':
        return redirect('admin_dashboard')
    elif user.role == 'cozinha':
        return redirect('kitchen_view')
    else:
        return redirect('waiter_view')


def redirect_order_entry(request):
    """Redireciona para a tela de criação de pedidos conforme o perfil."""
    if request.user.role == 'gerente':
        return redirect('admin_online_orders')
    return redirect('waiter_view')


# ============== GARÇOM VIEWS ==============

@login_required
def waiter_view(request):
    """View principal do garçom"""
    if request.user.role == 'cozinha':
        messages.error(request, 'Acesso não autorizado')
        return redirect('kitchen_view')

    categories = Category.objects.prefetch_related('products__recipe_items__ingredient').all()
    
    # Carrinho da sessão
    cart = request.session.get('cart', [])
    cart_total = sum(item['price'] * item['qty'] for item in cart)
    
    context = {
        'categories': categories,
        'cart': cart,
        'cart_total': cart_total,
    }
    return render(request, 'restaurante/waiter.html', context)


@login_required
def add_to_cart(request, product_id):
    """Adicionar produto ao carrinho"""
    product = get_object_or_404(Product, id=product_id)
    
    available_stock = product.available_stock
    if available_stock <= 0:
        messages.error(request, 'Produto sem estoque')
        return redirect_order_entry(request)
    
    cart = request.session.get('cart', [])
    
    # Verificar se já existe no carrinho
    for item in cart:
        if item['id'] == product_id:
            if item['qty'] >= available_stock:
                messages.error(request, 'Limite de estoque atingido')
                return redirect_order_entry(request)
            item['qty'] += 1
            request.session['cart'] = cart
            return redirect_order_entry(request)
    
    # Adicionar novo item
    cart.append({
        'id': product_id,
        'name': product.name,
        'price': float(product.price),
        'qty': 1,
        'icon': product.icon,
        'image': product.image.url if product.image else None,
    })
    request.session['cart'] = cart
    return redirect_order_entry(request)


@login_required
def remove_from_cart(request, product_id):
    """Remover produto do carrinho"""
    cart = request.session.get('cart', [])
    
    for item in cart:
        if item['id'] == product_id:
            if item['qty'] > 1:
                item['qty'] -= 1
            else:
                cart.remove(item)
            break
    
    request.session['cart'] = cart
    return redirect_order_entry(request)


@login_required
def clear_cart(request):
    """Limpar carrinho"""
    request.session['cart'] = []
    messages.info(request, 'Carrinho limpo')
    return redirect_order_entry(request)


@login_required
def submit_order(request):
    """Enviar pedido"""
    if request.method == 'POST':
        settings = AppSettings.get_settings()
        if not settings.is_store_open:
            messages.error(request, 'Loja fechada no momento. Aguarde o gerente abrir novamente.')
            return redirect_order_entry(request)

        cart = request.session.get('cart', [])
        
        if not cart:
            messages.error(request, '❌ O carrinho está vazio')
            return redirect_order_entry(request)
        
        mesa = request.POST.get('mesa', '').strip().upper()
        cliente = request.POST.get('cliente', '').strip() or 'Cliente'
        observacoes = request.POST.get('observacoes', '').strip()
        order_type = request.POST.get('order_type', 'dine-in')
        address = request.POST.get('address', '').strip()
        platform_note = ''
        
        if order_type == 'dine-in' and not mesa:
            messages.error(request, '❌ Informe o número da mesa')
            return redirect_order_entry(request)
        
        if order_type == 'delivery':
            mesa = 'DELIVERY'
            platform = request.POST.get('platform', 'Whatsapp')
            platform_note = f"Plataforma: {platform}"
            if not address:
                messages.error(request, '❌ Informe o endereço de entrega')
                return redirect_order_entry(request)

        if platform_note:
            observacoes = f"{platform_note} | {observacoes}" if observacoes else platform_note
        
        try:
            # Verificar se já existe pedido ativo para a mesa
            active_order = None
            if order_type == 'dine-in':
                active_order = Order.objects.filter(
                    mesa=mesa,
                    status__in=['cozinha', 'pronto']
                ).order_by('-updated_at', '-id').first()

            stock_error = validate_cart_ingredient_stock(cart)
            if stock_error:
                messages.error(request, f'❌ {stock_error}')
                return redirect_order_entry(request)

            product_ids = [item['id'] for item in cart]
            products_by_id = Product.objects.in_bulk(product_ids)
        
            with transaction.atomic():
                if active_order:
                # Adicionar itens ao pedido existente
                    existing_items = {
                        item.product_id: item
                        for item in active_order.items.select_related('product').all()
                    }

                    for cart_item in cart:
                        product = products_by_id.get(cart_item['id'])
                        if not product:
                            raise ValueError(f"Produto inválido: {cart_item['id']}")
                        existing_item = existing_items.get(product.id)

                        if existing_item:
                            existing_item.quantity += cart_item['qty']
                            existing_item.pending_quantity += cart_item['qty']
                            existing_item.save()
                        else:
                            OrderItem.objects.create(
                                order=active_order,
                                product=product,
                                quantity=cart_item['qty'],
                                pending_quantity=cart_item['qty'],
                                unit_price=product.price
                            )

                        product.consume_ingredients(cart_item['qty'])

                    active_order.status = 'cozinha'
                    if observacoes:
                        active_order.observacoes = (active_order.observacoes + " | " + observacoes) if active_order.observacoes else observacoes
                    active_order.calculate_total()
                    sync_order_kitchen_status(active_order)
                    messages.success(request, f'✅ Itens adicionados ao pedido da mesa {mesa}.')
                else:
                # Criar novo pedido
                    total = sum(item['price'] * item['qty'] for item in cart)
                    order = Order.objects.create(
                        mesa=mesa,
                        cliente=cliente,
                        observacoes=observacoes,
                        total=total,
                        status='cozinha',
                        order_type=order_type,
                        address=address,
                        waiter=request.user
                    )

                    for cart_item in cart:
                        product = products_by_id.get(cart_item['id'])
                        if not product:
                            raise ValueError(f"Produto inválido: {cart_item['id']}")
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=cart_item['qty'],
                            pending_quantity=cart_item['qty'],
                            unit_price=product.price
                        )
                        product.consume_ingredients(cart_item['qty'])

                    messages.success(request, f'✅ Pedido #{order.id} enviado para a cozinha!')
            
            # Limpar carrinho
            request.session['cart'] = []
            return redirect_order_entry(request)
        
        except Exception as e:
            messages.error(request, f'❌ Erro ao enviar pedido: {str(e)}')
            return redirect_order_entry(request)
    
    return redirect_order_entry(request)


def redirect_by_role(request):
    """Redireciona para a tela principal conforme função do usuário."""
    if request.user.role == 'gerente':
        return redirect('admin_dashboard')
    if request.user.role == 'cozinha':
        return redirect('kitchen_view')
    return redirect('waiter_view')


def can_manage_order(user):
    return user.role != 'cozinha'


def can_access_order(user, order):
    if user.role == 'gerente':
        return True
    if user.role == 'garcom':
        return order.waiter_id == user.id
    return False


def get_order_for_user_or_403(user, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not can_access_order(user, order):
        raise PermissionDenied('Você não tem permissão para acessar este pedido.')
    return order


def is_ajax_request(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def order_snapshot(order):
    order_items = order.items.select_related('product').all().order_by('id')
    return {
        'id': order.id,
        'mesa': order.mesa,
        'cliente': order.cliente,
        'observacoes': order.observacoes or '',
        'total': float(order.total),
        'items': [
            {
                'id': item.id,
                'product_name': item.product.name,
                'product_icon': item.product.icon or '🍔',
                'quantity': item.quantity,
                'pending_quantity': item.pending_quantity,
                'unit_price': float(item.unit_price),
                'subtotal': float(item.subtotal),
            }
            for item in order_items
        ]
    }


def sync_order_kitchen_status(order):
    """Mantém status baseado no que ainda falta preparar na cozinha."""
    if order.status in ['finalizado', 'cancelado']:
        return

    # Se o pedido ficou sem nenhum item, cancela automaticamente
    if not order.items.exists():
        order.status = 'cancelado'
        order.save(update_fields=['status', 'updated_at'])
        return

    has_pending_items = order.items.filter(pending_quantity__gt=0).exists()
    target_status = 'cozinha' if has_pending_items else 'pronto'

    if order.status != target_status:
        order.status = target_status
        order.save(update_fields=['status', 'updated_at'])


@login_required
def manage_order(request, order_id):
    """Tela para gerente/garçom alterar pedido ativo e adicionar itens."""
    if not can_manage_order(request.user):
        messages.error(request, 'Acesso não autorizado')
        return redirect_by_role(request)

    order = get_order_for_user_or_403(request.user, order_id)
    order = Order.objects.prefetch_related('items__product').get(id=order.id)

    if order.status in ['finalizado', 'cancelado']:
        messages.error(request, 'Não é possível alterar um pedido finalizado/cancelado.')
        return redirect_by_role(request)

    categories = Category.objects.prefetch_related('products__recipe_items__ingredient').all()
    context = {
        'order': order,
        'categories': categories,
    }
    return render(request, 'restaurante/manage_order.html', context)


@login_required
@require_POST
def update_order_info(request, order_id):
    """Atualiza dados principais do pedido ativo."""
    if not can_manage_order(request.user):
        messages.error(request, 'Acesso não autorizado')
        return redirect_by_role(request)

    order = get_order_for_user_or_403(request.user, order_id)
    if order.status in ['finalizado', 'cancelado']:
        messages.error(request, 'Pedido não pode mais ser alterado.')
        return redirect_by_role(request)

    mesa = request.POST.get('mesa', '').strip()
    cliente = request.POST.get('cliente', '').strip() or 'Cliente'
    observacoes = request.POST.get('observacoes', '').strip()

    if order.order_type == 'dine-in' and not mesa:
        if is_ajax_request(request):
            return JsonResponse({'success': False, 'message': 'Informe o número da mesa.'}, status=400)
        messages.error(request, 'Informe o número da mesa.')
        return redirect('manage_order', order_id=order.id)

    if order.order_type == 'delivery':
        mesa = 'DELIVERY'

    order.mesa = mesa
    order.cliente = cliente
    order.observacoes = observacoes
    order.save(update_fields=['mesa', 'cliente', 'observacoes', 'updated_at'])
    sync_order_kitchen_status(order)

    if is_ajax_request(request):
        return JsonResponse({
            'success': True,
            'message': 'Dados do pedido atualizados.',
            'order': order_snapshot(order)
        })

    messages.success(request, 'Dados do pedido atualizados.')
    return redirect('manage_order', order_id=order.id)


@login_required
@require_POST
def add_product_to_order(request, order_id, product_id):
    """Adiciona item ao pedido existente (mesa)."""
    if not can_manage_order(request.user):
        messages.error(request, 'Acesso não autorizado')
        return redirect_by_role(request)

    order = get_order_for_user_or_403(request.user, order_id)
    product = get_object_or_404(Product, id=product_id)

    if order.status in ['finalizado', 'cancelado']:
        if is_ajax_request(request):
            return JsonResponse({'success': False, 'message': 'Pedido não pode mais ser alterado.'}, status=400)
        messages.error(request, 'Pedido não pode mais ser alterado.')
        return redirect('manage_order', order_id=order.id)

    if product.available_stock <= 0:
        if is_ajax_request(request):
            return JsonResponse({'success': False, 'message': 'Produto sem estoque.'}, status=400)
        messages.error(request, 'Produto sem estoque.')
        return redirect('manage_order', order_id=order.id)

    order_item = order.items.filter(product=product).first()
    if order_item:
        order_item.quantity += 1
        order_item.pending_quantity += 1
        order_item.save()
    else:
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            pending_quantity=1,
            unit_price=product.price
        )

    product.consume_ingredients(1)
    order.calculate_total()
    sync_order_kitchen_status(order)

    if is_ajax_request(request):
        order.refresh_from_db()
        return JsonResponse({
            'success': True,
            'message': f'{product.name} adicionado ao pedido.',
            'order': order_snapshot(order)
        })

    messages.success(request, f'{product.name} adicionado ao pedido.')
    return redirect('manage_order', order_id=order.id)


@login_required
@require_POST
def change_order_item_qty(request, order_id, item_id):
    """Incrementa/decrementa/remove item de um pedido ativo."""
    if not can_manage_order(request.user):
        messages.error(request, 'Acesso não autorizado')
        return redirect_by_role(request)

    order = get_order_for_user_or_403(request.user, order_id)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)

    if order.status in ['finalizado', 'cancelado']:
        if is_ajax_request(request):
            return JsonResponse({'success': False, 'message': 'Pedido não pode mais ser alterado.'}, status=400)
        messages.error(request, 'Pedido não pode mais ser alterado.')
        return redirect('manage_order', order_id=order.id)

    action = request.POST.get('action')
    product = order_item.product

    if action == 'add':
        if product.available_stock <= 0:
            if is_ajax_request(request):
                return JsonResponse({'success': False, 'message': 'Produto sem estoque.'}, status=400)
            messages.error(request, 'Produto sem estoque.')
            return redirect('manage_order', order_id=order.id)
        order_item.quantity += 1
        order_item.pending_quantity += 1
        product.consume_ingredients(1)
        order_item.save(update_fields=['quantity', 'pending_quantity'])

    elif action == 'remove':
        if order_item.pending_quantity <= 0:
            if is_ajax_request(request):
                return JsonResponse({'success': False, 'message': 'Este item já está em preparo ou pronto e não pode ser cancelado.'}, status=400)
            messages.error(request, 'Este item já está em preparo ou pronto e não pode ser cancelado.')
            return redirect('manage_order', order_id=order.id)

        order_item.quantity -= 1
        order_item.pending_quantity -= 1
        product.restore_ingredients(1)
        if order_item.quantity <= 0:
            order_item.delete()
        else:
            order_item.save(update_fields=['quantity', 'pending_quantity'])

    elif action == 'delete':
        if order_item.pending_quantity <= 0:
            if is_ajax_request(request):
                return JsonResponse({'success': False, 'message': 'Não há quantidade pendente para cancelar neste item.'}, status=400)
            messages.error(request, 'Não há quantidade pendente para cancelar neste item.')
            return redirect('manage_order', order_id=order.id)

        pending_to_cancel = order_item.pending_quantity
        product.restore_ingredients(pending_to_cancel)
        order_item.quantity -= pending_to_cancel
        order_item.pending_quantity = 0
        if order_item.quantity <= 0:
            order_item.delete()
        else:
            order_item.save(update_fields=['quantity', 'pending_quantity'])

    else:
        if is_ajax_request(request):
            return JsonResponse({'success': False, 'message': 'Ação inválida.'}, status=400)
        messages.error(request, 'Ação inválida.')
        return redirect('manage_order', order_id=order.id)

    order.calculate_total()
    sync_order_kitchen_status(order)

    if is_ajax_request(request):
        order.refresh_from_db()
        return JsonResponse({
            'success': True,
            'message': 'Pedido atualizado.',
            'order': order_snapshot(order)
        })

    messages.success(request, 'Pedido atualizado.')
    return redirect('manage_order', order_id=order.id)


# ============== COZINHA VIEWS ==============

@login_required
def kitchen_view(request):
    """View da cozinha"""
    if request.user.role not in ['cozinha', 'gerente']:
        messages.error(request, 'Acesso não autorizado')
        return redirect('dashboard')

    now = timezone.now()
    threshold_time = now - timedelta(minutes=15)  # Pedidos com mais de 15 min
    
    orders_cozinha_raw = Order.objects.filter(status='cozinha').prefetch_related('items__product').order_by('created_at')
    orders_pronto = Order.objects.filter(status='pronto').prefetch_related('items__product').order_by('created_at')

    orders_cozinha = []
    
    # Adicionar flag de atrasado para cada pedido
    for order in orders_cozinha_raw:
        order.pending_items = [item for item in order.items.all() if item.pending_quantity > 0]
        if not order.pending_items:
            continue
        # Para pedidos alterados/reenviados, o tempo deve contar da última atualização enviada para cozinha.
        order.kitchen_reference_time = order.updated_at or order.created_at
        order.is_late = order.kitchen_reference_time < threshold_time
        order.wait_minutes = int((now - order.kitchen_reference_time).total_seconds() // 60)
        enrich_delivery_order_display(order)
        orders_cozinha.append(order)
    
    for order in orders_pronto:
        order.wait_minutes = int((now - order.created_at).total_seconds() // 60)
        enrich_delivery_order_display(order)
    
    context = {
        'orders_cozinha': orders_cozinha,
        'orders_pronto': orders_pronto,
        'now': now,
    }
    return render(request, 'restaurante/kitchen.html', context)


@login_required
@require_POST
def mark_order_ready(request, order_id):
    """Marcar pedido como pronto"""
    if request.user.role not in ['cozinha', 'gerente']:
        messages.error(request, 'Acesso não autorizado')
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    order.items.update(pending_quantity=0)
    order.status = 'pronto'
    order.save()
    messages.success(request, f'Pedido #{order.id} marcado como pronto!')
    return redirect('kitchen_view')


# ============== ADMIN VIEWS ==============

@login_required
def admin_dashboard(request):
    """Dashboard do gerente"""
    if request.user.role != 'gerente':
        messages.error(request, 'Acesso não autorizado')
        return redirect('dashboard')
    
    today = timezone.now().date()
    
    # Estatísticas do dia
    orders_today = Order.objects.filter(
        created_at__date=today,
        status='finalizado'
    )
    
    total_today = orders_today.aggregate(total=Sum('total'))['total'] or 0
    orders_count_today = orders_today.count()
    avg_ticket = orders_today.aggregate(avg=Avg('total'))['avg'] or 0
    
    # Pedidos ativos
    active_orders = Order.objects.filter(
        status__in=['cozinha', 'pronto']
    ).prefetch_related('items__product').order_by('-created_at')

    for order in active_orders:
        enrich_delivery_order_display(order)
    
    # Mesas ativas (pedidos não finalizados, excluindo delivery)
    mesas_ativas = Order.objects.filter(
        status__in=['cozinha', 'pronto'],
        order_type='dine-in'
    ).values('mesa').distinct().count()
    
    # Alertas de estoque baixo (ingredientes abaixo do limite configurado)
    low_stock_ingredients = Ingredient.objects.filter(
        low_stock_alert__gt=0,
        stock_quantity__lte=F('low_stock_alert'),
        is_active=True
    ).order_by('stock_quantity')[:5]
    
    # Top 5 produtos
    top_products = OrderItem.objects.filter(
        order__created_at__date=today,
        order__status='finalizado'
    ).values('product__name').annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty')[:5]
    
    context = {
        'vendas_hoje': total_today,
        'pedidos_hoje': orders_count_today,
        'ticket_medio': avg_ticket,
        'pedidos_ativos': active_orders.count(),
        'active_orders': active_orders,
        'top_products': top_products,
        'mesas_ativas': mesas_ativas,
        'low_stock_ingredients': low_stock_ingredients,
        'active_menu': 'dashboard',
    }
    return render(request, 'restaurante/admin/dashboard.html', context)


@login_required
def admin_reports(request):
    """Relatórios"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    today = timezone.localdate()
    filter_type = request.GET.get('filter', 'day')

    selected_day = request.GET.get('day') or today.strftime('%Y-%m-%d')
    selected_month = request.GET.get('month') or today.strftime('%Y-%m')
    selected_year = request.GET.get('year') or str(today.year)

    orders = Order.objects.filter(status='finalizado')

    if filter_type == 'day':
        try:
            year, month, day = [int(part) for part in selected_day.split('-')]
            target_day = date(year, month, day)
        except (TypeError, ValueError):
            target_day = today
            selected_day = today.strftime('%Y-%m-%d')
        orders = orders.filter(created_at__date=target_day)

    elif filter_type == 'month':
        try:
            year, month = [int(part) for part in selected_month.split('-')]
            start_month = date(year, month, 1)
        except (TypeError, ValueError):
            start_month = date(today.year, today.month, 1)
            selected_month = today.strftime('%Y-%m')

        if start_month.month == 12:
            next_month = date(start_month.year + 1, 1, 1)
        else:
            next_month = date(start_month.year, start_month.month + 1, 1)

        orders = orders.filter(created_at__date__gte=start_month, created_at__date__lt=next_month)

    elif filter_type == 'year':
        try:
            target_year = int(selected_year)
        except (TypeError, ValueError):
            target_year = today.year
            selected_year = str(today.year)
        orders = orders.filter(created_at__year=target_year)

    else:
        filter_type = 'day'
        orders = orders.filter(created_at__date=today)
        selected_day = today.strftime('%Y-%m-%d')
    
    # Estatísticas
    total_revenue = orders.aggregate(total=Sum('total'))['total'] or 0
    total_orders = orders.count()
    avg_ticket = orders.aggregate(avg=Avg('total'))['avg'] or 0
    
    # Vendas por garçom
    waiter_stats = orders.values('waiter__username').annotate(
        total_sales=Sum('total'),
        orders_count=Count('id'),
        avg_ticket=Avg('total')
    ).order_by('-total_sales')
    
    # Vendas por dia
    daily_sales = orders.annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('day')
    
    # Produtos mais vendidos
    top_products = OrderItem.objects.filter(
        order__in=orders
    ).values('product__name', 'product__icon').annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum('quantity') * Avg('unit_price')
    ).order_by('-total_qty')[:10]
    
    context = {
        'filter_type': filter_type,
        'selected_day': selected_day,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'year_options': range(today.year - 5, today.year + 1),
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'ticket_medio': avg_ticket,
        'waiter_ranking': waiter_stats,
        'daily_sales': list(daily_sales),
        'top_products': top_products,
        'active_menu': 'reports',
    }
    return render(request, 'restaurante/admin/reports.html', context)


@login_required
@require_POST
def toggle_store_status(request):
    """Alterna status da loja (aberta/fechada) no painel do gerente."""
    if request.user.role != 'gerente':
        messages.error(request, 'Apenas gerentes podem alterar o status da loja.')
        return redirect('dashboard')

    settings = AppSettings.get_settings()
    settings.is_store_open = not settings.is_store_open
    settings.save(update_fields=['is_store_open'])

    if settings.is_store_open:
        messages.success(request, 'Loja aberta com sucesso.')
    else:
        messages.warning(request, 'Loja fechada para novos pedidos.')

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('admin_dashboard')


@login_required
def admin_menu(request):
    """Gestão do cardápio"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    categories = Category.objects.prefetch_related('products__recipe_items__ingredient').all()
    
    context = {
        'categories': categories,
        'active_menu': 'menu',
    }
    return render(request, 'restaurante/admin/menu.html', context)


@login_required
def product_create(request):
    """Criar produto"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    recipe_count = save_product_recipe_from_request(product, request)
                    if product.use_ingredient_stock and recipe_count == 0:
                        raise ValueError('Defina ao menos 1 ingrediente na receita para usar estoque por ingredientes.')
                messages.success(request, 'Produto criado com sucesso!')
                return redirect('admin_menu')
            except ValueError as exc:
                messages.error(request, str(exc))
    else:
        form = ProductForm()
    
    categories = Category.objects.all()
    ingredients = Ingredient.objects.filter(is_active=True).order_by('name')
    return render(request, 'restaurante/admin/product_form.html', {'form': form, 'title': 'Novo Produto', 'active_menu': 'menu', 'categories': categories, 'ingredients': ingredients, 'recipe_items': []})


@login_required
def product_edit(request, product_id):
    """Editar produto"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    recipe_count = save_product_recipe_from_request(product, request)
                    if product.use_ingredient_stock and recipe_count == 0:
                        raise ValueError('Defina ao menos 1 ingrediente na receita para usar estoque por ingredientes.')
                messages.success(request, 'Produto atualizado!')
                return redirect('admin_menu')
            except ValueError as exc:
                messages.error(request, str(exc))
    else:
        form = ProductForm(instance=product)
    
    categories = Category.objects.all()
    ingredients = Ingredient.objects.filter(is_active=True).order_by('name')
    recipe_items = product.recipe_items.select_related('ingredient').all().order_by('ingredient__name')
    return render(request, 'restaurante/admin/product_form.html', {'form': form, 'title': 'Editar Produto', 'product': product, 'active_menu': 'menu', 'categories': categories, 'ingredients': ingredients, 'recipe_items': recipe_items})


@login_required
@require_POST
def product_delete(request, product_id):
    """Deletar produto"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    try:
        product = Product.objects.get(id=product_id)
        product.delete()
        messages.success(request, 'Produto removido!')
    except Product.DoesNotExist:
        messages.warning(request, 'Produto não encontrado ou já foi removido.')
    
    return redirect('admin_menu')


@login_required
def category_create(request):
    """Criar categoria"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria criada!')
            return redirect('admin_menu')
        messages.error(request, 'Não foi possível criar a categoria. Verifique os dados.')
    else:
        form = CategoryForm()
    
    return render(request, 'restaurante/admin/category_form.html', {'form': form, 'title': 'Nova Categoria', 'active_menu': 'menu'})


@login_required
def category_edit(request, category_id):
    """Editar categoria"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada!')
            return redirect('admin_menu')
        messages.error(request, 'Não foi possível atualizar a categoria. Verifique os dados.')
    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        'restaurante/admin/category_form.html',
        {'form': form, 'title': 'Editar Categoria', 'category': category, 'active_menu': 'menu'}
    )


@login_required
@require_POST
def category_delete(request, category_id):
    """Deletar categoria"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    try:
        category = Category.objects.get(id=category_id)
        category.delete()
        messages.success(request, 'Categoria removida!')
    except Category.DoesNotExist:
        messages.warning(request, 'Categoria não encontrada ou já foi removida.')
    
    return redirect('admin_menu')


@login_required
def admin_ingredients(request):
    """Gestão de ingredientes"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    ingredients = Ingredient.objects.all().order_by('name')
    context = {
        'ingredients': ingredients,
        'active_menu': 'ingredients',
    }
    return render(request, 'restaurante/admin/ingredients.html', context)


@login_required
def ingredient_create(request):
    """Criar ingrediente"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ingrediente criado com sucesso!')
            return redirect('admin_ingredients')
    else:
        form = IngredientForm()

    return render(request, 'restaurante/admin/ingredient_form.html', {
        'form': form,
        'title': 'Novo Ingrediente',
        'active_menu': 'ingredients',
    })


@login_required
def ingredient_edit(request, ingredient_id):
    """Editar ingrediente"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ingrediente atualizado!')
            return redirect('admin_ingredients')
    else:
        form = IngredientForm(instance=ingredient)

    return render(request, 'restaurante/admin/ingredient_form.html', {
        'form': form,
        'title': 'Editar Ingrediente',
        'ingredient': ingredient,
        'active_menu': 'ingredients',
    })


@login_required
@require_POST
def ingredient_delete(request, ingredient_id):
    """Remover ingrediente"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    try:
        ingredient = Ingredient.objects.get(id=ingredient_id)
        ingredient.delete()
        messages.success(request, 'Ingrediente removido!')
    except Ingredient.DoesNotExist:
        messages.warning(request, 'Ingrediente não encontrado ou já foi removido.')
    
    return redirect('admin_ingredients')


@login_required
def admin_users(request):
    """Gestão de usuários"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    users = User.objects.all().order_by('role', 'username')
    
    context = {
        'users': users,
        'active_menu': 'users',
    }
    return render(request, 'restaurante/admin/users.html', context)


@login_required
def user_create(request):
    """Criar usuário"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'garcom')
        if role not in ['garcom', 'cozinha', 'gerente']:
            messages.error(request, '❌ Função inválida.')
            return redirect('user_create')
        
        # Validações
        if not username:
            messages.error(request, '❌ Informe o nome de usuário')
            return redirect('user_create')

        try:
            validate_slug(username)
        except ValidationError:
            messages.error(request, '❌ Usuário inválido. Use apenas letras, números, hífen ou underline.')
            return redirect('user_create')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Este usuário já existe')
            return redirect('user_create')
        
        if not password:
            messages.error(request, '❌ Informe a senha')
            return redirect('user_create')

        try:
            validate_password(password)
        except ValidationError as exc:
            messages.error(request, '❌ ' + ' '.join(exc.messages))
            return redirect('user_create')
        
        # Criar usuário
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                role=role
            )
            messages.success(request, f'✅ Usuário "{username}" criado com sucesso!')
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f'❌ Erro ao criar usuário: {str(e)}')
            return redirect('user_create')
    
    return render(request, 'restaurante/admin/user_form.html', {'title': 'Novo Usuário', 'active_menu': 'users'})


@login_required
@require_POST
def user_delete(request, user_id):
    """Deletar usuário"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    if request.user.id == user_id:
        messages.error(request, 'Você não pode excluir a si mesmo')
        return redirect('admin_users')
    
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        messages.success(request, 'Usuário removido!')
    except User.DoesNotExist:
        messages.warning(request, 'Usuário não encontrado ou já foi removido.')
    
    return redirect('admin_users')


@login_required
def admin_settings(request):
    """Configurações da loja"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    settings = AppSettings.get_settings()
    
    if request.method == 'POST':
        form = AppSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações salvas!')
            return redirect('admin_settings')
        messages.error(request, 'Não foi possível salvar. Verifique os campos e tente novamente.')
    else:
        form = AppSettingsForm(instance=settings)
    
    def get_local_ip_address():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(('8.8.8.8', 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return '127.0.0.1'

    local_ip = get_local_ip_address()
    local_port = request.get_port() or '8000'
    access_links = {
        'local': f'http://localhost:{local_port}',
        'network': f'http://{local_ip}:{local_port}',
    }

    return render(request, 'restaurante/admin/settings.html', {
        'form': form,
        'settings': settings,
        'active_menu': 'settings',
        'access_links': access_links,
        'local_ip': local_ip,
    })


@login_required
def admin_online_orders(request):
    """Pedidos online/delivery"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Submeter pedido online usando a mesma lógica
        cart = request.session.get('cart', [])
        
        if not cart:
            messages.error(request, 'O carrinho está vazio')
            return redirect('admin_online_orders')
        
        cliente = request.POST.get('cliente', 'Cliente')
        address = request.POST.get('address', '')
        platform = request.POST.get('platform', 'Whatsapp')
        observacoes = request.POST.get('observacoes', '')
        
        if not cliente:
            messages.error(request, 'Informe o nome do cliente')
            return redirect('admin_online_orders')
        
        observacoes = f"Plataforma: {platform} | {observacoes}" if observacoes else f"Plataforma: {platform}"

        stock_error = validate_cart_ingredient_stock(cart)
        if stock_error:
            messages.error(request, stock_error)
            return redirect('admin_online_orders')

        product_ids = [item['id'] for item in cart]
        products_by_id = Product.objects.in_bulk(product_ids)

        with transaction.atomic():
            total = sum(item['price'] * item['qty'] for item in cart)
            order = Order.objects.create(
                mesa='DELIVERY',
                cliente=cliente,
                observacoes=observacoes,
                total=total,
                status='cozinha',
                order_type='delivery',
                address=address,
                waiter=request.user
            )

            for cart_item in cart:
                product = products_by_id.get(cart_item['id'])
                if not product:
                    raise ValueError(f"Produto inválido: {cart_item['id']}")
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=cart_item['qty'],
                    pending_quantity=cart_item['qty'],
                    unit_price=product.price
                )
                product.consume_ingredients(cart_item['qty'])
        
        request.session['cart'] = []
        messages.success(request, 'Pedido online enviado!')
        return redirect('admin_online_orders')
    
    categories = Category.objects.prefetch_related('products__recipe_items__ingredient').all()
    cart = request.session.get('cart', [])
    cart_total = sum(item['price'] * item['qty'] for item in cart)
    
    delivery_orders = Order.objects.filter(
        order_type='delivery',
        status__in=['cozinha', 'pronto']
    ).order_by('-created_at')
    
    context = {
        'categories': categories,
        'cart': cart,
        'cart_total': cart_total,
        'delivery_orders': delivery_orders,
        'active_menu': 'online',
    }
    return render(request, 'restaurante/admin/online.html', context)


# ============== FECHAMENTO DE CONTA ==============

@login_required
def close_order(request, order_id):
    """Fechar conta / finalizar pedido"""
    order = get_order_for_user_or_403(request.user, order_id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'dinheiro')
        order.status = 'finalizado'
        order.payment_method = payment_method
        order.save()
        messages.success(request, f'Conta fechada! Pagamento: {order.get_payment_method_display()}')
        
        if request.user.role == 'gerente':
            return redirect('admin_dashboard')
        return redirect('waiter_view')
    
    form = PaymentForm()
    return render(request, 'restaurante/close_order.html', {'order': order, 'form': form})


@login_required
@require_POST
def cancel_order(request, order_id):
    """Cancelar pedido"""
    if request.user.role != 'gerente':
        messages.error(request, 'Apenas gerentes podem cancelar pedidos')
        return redirect('dashboard')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Devolver estoque
    for item in order.items.all():
        item.product.restore_ingredients(item.quantity)
    
    order.status = 'cancelado'
    order.save()
    messages.warning(request, f'Pedido #{order.id} cancelado')
    return redirect('admin_dashboard')


@login_required
def print_order(request, order_id):
    """Imprimir cupom"""
    order = get_order_for_user_or_403(request.user, order_id)
    settings = AppSettings.get_settings()
    
    return render(request, 'restaurante/print_order.html', {
        'order': order,
        'settings': settings
    })


# ============== API VIEWS (AJAX) ==============

@login_required
def api_add_to_cart(request, product_id):
    """API: Adicionar ao carrinho via AJAX"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        available_stock = product.available_stock
        if available_stock <= 0:
            return JsonResponse({'success': False, 'message': 'Produto sem estoque'})
        
        cart = request.session.get('cart', [])
        
        for item in cart:
            if item['id'] == product_id:
                if item['qty'] >= available_stock:
                    return JsonResponse({'success': False, 'message': 'Limite de estoque'})
                item['qty'] += 1
                request.session['cart'] = cart
                request.session.modified = True
                return JsonResponse({'success': True, 'cart': cart})
        
        cart.append({
            'id': product_id,
            'name': product.name,
            'price': float(product.price),
            'qty': 1,
            'icon': product.icon,
            'image': product.image.url if product.image else None,
        })
        request.session['cart'] = cart
        request.session.modified = True
        return JsonResponse({'success': True, 'cart': cart})
    
    return JsonResponse({'success': False})


@login_required
def api_remove_from_cart(request, product_id):
    """API: Remover do carrinho via AJAX"""
    if request.method == 'POST':
        cart = request.session.get('cart', [])
        
        for item in cart:
            if item['id'] == product_id:
                if item['qty'] > 1:
                    item['qty'] -= 1
                else:
                    cart.remove(item)
                break
        
        request.session['cart'] = cart
        request.session.modified = True
        return JsonResponse({'success': True, 'cart': cart})
    
    return JsonResponse({'success': False})


@login_required
def api_get_cart(request):
    """API: Obter carrinho"""
    cart = request.session.get('cart', [])
    total = sum(item['price'] * item['qty'] for item in cart)
    return JsonResponse({'cart': cart, 'total': total})


@login_required
def api_clear_cart(request):
    """API: Limpar carrinho"""
    if request.method == 'POST':
        request.session['cart'] = []
        request.session.modified = True
        return JsonResponse({'success': True, 'cart': [], 'total': 0})

    return JsonResponse({'success': False})


def pwa_manifest(request):
    return render(request, 'pwa/manifest.webmanifest', content_type='application/manifest+json')


def pwa_service_worker(request):
    return render(request, 'pwa/sw.js', content_type='application/javascript')
