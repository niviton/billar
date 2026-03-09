# Deploy LAN Profissional (Windows)

## 1. Objetivo

Executar o sistema no notebook/mini-PC do restaurante, acessível por todos os dispositivos da rede local:

- Garçom (celular/PWA)
- Cozinha (tablet com atualização em tempo real)
- Gerente (desktop)

## 2. Serviços recomendados

- PostgreSQL (serviço do Windows)
- Redis (serviço do Windows ou Memurai)
- Nginx (reverse proxy)
- Waitress (HTTP Django)
- Daphne (ASGI/WebSocket)

## 3. Configuração do projeto

1. Copie `.env.example` para `.env`
2. Ajuste credenciais e IP/hosts
3. Instale dependências:

```bash
pip install -r requirements.txt
```

4. Rode migrações:

```bash
python manage.py migrate
```

## 4. Inicialização operacional

- Para iniciar manualmente: `deploy/windows/start_system.bat`
- Para gerar executável: `deploy/windows/build_exe.ps1`

Executável final esperado:

- `dist/SistemaRestaurante.exe`

## 5. Nginx

Arquivo base: `deploy/nginx/nginx.conf`

Ajuste os paths `alias` para os diretórios reais de `static` e `media` no seu servidor.

## 6. Backup automático

Script pronto:

- `deploy/windows/backup_postgres.ps1`

Agendar no Task Scheduler (diário, madrugada), mantendo retenção de 30 backups.

## 7. Checklist de produção

- [ ] `DJANGO_DEBUG=false`
- [ ] `DJANGO_SECRET_KEY` forte
- [ ] `DJANGO_ALLOWED_HOSTS` com IP/hostname LAN
- [ ] Senhas fortes para usuários do sistema
- [ ] Firewall liberando apenas portas necessárias na LAN
- [ ] Backup restaurável testado
- [ ] Equipamento ligado em nobreak

## 8. Observação importante sobre LAN sem internet

Todo o stack (Django, PostgreSQL, Redis e Nginx) roda localmente. Internet não é necessária para operação diária, apenas para atualização/manutenção.
