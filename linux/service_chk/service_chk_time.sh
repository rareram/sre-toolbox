#!/bin/bash

# 스크립트 디렉토리로 이동
cd "$(dirname "$0")"

# 환경 변수 설정
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 로깅 시작
echo "Script started at $(/bin/date)" >> ./service_chk.log
echo "Current directory: $PWD" >> ./service_chk.log

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

# 라인 정의
D='┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄'
E='════════════════════════════════════════════════════════════════════'

# 상태 확인 서비스 목록
SERVICE_LIST_FILE="$(pwd)/service_chk.conf"

# 결과 저장 파일
OUTPUT_FILE="$(pwd)/service_chk.txt"

# 이전 상태 저장 파일
PREVIOUS_STATE_FILE="$(pwd)/service_chk_state.txt"

# 현재 날짜
CURRENT_DATE=$(/bin/date +%Y-%m-%d)

# 파일 초기화
> "$OUTPUT_FILE"
echo -e "⚡ 서비스 상태 (마지막 업데이트: $(/bin/date))" >> "$OUTPUT_FILE"
echo -e "$D" >> "$OUTPUT_FILE"

# 이전 상태 파일이 없으면 생성
if [ ! -f "$PREVIOUS_STATE_FILE" ]; then
    touch "$PREVIOUS_STATE_FILE"
fi

# 버전 정보를 추출하는 함수
get_version_info() {
    local command="$1"
    local version_output
    local version_info
    
    # 명령어 실행 및 에러 출력 무시
    version_output=$(eval "$command" 2>&1)
    
    case "$command" in
        "rsyslogd -v")
            version_info=$(echo "$version_output" | awk 'NR<2 {print $2}')
            ;;
        "openssl version")
            version_info=$(echo "$version_output" | awk '{print $2}')
            ;;
        "python -V"|"python3 -V")
            version_info=$(echo "$version_output" | awk '{print $2}')
            ;;
        "java -version")
            version_info=$(echo "$version_output" | grep "version" | awk '{print $3}' | tr -d '"')
            ;;
        "docker --version")
            version_info=$(echo "$version_output" | awk '{print $3}' | tr -d ',')
            ;;
        "node --version")
            if [[ "$version_output" == "Node.js not found" ]]; then
                version_info="설치되지 않음"
            else
                version_info=$(echo "$version_output" | tr -d 'v')
            fi
            ;;
        "mysql --version")
            version_info=$(echo "$version_output" | awk '{split($3, a, "-"); print a[1]}')
            ;;
        "curl -s http://localhost:9200")
            version_info=$(echo "$version_output" | grep -o '"version":{"number":"[^"]*"' | cut -d'"' -f6)
            ;;
        *)
            version_info=$(echo "$version_output" | head -n1)
            ;;
    esac
    
    echo "$version_info"
}

# 서비스 및 버전 체크
while IFS= read -r line || [[ -n "$line" ]]; do
    # 주석 & 빈줄 무시
    [[ $line =~ ^[[:space:]]*# ]] || [[ -z $line ]] && continue
    
    IFS=':' read -r name type search_term <<< "$line"
    status="unknown"
    color=$NC
    uptime=""
    
    case $type in
        "docker")
            if container_id=$(/usr/bin/docker ps -q --filter "name=$search_term"); then
                if [ ! -z "$container_id" ]; then
                    status="실행중"
                    color=$GREEN
                    uptime=$(/usr/bin/docker inspect -f '{{.State.StartedAt}}' $container_id 2>/dev/null | xargs -I{} /bin/date -d {} '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
                    if [ $? -ne 0 ]; then
                        uptime="시간 정보 없음"
                    fi
                else
                    status="중지됨"
                    color=$RED
                fi
            else
                status="중지됨"
                color=$RED
            fi
            ;;
        "binary")
            if pid=$(/usr/bin/pgrep -f "$search_term"); then
                status="실행중"
                color=$GREEN
                uptime=$(/bin/ps -p $pid -o lstart= 2>/dev/null | xargs -I{} /bin/date -d {} '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
                if [ $? -ne 0 ]; then
                    uptime="시간 정보 없음"
                fi
            else
                status="중지됨"
                color=$RED
            fi
            ;;
        "system")
            if /bin/systemctl is-active --quiet "$search_term"; then
                status="실행중"
                color=$GREEN
                uptime=$(/bin/systemctl show -p ActiveEnterTimestamp --value "$search_term" 2>/dev/null | xargs -I{} /bin/date -d {} '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
                if [ $? -ne 0 ]; then
                    uptime="시간 정보 없음"
                fi
            else
                status="중지됨"
                color=$RED
            fi
            ;;
        "version")
            if version_info=$(get_version_info "$search_term"); then
                status="$version_info"
                color=$BLUE
            else
                status="버전 확인 실패"
                color=$RED
            fi
            ;;
    esac

    # 이전 상태 읽기
    previous_status=$(grep "^$name:" "$PREVIOUS_STATE_FILE" | cut -d':' -f2)
    previous_date=$(grep "^$name:" "$PREVIOUS_STATE_FILE" | cut -d':' -f3)

    # 상태 변경 확인 (버전 체크는 제외)
    if [ "$type" != "version" ] && [ "$previous_status" != "$status" ] && [ "$previous_date" = "$CURRENT_DATE" ]; then
        status="${status}⚠ "
        color=$YELLOW
    fi

    # 현재 상태 저장 (버전 체크는 제외)
    if [ "$type" != "version" ]; then
        sed -i "/^$name:/d" "$PREVIOUS_STATE_FILE"
        echo "$name:$status:$CURRENT_DATE" >> "$PREVIOUS_STATE_FILE"
    fi

    # 출력 포맷팅
    if [ "$type" = "version" ]; then
        printf " ▪ %-20s %-8s ${color}%s${NC}\n" "$name" "$type" "$status" >> "$OUTPUT_FILE"
    elif [ "$status" = "실행중" ] || [ "$status" = "실행중⚠ " ] && [ -n "$uptime" ]; then
        printf " ▪ %-20s %-8s ${color}%s${NC} (시작: %s)\n" "$name" "$type" "$status" "$uptime" >> "$OUTPUT_FILE"
    else
        printf " ▪ %-20s %-8s ${color}%s${NC}\n" "$name" "$type" "$status" >> "$OUTPUT_FILE"
    fi
done < "$SERVICE_LIST_FILE"

echo -e "$E" >> "$OUTPUT_FILE"

# 로깅 종료
echo "Script ended at $(/bin/date)" >> ./service_chk.log
