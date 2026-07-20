#!/bin/bash

# 설치 기본값 정의
SCRIPT_VERSION="0.2.0"
DEFAULT_INSTALL_DIR="/opt/monitoring/process_exporter"
DEFAULT_PROCESS_EXPORTER_VERSION="0.8.4"
DEFAULT_BINARY_PATH="$(pwd)/process-exporter-${DEFAULT_PROCESS_EXPORTER_VERSION}.linux-amd64.tar.gz"
PROCESS_EXPORTER_LATEST_VERSION=""
SYMLINK_PATH="$DEFAULT_INSTALL_DIR/process_exporter"
PORT=9256
INIT_SYSTEM=""

# 에러 처리 및 종료 함수
function error_exit {
    echo -e "\033[1;33m[오류] $1\033[0m" >&2
    exit 1
}

# 진행 로그 출력 함수
function log_info {
    echo -e "\033[1;36m[정보] $1\033[0m"
}

function log_error {
    echo -e "\033[1;33m[오류] $1\033[0m"
}

function log_warn {
    echo -e "\033[1;35m[경고] $1\033[0m"
}

if [[ $(id -u) -ne 0 ]]; then
    error_exit "이 스크립트는 root 권한으로 실행해야 합니다."
fi

# 로컬 tar.gz 파일에서 최신 버전 감지 함수
function detect_latest_local_version {
    local latest_local=""
    if [ -d "." ]; then
        latest_local=$(find . -maxdepth 1 -type f -name "process-exporter-*.linux-amd64.tar.gz" \
            | sed -E 's/.*process-exporter-([0-9\.]+)\.linux-amd64\.tar\.gz/\1/' \
            | sort -V \
            | tail -n 1)
    fi
    echo "$latest_local"
}

# 기본 버전 정보 초기화 및 로컬 최신화 반영
function initialize_default_version {
    local local_ver=$(detect_latest_local_version)
    if [[ -n "$local_ver" ]]; then
        DEFAULT_PROCESS_EXPORTER_VERSION="$local_ver"
        DEFAULT_BINARY_PATH="$(pwd)/process-exporter-${local_ver}.linux-amd64.tar.gz"
        log_info "로컬 디렉토리에서 최신 패키지 버전을 감지하여 기본값으로 설정했습니다: $DEFAULT_PROCESS_EXPORTER_VERSION"
    fi
}

# 서비스 관리 시스템 감지
function detect_init_system {
    if command -v systemctl >/dev/null 2>&1 && pidof systemd >/dev/null 2>&1; then
        INIT_SYSTEM="systemd"
    elif [[ -f /etc/init.d/functions ]] || [[ -f /etc/rc.d/init.d/functions ]]; then
        INIT_SYSTEM="sysvinit"
    elif [[ -f /etc/init/rc.conf ]]; then
        INIT_SYSTEM="upstart"
    else
        log_error "서비스 관리 시스템(init system)을 감지할 수 없습니다. systemd를 기본값으로 지정합니다..."
        INIT_SYSTEM="systemd"
    fi
    
    log_info "감지된 서비스 관리 시스템: $INIT_SYSTEM"
}

function resolve_port_conflict {
    local check_port=$PORT
    local port_used=false
    
    if command -v ss >/dev/null 2>&1; then
        eval "ss -tulnp | grep \"LISTEN.*:$check_port\"" >/dev/null 2>&1 && port_used=true
    else
        eval "netstat -tulnp | grep \"LISTEN.*:$check_port\"" >/dev/null 2>&1 && port_used=true
    fi
    
    if [[ "$port_used" == "true" ]]; then
        log_info "포트 $check_port 번호가 이미 사용 중입니다."
        
        local alt_port=38256
        while true; do
            local alt_used=false
            if command -v ss >/dev/null 2>&1; then
                eval "ss -tulnp | grep \"LISTEN.*:$alt_port\"" >/dev/null 2>&1 && alt_used=true
            else
                eval "netstat -tulnp | grep \"LISTEN.*:$alt_port\"" >/dev/null 2>&1 && alt_used=true
            fi
            
            if [[ "$alt_used" == "true" ]]; then
                ((alt_port+=1))
            else
                break
            fi
        done
        PORT=$alt_port
        log_info "Process Exporter 수신 포트를 사용할 수 있는 대체 포트 $PORT 번호로 변경했습니다."
    fi
}

function select_local_binary {
    local tar_files=()
    while IFS= read -r -d '' file; do
        tar_files+=("$file")
    done < <(find . -maxdepth 1 -type f -name "process-exporter-*.linux-amd64.tar.gz" -print0 | sort -z)
    
    if [ ${#tar_files[@]} -eq 0 ]; then
        log_error "현재 디렉토리에 process-exporter-*.linux-amd64.tar.gz 파일이 존재하지 않습니다."
        return 1
    fi
    
    echo -e "\n사용 가능한 로컬 바이너리 파일 목록:" >&2
    local display_idx=1
    for tar_file in "${tar_files[@]}"; do
        local base_name=$(basename "$tar_file")
        echo "  ${display_idx}) $base_name" >&2
        display_idx=$((display_idx + 1))
    done
    echo >&2
    
    while true; do
        read -p "설치할 바이너리 번호를 선택하세요 (또는 'q'로 취소): " choice
        local clean_choice="${choice,,}"
        clean_choice="${clean_choice//[[:space:]]/}"
        clean_choice="${clean_choice//$'\r'/}"
        
        if [[ "$clean_choice" == "q" ]]; then
            log_info "바이너리 선택이 취소되었습니다."
            return 1
        fi
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -lt "$display_idx" ]; then
            local selected_idx=$((choice - 1))
            BINARY_PATH="${tar_files[$selected_idx]}"
            PROCESS_EXPORTER_VERSION=$(echo "$(basename "$BINARY_PATH")" | sed -E 's/.*process-exporter-([0-9\.]+)\..*/\1/')
            log_info "선택된 바이너리: $(basename "$BINARY_PATH") (버전: $PROCESS_EXPORTER_VERSION)"
            return 0
        fi
        log_error "잘못된 선택입니다. 다시 번호를 입력해 주세요." >&2
    done
}

function system_information {
    echo -e "\033[1;36m-------------------------------시스템 정보----------------------------\033[0m"
    echo -e "\033[1;36m* Process Exporter 설치 도우미 버전: v$SCRIPT_VERSION\033[0m"

    # OS 정보 탐색
    if [[ -f /etc/redhat-release ]]; then
        OS_VERSION=$(cat /etc/redhat-release)
        MAJOR_VERSION=$(echo "$OS_VERSION" | grep -oE '[0-9]+\.' | cut -d. -f1)
        echo -e "\033[1;36m* 운영체제(OS): $OS_VERSION\033[0m"
        echo -e "\033[1;36m* 메이저 버전: $MAJOR_VERSION\033[0m"
    elif [[ -f /etc/os-release ]]; then
        OS_NAME=$(grep '^NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')
        OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
        echo -e "\033[1;36m* 운영체제(OS): $OS_NAME $OS_VERSION\033[0m"
    else
        OS_NAME=$(uname -s)
        OS_VERSION=$(uname -r)
        echo -e "\033[1;36m* 운영체제(OS): $OS_NAME $OS_VERSION\033[0m"
    fi

    # 서비스 관리 방식(Init System)
    detect_init_system
    echo -e "\033[1;36m* 서비스 관리 방식(Init System): $INIT_SYSTEM\033[0m"
    
    local install_type="미설치 / 알 수 없음"
    if [[ -f "$SYMLINK_PATH" ]]; then
        install_type="바이너리 (수동 연결: $SYMLINK_PATH)"
    fi
    echo -e "\033[1;36m* 설치 유형: $install_type\033[0m"
    echo ""

    # Process Exporter 구동 상태 확인
    if ps -ef | grep 'process_exporter' | grep -v grep | grep -v installer | grep -v vi > /dev/null; then
        echo -e "\033[1;31m* Process Exporter가 현재 실행 중입니다...\033[0m"
        ps -ef | grep 'process_exporter' | grep -v grep | grep -v installer | grep -v vi
        echo ""
    else
        echo -e "\033[1;36m* Process Exporter가 실행되고 있지 않습니다.\033[0m"
        echo ""
    fi

    # 포트 청취 여부 확인
    local check_port=$PORT
    if command -v ss >/dev/null 2>&1; then
        PORT_CHECK="ss -tulnp | grep \"LISTEN.*:$check_port\""
    else
        PORT_CHECK="netstat -tulnp | grep \"LISTEN.*:$check_port\""
    fi

    if eval "$PORT_CHECK" > /dev/null; then
        echo -e "\033[1;31m* 포트 $check_port 번호가 이미 Listening 상태입니다...\033[0m"
        eval "$PORT_CHECK"
    else
        echo -e "\033[1;36m* 포트 $check_port 번호는 사용 가능한 상태입니다."
    fi
    echo -e "\033[1;36m----------------------------------------------------------------------\033[0m"
}

function check_install_directory {
    if [[ ! -d "$INSTALL_DIR" ]] ; then
        log_info "설치 디렉토리가 존재하지 않아 생성합니다: $INSTALL_DIR..."
        mkdir -p "$INSTALL_DIR" || error_exit "디렉토리 생성에 실패했습니다: $INSTALL_DIR"
    fi
}

function check_selinux {
    if command -v getenforce >/dev/null 2>&1; then
        if [[ $(getenforce) == "Enforcing" ]]; then
            log_warn "SELinux가 Enforcing(활성) 모드입니다. 필요시 SELinux 보안 정책을 별도로 조정해야 할 수 있습니다."
        fi
    fi
}

function check_installation {
    if [[ -f "$SYMLINK_PATH" ]]; then
        binary=$(command -v process_exporter)
        if process_exporter --version >/dev/null 2>&1; then
            version=$(process_exporter --version 2>&1 | head -1)
        else
            version="버전 확인 불가"
        fi
        error_exit "Process Exporter가 이미 시스템에 설치되어 있습니다. ($version)"
    fi
}

function create_config {
    local config_path="$INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64/config.yml"
    if [[ "$PROCESS_EXPORTER_PROFILE" == "grouped" ]]; then
        sudo tee "$config_path" > /dev/null <<EOF
process_names:
  - name: "{{.Comm}}"
    cmdline:
    - '.+'
EOF
    else
        sudo tee "$config_path" > /dev/null <<EOF
process_names:
  - name: "{{.Comm}}({{.PID}}) [USER: {{.Username}}]"
    cmdline:
    - '.+'
EOF
    fi
    log_info "기본 설정 파일이 생성되었습니다: $config_path"
}

function select_process_exporter_profile {
    echo "-----------------------------------------------------------------------------------------"
    log_info "수집 방식 프로필(Profile)을 선택해 주세요:"
    echo "  1) 상세 수집 (기본값 - PID 기준 개별 프로세스 추적, 개발/테스트 권장)"
    echo "  2) 그룹 수집 (운영 권장 - 실행 파일명 기준 그룹화, 대용량 메트릭 폭발 방지)"
    local profile_choice
    while true; do
        read -p "선택 (1/2, 기본값: 1): " profile_choice
        profile_choice=${profile_choice:-1}
        if [[ "$profile_choice" == "1" ]]; then
            PROCESS_EXPORTER_PROFILE="detailed"
            log_info "상세 수집 모드가 설정되었습니다."
            break
        elif [[ "$profile_choice" == "2" ]]; then
            PROCESS_EXPORTER_PROFILE="grouped"
            log_info "그룹 수집 모드가 설정되었습니다."
            break
        else
            log_error "잘못된 선택입니다. 1 또는 2를 입력하세요."
        fi
    done
    echo "-----------------------------------------------------------------------------------------"
}

function online_install {
    log_info "Process Exporter 온라인 설치를 진행합니다..."
    log_info "다운로드할 Process Exporter 버전: $PROCESS_EXPORTER_VERSION"
    
    if [[ -f process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64.tar.gz ]]; then
        log_info "로컬에 이미 압축 파일이 존재하여 다운로드를 생략합니다."
    else
        wget https://github.com/ncabatoff/process-exporter/releases/download/v$PROCESS_EXPORTER_VERSION/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64.tar.gz || error_exit "다운로드에 실패했습니다."
    fi

    log_info "압축을 해제하는 중..."
    tar -xvf process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64.tar.gz -C $INSTALL_DIR || error_exit "압축 해제에 실패했습니다."
    cd $INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64 || error_exit "디렉토리 이동에 실패했습니다."
    sudo ln -sf "$INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64/process-exporter" "$SYMLINK_PATH" || error_exit "심링크 파일($SYMLINK_PATH) 생성에 실패했습니다."

    create_config
}

function offline_install {
    [[ -z "$BINARY_PATH" ]] && error_exit "오프라인 설치를 위해서는 로컬 바이너리 파일(tar.gz) 경로를 입력해야 합니다."

    log_info "Process Exporter 오프라인 설치를 진행합니다..."
    [[ ! -f "$BINARY_PATH" ]] && error_exit "지정된 바이너리 파일을 찾을 수 없습니다: $BINARY_PATH"
    PROCESS_EXPORTER_VERSION=$(echo "$BINARY_PATH" | sed -E 's/.*process-exporter-([0-9\.]+)\..*/\1/')
    [[ "$BINARY_PATH" == $PROCESS_EXPORTER_VERSION ]] && error_exit "파일명으로부터 process_exporter 버전을 추출할 수 없습니다: $BINARY_PATH"

    log_info "입력된 경로에서 압축 파일을 해제하는 중..."
    tar -xvf "$BINARY_PATH" -C $INSTALL_DIR || error_exit "압축 해제에 실패했습니다: $BINARY_PATH"
    cd $INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64 || error_exit "디렉토리 이동에 실패했습니다."
    sudo ln -sf "$INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64/process-exporter" "$SYMLINK_PATH" || error_exit "심링크 파일($SYMLINK_PATH) 생성에 실패했습니다."

    create_config
}

function configure_sysvinit_service {
    log_info "Process Exporter를 SysVInit 서비스로 설정하는 중..."

    cat > /etc/init.d/process_exporter <<EOF
#!/bin/bash
#
# process_exporter    Process Exporter
#
# chkconfig: 2345 80 20
# description: Process Exporter for Prometheus
# processname: process_exporter
# pidfile: /var/run/process_exporter.pid

### BEGIN INIT INFO
# Provides:          process_exporter
# Required-Start:    \$local_fs \$network \$named \$time
# Required-Stop:     \$local_fs \$network \$named \$time
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Process Exporter
# Description:       Process Exporter for Prometheus monitoring
### END INIT INFO

# Source function library
. /etc/init.d/functions

DAEMON=$SYMLINK_PATH
DAEMON_ARGS="--config.path=$INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64/config.yml --web.listen-address=:$PORT"
NAME=process_exporter
PIDFILE=/var/run/\${NAME}.pid
LOGFILE=/var/log/\${NAME}.log
USER=root

start() {
    echo -n \$"Starting \$NAME: "
    daemon --pidfile=\$PIDFILE "\$DAEMON \$DAEMON_ARGS >> \$LOGFILE 2>&1 & echo \\\$! > \$PIDFILE"
    RETVAL=\$?
    echo
    return \$RETVAL
}

stop() {
    echo -n \$"Stopping \$NAME: "
    killproc -p \$PIDFILE \$NAME
    RETVAL=\$?
    echo
    [ \$RETVAL = 0 ] && rm -f \$PIDFILE
    return \$RETVAL
}

restart() {
    stop
    start
}

case "\$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status -p \$PIDFILE \$NAME
        ;;
    restart|reload)
        restart
        ;;
    *)
        echo \$"Usage: \$0 {start|stop|status|restart}"
        exit 1
esac

exit \$?
EOF

    chmod +x /etc/init.d/process_exporter
    chkconfig --add process_exporter
    chkconfig process_exporter on
    service process_exporter start || error_exit "Process Exporter 서비스 시작에 실패했습니다."

    log_info "SysVInit 서비스 설정이 성공적으로 완료되었습니다."
}

function configure_service {
    if [[ "$INIT_SYSTEM" == "systemd" ]]; then
        log_info "Process Exporter를 systemd 서비스로 설정하는 중..."

        sudo tee /etc/systemd/system/process_exporter.service > /dev/null <<EOF
[Unit]
Description=Process Exporter
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=$SYMLINK_PATH --config.path=$INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64/config.yml --web.listen-address=:$PORT

[Install]
WantedBy=multi-user.target
EOF

        log_info "Process Exporter 서비스를 등록 및 시작하는 중..."
        sudo systemctl daemon-reload || error_exit "systemd 데몬 리로드에 실패했습니다."
        sudo systemctl enable process_exporter || error_exit "Process Exporter 서비스 활성화에 실패했습니다."
        sudo systemctl restart process_exporter || error_exit "Process Exporter 서비스 시작(재기동)에 실패했습니다."
    else
        configure_sysvinit_service
    fi

    # 기존 시스템 전역(/usr/local/bin) 심링크 찌꺼기 안전 제거
    if [[ -f "/usr/local/bin/process_exporter" ]] && [[ "/usr/local/bin/process_exporter" != "$SYMLINK_PATH" ]]; then
        rm -f "/usr/local/bin/process_exporter"
        log_info "시스템 전역(/usr/local/bin)에 존재하던 레거시 심링크 찌꺼기를 정리했습니다."
    fi

    log_info "Process Exporter 서비스 구성 및 설치 작업이 성공적으로 완료되었습니다."
}

function uninstall {
    log_info "Process Exporter 제거를 시작합니다..."

    # 실행 중인 프로세스 중지 - 모든 방식 시도
    if command -v systemctl >/dev/null 2>&1; then
        systemctl stop process_exporter 2>/dev/null || log_error "systemctl을 통한 서비스 중지에 실패했습니다."
        systemctl disable process_exporter 2>/dev/null || log_error "서비스 비활성화에 실패했습니다."
        rm -f /etc/systemd/system/process_exporter.service 2>/dev/null || log_error "systemd 서비스 파일 삭제에 실패했습니다."
        systemctl daemon-reload 2>/dev/null
    fi
    
    service process_exporter stop 2>/dev/null || log_error "service 명령을 통한 중지에 실패했습니다."
    chkconfig process_exporter off 2>/dev/null || log_error "chkconfig를 통한 서비스 해제에 실패했습니다."
    rm -f /etc/init.d/process_exporter 2>/dev/null || log_error "init.d 스크립트 삭제에 실패했습니다."

    # 프로세스가 여전히 실행 중인지 확인
    if pgrep -f "process_exporter" > /dev/null; then
        log_error "Process Exporter 프로세스가 여전히 기동 중입니다. 강제 종료를 시도합니다..."
        pkill -f "process_exporter" || log_error "프로세스 강제 종료에 실패했습니다."
    fi

    # 파일 정리
    if [[ -f "$SYMLINK_PATH" ]]; then
        rm -f "$SYMLINK_PATH" || error_exit "심링크 파일($SYMLINK_PATH) 제거에 실패했습니다."
    fi
    # 시스템 전역(/usr/local/bin) 심링크 잔여물 안전 제거
    if [[ -f "/usr/local/bin/process_exporter" ]] && [[ "/usr/local/bin/process_exporter" != "$SYMLINK_PATH" ]]; then
        rm -f "/usr/local/bin/process_exporter"
    fi

    DELETE_DIR="$INSTALL_DIR/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64"
    if [[ -d "$DELETE_DIR" ]]; then
        rm -rf "$DELETE_DIR" || error_exit "Process Exporter 디렉토리($DELETE_DIR) 삭제에 실패했습니다."
    fi

    log_info "Process Exporter가 성공적으로 언인스톨(제거)되었습니다."
    exit 0
}

function prune_unused_binaries {
    log_info "현재 디렉토리에서 미사용 Process Exporter 바이너리를 검색하는 중..."
    
    # 현재 실행 중이거나 심링크된 활성 버전 확인
    local active_version=""
    if [[ -L "$SYMLINK_PATH" ]]; then
        local real_binary=$(readlink -f "$SYMLINK_PATH")
        active_version=$(echo "$real_binary" | grep -oE 'process-exporter-[0-9]+\.[0-9]+\.[0-9]+' | sed 's/process-exporter-//')
    fi
    
    log_info "보호 대상 활성 Process Exporter 버전: ${active_version:-없음}"
    
    # 현재 디렉토리($PWD)에서 process-exporter-*.tar.gz 스캔
    local tar_files=()
    while IFS= read -r -d '' file; do
        tar_files+=("$file")
    done < <(find . -maxdepth 1 -type f -name "process-exporter-*.linux-amd64.tar.gz" -print0 | sort -z)
    
    if [ ${#tar_files[@]} -eq 0 ]; then
        log_warn "현재 디렉토리에 process-exporter-*.tar.gz 파일이 존재하지 않습니다."
        return 0
    fi
    
    echo -e "\n발견된 Process Exporter 바이너리 및 디렉토리 목록:"
    local valid_targets=()
    local display_idx=1
    
    for tar_file in "${tar_files[@]}"; do
        local base_name=$(basename "$tar_file")
        local dir_name="${base_name%.tar.gz}"
        local ver_num=$(echo "$base_name" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        
        local is_active=false
        if [[ -n "$active_version" ]] && [[ "$ver_num" == "$active_version" ]]; then
            is_active=true
        fi
        
        local dir_exists="존재하지 않음"
        if [[ -d "./$dir_name" ]]; then
            dir_exists="존재"
        fi
        
        if [[ "$is_active" == "true" ]]; then
            echo "  ${display_idx}) $base_name (폴더: $dir_exists) [현재 사용 중 - 삭제 불가]"
        else
            echo "  ${display_idx}) $base_name (폴더: $dir_exists) [삭제 가능]"
            valid_targets+=("$display_idx:$tar_file:$dir_name")
        fi
        display_idx=$((display_idx + 1))
    done
    
    if [ ${#valid_targets[@]} -eq 0 ]; then
        log_info "정리할 수 있는 미사용 바이너리가 존재하지 않습니다."
        return 0
    fi
    
    echo
    read -p "삭제할 바이너리 번호를 선택하세요 (또는 'q'로 취소): " choice
    if [[ "$choice" == "q" ]] || [[ "$choice" == "Q" ]]; then
        log_info "바이너리 정리가 취소되었습니다."
        return 0
    fi
    
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -lt "$display_idx" ]; then
        local target_info=""
        for item in "${valid_targets[@]}"; do
            if [[ "$item" == "$choice:"* ]]; then
                target_info="$item"
                break
            fi
        done
        
        if [[ -z "$target_info" ]]; then
            log_error "선택하신 바이너리는 사용 중이거나 삭제할 수 없는 항목입니다."
            return 0
        fi
        
        local t_file=$(echo "$target_info" | cut -d':' -f2)
        local t_dir=$(echo "$target_info" | cut -d':' -f3)
        
        echo -e "\n다음 항목들이 시스템에서 영구적으로 삭제됩니다:"
        echo "- 압축 파일: $t_file"
        if [[ -d "./$t_dir" ]]; then
            echo "- 해제 폴더: ./$t_dir"
        fi
        
        read -p "정말 삭제하시겠습니까? (y/n): " confirm
        local clean_confirm="${confirm,,}"
        clean_confirm="${clean_confirm//[[:space:]]/}"
        clean_confirm="${clean_confirm//$'\r'/}"
        
        if [[ "$clean_confirm" == "y" ]] || [[ "$clean_confirm" == "yes" ]]; then
            log_info "삭제를 진행하는 중..."
            rm -f "$t_file"
            if [[ -d "./$t_dir" ]]; then
                rm -rf "./$t_dir"
            fi
            log_info "삭제가 성공적으로 완료되었습니다."
            
            # 삭제 후 남은 파일 목록 1회성 출력
            echo -e "\n[현재 디렉토리의 정리 후 파일 현황]"
            for f in process-exporter-*.linux-amd64.tar.gz; do
                if [[ -f "$f" ]]; then
                    local d="${f%.tar.gz}"
                    local d_exists="존재하지 않음"
                    [[ -d "$d" ]] && d_exists="존재"
                    echo "  - $f (폴더: $d_exists)"
                fi
            done
        else
            log_info "삭제가 취소되었습니다."
        fi
    else
        log_error "잘못된 선택 번호입니다."
    fi
}

show_main_menu() {
    echo
    echo "===================================================="
    echo "  Process Exporter 관리 스크립트 v$SCRIPT_VERSION (2026.07.20)"
    echo "  [실행 경로] $PWD"
    echo "===================================================="
    echo "1. 시스템 정보 및 서비스 상태 확인"
    echo "2. 온라인 설치 (바이너리)"
    echo "3. 오프라인 설치 (바이너리)"
    echo "4. 미사용 바이너리 관리 (Prune)"
    echo "5. 서비스 삭제 (Uninstall)"
    echo "q. 종료"
    echo "===================================================="
    echo -n "메뉴를 선택하세요: "
}

main() {
    local choice
    
    # 로컬 파일 기준 기본 버전 설정 최신화
    initialize_default_version
    
    while true; do
        show_main_menu
        read choice
        echo
        
        case $choice in
            1)
                log_info "시스템 정보 및 서비스 상태를 확인합니다..."
                system_information
                echo
                read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                ;;
            2)
                INSTALL_MODE="online"
                log_warn "외부 API(GitHub) 및 다운로드 연결을 시도합니다."
                log_warn "사내 방화벽 정책에 의해 연결이 차단되거나 보안 팀의 확인 문의가 있을 수 있습니다."
                echo
                log_info "GitHub에서 최신 Process Exporter 버전을 조회하는 중..."
                PROCESS_EXPORTER_LATEST_VERSION=$(curl --connect-timeout 3 -s https://api.github.com/repos/ncabatoff/process-exporter/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' | sed -E 's/^v//')
                PROCESS_EXPORTER_LATEST_VERSION=${PROCESS_EXPORTER_LATEST_VERSION:-$DEFAULT_PROCESS_EXPORTER_VERSION}
                
                read -p "설치할 버전을 입력하세요 (기본값: $DEFAULT_PROCESS_EXPORTER_VERSION / 최신: $PROCESS_EXPORTER_LATEST_VERSION, 또는 'q'로 취소): " PROCESS_EXPORTER_VERSION
                if [[ "$PROCESS_EXPORTER_VERSION" == "q" ]] || [[ "$PROCESS_EXPORTER_VERSION" == "Q" ]]; then
                    log_info "설치가 취소되었습니다."
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                PROCESS_EXPORTER_VERSION=${PROCESS_EXPORTER_VERSION:-$DEFAULT_PROCESS_EXPORTER_VERSION}
                
                read -p "설치 디렉토리 경로를 입력하세요 (기본값: $DEFAULT_INSTALL_DIR, 또는 'q'로 취소): " INSTALL_DIR
                if [[ "$INSTALL_DIR" == "q" ]] || [[ "$INSTALL_DIR" == "Q" ]]; then
                    log_info "설치가 취소되었습니다."
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}
                SYMLINK_PATH="$INSTALL_DIR/process_exporter"
                
                echo "-----------------------------------------------------------------------------------------"
                echo "설치 방식: $INSTALL_MODE"
                echo "설치 디렉토리: $INSTALL_DIR"
                
                read -p "설치를 계속 진행하시겠습니까? (y/n): " CONFIRM
                local clean_confirm="${CONFIRM,,}"
                clean_confirm="${clean_confirm//[[:space:]]/}"
                clean_confirm="${clean_confirm//$'\r'/}"
                if [[ "$clean_confirm" != "y" ]] && [[ "$clean_confirm" != "yes" ]]; then
                    log_info "설치가 중단되었습니다."
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                
                check_installation
                check_selinux
                check_install_directory
                resolve_port_conflict
                select_process_exporter_profile
                online_install
                configure_service
                log_info "설치가 성공적으로 완료되었습니다."
                echo
                read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                ;;
            3)
                INSTALL_MODE="offline"
                if ! select_local_binary; then
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                
                read -p "설치 디렉토리 경로를 입력하세요 (기본값: $DEFAULT_INSTALL_DIR, 또는 'q'로 취소): " INSTALL_DIR
                if [[ "$INSTALL_DIR" == "q" ]] || [[ "$INSTALL_DIR" == "Q" ]]; then
                    log_info "설치가 취소되었습니다."
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}
                SYMLINK_PATH="$INSTALL_DIR/process_exporter"
                
                echo "-----------------------------------------------------------------------------------------"
                echo "설치 방식: $INSTALL_MODE"
                echo "설치 파일 경로: $BINARY_PATH"
                echo "설치 디렉토리: $INSTALL_DIR"
                
                read -p "설치를 계속 진행하시겠습니까? (y/n): " CONFIRM
                local clean_confirm="${CONFIRM,,}"
                clean_confirm="${clean_confirm//[[:space:]]/}"
                clean_confirm="${clean_confirm//$'\r'/}"
                if [[ "$clean_confirm" != "y" ]] && [[ "$clean_confirm" != "yes" ]]; then
                    log_info "설치가 중단되었습니다."
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                
                check_installation
                check_selinux
                check_install_directory
                resolve_port_conflict
                select_process_exporter_profile
                offline_install
                configure_service
                log_info "설치가 성공적으로 완료되었습니다."
                echo
                read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                ;;
            4)
                prune_unused_binaries
                echo
                read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                ;;
            5)
                INSTALL_MODE="uninstall"
                read -p "제거할 Process Exporter 설치 디렉토리를 입력하세요 (기본값: $DEFAULT_INSTALL_DIR, 또는 'q'로 취소): " INSTALL_DIR
                if [[ "$INSTALL_DIR" == "q" ]] || [[ "$INSTALL_DIR" == "Q" ]]; then
                    log_info "제거 작업이 취소되었습니다."
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}
                SYMLINK_PATH="$INSTALL_DIR/process_exporter"
                
                read -p "정말 Process Exporter를 삭제하시겠습니까? (y/n): " CONFIRM
                local clean_confirm="${CONFIRM,,}"
                clean_confirm="${clean_confirm//[[:space:]]/}"
                clean_confirm="${clean_confirm//$'\r'/}"
                if [[ "$clean_confirm" != "y" ]] && [[ "$clean_confirm" != "yes" ]]; then
                    log_info "제거 작업이 취소되었습니다."
                    echo
                    read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                    continue
                fi
                
                uninstall
                echo
                read -p "Enter를 누르면 메인 메뉴로 돌아갑니다..." input
                ;;
            q|Q)
                log_info "프로그램을 종료합니다."
                exit 0
                ;;
            *)
                log_error "잘못된 선택입니다."
                sleep 1
                ;;
        esac
    done
}

# 스크립트 실행
main
