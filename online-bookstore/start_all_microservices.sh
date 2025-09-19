#!/bin/bash

# Complete microservices startup script
echo "🚀 Starting Online Bookstore Microservices..."

# Kill any existing processes
echo "🔄 Cleaning up existing processes..."
pkill -f "python.*main.py" 2>/dev/null || true
sleep 2

# Start services in background
echo "▶️  Starting User Service (Port 8001)..."
cd /home/sachinn-p/Codes/Microservices/online-bookstore/user_service
/home/sachinn-p/Codes/Microservices/.venv/bin/python3 main.py &
USER_PID=$!
sleep 3

echo "▶️  Starting Catalog Service (Port 8002)..."
cd /home/sachinn-p/Codes/Microservices/online-bookstore/catalog_service
/home/sachinn-p/Codes/Microservices/.venv/bin/python3 main.py &
CATALOG_PID=$!
sleep 3

echo "▶️  Starting Order Service (Port 8003)..."
cd /home/sachinn-p/Codes/Microservices/online-bookstore/order_service
/home/sachinn-p/Codes/Microservices/.venv/bin/python3 main.py &
ORDER_PID=$!
sleep 3

echo "▶️  Starting Payment Service (Port 8004)..."
cd /home/sachinn-p/Codes/Microservices/online-bookstore/payment_service
/home/sachinn-p/Codes/Microservices/.venv/bin/python3 main.py &
PAYMENT_PID=$!
sleep 3

echo "▶️  Starting Notification Service (Port 8005)..."
cd /home/sachinn-p/Codes/Microservices/online-bookstore/notification_service
/home/sachinn-p/Codes/Microservices/.venv/bin/python3 main.py &
NOTIFICATION_PID=$!
sleep 3

echo "▶️  Starting Review Service (Port 8006)..."
cd /home/sachinn-p/Codes/Microservices/online-bookstore/review_service
/home/sachinn-p/Codes/Microservices/.venv/bin/python3 main.py &
REVIEW_PID=$!
sleep 3

echo "✅ All services started successfully!"
echo ""
echo "📊 Service Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 User Service:         http://localhost:8001  (PID: $USER_PID)"
echo "📚 Catalog Service:      http://localhost:8002  (PID: $CATALOG_PID)"
echo "🛒 Order Service:        http://localhost:8003  (PID: $ORDER_PID)"
echo "💳 Payment Service:      http://localhost:8004  (PID: $PAYMENT_PID)"
echo "🔔 Notification Service: http://localhost:8005  (PID: $NOTIFICATION_PID)"
echo "⭐ Review Service:       http://localhost:8006  (PID: $REVIEW_PID)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 To test the services:"
echo "1. Create a user: curl -X POST 'http://localhost:8001/users' -H 'Content-Type: application/json' -d '{\"username\":\"testuser\",\"email\":\"test@example.com\",\"password\":\"testpass123\",\"full_name\":\"Test User\"}'"
echo "2. Login: curl -X POST 'http://localhost:8001/login' -H 'Content-Type: application/json' -d '{\"username\":\"testuser\",\"password\":\"testpass123\"}'"
echo "3. Use the token in Authorization header: -H 'Authorization: Bearer YOUR_TOKEN'"
echo ""
echo "🛑 To stop all services: pkill -f 'python.*main.py'"
echo ""
echo "📋 All services are secured with JWT authentication except:"
echo "   - Health check endpoints (/health)"
echo "   - User registration (/users POST)"
echo "   - User login (/login)"
echo "   - Review stats (/reviews/book/{id}/stats)"

# Keep script running and wait for services
trap 'echo "🛑 Shutting down all services..."; pkill -f "python.*main.py"; exit 0' SIGINT SIGTERM

echo "💡 Press Ctrl+C to stop all services..."
wait
