#!/bin/bash
# SSL 憑證設定腳本
# 安全措施 #7: HTTPS 與網域設定完整
#
# 此腳本會：
# 1. 安裝 Certbot
# 2. 取得 Let's Encrypt SSL 憑證
# 3. 設定自動更新
# 4. 更新 Nginx 配置

set -e

DOMAIN="journal.gamma-level.cc"
EMAIL="admin@gamma-level.cc"  # 請替換為你的 email
PROJECT_DIR="/root/ai_trading_journal"

echo "=========================================="
echo "  SSL 憑證設定腳本"
echo "  網域: $DOMAIN"
echo "=========================================="

# 檢查是否為 root
if [ "$EUID" -ne 0 ]; then
    echo "錯誤：請使用 sudo 執行此腳本"
    exit 1
fi

# 1. 安裝 Certbot
echo ""
echo "[1/6] 安裝 Certbot..."
if ! command -v certbot &> /dev/null; then
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
    echo "✅ Certbot 安裝完成"
else
    echo "✅ Certbot 已安裝"
fi

# 2. 建立 ACME challenge 目錄
echo ""
echo "[2/6] 建立 ACME challenge 目錄..."
mkdir -p /var/www/certbot
chown -R www-data:www-data /var/www/certbot
echo "✅ 目錄已建立"

# 3. 複製 Rate Limiting 設定
echo ""
echo "[3/6] 設定 Nginx Rate Limiting..."
if [ -f "$PROJECT_DIR/nginx-rate-limit.conf" ]; then
    # 檢查是否已包含在 nginx.conf 中
    if ! grep -q "nginx-rate-limit.conf" /etc/nginx/nginx.conf 2>/dev/null; then
        # 在 http 區塊中加入 include
        sed -i '/http {/a \    include '"$PROJECT_DIR"'/nginx-rate-limit.conf;' /etc/nginx/nginx.conf
        echo "✅ Rate Limiting 設定已加入"
    else
        echo "✅ Rate Limiting 設定已存在"
    fi
fi

# 4. 取得 SSL 憑證
echo ""
echo "[4/6] 取得 SSL 憑證..."
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    # 先使用臨時設定讓 Certbot 能夠驗證
    certbot certonly --nginx \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        -d "$DOMAIN" \
        --redirect
    echo "✅ SSL 憑證取得成功"
else
    echo "✅ SSL 憑證已存在"
fi

# 5. 複製 Nginx SSL 設定
echo ""
echo "[5/6] 更新 Nginx 設定..."
if [ -f "$PROJECT_DIR/journal.nginx.ssl.conf" ]; then
    cp "$PROJECT_DIR/journal.nginx.ssl.conf" /etc/nginx/sites-available/journal
    ln -sf /etc/nginx/sites-available/journal /etc/nginx/sites-enabled/
    
    # 移除預設設定（如果存在）
    rm -f /etc/nginx/sites-enabled/default
    
    echo "✅ Nginx 設定已更新"
fi

# 6. 測試並重啟 Nginx
echo ""
echo "[6/6] 測試並重啟 Nginx..."
nginx -t
if [ $? -eq 0 ]; then
    systemctl reload nginx
    echo "✅ Nginx 重啟成功"
else
    echo "❌ Nginx 設定測試失敗，請檢查設定檔"
    exit 1
fi

# 7. 設定自動更新
echo ""
echo "[bonus] 設定 SSL 憑證自動更新..."
# Certbot 安裝時會自動建立 cron job 或 systemd timer
if systemctl is-active --quiet certbot.timer; then
    echo "✅ 自動更新已啟用 (systemd timer)"
elif crontab -l 2>/dev/null | grep -q certbot; then
    echo "✅ 自動更新已啟用 (cron)"
else
    # 手動加入 cron job
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    echo "✅ 已加入自動更新 cron job"
fi

echo ""
echo "=========================================="
echo "  設定完成！"
echo "=========================================="
echo ""
echo "你的網站現在可以使用 HTTPS 訪問："
echo "  https://$DOMAIN"
echo ""
echo "SSL 憑證資訊："
certbot certificates 2>/dev/null | grep -A5 "$DOMAIN" || echo "  請執行 'certbot certificates' 查看"
echo ""
echo "重要提醒："
echo "  1. 確保 DNS 已正確指向此伺服器"
echo "  2. 確保防火牆允許 443 端口"
echo "  3. 憑證會在到期前自動更新"
echo ""
