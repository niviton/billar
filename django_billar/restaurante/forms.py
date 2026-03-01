from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User, Category, Product, Order, OrderItem, AppSettings


class LoginForm(AuthenticationForm):
    """Formulário de login personalizado"""
    username = forms.CharField(
        label='Usuário',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Usuário',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Senha'
        })
    )


class UserForm(UserCreationForm):
    """Formulário de criação de usuário"""
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    """Formulário de categoria"""
    class Meta:
        model = Category
        fields = ['name', 'icon', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ProductForm(forms.ModelForm):
    """Formulário de produto"""
    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'stock', 'icon', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class OrderForm(forms.ModelForm):
    """Formulário de pedido"""
    class Meta:
        model = Order
        fields = ['mesa', 'cliente', 'observacoes', 'order_type', 'address']
        widgets = {
            'mesa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número da Mesa'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Cliente'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações...'}),
            'order_type': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Endereço de entrega...'}),
        }


class DeliveryOrderForm(forms.ModelForm):
    """Formulário de pedido delivery"""
    PLATFORM_CHOICES = [
        ('Whatsapp', 'WhatsApp'),
        ('iFood', 'iFood'),
        ('Rappi', 'Rappi'),
        ('Telefone', 'Telefone'),
        ('Outro', 'Outro'),
    ]
    platform = forms.ChoiceField(choices=PLATFORM_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Order
        fields = ['cliente', 'address', 'observacoes']
        widgets = {
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Cliente'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Endereço completo...'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações...'}),
        }


class PaymentForm(forms.Form):
    """Formulário de pagamento"""
    PAYMENT_CHOICES = [
        ('dinheiro', '💵 Dinheiro'),
        ('pix', '📱 PIX'),
        ('credito', '💳 Cartão de Crédito'),
        ('debito', '💳 Cartão de Débito'),
    ]
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )


class AppSettingsForm(forms.ModelForm):
    """Formulário de configurações"""
    class Meta:
        model = AppSettings
        fields = ['store_name', 'slogan', 'logo', 'font', 'font_size', 
                  'primary_color', 'secondary_color', 'background_color', 'text_color', 'pix_key']
        widgets = {
            'store_name': forms.TextInput(attrs={'class': 'form-control'}),
            'slogan': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'font': forms.TextInput(attrs={'class': 'form-control'}),
            'font_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'background_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'text_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'pix_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chave PIX'}),
        }
