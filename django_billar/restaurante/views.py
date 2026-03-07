from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta, date
import json

from .models import User, Category, Product, Order, OrderItem, AppSettings
from .forms import (
    LoginForm, UserForm, CategoryForm, ProductForm, 
    OrderForm, DeliveryOrderForm, PaymentForm, AppSettingsForm
)


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
    elif user.role == 'garcom':
        return redirect('waiter_view')
    else:  # cozinha
        return redirect('kitchen_view')


def redirect_order_entry(request):
    """Redireciona para a tela de criação de pedidos conforme o perfil."""
    if request.user.role == 'gerente':
        return redirect('admin_online_orders')
    return redirect('waiter_view')


# ============== GARÇOM VIEWS ==============

@login_required
def waiter_view(request):
    """View principal do garçom"""
    categories = Category.objects.prefetch_related('products').all()
    active_orders = Order.objects.filter(
        status__in=['cozinha', 'pronto']
    ).order_by('-created_at')
    
    # Carrinho da sessão
    cart = request.session.get('cart', [])
    cart_total = sum(item['price'] * item['qty'] for item in cart)
    
    context = {
        'categories': categories,
        'active_orders': active_orders,
        'cart': cart,
        'cart_total': cart_total,
    }
    return render(request, 'restaurante/waiter.html', context)


@login_required
def add_to_cart(request, product_id):
    """Adicionar produto ao carrinho"""
    product = get_object_or_404(Product, id=product_id)
    
    if product.stock <= 0:
        messages.error(request, 'Produto sem estoque')
        return redirect_order_entry(request)
    
    cart = request.session.get('cart', [])
    
    # Verificar se já existe no carrinho
    for item in cart:
        if item['id'] == product_id:
            if item['qty'] >= product.stock:
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
        
        mesa = request.POST.get('mesa', '').strip()
        cliente = request.POST.get('cliente', '').strip() or 'Cliente'
        observacoes = request.POST.get('observacoes', '').strip()
        order_type = request.POST.get('order_type', 'dine-in')
        address = request.POST.get('address', '').strip()
        
        if order_type == 'dine-in' and not mesa:
            messages.error(request, '❌ Informe o número da mesa')
            return redirect_order_entry(request)
        
        if order_type == 'delivery':
            mesa = 'DELIVERY'
            platform = request.POST.get('platform', 'Whatsapp')
            cliente = f"[{platform}] {cliente}"
            if not address:
                messages.error(request, '❌ Informe o endereço de entrega')
                return redirect_order_entry(request)
        
        try:
            # Verificar se já existe pedido ativo para a mesa
            active_order = None
            if order_type == 'dine-in':
                active_order = Order.objects.filter(
                    mesa=mesa, 
                    status__in=['cozinha', 'pronto']
                ).first()
        
            if active_order:
                # Adicionar itens ao pedido existente
                for cart_item in cart:
                    product = Product.objects.get(id=cart_item['id'])
                    existing_item = active_order.items.filter(product=product).first()
                    
                    if existing_item:
                        existing_item.quantity += cart_item['qty']
                        existing_item.save()
                    else:
                        OrderItem.objects.create(
                            order=active_order,
                            product=product,
                            quantity=cart_item['qty'],
                            unit_price=product.price
                        )
                    
                    # Atualizar estoque
                    product.stock -= cart_item['qty']
                    product.save()
                
                active_order.status = 'cozinha'
                if observacoes:
                    active_order.observacoes = (active_order.observacoes + " | " + observacoes) if active_order.observacoes else observacoes
                active_order.calculate_total()
                messages.success(request, f'✅ Pedido atualizado para mesa {mesa}')
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
                    product = Product.objects.get(id=cart_item['id'])
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=cart_item['qty'],
                        unit_price=product.price
                    )
                    # Atualizar estoque
                    product.stock -= cart_item['qty']
                    product.save()
                
                messages.success(request, f'✅ Pedido #{order.id} enviado para a cozinha!')
            
            # Limpar carrinho
            request.session['cart'] = []
            return redirect_order_entry(request)
        
        except Exception as e:
            messages.error(request, f'❌ Erro ao enviar pedido: {str(e)}')
            return redirect_order_entry(request)
    
    return redirect_order_entry(request)


# ============== COZINHA VIEWS ==============

@login_required
def kitchen_view(request):
    """View da cozinha"""
    now = timezone.now()
    threshold_time = now - timedelta(minutes=15)  # Pedidos com mais de 15 min
    
    orders_cozinha = Order.objects.filter(status='cozinha').prefetch_related('items__product').order_by('created_at')
    orders_pronto = Order.objects.filter(status='pronto').prefetch_related('items__product').order_by('created_at')
    
    # Adicionar flag de atrasado para cada pedido
    for order in orders_cozinha:
        order.is_late = order.created_at < threshold_time
        order.wait_minutes = int((now - order.created_at).total_seconds() // 60)
    
    for order in orders_pronto:
        order.wait_minutes = int((now - order.created_at).total_seconds() // 60)
    
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
    order = get_object_or_404(Order, id=order_id)
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
    
    # Mesas ativas (pedidos não finalizados, excluindo delivery)
    mesas_ativas = Order.objects.filter(
        status__in=['cozinha', 'pronto'],
        order_type='dine-in'
    ).values('mesa').distinct().count()
    
    # Alertas de estoque baixo (produtos com menos de 10 unidades)
    low_stock_products = Product.objects.filter(
        stock__lt=10,
        is_active=True
    ).order_by('stock')[:5]
    
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
        'low_stock_products': low_stock_products,
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
    
    categories = Category.objects.prefetch_related('products').all()
    
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
            form.save()
            messages.success(request, 'Produto criado com sucesso!')
            return redirect('admin_menu')
    else:
        form = ProductForm()
    
    categories = Category.objects.all()
    return render(request, 'restaurante/admin/product_form.html', {'form': form, 'title': 'Novo Produto', 'active_menu': 'menu', 'categories': categories})


@login_required
def product_edit(request, product_id):
    """Editar produto"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado!')
            return redirect('admin_menu')
    else:
        form = ProductForm(instance=product)
    
    categories = Category.objects.all()
    return render(request, 'restaurante/admin/product_form.html', {'form': form, 'title': 'Editar Produto', 'product': product, 'active_menu': 'menu', 'categories': categories})


@login_required
def product_delete(request, product_id):
    """Deletar produto"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Produto removido!')
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
def category_delete(request, category_id):
    """Deletar categoria"""
    if request.user.role != 'gerente':
        return redirect('dashboard')

    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, 'Categoria removida!')
    return redirect('admin_menu')


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
        
        # Validações
        if not username:
            messages.error(request, '❌ Informe o nome de usuário')
            return redirect('user_create')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Este usuário já existe')
            return redirect('user_create')
        
        if not password or len(password) < 4:
            messages.error(request, '❌ A senha deve ter pelo menos 4 caracteres')
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
def user_delete(request, user_id):
    """Deletar usuário"""
    if request.user.role != 'gerente':
        return redirect('dashboard')
    
    if request.user.id == user_id:
        messages.error(request, 'Você não pode excluir a si mesmo')
        return redirect('admin_users')
    
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, 'Usuário removido!')
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
    else:
        form = AppSettingsForm(instance=settings)
    
    return render(request, 'restaurante/admin/settings.html', {'form': form, 'settings': settings, 'active_menu': 'settings'})


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
        
        total = sum(item['price'] * item['qty'] for item in cart)
        order = Order.objects.create(
            mesa='DELIVERY',
            cliente=f"[{platform}] {cliente}",
            observacoes=observacoes,
            total=total,
            status='cozinha',
            order_type='delivery',
            address=address,
            waiter=request.user
        )
        
        for cart_item in cart:
            product = Product.objects.get(id=cart_item['id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=cart_item['qty'],
                unit_price=product.price
            )
            product.stock -= cart_item['qty']
            product.save()
        
        request.session['cart'] = []
        messages.success(request, 'Pedido online enviado!')
        return redirect('admin_online_orders')
    
    categories = Category.objects.prefetch_related('products').all()
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
    order = get_object_or_404(Order, id=order_id)
    
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
def cancel_order(request, order_id):
    """Cancelar pedido"""
    if request.user.role != 'gerente':
        messages.error(request, 'Apenas gerentes podem cancelar pedidos')
        return redirect('dashboard')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Devolver estoque
    for item in order.items.all():
        item.product.stock += item.quantity
        item.product.save()
    
    order.status = 'cancelado'
    order.save()
    messages.warning(request, f'Pedido #{order.id} cancelado')
    return redirect('admin_dashboard')


@login_required
def print_order(request, order_id):
    """Imprimir cupom"""
    order = get_object_or_404(Order, id=order_id)
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
        
        if product.stock <= 0:
            return JsonResponse({'success': False, 'message': 'Produto sem estoque'})
        
        cart = request.session.get('cart', [])
        
        for item in cart:
            if item['id'] == product_id:
                if item['qty'] >= product.stock:
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
