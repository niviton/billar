
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  User, Product, Order, OrderItem, UserRole, OrderStatus, AppSettings, WaiterStats, OrderType
} from './types';
import { DEFAULT_PRODUCTS, DEFAULT_SETTINGS } from './constants';
import { StorageService } from './services/storage';
import { 
  Utensils, LayoutDashboard, LogOut, ShoppingBag, 
  ChefHat, Users, Settings, Plus, Minus, 
  CheckCircle2, Clock, Trash2, TrendingUp, 
  BarChart3, Package, AlertCircle, Search, Save, 
  User as UserIcon, CreditCard, Banknote, QrCode, 
  Printer, Edit3, Image as ImageIcon, FileText, Calendar, DollarSign, Shield, Lock,
  Smartphone, MapPin, Bike, MessageCircle, XCircle, X
} from 'lucide-react';

// --- COMPONENTS ---

const Toast = ({ message, type, onClose }: { message: string, type: 'success' | 'error', onClose: () => void }) => (
  <div className={`fixed bottom-4 right-4 z-[150] px-6 py-3 rounded-xl shadow-2xl flex items-center gap-3 animate-bounce ${type === 'success' ? 'bg-emerald-600' : 'bg-red-600'} text-white`}>
    <span>{message}</span>
    <button onClick={onClose} className="hover:opacity-70">✕</button>
  </div>
);

// --- MAIN APP ---

const App: React.FC = () => {
  // Auth State
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [view, setView] = useState<'login' | 'waiter' | 'kitchen' | 'admin'>('login');
  const [adminView, setAdminView] = useState<'dashboard' | 'reports' | 'menu' | 'users' | 'settings' | 'online'>('dashboard');

  // App Data
  const [users, setUsers] = useState<User[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);

  // UI State
  const [toast, setToast] = useState<{ message: string, type: 'success' | 'error' } | null>(null);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  
  // Modals State
  const [closingOrderId, setClosingOrderId] = useState<string | null>(null);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [printingOrder, setPrintingOrder] = useState<Order | null>(null);
  const [splitItems, setSplitItems] = useState<{[key: string]: number}>({}); // { itemId_idx: qtyToPay }
  
  // User Management State
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [userForm, setUserForm] = useState({ username: '', password: '', role: 'garcom' as UserRole });

  // Online Order State
  const [onlineOrderForm, setOnlineOrderForm] = useState({ customer: '', address: '', platform: 'Whatsapp' });

  // Waiter State
  const [currentTable, setCurrentTable] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [cart, setCart] = useState<OrderItem[]>([]);
  const [orderObs, setOrderObs] = useState('');

  // Report State
  const [reportPeriod, setReportPeriod] = useState<'day' | 'week' | 'month' | 'year'>('day');

  // Initial Data Load
  useEffect(() => {
    const savedUsers = StorageService.getUsers();
    if (savedUsers.length === 0) {
      const initialUsers: User[] = [{ id: '1', username: 'gerente', password: 'admin', role: 'gerente' }];
      StorageService.saveUsers(initialUsers);
      setUsers(initialUsers);
    } else {
      setUsers(savedUsers);
    }

    const savedProducts = StorageService.getProducts();
    if (savedProducts.length === 0) {
      StorageService.saveProducts(DEFAULT_PRODUCTS);
      setProducts(DEFAULT_PRODUCTS);
    } else {
      setProducts(savedProducts);
    }

    const savedOrders = StorageService.getOrders();
    setOrders(savedOrders);

    const savedSettings = StorageService.getSettings();
    if (savedSettings) setSettings(savedSettings);
  }, []);

  // Save changes
  useEffect(() => { if (users.length) StorageService.saveUsers(users); }, [users]);
  useEffect(() => { if (products.length) StorageService.saveProducts(products); }, [products]);
  useEffect(() => { StorageService.saveOrders(orders); }, [orders]);
  useEffect(() => { StorageService.saveSettings(settings); }, [settings]);

  // Clear cart when switching to online view to avoid state mixing
  useEffect(() => {
    if (adminView === 'online') {
      setCart([]);
      setOrderObs('');
      setOnlineOrderForm({ customer: '', address: '', platform: 'Whatsapp' });
    }
  }, [adminView]);

  // --- ACTIONS ---

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const user = users.find(u => u.username === loginForm.username && u.password === loginForm.password);
    if (user) {
      setCurrentUser(user);
      if (user.role === 'gerente') setView('admin');
      else if (user.role === 'garcom') setView('waiter');
      else setView('kitchen');
      showToast(`Bem-vindo, ${user.username}!`);
    } else {
      showToast('Usuário ou senha incorretos', 'error');
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setView('login');
    setCart([]);
    setCurrentTable('');
    setCustomerName('');
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>, callback: (base64: string) => void) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        callback(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // --- WAITER LOGIC ---
  useEffect(() => {
    if (currentTable) {
      const activeOrder = orders.find(o => o.mesa === currentTable && o.status !== 'finalizado' && o.status !== 'cancelado');
      if (activeOrder) setCustomerName(activeOrder.cliente);
    }
  }, [currentTable, orders]);

  const selectActiveTable = (mesa: string, cliente: string) => {
    setCurrentTable(mesa);
    setCustomerName(cliente);
  };

  const clearWaiterSelection = () => {
    setCurrentTable('');
    setCustomerName('');
    setCart([]);
    setOrderObs('');
    showToast('Seleção limpa');
  };

  const addToCart = (product: Product) => {
    if (product.stock <= 0) return showToast('Produto sem estoque', 'error');
    setCart(prev => {
      const existing = prev.find(item => item.id === product.id);
      if (existing) {
        if (existing.qty >= product.stock) {
          showToast('Limite de estoque atingido', 'error');
          return prev;
        }
        return prev.map(item => item.id === product.id ? { ...item, qty: item.qty + 1 } : item);
      }
      return [...prev, { id: product.id, name: product.name, price: product.price, qty: 1, icon: product.icon, isImage: product.isImage }];
    });
  };

  const removeFromCart = (id: string) => {
    setCart(prev => {
      const existing = prev.find(item => item.id === id);
      if (existing && existing.qty > 1) {
        return prev.map(item => item.id === id ? { ...item, qty: item.qty - 1 } : item);
      }
      return prev.filter(item => item.id !== id);
    });
  };

  const submitOrder = (type: OrderType = 'dine-in', deliveryDetails?: { customer: string, address: string, platform: string }) => {
    const table = type === 'delivery' ? 'DELIVERY' : currentTable;
    // For delivery, prepend the platform icon/name to the client name for kitchen visibility
    const client = type === 'delivery' 
      ? `[${deliveryDetails?.platform}] ${deliveryDetails?.customer || 'Cliente'}`
      : customerName || 'Cliente';
    
    // Address logic: Stored in a separate field now, NOT baked into observations for clean display
    const address = type === 'delivery' ? deliveryDetails?.address : undefined;
    const obs = orderObs; // Observations contain ONLY food instructions now

    if (!table && type === 'dine-in') return showToast('Informe o número da mesa', 'error');
    if (type === 'delivery' && !deliveryDetails?.customer) return showToast('Informe o nome do cliente', 'error');
    if (cart.length === 0) return showToast('O pedido está vazio', 'error');

    // For delivery, always create new order. For dine-in, check existing.
    const activeOrderIndex = type === 'dine-in' 
      ? orders.findIndex(o => o.mesa === table && o.status !== 'finalizado' && o.status !== 'cancelado')
      : -1;

    if (activeOrderIndex !== -1) {
      const updatedOrders = [...orders];
      const existingOrder = updatedOrders[activeOrderIndex];
      const newItems = [...existingOrder.items];
      cart.forEach(cartItem => {
        const itemIndex = newItems.findIndex(ni => ni.id === cartItem.id);
        if (itemIndex !== -1) newItems[itemIndex].qty += cartItem.qty;
        else newItems.push(cartItem);
      });

      updatedOrders[activeOrderIndex] = {
        ...existingOrder,
        items: newItems,
        total: newItems.reduce((acc, item) => acc + (item.price * item.qty), 0),
        status: 'cozinha',
        timestamp: Date.now(),
        cliente: client,
        observacoes: obs ? (existingOrder.observacoes ? existingOrder.observacoes + " | " + obs : obs) : existingOrder.observacoes
      };
      setOrders(updatedOrders);
      showToast('Pedido atualizado para mesa ' + table);
    } else {
      const newOrder: Order = {
        id: Math.random().toString(36).substr(2, 9),
        mesa: table,
        cliente: client,
        items: [...cart],
        observacoes: obs,
        total: cart.reduce((acc, item) => acc + (item.price * item.qty), 0),
        status: 'cozinha',
        timestamp: Date.now(),
        waiterId: currentUser?.id || 'unknown',
        orderType: type,
        address: address
      };
      setOrders(prev => [...prev, newOrder]);
      showToast('Novo pedido enviado!');
    }

    setProducts(prev => prev.map(p => {
      const cartItem = cart.find(ci => ci.id === p.id);
      return cartItem ? { ...p, stock: p.stock - cartItem.qty } : p;
    }));

    setCart([]);
    if (type === 'dine-in') {
      setCurrentTable('');
      setCustomerName('');
    } else {
      setOnlineOrderForm({ customer: '', address: '', platform: 'Whatsapp' });
    }
    setOrderObs('');
  };

  // --- KITCHEN LOGIC ---
  const markAsReady = (orderId: string) => {
    setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'pronto' } : o));
    showToast('Pedido marcado como pronto!');
  };

  // --- ADMIN LOGIC ---
  const finalizeOrder = (orderId: string, paymentMethod: string) => {
    setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'finalizado', pagamento: paymentMethod } : o));
    setClosingOrderId(null);
    showToast(`Conta fechada! Pagamento: ${paymentMethod}`);
  };

  const cancelOrder = (orderId: string) => {
    if (currentUser?.role !== 'gerente') return showToast('Apenas gerentes podem cancelar pedidos', 'error');
    if (window.confirm('Tem certeza que deseja CANCELAR este pedido?')) {
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'cancelado' } : o));
      showToast('Pedido Cancelado com sucesso.', 'error');
    }
  };

  const handleProductSave = (p: Product) => {
    if (products.find(prod => prod.id === p.id)) {
      setProducts(prev => prev.map(prod => prod.id === p.id ? p : prod));
      showToast('Produto atualizado');
    } else {
      setProducts(prev => [...prev, { ...p, id: Math.random().toString(36).substr(2, 9) }]);
      showToast('Produto criado');
    }
    setEditingProduct(null);
  };

  const deleteProduct = (id: string) => {
    setProducts(prev => prev.filter(p => p.id !== id));
    showToast('Produto removido');
  };

  const handleAddUser = () => {
    if (!userForm.username || !userForm.password) return showToast('Preencha todos os campos', 'error');
    if (users.find(u => u.username === userForm.username)) return showToast('Usuário já existe', 'error');
    
    const newUser: User = {
      id: Math.random().toString(36).substr(2, 9),
      username: userForm.username,
      password: userForm.password,
      role: userForm.role
    };

    setUsers([...users, newUser]);
    setUserModalOpen(false);
    setUserForm({ username: '', password: '', role: 'garcom' });
    showToast('Membro adicionado à equipe!');
  };

  const handleDeleteUser = (userId: string) => {
    if (currentUser?.id === userId) return showToast('Você não pode excluir a si mesmo.', 'error');
    setUsers(users.filter(u => u.id !== userId));
    showToast('Usuário removido da equipe.');
  };

  // --- BILL PRINTING LOGIC ---
  const openPrintModal = (order: Order) => {
    // Initialize split items with full quantities
    const initialSplit: {[key: string]: number} = {};
    order.items.forEach(item => {
      initialSplit[item.id] = item.qty;
    });
    setSplitItems(initialSplit);
    setPrintingOrder(order);
  };

  const handlePrint = () => {
    if (!printingOrder) return;
    
    // Calculate total based on split selection
    let subtotal = 0;
    const itemsToPrint = printingOrder.items.filter(item => (splitItems[item.id] || 0) > 0).map(item => {
      const qty = splitItems[item.id];
      const total = qty * item.price;
      subtotal += total;
      return { ...item, qty, total };
    });

    if (itemsToPrint.length === 0) return showToast('Selecione itens para imprimir', 'error');

    const printContent = `
      <html>
        <head>
          <title>Cupom Fiscal - ${settings.storeName}</title>
          <style>
            body { font-family: 'Courier New', monospace; font-size: 14px; width: 300px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 10px; border-bottom: 1px dashed #000; padding-bottom: 10px; }
            .item { display: flex; justify-content: space-between; margin-bottom: 5px; }
            .total { border-top: 1px dashed #000; margin-top: 10px; padding-top: 10px; font-weight: bold; font-size: 16px; text-align: right; }
            .footer { text-align: center; margin-top: 20px; font-size: 10px; }
            .qrcode { text-align: center; margin-top: 20px; border-top: 1px dashed #000; padding-top: 10px; }
            .qrcode img { width: 150px; height: 150px; }
            .address { border: 1px solid #000; padding: 5px; margin: 10px 0; text-align:center; font-weight:bold; }
          </style>
        </head>
        <body>
          <div class="header">
            ${settings.logo ? `<img src="${settings.logo}" style="width: 50px; height: 50px; margin-bottom: 5px;" />` : ''}
            <h2 style="margin:0">${settings.storeName}</h2>
            <p>${settings.slogan}</p>
            <p>Mesa: ${printingOrder.mesa} | Cliente: ${printingOrder.cliente}</p>
            <p>Data: ${new Date().toLocaleString()}</p>
            <p><strong>CUPOM NÃO FISCAL</strong></p>
          </div>
          ${printingOrder.address ? `<div class="address">ENTREGA: ${printingOrder.address}</div>` : ''}
          <div class="items">
            ${itemsToPrint.map(item => `
              <div class="item">
                <span>${item.qty}x ${item.name}</span>
                <span>R$ ${item.total.toFixed(2)}</span>
              </div>
            `).join('')}
          </div>
          <div class="total">
            TOTAL: R$ ${subtotal.toFixed(2)}
          </div>
          <div class="qrcode">
             <p>PAGAMENTO VIA PIX</p>
             <!-- Static QR Code Placeholder -->
             <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=00020126360014BR.GOV.BCB.PIX0114+551199999999520400005303986540${subtotal.toFixed(2).replace('.', '')}5802BR5913Billa Burger6009Sao Paulo62070503***6304" alt="QR Code Pix" />
             <p style="font-size: 10px;">Escaneie para pagar</p>
          </div>
          <div class="footer">
            <p>Obrigado pela preferência!</p>
            <p>Volte sempre.</p>
          </div>
          <script>window.print();</script>
        </body>
      </html>
    `;

    const printWindow = window.open('', '', 'width=400,height=600');
    if (printWindow) {
      printWindow.document.write(printContent);
      printWindow.document.close();
    }
  };

  // --- STATS & REPORTS ---
  const activeOrders = orders.filter(o => o.status !== 'finalizado' && o.status !== 'cancelado');
  const kitchenOrders = orders.filter(o => o.status === 'cozinha');

  const stats = useMemo(() => {
    const today = new Date().setHours(0,0,0,0);
    const now = new Date();
    let startTime = today;

    if (reportPeriod === 'week') {
      const d = new Date(now);
      const day = d.getDay();
      const diff = d.getDate() - day + (day === 0 ? -6 : 1);
      startTime = new Date(d.setDate(diff)).setHours(0,0,0,0);
    } else if (reportPeriod === 'month') {
      startTime = new Date(now.getFullYear(), now.getMonth(), 1).getTime();
    } else if (reportPeriod === 'year') {
      startTime = new Date(now.getFullYear(), 0, 1).getTime();
    }

    const filteredOrders = orders.filter(o => o.status === 'finalizado' && o.timestamp >= startTime);
    const revenue = filteredOrders.reduce((acc, o) => acc + o.total, 0);

    // Waiter Stats
    const waiterMap: {[key: string]: WaiterStats} = {};
    filteredOrders.forEach(order => {
      const wid = order.waiterId;
      const wName = users.find(u => u.id === wid)?.username || 'Desconhecido';
      
      if (!waiterMap[wid]) {
        waiterMap[wid] = { id: wid, name: wName, totalSales: 0, ordersCount: 0, averageTicket: 0 };
      }
      waiterMap[wid].totalSales += order.total;
      waiterMap[wid].ordersCount += 1;
    });

    const waiterRanking = Object.values(waiterMap).map(w => ({
      ...w,
      averageTicket: w.totalSales / w.ordersCount
    })).sort((a, b) => b.totalSales - a.totalSales);

    // Low Stock
    const lowStock = products.filter(p => p.stock <= 5);

    return { revenue, count: filteredOrders.length, waiterRanking, lowStock };
  }, [orders, products, reportPeriod, users]);

  // --- STYLES ---
  const dynamicStyles = `
    :root {
      --bg: ${settings.colors.background};
      --surface: ${settings.colors.surface};
      --text: ${settings.colors.text};
      --primary: ${settings.colors.primary};
      --secondary: ${settings.colors.secondary};
      --font-family: '${settings.font}', sans-serif;
    }
    body { background-color: var(--bg); color: var(--text); font-family: var(--font-family); }
  `;

  // --- VIEWS ---

  if (view === 'login') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4 relative overflow-hidden">
        <style>{dynamicStyles}</style>
        {/* Background blobs */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600 rounded-full blur-[150px] opacity-20 animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-red-600 rounded-full blur-[150px] opacity-20 animate-pulse delay-700"></div>

        <div className="bg-white/10 backdrop-blur-xl p-10 rounded-[2.5rem] shadow-2xl w-full max-w-md border border-white/20 animate-in fade-in zoom-in duration-500 z-10">
          <div className="text-center mb-10">
            <div className="w-28 h-28 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner ring-4 ring-white/10 overflow-hidden">
              {settings.logo ? (
                 <img src={settings.logo} alt="Logo" className="w-full h-full object-cover" />
              ) : (
                <Utensils size={48} className="text-white" />
              )}
            </div>
            <h1 className="text-4xl font-black text-white tracking-tighter">{settings.storeName}</h1>
            <p className="text-white/60 font-medium mt-1">{settings.slogan}</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-white/50 uppercase tracking-widest ml-1">Usuário</label>
              <input 
                type="text" 
                value={loginForm.username}
                onChange={e => setLoginForm({...loginForm, username: e.target.value})}
                className="w-full px-5 py-4 bg-slate-800/50 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:ring-2 focus:ring-red-500/50 outline-none transition-all font-medium"
                placeholder="Ex: gerente"
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-white/50 uppercase tracking-widest ml-1">Senha</label>
              <input 
                type="password" 
                value={loginForm.password}
                onChange={e => setLoginForm({...loginForm, password: e.target.value})}
                className="w-full px-5 py-4 bg-slate-800/50 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:ring-2 focus:ring-red-500/50 outline-none transition-all font-medium"
                placeholder="••••••••"
                required
              />
            </div>
            <button 
              type="submit" 
              className="w-full py-5 bg-gradient-to-r from-red-600 to-orange-600 text-white rounded-[1.5rem] font-bold shadow-xl hover:shadow-red-600/30 hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              Entrar no Sistema
            </button>
          </form>
        </div>
        {toast && <Toast {...toast} onClose={() => setToast(null)} />}
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-slate-50">
      <style>{dynamicStyles}</style>
      
      {/* Header */}
      <header className="h-20 bg-white border-b border-slate-200 flex items-center justify-between px-8 z-30 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl overflow-hidden bg-slate-100 flex items-center justify-center border border-slate-200">
             {settings.logo ? <img src={settings.logo} className="w-full h-full object-cover" /> : <Utensils size={20} className="text-slate-400" />}
          </div>
          <div>
            <h2 className="text-xl font-black tracking-tighter text-slate-800 leading-none">{settings.storeName}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className={`w-2 h-2 rounded-full ${currentUser?.role === 'cozinha' ? 'bg-orange-500' : 'bg-emerald-500'} animate-pulse`}></span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                {currentUser?.role === 'gerente' ? 'Administração' : currentUser?.role === 'garcom' ? 'Salão' : 'Cozinha'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="text-right hidden md:block">
            <p className="text-sm font-bold text-slate-700">{currentUser?.username}</p>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{currentUser?.role}</p>
          </div>
          <button 
            onClick={handleLogout}
            className="p-3 bg-slate-100 text-slate-500 rounded-2xl hover:bg-red-50 hover:text-red-600 transition-all group border border-transparent hover:border-red-100"
          >
            <LogOut size={20} className="group-hover:rotate-12 transition-transform" />
          </button>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Admin Sidebar */}
        {view === 'admin' && (
          <nav className="w-72 bg-white border-r border-slate-200 flex flex-col p-6 gap-2 z-20 shadow-[4px_0_24px_-12px_rgba(0,0,0,0.1)]">
            <div className="mb-6 px-4">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Menu Principal</p>
            </div>
            {[
              { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
              { id: 'reports', icon: BarChart3, label: 'Relatórios' },
              { id: 'menu', icon: ShoppingBag, label: 'Cardápio' },
              { id: 'users', icon: Users, label: 'Equipe' },
              { id: 'online', icon: Smartphone, label: 'Pedidos Online' }, // NEW BUTTON
              { id: 'settings', icon: Settings, label: 'Configurações' },
            ].map(item => (
              <button
                key={item.id}
                onClick={() => {
                   if (item.id === 'online') {
                     // Reset states to ensure clean view
                     setAdminView('online');
                     setCart([]);
                   } else {
                     setAdminView(item.id as any);
                   }
                }}
                className={`flex items-center gap-4 px-5 py-4 rounded-2xl font-bold text-sm transition-all group ${adminView === item.id ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/20' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'}`}
              >
                <item.icon size={20} className={`${adminView === item.id ? 'text-white' : 'text-slate-400 group-hover:text-slate-900'}`} />
                {item.label}
              </button>
            ))}
          </nav>
        )}

        <main className="flex-1 overflow-y-auto bg-slate-50/50 relative">
          <div className="max-w-[1600px] mx-auto p-8 h-full">

          {/* --- WAITER VIEW --- */}
          {view === 'waiter' && (
            <div className="grid grid-cols-12 gap-8 h-full">
              <div className="col-span-12 lg:col-span-8 flex flex-col gap-8">
                
                {/* Active Tables Horizontal Scroll */}
                {activeOrders.filter(o => o.orderType !== 'delivery').length > 0 && (
                   <div className="w-full overflow-x-auto pb-2 custom-scrollbar">
                     <div className="flex gap-4">
                        {activeOrders.filter(o => o.orderType !== 'delivery').map(order => (
                          <button 
                            key={order.id}
                            onClick={() => selectActiveTable(order.mesa, order.cliente)}
                            className={`flex-shrink-0 p-4 rounded-2xl border flex items-center gap-3 transition-all min-w-[180px] ${currentTable === order.mesa ? 'bg-slate-900 text-white border-slate-900 shadow-lg' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}
                          >
                             <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-black text-lg ${currentTable === order.mesa ? 'bg-white/20' : 'bg-slate-100 text-slate-800'}`}>
                               {order.mesa}
                             </div>
                             <div className="text-left">
                               <p className="text-xs font-bold uppercase tracking-wide opacity-70">Mesa</p>
                               <p className="font-bold truncate max-w-[100px]">{order.cliente}</p>
                             </div>
                          </button>
                        ))}
                     </div>
                   </div>
                )}

                <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-slate-200 flex flex-col gap-6">
                  <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1 bg-slate-50 p-2 rounded-2xl border border-slate-100 flex items-center gap-4">
                      <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center text-slate-400 shadow-sm">
                        <Utensils size={20} />
                      </div>
                      <div className="flex-1">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Mesa</label>
                        <input 
                          type="number" 
                          value={currentTable}
                          onChange={e => setCurrentTable(e.target.value)}
                          className="w-full bg-transparent font-bold text-xl text-slate-800 outline-none"
                          placeholder="00"
                        />
                      </div>
                    </div>
                    <div className="flex-[2] bg-slate-50 p-2 rounded-2xl border border-slate-100 flex items-center gap-4">
                      <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center text-slate-400 shadow-sm">
                        <UserIcon size={20} />
                      </div>
                      <div className="flex-1">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Cliente</label>
                        <input 
                          type="text" 
                          value={customerName}
                          onChange={e => setCustomerName(e.target.value)}
                          className="w-full bg-transparent font-bold text-xl text-slate-800 outline-none"
                          placeholder="Nome do cliente"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6 pb-20">
                  {products.map(p => (
                    <button
                      key={p.id}
                      onClick={() => addToCart(p)}
                      disabled={p.stock <= 0}
                      className={`group p-4 rounded-[2rem] border transition-all relative flex flex-col items-center text-center overflow-hidden ${p.stock > 0 ? 'bg-white border-slate-200 hover:border-red-200 hover:shadow-xl hover:shadow-red-500/5 hover:-translate-y-1' : 'bg-slate-100 border-transparent opacity-60 grayscale'}`}
                    >
                      <div className="w-24 h-24 mb-4 rounded-full overflow-hidden flex items-center justify-center bg-slate-50 shadow-inner group-hover:scale-110 transition-transform duration-300">
                        {p.isImage ? (
                          <img src={p.icon} alt={p.name} className="w-full h-full object-cover" />
                        ) : (
                          <span className="text-5xl">{p.icon}</span>
                        )}
                      </div>
                      <h4 className="font-bold text-slate-800 line-clamp-1 w-full text-sm">{p.name}</h4>
                      <div className="flex items-center justify-between w-full mt-auto pt-3 border-t border-slate-50">
                        <span className="text-sm font-black text-slate-800">R$ {p.price.toFixed(2)}</span>
                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${p.stock <= 5 ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-400'}`}>
                          {p.stock}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="col-span-12 lg:col-span-4 h-full relative">
                <div className="bg-white rounded-[2.5rem] shadow-xl border border-slate-200 p-6 flex flex-col h-[calc(100vh-8rem)] sticky top-0">
                  <div className="flex items-center justify-between mb-6 pb-6 border-b border-slate-100">
                    <h3 className="text-lg font-black text-slate-800">Pedido Atual</h3>
                    <div className="flex gap-2">
                      <button 
                        onClick={clearWaiterSelection} 
                        className="bg-slate-100 hover:bg-red-100 text-slate-400 hover:text-red-500 px-3 py-1 rounded-full text-xs font-bold transition-colors flex items-center gap-1"
                        title="Limpar mesa e carrinho"
                      >
                         <X size={14} /> Cancelar/Limpar
                      </button>
                      <div className="bg-slate-900 text-white px-3 py-1 rounded-full text-xs font-bold">
                        {cart.reduce((a, b) => a + b.qty, 0)} itens
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                    {cart.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-slate-300 text-center">
                        <ShoppingBag size={48} className="mb-4 opacity-50" />
                        <p className="text-xs font-bold uppercase tracking-widest">Seu carrinho está vazio</p>
                      </div>
                    ) : (
                      cart.map(item => (
                        <div key={item.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-2xl border border-slate-100">
                          <div className="w-10 h-10 rounded-lg overflow-hidden bg-white flex items-center justify-center border border-slate-100 shrink-0">
                            {item.isImage ? <img src={item.icon} className="w-full h-full object-cover" /> : <span className="text-xl">{item.icon}</span>}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-bold text-xs text-slate-800 truncate">{item.name}</p>
                            <p className="text-[10px] font-bold text-slate-500">R$ {item.price.toFixed(2)}</p>
                          </div>
                          <div className="flex items-center gap-2 bg-white rounded-lg p-1 shadow-sm border border-slate-100">
                            <button onClick={() => removeFromCart(item.id)} className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-red-500"><Minus size={12}/></button>
                            <span className="font-bold text-xs w-4 text-center">{item.qty}</span>
                            <button onClick={() => addToCart(products.find(p=>p.id===item.id)!)} className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-emerald-500"><Plus size={12}/></button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="mt-6 space-y-4 pt-6 border-t border-slate-100">
                    <textarea 
                      value={orderObs}
                      onChange={e => setOrderObs(e.target.value)}
                      className="w-full h-16 bg-slate-50 rounded-xl p-3 text-xs outline-none border border-slate-200 focus:border-slate-400 transition-all resize-none"
                      placeholder="Observações (Ex: Sem cebola)"
                    />
                    <button 
                      onClick={() => submitOrder('dine-in')}
                      className="w-full py-4 bg-slate-900 text-white rounded-xl font-bold shadow-lg shadow-slate-900/20 hover:bg-black active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                    >
                      <ChefHat size={18} />
                      {orders.some(o => o.mesa === currentTable && o.status !== 'finalizado' && o.status !== 'cancelado') ? 'Atualizar Pedido' : 'Enviar Pedido'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* --- ONLINE ORDER VIEW (WAITER-STYLE REFACTOR) --- */}
          {view === 'admin' && adminView === 'online' && (
             <div className="grid grid-cols-12 gap-8 h-full pb-20">
               <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
                 <div className="bg-orange-50 p-6 rounded-[2rem] border border-orange-100 flex items-center gap-4">
                    <div className="w-16 h-16 bg-orange-500 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-orange-500/20">
                      <Smartphone size={32} />
                    </div>
                    <div>
                      <h3 className="text-3xl font-black text-slate-800">Novo Pedido Online</h3>
                      <p className="text-orange-600 font-bold">Delivery & Takeout</p>
                    </div>
                 </div>

                 <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
                    {products.map(p => (
                      <button
                        key={p.id}
                        onClick={() => addToCart(p)}
                        disabled={p.stock <= 0}
                        className={`group p-4 rounded-[2rem] border transition-all relative flex flex-col items-center text-center overflow-hidden ${p.stock > 0 ? 'bg-white border-slate-200 hover:border-orange-200 hover:shadow-xl hover:shadow-orange-500/5 hover:-translate-y-1' : 'bg-slate-100 border-transparent opacity-60 grayscale'}`}
                      >
                        <div className="w-24 h-24 mb-4 rounded-full overflow-hidden flex items-center justify-center bg-slate-50 shadow-inner group-hover:scale-110 transition-transform duration-300">
                          {p.isImage ? (
                            <img src={p.icon} alt={p.name} className="w-full h-full object-cover" />
                          ) : (
                            <span className="text-5xl">{p.icon}</span>
                          )}
                        </div>
                        <h4 className="font-bold text-slate-800 line-clamp-1 w-full text-sm">{p.name}</h4>
                        <div className="flex items-center justify-between w-full mt-auto pt-3 border-t border-slate-50">
                          <span className="text-sm font-black text-slate-800">R$ {p.price.toFixed(2)}</span>
                          <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${p.stock <= 5 ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-400'}`}>
                            {p.stock}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
               </div>

               <div className="col-span-12 lg:col-span-4 h-full relative">
                  <div className="bg-white rounded-[2.5rem] shadow-xl border border-slate-200 p-6 flex flex-col h-[calc(100vh-8rem)] sticky top-0">
                    <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100">
                      <h3 className="text-lg font-black text-slate-800">Dados da Entrega</h3>
                      <div className="bg-orange-500 text-white px-3 py-1 rounded-full text-xs font-bold">
                        Delivery
                      </div>
                    </div>

                    <div className="space-y-4 mb-6">
                      <div className="flex gap-3">
                         <div className="flex-1">
                           <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block ml-1">Cliente</label>
                           <div className="relative">
                             <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
                             <input 
                               type="text" 
                               value={onlineOrderForm.customer} 
                               onChange={e => setOnlineOrderForm({...onlineOrderForm, customer: e.target.value})}
                               className="w-full pl-9 pr-3 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-sm text-slate-800"
                               placeholder="Nome"
                             />
                           </div>
                         </div>
                         <div className="w-1/3">
                           <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block ml-1">Origem</label>
                           <div className="relative">
                             <select 
                               value={onlineOrderForm.platform}
                               onChange={e => setOnlineOrderForm({...onlineOrderForm, platform: e.target.value})}
                               className="w-full px-3 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-sm text-slate-800 appearance-none"
                             >
                               <option value="Whatsapp">Zap</option>
                               <option value="iFood">iFood</option>
                               <option value="Tel">Tel</option>
                             </select>
                           </div>
                         </div>
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block ml-1">Endereço</label>
                         <div className="relative">
                           <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
                           <input 
                             type="text" 
                             value={onlineOrderForm.address} 
                             onChange={e => setOnlineOrderForm({...onlineOrderForm, address: e.target.value})}
                             className="w-full pl-9 pr-3 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-sm text-slate-800"
                             placeholder="Rua, Bairro..."
                           />
                         </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between mb-2 pt-4 border-t border-slate-100">
                       <span className="text-xs font-bold text-slate-400 uppercase">Itens do Pedido</span>
                       <span className="text-xs font-bold text-slate-800">{cart.reduce((a,b) => a+b.qty, 0)} un.</span>
                    </div>

                    <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                      {cart.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-300 text-center min-h-[150px]">
                          <ShoppingBag size={48} className="mb-4 opacity-50" />
                          <p className="text-xs font-bold uppercase tracking-widest">Carrinho vazio</p>
                        </div>
                      ) : (
                        cart.map(item => (
                          <div key={item.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-2xl border border-slate-100">
                            <div className="w-10 h-10 rounded-lg overflow-hidden bg-white flex items-center justify-center border border-slate-100 shrink-0">
                              {item.isImage ? <img src={item.icon} className="w-full h-full object-cover" /> : <span className="text-xl">{item.icon}</span>}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-bold text-xs text-slate-800 truncate">{item.name}</p>
                              <p className="text-[10px] font-bold text-slate-500">R$ {item.price.toFixed(2)}</p>
                            </div>
                            <div className="flex items-center gap-2 bg-white rounded-lg p-1 shadow-sm border border-slate-100">
                              <button onClick={() => removeFromCart(item.id)} className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-red-500"><Minus size={12}/></button>
                              <span className="font-bold text-xs w-4 text-center">{item.qty}</span>
                              <button onClick={() => addToCart(products.find(p=>p.id===item.id)!)} className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-emerald-500"><Plus size={12}/></button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    <div className="mt-4 space-y-4 pt-4 border-t border-slate-100">
                      <textarea 
                        value={orderObs}
                        onChange={e => setOrderObs(e.target.value)}
                        className="w-full h-14 bg-slate-50 rounded-xl p-3 text-xs outline-none border border-slate-200 focus:border-slate-400 transition-all resize-none"
                        placeholder="Obs: Sem picles..."
                      />
                      <button 
                        onClick={() => submitOrder('delivery', onlineOrderForm)}
                        className="w-full py-4 bg-orange-500 text-white rounded-xl font-bold shadow-lg shadow-orange-500/20 hover:bg-orange-600 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                      >
                        <Bike size={20} />
                        Confirmar Delivery
                      </button>
                    </div>
                  </div>
               </div>
             </div>
          )}

          {/* --- KITCHEN VIEW (UPDATED FONTS) --- */}
          {view === 'kitchen' && (
             <div className="h-full flex flex-col">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h3 className="text-4xl font-black tracking-tighter text-slate-800">Monitor de Cozinha</h3>
                  <p className="text-slate-400 font-medium text-lg">Gerencie o fluxo de pedidos</p>
                </div>
                <div className="bg-white px-6 py-4 rounded-xl shadow-sm border border-slate-200 text-xl font-bold text-slate-600">
                  {kitchenOrders.length} Pedidos Pendentes
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {kitchenOrders.map(order => {
                  const elapsed = Math.floor((Date.now() - order.timestamp) / 60000);
                  const isLate = elapsed >= 15;
                  const isDelivery = order.orderType === 'delivery';
                  
                  return (
                    <div key={order.id} className={`bg-white rounded-[2rem] shadow-lg border overflow-hidden flex flex-col ${isLate ? 'border-red-500 ring-4 ring-red-500/10' : 'border-slate-200'}`}>
                      <div className={`p-6 flex flex-col justify-between ${isLate ? 'bg-red-50' : 'bg-slate-50'}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                             <div className={`w-16 h-16 rounded-2xl flex items-center justify-center font-black text-2xl text-white ${isDelivery ? 'bg-orange-500' : 'bg-slate-800'}`}>
                               {isDelivery ? <Bike size={32} /> : order.mesa}
                             </div>
                             <div>
                               <p className="text-xs font-bold uppercase tracking-widest text-slate-500">#{order.id.slice(0,4)} {isDelivery && '• DELIVERY'}</p>
                               <p className="text-2xl font-black text-slate-800">{order.cliente}</p>
                             </div>
                          </div>
                          <div className={`text-3xl font-black ${isLate ? 'text-red-600' : 'text-slate-800'}`}>{elapsed}m</div>
                        </div>
                        {order.address && (
                          <div className="mt-4 flex items-center gap-2 text-slate-600 bg-white/50 p-2 rounded-lg border border-slate-200/50">
                            <MapPin size={16} className="shrink-0" />
                            <span className="text-sm font-bold leading-tight">{order.address}</span>
                          </div>
                        )}
                      </div>
                      <div className="p-6 flex-1 space-y-3 overflow-y-auto max-h-80">
                         {order.items.map((item, idx) => (
                           <div key={idx} className="flex items-center gap-4 text-xl font-bold text-slate-700 border-b border-slate-100 pb-3 last:border-0">
                             <span className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center text-lg">{item.qty}</span>
                             <span className="flex-1">{item.name}</span>
                           </div>
                         ))}
                         {order.observacoes && (
                           <div className="bg-amber-50 text-amber-800 p-4 rounded-2xl text-lg font-bold mt-4 border border-amber-100">
                             ⚠️ {order.observacoes}
                           </div>
                         )}
                      </div>
                      <div className="p-6 border-t border-slate-100">
                        <button onClick={() => markAsReady(order.id)} className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl font-black text-xl shadow-lg shadow-emerald-500/20 transition-all">
                          Pronto
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
             </div>
          )}

          {/* --- ADMIN DASHBOARD --- */}
          {view === 'admin' && adminView === 'dashboard' && (
            <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-right-4 duration-500">
               {/* Stats Row */}
               <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                 <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-slate-200 flex items-center gap-4 hover:-translate-y-1 transition-transform duration-300">
                   <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center"><DollarSign size={32} /></div>
                   <div>
                     <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Faturamento Hoje</p>
                     <p className="text-3xl font-black text-slate-800">R$ {stats.revenue.toFixed(2)}</p>
                   </div>
                 </div>
                 <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-slate-200 flex items-center gap-4 hover:-translate-y-1 transition-transform duration-300">
                   <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center"><Utensils size={32} /></div>
                   <div>
                     <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Mesas Ativas</p>
                     <p className="text-3xl font-black text-slate-800">{activeOrders.length}</p>
                   </div>
                 </div>
                 <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-slate-200 flex items-center gap-4 hover:-translate-y-1 transition-transform duration-300">
                   <div className="w-16 h-16 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center"><AlertCircle size={32} /></div>
                   <div>
                     <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Estoque Baixo</p>
                     <p className="text-3xl font-black text-slate-800">{stats.lowStock.length}</p>
                   </div>
                 </div>
               </div>

               {/* Active Tables Grid */}
               <div>
                 <div className="flex items-center justify-between mb-6">
                   <h3 className="text-2xl font-black text-slate-800">Mesas em Atendimento</h3>
                 </div>
                 
                 {activeOrders.length === 0 ? (
                   <div className="bg-white rounded-[2.5rem] p-12 text-center border border-dashed border-slate-300">
                     <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-300">
                       <Utensils size={32} />
                     </div>
                     <p className="text-slate-400 font-bold">Nenhuma mesa aberta no momento.</p>
                   </div>
                 ) : (
                   <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                     {activeOrders.map(order => (
                       <div key={order.id} className="bg-white rounded-[2.5rem] shadow-lg border border-slate-200 overflow-hidden group hover:border-slate-300 transition-all">
                         <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                           <div className="flex items-center gap-4">
                             <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-black text-xl shadow-lg ${order.orderType === 'delivery' ? 'bg-orange-500 shadow-orange-500/20' : 'bg-slate-800 shadow-slate-900/10'}`}>
                                {order.orderType === 'delivery' ? <Bike size={20} /> : order.mesa}
                             </div>
                             <div>
                               <p className="font-black text-slate-800 text-lg truncate max-w-[150px]">{order.cliente}</p>
                               <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wide ${order.status === 'cozinha' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                                 {order.status === 'cozinha' ? 'Em Preparo' : 'Pronto p/ Servir'}
                               </span>
                             </div>
                           </div>
                           <div className="text-right">
                             <p className="text-2xl font-black text-slate-800">R$ {order.total.toFixed(2)}</p>
                           </div>
                         </div>
                         <div className="p-6 max-h-40 overflow-y-auto space-y-2 custom-scrollbar">
                           {order.items.map((item, idx) => (
                             <div key={idx} className="flex justify-between text-sm font-medium text-slate-600">
                               <span>{item.qty}x {item.name}</span>
                               <span className="text-slate-400">R$ {(item.qty * item.price).toFixed(2)}</span>
                             </div>
                           ))}
                           {order.observacoes && <p className="text-xs text-amber-600 font-bold mt-2 pt-2 border-t border-slate-100">OBS: {order.observacoes}</p>}
                         </div>
                         <div className="p-4 bg-slate-50 border-t border-slate-100 grid grid-cols-2 gap-3">
                           <button 
                             onClick={() => openPrintModal(order)}
                             className="py-3 bg-white border border-slate-200 text-slate-700 rounded-xl font-bold text-xs hover:bg-slate-100 transition-all flex items-center justify-center gap-2"
                           >
                             <Printer size={16} />
                             Imprimir
                           </button>
                           <button 
                             onClick={() => setClosingOrderId(order.id)}
                             className="py-3 bg-slate-900 text-white rounded-xl font-bold text-xs hover:bg-black transition-all flex items-center justify-center gap-2 shadow-lg shadow-slate-900/10"
                           >
                             <CreditCard size={16} />
                             Fechar Conta
                           </button>
                           <button 
                             onClick={() => cancelOrder(order.id)}
                             className="col-span-2 py-3 bg-red-50 text-red-600 border border-red-100 rounded-xl font-bold text-xs hover:bg-red-100 transition-all flex items-center justify-center gap-2"
                           >
                             <XCircle size={16} />
                             Cancelar Pedido
                           </button>
                         </div>
                       </div>
                     ))}
                   </div>
                 )}
               </div>
            </div>
          )}

          {/* --- ADMIN REPORTS --- */}
          {view === 'admin' && adminView === 'reports' && (
             <div className="space-y-8 pb-20">
               <div className="flex items-center justify-between">
                 <h3 className="text-3xl font-black text-slate-800 tracking-tighter">Relatórios de Desempenho</h3>
                 <div className="flex bg-white p-1 rounded-xl shadow-sm border border-slate-200">
                   {['day', 'week', 'month', 'year'].map(p => (
                     <button 
                       key={p}
                       onClick={() => setReportPeriod(p as any)}
                       className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wide transition-all ${reportPeriod === p ? 'bg-slate-900 text-white shadow-md' : 'text-slate-400 hover:text-slate-700'}`}
                     >
                       {p === 'day' ? 'Hoje' : p === 'week' ? 'Semana' : p === 'month' ? 'Mês' : 'Ano'}
                     </button>
                   ))}
                 </div>
               </div>

               <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                 {/* Ranking de Garçons */}
                 <div className="bg-white p-8 rounded-[2.5rem] shadow-sm border border-slate-200">
                   <h4 className="text-xl font-black mb-6 flex items-center gap-2 text-slate-800">
                     <Users className="text-blue-500" size={24} />
                     Ranking de Vendas
                   </h4>
                   <div className="space-y-4">
                     {stats.waiterRanking.map((w, idx) => (
                       <div key={w.id} className="flex items-center gap-4 p-4 rounded-2xl border border-slate-100 hover:border-blue-100 hover:bg-blue-50/30 transition-all">
                         <div className={`w-10 h-10 rounded-full flex items-center justify-center font-black text-white ${idx === 0 ? 'bg-yellow-400' : idx === 1 ? 'bg-slate-400' : idx === 2 ? 'bg-amber-700' : 'bg-slate-200 text-slate-500'}`}>
                           {idx + 1}
                         </div>
                         <div className="flex-1">
                           <p className="font-bold text-slate-800">{w.name}</p>
                           <p className="text-xs text-slate-400 font-bold">{w.ordersCount} pedidos atendidos</p>
                         </div>
                         <div className="text-right">
                           <p className="font-black text-slate-800">R$ {w.totalSales.toFixed(2)}</p>
                           <p className="text-[10px] text-slate-400 font-bold uppercase">Ticket Médio: R$ {w.averageTicket.toFixed(2)}</p>
                         </div>
                       </div>
                     ))}
                   </div>
                 </div>

                 {/* Top Products */}
                 <div className="bg-white p-8 rounded-[2.5rem] shadow-sm border border-slate-200">
                   <h4 className="text-xl font-black mb-6 flex items-center gap-2 text-slate-800">
                     <TrendingUp className="text-emerald-500" size={24} />
                     Resumo do Período
                   </h4>
                   <div className="grid grid-cols-2 gap-4">
                     <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100 text-center">
                       <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Total Pedidos</p>
                       <p className="text-4xl font-black text-slate-800">{stats.count}</p>
                     </div>
                     <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100 text-center">
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Ticket Médio</p>
                        <p className="text-4xl font-black text-slate-800">R$ {(stats.count > 0 ? stats.revenue / stats.count : 0).toFixed(0)}</p>
                     </div>
                   </div>
                   <div className="mt-6 p-6 bg-emerald-50 rounded-2xl border border-emerald-100 text-center">
                      <p className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-2">Receita Total</p>
                      <p className="text-5xl font-black text-emerald-700">R$ {stats.revenue.toFixed(2)}</p>
                   </div>
                 </div>
               </div>
             </div>
          )}

          {/* --- ADMIN MENU --- */}
          {view === 'admin' && adminView === 'menu' && (
            <div className="space-y-8 pb-20">
               <div className="flex items-center justify-between">
                <h3 className="text-3xl font-black text-slate-800 tracking-tighter">Cardápio Digital</h3>
                <button 
                  onClick={() => setEditingProduct({ id: '', name: '', category: 'Geral', price: 0, stock: 0, icon: '🍔', isImage: false })}
                  className="bg-slate-900 text-white px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-black transition-all flex items-center gap-2"
                >
                  <Plus size={20} />
                  Adicionar Item
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {products.map(p => (
                  <div key={p.id} className="bg-white rounded-[2rem] shadow-sm border border-slate-200 overflow-hidden group hover:shadow-lg transition-all">
                    <div className="h-48 bg-slate-100 relative group-hover:opacity-90 transition-opacity">
                      {p.isImage ? (
                        <img src={p.icon} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-6xl">{p.icon}</div>
                      )}
                      <button 
                        onClick={() => setEditingProduct(p)}
                        className="absolute top-4 right-4 bg-white/90 backdrop-blur p-2 rounded-full shadow-lg text-slate-700 hover:text-blue-600 transition-colors"
                      >
                        <Edit3 size={18} />
                      </button>
                    </div>
                    <div className="p-5">
                      <div className="flex justify-between items-start mb-2">
                         <div>
                           <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{p.category}</p>
                           <h4 className="font-bold text-slate-800 text-lg line-clamp-1">{p.name}</h4>
                         </div>
                         <p className="font-black text-lg text-slate-800">R$ {p.price.toFixed(2)}</p>
                      </div>
                      <div className="flex items-center justify-between mt-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${p.stock <= 5 ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-500'}`}>
                          {p.stock} un.
                        </span>
                        <button onClick={() => deleteProduct(p.id)} className="text-slate-300 hover:text-red-500 transition-colors"><Trash2 size={18}/></button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* --- ADMIN SETTINGS --- */}
          {view === 'admin' && adminView === 'settings' && (
            <div className="max-w-4xl mx-auto space-y-8 pb-20">
               <h3 className="text-3xl font-black text-slate-800 tracking-tighter">Configurações da Loja</h3>
               
               <div className="bg-white p-8 rounded-[2.5rem] shadow-sm border border-slate-200 space-y-8">
                 <div className="flex gap-8 items-start">
                   <div className="w-32 h-32 bg-slate-100 rounded-3xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400 hover:bg-slate-50 hover:border-slate-400 transition-all cursor-pointer relative overflow-hidden group">
                     {settings.logo ? <img src={settings.logo} className="w-full h-full object-cover" /> : <ImageIcon size={32} />}
                     <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => handleFileUpload(e, (base64) => setSettings({...settings, logo: base64}))} accept="image/*" />
                     <div className="absolute inset-0 bg-black/50 flex items-center justify-center text-white text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity">Alterar Logo</div>
                   </div>
                   <div className="flex-1 space-y-4">
                     <div>
                       <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-2">Nome do Estabelecimento</label>
                       <input type="text" value={settings.storeName} onChange={e => setSettings({...settings, storeName: e.target.value})} className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold" />
                     </div>
                     <div>
                       <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-2">Slogan</label>
                       <input type="text" value={settings.slogan} onChange={e => setSettings({...settings, slogan: e.target.value})} className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold" />
                     </div>
                   </div>
                 </div>

                 <div className="pt-8 border-t border-slate-100">
                    <h4 className="text-lg font-black mb-4">Cores do Tema</h4>
                    <div className="grid grid-cols-2 gap-4">
                       <div>
                         <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-2">Cor Primária</label>
                         <input type="color" value={settings.colors.primary} onChange={e => setSettings({...settings, colors: {...settings.colors, primary: e.target.value}})} className="w-full h-12 rounded-xl cursor-pointer" />
                       </div>
                       <div>
                         <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-2">Cor Secundária</label>
                         <input type="color" value={settings.colors.secondary} onChange={e => setSettings({...settings, colors: {...settings.colors, secondary: e.target.value}})} className="w-full h-12 rounded-xl cursor-pointer" />
                       </div>
                    </div>
                 </div>
               </div>
            </div>
          )}

          {/* ADMIN USERS */}
          {view === 'admin' && adminView === 'users' && (
             <div className="max-w-4xl mx-auto space-y-8 pb-20">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-3xl font-black text-slate-800 tracking-tighter">Gestão de Equipe</h3>
                    <p className="text-slate-400 font-medium">Controle de acesso e cargos</p>
                  </div>
                  <button 
                    onClick={() => setUserModalOpen(true)}
                    className="bg-slate-900 text-white px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-black transition-all flex items-center gap-2"
                  >
                    <Plus size={20} />
                    Novo Membro
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                   {users.map(user => (
                     <div key={user.id} className="bg-white p-6 rounded-[2rem] shadow-sm border border-slate-200 flex items-center justify-between group hover:border-slate-300 transition-all">
                        <div className="flex items-center gap-5">
                           <div className={`w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl uppercase shadow-sm ${user.role === 'gerente' ? 'bg-red-50 text-red-600' : user.role === 'cozinha' ? 'bg-orange-50 text-orange-600' : 'bg-blue-50 text-blue-600'}`}>
                             {user.username[0]}
                           </div>
                           <div>
                              <p className="font-bold text-slate-800 text-lg">{user.username}</p>
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wide ${user.role === 'gerente' ? 'bg-red-100 text-red-600' : user.role === 'cozinha' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'}`}>
                                {user.role === 'gerente' ? 'Gerente' : user.role === 'cozinha' ? 'Cozinha' : 'Garçom'}
                              </span>
                           </div>
                        </div>
                        {user.id !== '1' && user.id !== currentUser?.id && (
                          <button 
                            onClick={() => handleDeleteUser(user.id)} 
                            className="p-3 bg-slate-50 text-slate-400 rounded-xl hover:bg-red-50 hover:text-red-600 transition-colors"
                            title="Remover Usuário"
                          >
                            <Trash2 size={20} />
                          </button>
                        )}
                        {user.id === '1' && (
                          <div className="p-3 text-slate-300" title="Admin Principal"><Shield size={20} /></div>
                        )}
                     </div>
                   ))}
                </div>
             </div>
          )}

          </div>
        </main>
      </div>

      {/* --- MODALS --- */}
      
      {/* 1. PRODUCT EDIT MODAL */}
      {editingProduct && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-lg rounded-[2.5rem] p-8 shadow-2xl flex flex-col gap-6 max-h-[90vh] overflow-y-auto custom-scrollbar">
            <h3 className="text-2xl font-black text-slate-800">{editingProduct.id ? 'Editar Produto' : 'Novo Produto'}</h3>
            
            <div className="flex justify-center">
               <div className="w-32 h-32 bg-slate-100 rounded-3xl overflow-hidden relative group cursor-pointer border-2 border-dashed border-slate-300 hover:border-slate-400">
                 {editingProduct.isImage ? (
                   <img src={editingProduct.icon} className="w-full h-full object-cover" />
                 ) : (
                   <div className="w-full h-full flex items-center justify-center text-4xl">{editingProduct.icon}</div>
                 )}
                 <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center text-white text-xs font-bold transition-opacity">
                    Trocar Imagem
                 </div>
                 <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" accept="image/*" onChange={(e) => handleFileUpload(e, (base64) => setEditingProduct({...editingProduct, icon: base64, isImage: true}))} />
               </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Nome</label>
                <input type="text" value={editingProduct.name} onChange={e => setEditingProduct({...editingProduct, name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-slate-800" />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Preço (R$)</label>
                <input type="number" step="0.10" value={editingProduct.price} onChange={e => setEditingProduct({...editingProduct, price: parseFloat(e.target.value)})} className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-slate-800" />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Estoque</label>
                <input type="number" value={editingProduct.stock} onChange={e => setEditingProduct({...editingProduct, stock: parseInt(e.target.value)})} className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-slate-800" />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Categoria</label>
                <input type="text" value={editingProduct.category} onChange={e => setEditingProduct({...editingProduct, category: e.target.value})} className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-slate-800" />
              </div>
            </div>

            <div className="flex gap-4 mt-2">
              <button onClick={() => setEditingProduct(null)} className="flex-1 py-4 bg-slate-100 text-slate-500 rounded-xl font-bold hover:bg-slate-200 transition-colors">Cancelar</button>
              <button onClick={() => handleProductSave(editingProduct)} className="flex-1 py-4 bg-slate-900 text-white rounded-xl font-bold hover:bg-black transition-colors">Salvar</button>
            </div>
          </div>
        </div>
      )}

      {/* 2. USER ADD MODAL */}
      {userModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-md rounded-[2.5rem] p-8 shadow-2xl flex flex-col gap-6">
            <h3 className="text-2xl font-black text-slate-800">Novo Membro</h3>
            
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Nome de Usuário</label>
                <div className="relative">
                  <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input 
                    type="text" 
                    value={userForm.username} 
                    onChange={e => setUserForm({...userForm, username: e.target.value})} 
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-slate-800"
                    placeholder="Ex: joao.silva"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Senha de Acesso</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input 
                    type="password" 
                    value={userForm.password} 
                    onChange={e => setUserForm({...userForm, password: e.target.value})} 
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-slate-800"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Cargo</label>
                <div className="relative">
                  <ChefHat className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <select 
                    value={userForm.role}
                    onChange={e => setUserForm({...userForm, role: e.target.value as UserRole})}
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-slate-400 font-bold text-slate-800 appearance-none"
                  >
                    <option value="garcom">Garçom</option>
                    <option value="cozinha">Cozinha</option>
                    <option value="gerente">Gerente</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-4 mt-2">
              <button onClick={() => setUserModalOpen(false)} className="flex-1 py-4 bg-slate-100 text-slate-500 rounded-xl font-bold hover:bg-slate-200 transition-colors">Cancelar</button>
              <button onClick={handleAddUser} className="flex-1 py-4 bg-slate-900 text-white rounded-xl font-bold hover:bg-black transition-colors">Cadastrar</button>
            </div>
          </div>
        </div>
      )}

      {/* 4. PRINT / SPLIT BILL MODAL */}
      {printingOrder && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-md rounded-[2.5rem] p-8 shadow-2xl flex flex-col gap-6 max-h-[90vh]">
            <div className="text-center border-b border-slate-100 pb-4">
              <h3 className="text-2xl font-black text-slate-800">Dividir & Imprimir</h3>
              <p className="text-slate-400 font-medium text-sm">Selecione os itens para gerar o cupom</p>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-3">
              {printingOrder.items.map(item => (
                <div key={item.id} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex-1">
                    <p className="font-bold text-sm text-slate-800">{item.name}</p>
                    <p className="text-xs text-slate-500">Total: {item.qty} un</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button 
                      onClick={() => setSplitItems(prev => ({...prev, [item.id]: Math.max(0, (prev[item.id] || 0) - 1)}))}
                      className="w-8 h-8 bg-white border border-slate-200 rounded-lg flex items-center justify-center hover:bg-red-50 hover:text-red-500"
                    >
                      <Minus size={14} />
                    </button>
                    <span className="font-black text-lg w-6 text-center">{splitItems[item.id] || 0}</span>
                     <button 
                      onClick={() => setSplitItems(prev => ({...prev, [item.id]: Math.min(item.qty, (prev[item.id] || 0) + 1)}))}
                      className="w-8 h-8 bg-white border border-slate-200 rounded-lg flex items-center justify-center hover:bg-emerald-50 hover:text-emerald-500"
                    >
                      <Plus size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-slate-900 text-white p-4 rounded-xl flex justify-between items-center">
              <span className="font-bold text-sm text-white/60">Total Selecionado</span>
              <span className="font-black text-xl">
                R$ {printingOrder.items.reduce((acc, item) => acc + (item.price * (splitItems[item.id] || 0)), 0).toFixed(2)}
              </span>
            </div>

            <div className="flex gap-4">
              <button onClick={() => setPrintingOrder(null)} className="flex-1 py-4 bg-slate-100 text-slate-500 rounded-xl font-bold hover:bg-slate-200">Voltar</button>
              <button onClick={handlePrint} className="flex-1 py-4 bg-emerald-500 text-white rounded-xl font-bold hover:bg-emerald-600 shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2">
                <Printer size={18} /> Imprimir
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. CLOSE ACCOUNT MODAL (Payment) */}
      {closingOrderId && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-8 bg-slate-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-md rounded-[3rem] shadow-2xl p-10 flex flex-col gap-8">
            <div className="text-center">
              <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6 text-emerald-600 shadow-inner">
                <CreditCard size={32} />
              </div>
              <h3 className="text-3xl font-black text-slate-800 tracking-tighter">Fechar Conta</h3>
              <p className="text-slate-400 font-medium">Selecione a forma de pagamento</p>
              <div className="mt-4 p-4 bg-slate-50 rounded-2xl border border-slate-100">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-1">Valor Total</span>
                <span className="text-4xl font-black text-slate-800">R$ {orders.find(o=>o.id===closingOrderId)?.total.toFixed(2)}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {[
                { id: 'Dinheiro', icon: Banknote, color: 'text-emerald-600 bg-emerald-50 border-emerald-100' },
                { id: 'Cartão', icon: CreditCard, color: 'text-blue-600 bg-blue-50 border-blue-100' },
                { id: 'Pix', icon: QrCode, color: 'text-purple-600 bg-purple-50 border-purple-100' }
              ].map(method => (
                <button
                  key={method.id}
                  onClick={() => finalizeOrder(closingOrderId, method.id)}
                  className={`flex items-center gap-6 p-5 rounded-3xl border-2 transition-all hover:scale-[1.02] active:scale-95 ${method.color}`}
                >
                  <method.icon size={24} />
                  <span className="font-black text-lg">{method.id}</span>
                </button>
              ))}
            </div>
            <button onClick={() => setClosingOrderId(null)} className="w-full py-4 text-slate-400 font-bold hover:text-slate-600 transition-colors">Cancelar</button>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
};

export default App;
