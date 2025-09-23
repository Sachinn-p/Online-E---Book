#!/bin/bash

# Script to start all microservices with logging enabled
echo "🚀 Starting Online Bookstore Microservices with Logging..."

# Function to check if a port is available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Port $1 is already in use"
        return 1
    else
        return 0
    fi
}

# Function to start a service
start_service() {
    local service_name=$1
    local port=$2
    local directory=$3
    
    echo "📦 Starting $service_name on port $port..."
    
    if check_port $port; then
        cd "/home/sachinn-p/Codes/Microservices/online-bookstore/$directory"
        # Start service in background
        python3 main.py > "/home/sachinn-p/Codes/Microservices/online-bookstore/logs/${service_name}.log" 2>&1 &
        local pid=$!
        echo $pid > "/home/sachinn-p/Codes/Microservices/online-bookstore/logs/${service_name}.pid"
        echo "✅ $service_name started with PID $pid"
        cd "/home/sachinn-p/Codes/Microservices/online-bookstore"
        sleep 2
    else
        echo "❌ Cannot start $service_name - port $port is busy"
    fi
}

# Create logs directory
mkdir -p "/home/sachinn-p/Codes/Microservices/online-bookstore/logs"

# Start logging service first
echo "🔍 Starting Logging Service..."
start_service "logging_service" 8004 "logging_service"

# Wait for logging service to be ready
echo "⏳ Waiting for logging service to be ready..."
sleep 5

# Start all microservices
start_service "user_service" 8001 "user_service"
start_service "catalog_service" 8002 "catalog_service"
start_service "order_service" 8003 "order_service"
start_service "payment_service" 8005 "payment_service"
start_service "notification_service" 8006 "notification_service"
start_service "review_service" 8007 "review_service"

echo ""
echo "🎉 All services started!"
echo ""
echo "📝 Service URLs:"
echo "   - Logging Service:      http://localhost:8004"
echo "   - User Service:         http://localhost:8001"
echo "   - Catalog Service:      http://localhost:8002"
echo "   - Order Service:        http://localhost:8003"
echo "   - Payment Service:      http://localhost:8005"
echo "   - Notification Service: http://localhost:8006"
echo "   - Review Service:       http://localhost:8007"
echo ""
echo "📊 Logs location: logs/"
echo "📁 Main logs file: logs/micro_services.log"
echo ""
echo "🔍 To view logs in real-time:"
echo "   tail -f logs/micro_services.log"
echo ""
echo "🛑 To stop all services:"
echo "   ./stop_all_microservices.sh"
