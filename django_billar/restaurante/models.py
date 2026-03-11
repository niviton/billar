from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from decimal import Decimal, ROUND_FLOOR


class User(AbstractUser):
    """Usuário personalizado com roles"""
    ROLE_CHOICES = [
        ('garcom', 'Garçom'),
        ('cozinha', 'Cozinha'),
        ('gerente', 'Gerente'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='garcom', verbose_name='Função')

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Category(models.Model):
    """Categoria de produtos"""
    name = models.CharField(max_length=100, verbose_name='Nome')
    icon = models.CharField(max_length=10, default='🍽️', verbose_name='Emoji/Ícone')
    order = models.IntegerField(default=0, verbose_name='Ordem')

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class Product(models.Model):
    """Produto do cardápio"""
    name = models.CharField(max_length=200, verbose_name='Nome')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Categoria')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço')
    stock = models.IntegerField(default=0, verbose_name='Estoque')
    use_ingredient_stock = models.BooleanField(default=False, verbose_name='Controlar por ingredientes')
    icon = models.CharField(max_length=10, default='🍽️', verbose_name='Emoji')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Imagem')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['category', 'name']
        constraints = [
            models.CheckConstraint(condition=models.Q(stock__gte=0), name='product_stock_non_negative'),
        ]

    def __str__(self):
        return f"{self.icon} {self.name}"

    @property
    def display_icon(self):
        if self.image:
            return self.image.url
        return self.icon

    @property
    def has_recipe(self):
        return self.recipe_items.exists()

    @property
    def available_stock(self):
        if not self.use_ingredient_stock:
            return max(self.stock, 0)

        recipe_items = list(self.recipe_items.select_related('ingredient').all())
        if not recipe_items:
            return 0

        possible_units = []
        for recipe_item in recipe_items:
            ingredient_stock = recipe_item.ingredient.stock_quantity
            needed = recipe_item.quantity
            if needed <= 0:
                continue
            units = int((ingredient_stock / needed).to_integral_value(rounding=ROUND_FLOOR))
            possible_units.append(max(units, 0))

        if not possible_units:
            return 0
        return min(possible_units)

    def can_make(self, quantity):
        return self.available_stock >= quantity

    def consume_ingredients(self, quantity):
        quantity = Decimal(str(quantity))
        if not self.use_ingredient_stock:
            if self.stock < int(quantity):
                raise ValueError(f'Estoque insuficiente para {self.name}.')
            self.stock -= int(quantity)
            self.save(update_fields=['stock', 'updated_at'])
            return

        recipe_items = list(self.recipe_items.select_related('ingredient').all())
        if not recipe_items:
            raise ValueError(f'Receita não definida para {self.name}.')
            
        if not self.can_make(quantity):
            raise ValueError(f'Estoque insuficiente para {self.name}.')

        for recipe_item in recipe_items:
            required = recipe_item.quantity * quantity
            ingredient = recipe_item.ingredient
            ingredient.stock_quantity -= required
            ingredient.save(update_fields=['stock_quantity', 'updated_at'])

    def restore_ingredients(self, quantity):
        quantity = Decimal(str(quantity))
        if not self.use_ingredient_stock:
            self.stock += int(quantity)
            self.save(update_fields=['stock', 'updated_at'])
            return

        recipe_items = list(self.recipe_items.select_related('ingredient').all())
        if not recipe_items:
            return

        for recipe_item in recipe_items:
            ingredient = recipe_item.ingredient
            ingredient.stock_quantity += recipe_item.quantity * quantity
            ingredient.save(update_fields=['stock_quantity', 'updated_at'])


class Ingredient(models.Model):
    """Ingrediente base para produção de produtos"""
    UNIT_CHOICES = [
        ('un', 'Unidade'),
        ('g', 'Gramas'),
        ('kg', 'Quilos'),
        ('ml', 'Mililitros'),
        ('l', 'Litros'),
    ]

    name = models.CharField(max_length=120, unique=True, verbose_name='Nome')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='un', verbose_name='Unidade')
    stock_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0, verbose_name='Estoque')
    low_stock_alert = models.DecimalField(max_digits=12, decimal_places=3, default=0, verbose_name='Alerta de estoque baixo')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Custo')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ingrediente'
        verbose_name_plural = 'Ingredientes'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(condition=models.Q(stock_quantity__gte=0), name='ingredient_stock_non_negative'),
            models.CheckConstraint(condition=models.Q(cost_price__gte=0), name='ingredient_cost_non_negative'),
        ]

    def __str__(self):
        return self.name


class ProductIngredient(models.Model):
    """Receita de ingredientes por produto"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recipe_items', verbose_name='Produto')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='recipe_products', verbose_name='Ingrediente')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Quantidade na receita')

    class Meta:
        verbose_name = 'Ingrediente da Receita'
        verbose_name_plural = 'Ingredientes da Receita'
        unique_together = ('product', 'ingredient')
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='recipe_quantity_positive'),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.ingredient.name} ({self.quantity} {self.ingredient.unit})"


class Order(models.Model):
    """Pedido"""
    STATUS_CHOICES = [
        ('cozinha', 'Na Cozinha'),
        ('pronto', 'Pronto'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    TYPE_CHOICES = [
        ('dine-in', 'Mesa'),
        ('delivery', 'Delivery'),
    ]
    
    PAYMENT_CHOICES = [
        ('dinheiro', 'Dinheiro'),
        ('pix', 'PIX'),
        ('credito', 'Cartão de Crédito'),
        ('debito', 'Cartão de Débito'),
    ]

    mesa = models.CharField(max_length=50, verbose_name='Mesa')
    cliente = models.CharField(max_length=200, blank=True, verbose_name='Cliente')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Total')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='cozinha', verbose_name='Status')
    order_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='dine-in', verbose_name='Tipo')
    address = models.TextField(blank=True, verbose_name='Endereço de Entrega')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, blank=True, verbose_name='Pagamento')
    waiter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Garçom')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pedido #{self.id} - Mesa {self.mesa}"

    def calculate_total(self):
        total = sum(item.subtotal for item in self.items.all())
        self.total = total
        self.save()
        return total

    @property
    def status_color(self):
        colors = {
            'cozinha': 'warning',
            'pronto': 'info',
            'finalizado': 'success',
            'cancelado': 'danger',
        }
        return colors.get(self.status, 'secondary')


class OrderItem(models.Model):
    """Item de um pedido"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Pedido')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Produto')
    quantity = models.IntegerField(default=1, verbose_name='Quantidade')
    pending_quantity = models.IntegerField(default=0, verbose_name='Qtd. Pendente Cozinha')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço Unitário')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='orderitem_quantity_positive'),
            models.CheckConstraint(condition=models.Q(pending_quantity__gte=0), name='orderitem_pending_non_negative'),
            models.CheckConstraint(condition=models.Q(pending_quantity__lte=models.F('quantity')), name='orderitem_pending_lte_quantity'),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name='orderitem_unit_price_non_negative'),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)


class AppSettings(models.Model):
    """Configurações da aplicação (singleton)"""
    store_name = models.CharField(max_length=200, default='Billá Burger', verbose_name='Nome da Loja')
    slogan = models.CharField(max_length=500, default='Os melhores hambúrgueres da cidade!', verbose_name='Slogan')
    logo = models.ImageField(upload_to='settings/', blank=True, null=True, verbose_name='Logo')
    pix_qrcode = models.ImageField(upload_to='settings/', blank=True, null=True, verbose_name='QR Code PIX')
    
    # Dados da empresa para nota fiscal
    cnpj = models.CharField(max_length=20, blank=True, verbose_name='CNPJ/CPF')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefone')
    address = models.CharField(max_length=300, blank=True, verbose_name='Endereço')
    city = models.CharField(max_length=100, blank=True, verbose_name='Cidade/UF')
    
    # Aparência
    font = models.CharField(max_length=100, default='Google Sans', verbose_name='Fonte')
    font_size = models.IntegerField(default=16, verbose_name='Tamanho da Fonte')
    primary_color = models.CharField(max_length=20, default='#ef4444', verbose_name='Cor Primária')
    secondary_color = models.CharField(max_length=20, default='#fbbf24', verbose_name='Cor Secundária')
    background_color = models.CharField(max_length=20, default='#f8f9fa', verbose_name='Cor de Fundo')
    text_color = models.CharField(max_length=20, default='#1e293b', verbose_name='Cor do Texto')
    
    # PIX
    pix_key = models.CharField(max_length=200, blank=True, verbose_name='Chave PIX')
    pix_name = models.CharField(max_length=100, blank=True, verbose_name='Nome do titular PIX')
    show_pix_on_receipt = models.BooleanField(default=True, verbose_name='Mostrar QR Code PIX na nota')
    
    is_store_open = models.BooleanField(default=True, verbose_name='Loja Aberta')

    class Meta:
        verbose_name = 'Configurações'
        verbose_name_plural = 'Configurações'

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        # Garantir que só existe uma instância
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
