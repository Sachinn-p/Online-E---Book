#!/bin/bash

# Script to stop all microservices
echo "🛑 Stopping all microservices..."

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="logs/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "🔪 Stopping $service_name (PID: $pid)..."
            kill "$pid"
            rm "$pid_file"
            echo "✅ $service_name stopped"
        else
            echo "⚠️  $service_name was not running"
            rm "$pid_file"
        fi
    else
        echo "⚠️  No PID file found for $service_name"
    fi
}

# Stop all services
stop_service "logging_service"
stop_service "user_service"
stop_service "catalog_service"
stop_service "order_service"
stop_service "payment_service"
stop_service "notification_service"
stop_service "review_service"

echo ""
echo "✅ All microservices stopped!"
