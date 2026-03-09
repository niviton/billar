 🍔 Billá Burger - Sistema de Gestão

## 📋 Opção 1: Usar o Executável Pronto (Recomendado)

### Passo a passo:

1. **Copie a pasta do executável** para o computador:
   ```
   dist\SistemaRestaurante\
   ```

2. **Execute o programa:**
   - Dê duplo clique em `SistemaRestaurante.exe`
   - O navegador abrirá automaticamente

3. **Acesse pelo celular/tablet:**
   - Conecte na mesma rede Wi-Fi
   - Abra o navegador e digite: `http://IP_DO_COMPUTADOR:8000`
   - Para descobrir o IP, no computador execute: `ipconfig`

### ⚠️ Firewall
Se outros dispositivos não conseguirem acessar, libere a porta no firewall (executar como Administrador):
```powershell
New-NetFirewallRule -DisplayName "Billa Burger" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## 📋 Opção 2: Rodar do Código Fonte (Git Clone)

### Requisitos:
- Python 3.11 ou superior: https://www.python.org/downloads/
- Git (opcional): https://git-scm.com/downloads

### Passo a passo:

1. **Clone o repositório:**
   ```powershell
   git clone <URL_DO_REPOSITORIO>
   cd django_billar
   ```

2. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Execute o sistema:**
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```

4. **Acesse no navegador:**
   - No mesmo PC: `http://localhost:8000`
   - Em outro dispositivo: `http://IP_DO_COMPUTADOR:8000`

---

## 📋 Opção 3: Gerar o Executável

Depois de clonar o repositório:

1. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Gere o executável:**
   ```powershell
   pyinstaller SistemaRestaurante.spec
   ```

3. **O executável estará em:**
   ```
   dist\SistemaRestaurante\SistemaRestaurante.exe
   ```

---

## 🔐 Login Padrão

Na primeira vez, crie um usuário administrador:

1. Acesse o sistema
2. Se não houver usuários, o sistema pedirá para criar
3. Ou pelo terminal:
   ```powershell
   python manage.py createsuperuser
   ```

---

## 📱 Instalar como App no Celular (PWA)

1. Acesse o sistema pelo navegador Chrome
2. Toque nos 3 pontinhos (⋮)
3. Selecione "Adicionar à tela inicial"
4. Pronto! O app aparecerá como um ícone

---

## 🆘 Problemas Comuns

### "Porta 8000 já está em uso"
```powershell
# Descobrir qual programa está usando
netstat -ano | findstr :8000

# Encerrar o processo (substitua XXXX pelo número do PID)
taskkill /PID XXXX /F
```

### "Não consigo acessar pelo celular"
1. Verifique se está na mesma rede Wi-Fi
2. Libere o firewall (comando acima)
3. Verifique o IP com `ipconfig`

### "Executável não abre"
Execute pelo terminal para ver o erro:
```powershell
cd dist\SistemaRestaurante
.\SistemaRestaurante.exe
```

---

## 📁 Estrutura de Arquivos

```
django_billar/
├── SistemaRestaurante.exe    ← Executável principal
├── manage.py                 ← Script Django (desenvolvimento)
├── requirements.txt          ← Dependências Python
├── db.sqlite3               ← Banco de dados
├── media/                   ← Fotos dos produtos
├── static/                  ← CSS, JS, imagens do sistema
└── templates/               ← Páginas HTML
```

---

**Desenvolvido para Billá Burger** 🍔
