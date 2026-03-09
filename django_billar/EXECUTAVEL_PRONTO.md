# 🎉 Executável Criado com Sucesso!

O seu **Sistema de Restaurante** foi compilado como executável Windows (.exe).

## 📁 Localização do executável

```
C:\Users\Viviane\Desktop\billar\django_billar\dist\SistemaRestaurante\
```

## 📦 O que foi criado:

```
SistemaRestaurante/
├── SistemaRestaurante.exe      ← Arquivo principal (7 MB)
├── _internal/                  ← Bibliotecas Python empacotadas
├── docs/                       ← Documentação completa
├── media/                      ← Pasta para fotos de produtos
│   ├── products/
│   └── settings/
└── README.md                   ← Instruções de uso
```

## 🚀 Como usar o executável:

### Opção 1: Executar diretamente neste computador

1. **Navegue até a pasta:**
   ```cmd
   cd C:\Users\Viviane\Desktop\billar\django_billar\dist\SistemaRestaurante
   ```

2. **Duplo clique em:**
   ```
   SistemaRestaurante.exe
   ```

3. **O sistema irá:**
   - ✅ Iniciar servidores HTTP e WebSocket
   - ✅ Abrir navegador automaticamente
   - ✅ Conectar ao banco de dados (SQLite por padrão)

### Opção 2: Copiar para outro computador

1. **Copie toda a pasta `SistemaRestaurante` para outro PC Windows**

2. **No computador de destino, instale:**
   - Redis: `choco install redis-64` (obrigatório para tempo real)
   - PostgreSQL (opcional, recomendado para produção)

3. **Crie arquivo `.env` na pasta do executável:**
   ```env
   DB_ENGINE=sqlite
   DJANGO_SECRET_KEY=chave-secreta-aqui
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,SEU_IP
   REDIS_URL=redis://localhost:6379/0
   ENABLE_REALTIME=True
   ```

4. **Execute `SistemaRestaurante.exe`**

## ⚠️ IMPORTANTE: Dependências

O executável precisa que os seguintes serviços estejam instalados e rodando:

### Redis (Obrigatório)
Para recursos em tempo real (WebSocket).

**Instalar:**
```powershell
choco install redis-64
```

**Verificar se está rodando:**
```cmd
redis-cli ping
# Deve retornar: PONG
```

**Iniciar serviço:**
```cmd
sc start Redis
```

### PostgreSQL (Opcional)
Por padrão usa SQLite, mas PostgreSQL é recomendado para produção.

**Instalar:** https://www.postgresql.org/download/windows/

## 🔧 Troubleshooting

### "Redis connection failed"
**Solução:** Instale e inicie o Redis
```cmd
choco install redis-64
sc start Redis
```

### "Port 8000 already in use"
**Solução:** Outro programa está usando a porta
```cmd
netstat -ano | findstr :8000
# Matar processo: taskkill /PID NUMERO /F
```

### Executável não inicia
**Solução:** Execute via terminal para ver erros
```cmd
cd dist\SistemaRestaurante
.\SistemaRestaurante.exe
```

### WebSocket não conecta
**Solução:** Libere portas no firewall
```powershell
New-NetFirewallRule -DisplayName "Django HTTP" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Django WebSocket" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

## 📱 Acesso em Rede Local (LAN)

Para que tablets/celulares acessem o sistema:

1. **Descubra seu IP:**
   ```cmd
   ipconfig
   ```
   Exemplo: `192.168.1.100`

2. **No arquivo `.env` (ou no primeiro inicio):**
   ```env
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100
   ```

3. **Libere firewall (comando acima)**

4. **Acesse de outro dispositivo:**
   ```
   http://192.168.1.100:8000
   ```

## 📚 Documentação Completa

Dentro da pasta `docs/` você encontra:

- **DEPLOY_WINDOWS_LAN.md:** Guia completo de deploy em rede local
- **REALTIME_FEATURES.md:** Como funcionam as atualizações em tempo real
- **E mais...**

Ou acesse online: [github.com/seu-repo](URL_DO_REPOSITORIO)

## ✨ Recursos Incluídos

O executável já vem com:

- ✅ Sistema completo de pedidos
- ✅ Gestão de mesas e delivery
- ✅ Tela de cozinha com tempo real
- ✅ Dashboard do gerente
- ✅ Relatórios de vendas
- ✅ Controle de estoque
- ✅ PWA (instalável em celulares)
- ✅ WebSocket para atualizações instantâneas
- ✅ Notificações toast
- ✅ Impressão de cupons

## 🔐 Login Padrão

Se iniciou com banco novo, crie o primeiro usuário:

**Via interface:** Acesse `/admin/users/` após login inicial

**Via linha de comando:** Execute o executável e depois:
```python
# No terminal Python que abrirá
from restaurante.models import User
User.objects.create_superuser(
    username='admin',
    password='admin123',
    role='gerente'
)
```

---

**Sistema de Gestão de Restaurante v2.0**  
Build: Março 2026  
Desenvolvido com Django + Channels + WebSocket + PyInstaller
