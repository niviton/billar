# Billá Burger - Sistema de Gestão (Django)

Sistema completo de gestão para restaurantes/lanchonetes desenvolvido em Django.

## 📋 Funcionalidades

- **Login com Roles**: Garçom, Cozinha, Gerente
- **Gestão de Pedidos**: Mesa e Delivery
- **Cozinha**: Visualização e controle de pedidos
- **Cardápio**: Categorias e produtos com estoque
- **Relatórios**: Vendas por período, por garçom, produtos mais vendidos
- **Configurações**: Personalização da loja (nome, logo, cores)
- **Impressão**: Cupom não-fiscal com QR Code PIX

## 🚀 Como Executar

### 1. Criar ambiente virtual (recomendado)

```bash
cd django_billar
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Criar banco de dados

```bash
python manage.py makemigrations restaurante
python manage.py migrate
```

### 4. Criar dados iniciais

```bash
python manage.py shell
```

No shell, cole o conteúdo do arquivo `initial_data.py` ou execute:

```python
exec(open('initial_data.py').read())
```

Ou crie um superusuário manualmente:

```bash
python manage.py createsuperuser
```

### 5. Executar o servidor

```bash
python manage.py runserver
```

Acesse: http://127.0.0.1:8000

## 👤 Usuários Padrão

Após executar `initial_data.py`:

| Usuário | Senha | Role |
|---------|-------|------|
| gerente | admin | Gerente (acesso total) |

## 📱 Views por Role

- **Garçom** (`/garcom/`): Fazer pedidos, ver carrinho
- **Cozinha** (`/cozinha/`): Ver e marcar pedidos como prontos
- **Gerente** (`/admin-panel/`): Dashboard, relatórios, cardápio, equipe, configurações

## 🗂️ Estrutura do Projeto

```
django_billar/
├── billar_project/          # Configurações Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── restaurante/             # App principal
│   ├── models.py            # User, Category, Product, Order, OrderItem, AppSettings
│   ├── views.py             # Todas as views
│   ├── forms.py             # Formulários
│   ├── urls.py              # Rotas
│   └── admin.py             # Admin Django
├── templates/               # Templates HTML
│   ├── base.html
│   └── restaurante/
│       ├── login.html
│       ├── waiter.html
│       ├── kitchen.html
│       └── admin/
├── static/                  # Arquivos estáticos
├── media/                   # Uploads (logo, imagens de produtos)
├── manage.py
├── requirements.txt
└── initial_data.py          # Script de dados iniciais
```

## 🔧 Tecnologias

- **Backend**: Django 4.2+
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **Banco de Dados**: SQLite (padrão), pode ser alterado para PostgreSQL/MySQL
- **Formulários**: django-crispy-forms com crispy-bootstrap5

## 📝 Customização

### Alterar Cores/Logo

Acesse como gerente: **Configurações** > altere as cores e faça upload do logo.

### Adicionar Produtos

Acesse como gerente: **Cardápio** > **Novo Produto**

### Criar Usuários

Acesse como gerente: **Equipe** > **Novo Membro**

## 🐛 Problemas Comuns

### Erro de migração
```bash
python manage.py makemigrations
python manage.py migrate --run-syncdb
```

### Senha esquecida
```bash
python manage.py changepassword gerente
```

### Resetar banco de dados
```bash
del db.sqlite3
python manage.py migrate
python manage.py shell
# Cole o initial_data.py
```

## 📄 Licença

Projeto desenvolvido para fins educacionais.
