# Recursos de Atualização em Tempo Real

## Visão Geral

O sistema de gerenciamento de restaurante agora possui **atualizações em tempo real via WebSocket**, eliminando a necessidade de recarregar páginas manualmente. Todas as telas do gerente, cozinha e garçons recebem atualizações instantâneas quando pedidos são criados, modificados ou cancelados.

## Arquitetura

### Tecnologias Utilizadas

- **Django Channels**: Framework para suporte WebSocket no Django
- **Redis**: Message broker para comunicação pub/sub entre processos
- **Daphne**: Servidor ASGI para lidar com conexões WebSocket
- **WebSocket API**: Conexões bidirecionais em tempo real do navegador

### Fluxo de Dados

```
[Ação do Usuário] → [View Django] → [Signal] → [Realtime Helper] 
     ↓
[Redis Channel Layer] → [WebSocket Consumer] → [Navegadores Conectados]
```

## Páginas com Atualização em Tempo Real

### 1. Dashboard do Gerente (`/admin/dashboard/`)

**Atualizações automáticas:**
- ✅ Vendas do dia (R$)
- ✅ Total de pedidos finalizados hoje
- ✅ Número de pedidos ativos
- ✅ Mesas ocupadas
- ✅ Lista de pedidos ativos (detalhes completos)
- ✅ Alertas de ingredientes com estoque baixo

**Notificações toast:**
- 🟢 "Novo pedido criado: Mesa X" (verde)
- 🔵 "Pedido Mesa X atualizado" (azul)
- 🟠 "Pedido cancelado" (laranja)
- 🔵 "Status do pedido alterado" (azul)

**Indicador de conexão:**
- 🔄 Amarelo: Conectando/Reconectando
- ✅ Verde: Conectado (desaparece após 3s)
- ⚠️ Vermelho: Erro ou sem conexão em tempo real

---

### 2. Cozinha (`/kitchen/`)

**Atualizações automáticas:**
- ✅ Pedidos pendentes na cozinha
- ✅ Pedidos em preparo
- ✅ Reordenação automática quando status muda
- ✅ Novos pedidos aparecem instantaneamente
- ✅ Pedidos removidos quando finalizados/cancelados

**Notificações sonoras:** (implementável)
- Pode ser adicionado um som de notificação quando novo pedido chega

**Indicador de conexão:**
- Visual discreto no topo da tela
- Reconexão automática com backoff exponencial (1s, 2s, 4s, 8s, 16s, 30s)

**Fallback:**
- Se WebSocket falhar após 5 tentativas, sistema volta a atualizar a cada 15 segundos via HTTP

---

### 3. Tela do Garçom (`/waiter/`)

**Atualizações automáticas:**
- ✅ Seção "Mesas Ativas" atualiza em tempo real
- ✅ Mostra/oculta automaticamente quando há ou não pedidos ativos
- ✅ Sincronização entre múltiplos garçons

**Notificações toast:**
- 🟢 "Novo pedido: Mesa X" (verde, 2s)
- 🔵 "Status alterado: Mesa X" (azul, 2s)
- 🟠 "Pedido cancelado" (laranja, 2s)

**Benefícios:**
- Garçons veem imediatamente quando cozinha muda status do pedido
- Evita conflitos quando múltiplos garçons gerenciam o mesmo salão
- Reduz tempo de resposta ao cliente

---

## Sistema de Notificações Toast

### JavaScript Global (`showToast()`)

Disponível em todas as páginas via `base.html`:

```javascript
showToast(mensagem, tipo, duração);
```

**Parâmetros:**
- `mensagem` (string): Texto da notificação
- `tipo` (string): `'success'`, `'error'`, `'warning'`, `'info'`
- `duração` (number): Milissegundos (padrão: 3000)

**Exemplo de uso:**
```javascript
showToast('Pedido criado com sucesso!', 'success', 2000);
showToast('Erro ao processar pagamento', 'error', 5000);
```

**Estilos automáticos:**
- ✅ Success: Verde com ícone ✓
- ❌ Error: Vermelho com ícone ✗
- ⚠️ Warning: Laranja com ícone △
- ℹ️ Info: Cinza com ícone ℹ

---

## Grupos WebSocket e Permissões

### Consumer: `OrdersConsumer`

Localização: `restaurante/consumers.py`

**Grupos de assinatura automática:**

| Usuário       | Grupos Inscritos                                      | Recebe Eventos |
|---------------|-------------------------------------------------------|----------------|
| **Garçom**    | `orders_global`, `orders_waiter_{user_id}`            | Seus pedidos + eventos globais |
| **Cozinha**   | `orders_global`, `orders_kitchen`                     | Todos os pedidos da cozinha |
| **Gerente**   | `orders_global`, `orders_kitchen`, `orders_admin`     | Todos os eventos do sistema |

### Eventos Publicados

Localização: `restaurante/signals.py` + `restaurante/realtime.py`

**Tipos de eventos:**

1. **`order.created`**
   - Disparado quando novo pedido é criado
   - Payload: `{ event_type, order: { id, mesa, cliente, total, ... } }`

2. **`order.updated`**
   - Disparado quando pedido é modificado (itens adicionados/removidos)
   - Payload: Objeto completo do pedido atualizado

3. **`order.status_changed`**
   - Disparado quando status muda (pendente → cozinha → pronto → finalizado)
   - Payload: Pedido com novo status

4. **`order.deleted`**
   - Disparado quando pedido é cancelado
   - Payload: `{ event_type, order_id }`

---

## Requisitos Técnicos

### Serviços Necessários

1. **Redis Server**
   ```bash
   # Windows (via Chocolatey)
   choco install redis-64
   redis-server
   ```

2. **Django Channels**
   ```bash
   pip install channels channels-redis
   ```

3. **Daphne ASGI Server** (para WebSocket)
   ```bash
   pip install daphne
   ```

### Configuração (.env)

```env
# Redis connection
REDIS_URL=redis://localhost:6379/0

# Enable real-time features
ENABLE_REALTIME=True
```

### URLs WebSocket

- **Endpoint:** `ws://localhost:8000/ws/orders/`
- **Protocolo:** WebSocket (upgrade de HTTP)
- **Autenticação:** Cookie de sessão Django

---

## Executando o Sistema

### Desenvolvimento Local

**Terminal 1 - HTTP Server (Waitress/Django):**
```bash
python manage.py runserver
# OU
waitress-serve --listen=*:8000 billar_project.wsgi:application
```

**Terminal 2 - WebSocket Server (Daphne):**
```bash
daphne -b 0.0.0.0 -p 8001 billar_project.asgi:application
```

**Terminal 3 - Redis:**
```bash
redis-server
```

### Produção (Windows)

Use o launcher automático:
```bash
deploy\windows\start_system.bat
```

O launcher inicia automaticamente:
- ✅ PostgreSQL
- ✅ Redis
- ✅ Waitress (HTTP na porta 8000)
- ✅ Daphne (WebSocket na porta 8001)
- ✅ Nginx (Proxy reverso na porta 80)

---

## Troubleshooting

### WebSocket não conecta

**Sintomas:**
- Indicador de conexão fica em "Conectando..."
- Console do navegador mostra erro `WebSocket connection failed`

**Verificações:**

1. **Redis está rodando?**
   ```bash
   redis-cli ping
   # Deve retornar: PONG
   ```

2. **Daphne está rodando?**
   ```bash
   netstat -ano | findstr :8001
   # Deve mostrar processo escutando na porta 8001
   ```

3. **Firewall bloqueando?**
   ```powershell
   # Windows: Adicionar regra de entrada
   New-NetFirewallRule -DisplayName "Django WebSocket" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
   ```

4. **Nginx configurado corretamente?** (produção)
   - Verificar se `/ws/` está sendo proxy_pass para `http://127.0.0.1:8001`
   - Headers de upgrade WebSocket devem estar presentes

---

### Atualização falha mas WebSocket está conectado

**Sintomas:**
- Conexão WebSocket OK
- Dados não atualizam na interface

**Verificações:**

1. **Console do navegador:**
   - Verifique mensagens recebidas: `Dashboard received: {...}`
   - Confirme que `event_type` está correto

2. **Signals Django:**
   ```python
   # restaurante/apps.py
   def ready(self):
       import restaurante.signals  # Deve estar presente
   ```

3. **ENABLE_REALTIME está True?**
   ```python
   # settings.py
   ENABLE_REALTIME = os.getenv('ENABLE_REALTIME', 'True').lower() == 'true'
   ```

4. **Force refresh do navegador:**
   - Ctrl+Shift+R (Windows/Linux)
   - Cmd+Shift+R (Mac)

---

### Múltiplas conexões/memory leak

**Sintomas:**
- Múltiplos WebSockets abertos para mesma página
- Uso crescente de memória

**Solução:**
- Sistema já implementa cleanup no `beforeunload`
- Apenas uma conexão por página
- Reconexão automática com exponential backoff

**Validação:**
```javascript
// Console do navegador (Dev Tools > Console)
console.log(adminDashboardSocket?.readyState);
// 0: CONNECTING, 1: OPEN, 2: CLOSING, 3: CLOSED
```

---

## Monitoramento

### Logs do Sistema

**Django/Daphne (stdout):**
```
Dashboard WebSocket connected
Kitchen received: {event_type: "order.created", order: {...}}
Waiter WebSocket closed: 1000
```

**Redis Monitor:**
```bash
redis-cli monitor
# Ver mensagens pub/sub em tempo real
```

**Nginx Access Log:** (produção)
```bash
tail -f /var/log/nginx/access.log | grep "ws/"
```

### Métricas de Performance

**Latência típica:**
- Criação de pedido → WebSocket recebido: **< 100ms**
- Atualização de UI: **< 50ms**
- Total (ação → UI atualizada): **< 150ms**

**Capacidade:**
- 100+ conexões WebSocket simultâneas
- Broadcast para todas conexões: **< 200ms**

---

## Próximas Melhorias

### Planejadas:

1. **Notificações sonoras na cozinha**
   - Som de "ding" quando novo pedido chega
   - Configurável nas settings

2. **WebSocket para tela de pedidos online**
   - Confirmação visual instantânea ao criar pedido
   - Atualização de estoque em tempo real

3. **Indicador de "Quem está online"**
   - Mostrar garçons/gerentes conectados
   - Status "ativo" vs "ausente"

4. **Histórico de eventos em tempo real**
   - Log visual de últimas ações
   - "Pedido X criado há 2 minutos"

5. **Métricas de atendimento**
   - Tempo médio de preparo
   - Taxa de pedidos/hora
   - Atualização em tempo real no dashboard

---

## Referências Técnicas

- **Django Channels:** https://channels.readthedocs.io/
- **WebSocket API:** https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- **Redis Pub/Sub:** https://redis.io/docs/manual/pubsub/
- **Daphne Server:** https://github.com/django/daphne

---

**Última atualização:** Março 2026  
**Versão do sistema:** 2.0 (Real-time Edition)
