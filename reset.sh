#!/bin/bash

# 전체 시스템 재시작 및 데이터베이스 초기화 스크립트
# System Reset and Database Cleanup Script

set -e  # 오류 발생 시 스크립트 중단

echo "================================================"
echo "  🔄 시스템 초기화 시작 (System Reset Starting)"
echo "================================================"
echo ""

# 1. 모든 컨테이너 중지 및 볼륨 삭제
echo "📦 Step 1/3: 모든 컨테이너 및 데이터 삭제 중..."
echo "           (Stopping containers and removing volumes...)"
docker-compose down -v

echo ""
echo "✅ 컨테이너 및 데이터 삭제 완료"
echo ""

# 2. 시스템 재시작
echo "🚀 Step 2/3: 시스템 재시작 중..."
echo "           (Starting all services...)"
docker-compose up -d

echo ""
echo "✅ 시스템 재시작 완료"
echo ""

# 3. 서비스 안정화 대기
echo "⏳ Step 3/3: 서비스 안정화 대기 중 (10초)..."
echo "           (Waiting for services to stabilize...)"
sleep 10

echo ""
echo "================================================"
echo "  ✨ 시스템 초기화 완료! (Reset Complete!)"
echo "================================================"
echo ""

# 4. 실행 중인 컨테이너 상태 확인
echo "📊 실행 중인 서비스 상태:"
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "================================================"
echo "  💡 참고사항 (Notes):"
echo "================================================"
echo "  - 모든 데이터베이스 데이터가 삭제되었습니다"
echo "  - 새로운 분석을 시작할 수 있습니다"
echo "  - 웹 프론트엔드: http://localhost:5173"
echo "  - Query API: http://localhost:8004"
echo "================================================"
