#!/bin/bash

# Default values for installation
DEFAULT_BINARY_PATH="$(pwd)/node_exporter-1.8.2.linux-amd64.tar.gz"
DEFAULT_INSTALL_DIR="/opt/monitoring/node_exporter"
DEFAULT_NODE_EXPORTER_VERSION="1.8.2"
NODE_EXPORTER_LATEST_VERSION=""
SYMLINK_PATH="/usr/local/bin/node_exporter"
PORT=9100
INIT_SYSTEM=""
COLLECTOR_PARAMS=""

# Function to handle errors and exit
function error_exit {
    echo -e "\033[1;33m[ERROR] $1\033[0m" >&2
    exit 1
}

# Function to log installation progress
function log_info {
    echo -e "\033[1;36m[INFO] $1\033[0m"
}

function log_error {
    echo -e "\033[1;33m[ERROR] $1\033[0m"
}

if [[ $(id -u) -ne 0 ]]; then
    error_exit "This script must be run as root"
fi

# Enhanced system information detection
function detect_init_system {
    if command -v systemctl >/dev/null 2>&1 && pidof systemd >/dev/null 2>&1; then
        INIT_SYSTEM="systemd"
    elif [[ -f /etc/init.d/functions ]] || [[ -f /etc/rc.d/init.d/functions ]]; then
        INIT_SYSTEM="sysvinit"
    elif [[ -f /etc/init/rc.conf ]]; then
        INIT_SYSTEM="upstart"
    else
        log_error "Unable to detect init system. Defaulting to systemd..."
        INIT_SYSTEM="systemd"
    fi
    
    log_info "Detected init system: $INIT_SYSTEM"
}

function set_collector_params {
    if [[ -f /etc/redhat-release ]]; then
        MAJOR_VERSION=$(cat /etc/redhat-release | grep -oE '[0-9]+\.' | cut -d. -f1)
        if [[ "$MAJOR_VERSION" == "6" ]]; then
            log_info "CentOS/RHEL 6.x detected. Note: If you experience issues with filesystem metrics, you may need to use '--no-collector.filesystem' parameter."
            read -p "Do you want to disable filesystem collector? (y/n, or 'q' to cancel): " DISABLE_FS
            local clean_dfs="${DISABLE_FS,,}"
            clean_dfs="${clean_dfs//[[:space:]]/}"
            clean_dfs="${clean_dfs//$'\r'/}"
            if [[ "$clean_dfs" == "q" ]]; then
                echo "Installation canceled."
                exit 0
            fi
            if [[ "$clean_dfs" == "y" ]] || [[ "$clean_dfs" == "yes" ]]; then
                COLLECTOR_PARAMS="--no-collector.filesystem"
                log_info "Filesystem collector will be disabled."
            fi
        fi
    fi
}

function system_information {
    echo -e "\033[1;36m-------------------------------System Information----------------------------\033[0m"

    # Enhanced OS detection
    if [[ -f /etc/redhat-release ]]; then
        OS_VERSION=$(cat /etc/redhat-release)
        MAJOR_VERSION=$(echo "$OS_VERSION" | grep -oE '[0-9]+\.' | cut -d. -f1)
        echo -e "\033[1;36m* Operating System: $OS_VERSION\033[0m"
        echo -e "\033[1;36m* Major Version: $MAJOR_VERSION\033[0m"
    elif [[ -f /etc/os-release ]]; then
        OS_NAME=$(grep '^NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')
        OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
        echo -e "\033[1;36m* Operating System: $OS_NAME $OS_VERSION\033[0m"
    else
        OS_NAME=$(uname -s)
        OS_VERSION=$(uname -r)
        echo -e "\033[1;36m* Operating System: $OS_NAME $OS_VERSION\033[0m"
    fi

    # Detect and display init system
    detect_init_system
    echo -e "\033[1;36m* Init System: $INIT_SYSTEM\033[0m"
    echo ""

    # Check if Node Exporter is running
    if ps -ef | grep 'node_exporter' | grep -v grep | grep -v installer | grep -v vi > /dev/null; then
        echo -e "\033[1;31m* Node Exporter is running...\033[0m"
        ps -ef | grep 'node_exporter' | grep -v grep | grep -v installer | grep -v vi
        echo ""
    else
        echo -e "\033[1;36m* Node Exporter is not running\033[0m"
        echo ""
    fi

    # Check port availability using netstat or ss
    if command -v ss >/dev/null 2>&1; then
        PORT_CHECK="ss -tulnp | grep \"LISTEN.*:$PORT\""
    else
        PORT_CHECK="netstat -tulnp | grep \"LISTEN.*:$PORT\""
    fi

    if eval "$PORT_CHECK" > /dev/null; then
        echo -e "\033[1;31m* Port $PORT is listening...\033[0m"
        eval "$PORT_CHECK"
        PORT=38001
        while true; do
            if command -v ss >/dev/null 2>&1; then
                CHECK_CMD="ss -tulnp | grep \"LISTEN.*:$PORT\""
            else
                CHECK_CMD="netstat -tulnp | grep \"LISTEN.*:$PORT\""
            fi
            if eval "$CHECK_CMD" > /dev/null; then
                echo -e "\033[1;31m* Port $PORT is listening...\033[0m"
                eval "$CHECK_CMD"
                ((PORT+=1))
            else
                break
            fi
        done
        log_info "The port has been changed to \"$PORT\"."
    else
        echo -e "\033[1;36m* Port 9100 is not using...\033[0m"
    fi
    echo -e "\033[1;36m-----------------------------------------------------------------------------\033[0m"
}

function check_install_directory {
    if [[ ! -d "$INSTALL_DIR" ]] ; then
        log_info "Installation directory does not exist. Creating $INSTALL_DIR..."
        mkdir -p "$INSTALL_DIR" || error_exit "Failed to create directory $INSTALL_DIR."
    fi
}

function check_selinux {
    if command -v getenforce >/dev/null 2>&1; then
        if [[ $(getenforce) == "Enforcing" ]]; then
            # error_exit "SELinux is enabled. You need to disable..(e.g. setenforce 0)"
            echo -e "\033[1;35m[WARNING] SELinux is enabled. You might need to configure SELinux policy.\033[0m"
        fi
    fi
}

function check_installation {
    if [[ -f "$SYMLINK_PATH" ]]; then
        binary=$(command -v node_exporter)
        if node_exporter --version >/dev/null 2>&1; then
            version=$(node_exporter --version 2>&1 | head -1)
        else
            version="version unknown"
        fi
        error_exit "Node Exporter is already installed. ($version)"
    fi
}

function online_install {
    log_info "Starting online installation of Node Exporter..."

    log_info "Downloading Node Exporter version: $NODE_EXPORTER_VERSION"
    wget https://github.com/prometheus/node_exporter/releases/download/v$NODE_EXPORTER_VERSION/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz || error_exit "Download failed."

    # Extract and install
    log_info "Extracting Node Exporter..."
    tar -xvf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz -C $INSTALL_DIR || error_exit "Failed to extract Node Exporter."
    cd $INSTALL_DIR/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64 || error_exit "Failed to change directory."
    sudo ln -s "$INSTALL_DIR/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" "$SYMLINK_PATH" || error_exit "Failed to create symlink at $SYMLINK_PATH."
}

function offline_install {
    [[ -z "$BINARY_PATH" ]] && error_exit "Binary path must be provided for offline installation."

    log_info "Starting offline installation of Node Exporter..."
    [[ ! -f "$BINARY_PATH" ]] && error_exit "File not found at $BINARY_PATH."
    NODE_EXPORTER_VERSION=$(echo "$BINARY_PATH" | sed -E 's/.*node_exporter-([0-9\.]+)\..*/\1/')
    [[ "$BINARY_PATH" == $NODE_EXPORTER_VERSION ]] && error_exit "Failed to extract node_exporter version from filename: $BINARY_PATH"

    log_info "Extracting Node Exporter from provided path..."
    tar -xvf "$BINARY_PATH" -C $INSTALL_DIR || error_exit "Failed to extract Node Exporter from $BINARY_PATH."
    cd $INSTALL_DIR/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64 || error_exit "Failed to change directory."
    sudo ln -s "$INSTALL_DIR/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" "$SYMLINK_PATH" || error_exit "Failed to create symlink at $SYMLINK_PATH."
}

function configure_sysvinit_service {
    log_info "Configuring Node Exporter as a sysvinit service..."

    cat > /etc/init.d/node_exporter <<EOF
#!/bin/bash
#
# node_exporter    Node Exporter
#
# chkconfig: 2345 80 20
# description: Node Exporter for Prometheus
# processname: node_exporter
# pidfile: /var/run/node_exporter.pid

### BEGIN INIT INFO
# Provides:          node_exporter
# Required-Start:    \$local_fs \$network \$named \$time
# Required-Stop:     \$local_fs \$network \$named \$time
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Node Exporter
# Description:       Node Exporter for Prometheus monitoring
### END INIT INFO

# Source function library
. /etc/init.d/functions

DAEMON=$SYMLINK_PATH
DAEMON_ARGS="--web.listen-address=:$PORT $COLLECTOR_PARAMS"
NAME=node_exporter
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

    chmod +x /etc/init.d/node_exporter
    chkconfig --add node_exporter
    chkconfig node_exporter on
    service node_exporter start || error_exit "Failed to start Node Exporter service"

    log_info "SysVInit service configuration completed"
}

function configure_service {
    if [[ "$INIT_SYSTEM" == "systemd" ]]; then
        log_info "Configuring Node Exporter as a systemd service..."

        sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
Environment="NODE_EXPORTER_ARGS=--web.listen-address=\":$PORT\" $COLLECTOR_PARAMS"
ExecStart=$SYMLINK_PATH \$NODE_EXPORTER_ARGS

[Install]
WantedBy=multi-user.target
EOF

        log_info "Enabling and starting Node Exporter service..."
        sudo systemctl daemon-reload || error_exit "Failed to reload systemd."
        sudo systemctl enable node_exporter || error_exit "Failed to enable Node Exporter service."
        sudo systemctl start node_exporter || error_exit "Failed to start Node Exporter service."
    else
        configure_sysvinit_service
    fi

    log_info "Node Exporter installation and configuration completed."
}

function uninstall {
    log_info "Uninstalling Node Exporter..."

    # 실행 중인 프로세스 중지 - 모든 방식 시도
    if command -v systemctl >/dev/null 2>&1; then
        systemctl stop node_exporter 2>/dev/null || log_error "Failed to stop Node Exporter via systemctl"
        systemctl disable node_exporter 2>/dev/null || log_error "Failed to disable Node Exporter service"
        rm -f /etc/systemd/system/node_exporter.service 2>/dev/null || log_error "Failed to remove systemd service file"
        systemctl daemon-reload 2>/dev/null
    fi
    
    service node_exporter stop 2>/dev/null || log_error "Failed to stop Node Exporter via service command"
    chkconfig node_exporter off 2>/dev/null || log_error "Failed to disable Node Exporter via chkconfig"
    rm -f /etc/init.d/node_exporter 2>/dev/null || log_error "Failed to remove init.d script"

    # 프로세스가 여전히 실행 중인지 확인
    if pgrep -f "node_exporter" > /dev/null; then
        log_error "Node Exporter process is still running. Attempting to kill..."
        pkill -f "node_exporter" || log_error "Failed to kill Node Exporter process"
    fi

    # 파일 정리
    if [[ -f "$SYMLINK_PATH" ]]; then
        rm -f "$SYMLINK_PATH" || error_exit "Failed to remove symlink $SYMLINK_PATH"
    fi

    DELETE_DIR="$INSTALL_DIR/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64"
    if [[ -d "$DELETE_DIR" ]]; then
        rm -rf "$DELETE_DIR" || error_exit "Failed to remove Node Exporter directory $DELETE_DIR"
    fi

    log_info "Node Exporter has been uninstalled successfully."
    exit 0
}

function prune_unused_binaries {
    log_info "Searching for unused Node Exporter binaries in the current directory..."
    
    # 현재 실행 중이거나 심링크된 활성 버전 확인
    local active_version=""
    if [[ -L "$SYMLINK_PATH" ]]; then
        local real_binary=$(readlink -f "$SYMLINK_PATH")
        active_version=$(echo "$real_binary" | grep -oE 'node_exporter-[0-9\.]+' | sed 's/node_exporter-//')
    fi
    
    log_info "Active Node Exporter version to protect: ${active_version:-none}"
    
    # 현재 디렉토리($PWD)에서 node_exporter-*.tar.gz 스캔
    local tar_files=()
    while IFS= read -r -d '' file; do
        tar_files+=("$file")
    done < <(find . -maxdepth 1 -type f -name "node_exporter-*.linux-amd64.tar.gz" -print0 | sort -z)
    
    if [ ${#tar_files[@]} -eq 0 ]; then
        log_warn "No node_exporter-*.tar.gz files found in the current directory."
        return 0
    fi
    
    echo -e "\nFound node_exporter binaries:"
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
        
        local dir_exists="No"
        if [[ -d "./$dir_name" ]]; then
            dir_exists="Yes"
        fi
        
        if [[ "$is_active" == "true" ]]; then
            echo "  ${display_idx}) $base_name (folder: $dir_exists) [ACTIVE - Cannot delete]"
        else
            echo "  ${display_idx}) $base_name (folder: $dir_exists) [Unused - Can delete]"
            valid_targets+=("$display_idx:$tar_file:$dir_name")
        fi
        display_idx=$((display_idx + 1))
    done
    
    if [ ${#valid_targets[@]} -eq 0 ]; then
        log_info "No unused binaries to delete."
        return 0
    fi
    
    echo
    read -p "Select the binary number to delete (or 'q' to cancel): " choice
    if [[ "$choice" == "q" ]] || [[ "$choice" == "Q" ]]; then
        log_info "Pruning canceled."
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
            log_error "Selected number is active or cannot be deleted."
            return 0
        fi
        
        local t_file=$(echo "$target_info" | cut -d':' -f2)
        local t_dir=$(echo "$target_info" | cut -d':' -f3)
        
        echo -e "\nThe following items will be deleted:"
        echo "- File: $t_file"
        if [[ -d "./$t_dir" ]]; then
            echo "- Folder: ./$t_dir"
        fi
        
        read -p "Are you sure you want to delete? (y/n): " confirm
        local clean_confirm="${confirm,,}"
        clean_confirm="${clean_confirm//[[:space:]]/}"
        clean_confirm="${clean_confirm//$'\r'/}"
        
        if [[ "$clean_confirm" == "y" ]] || [[ "$clean_confirm" == "yes" ]]; then
            log_info "Deleting..."
            rm -f "$t_file"
            if [[ -d "./$t_dir" ]]; then
                rm -rf "./$t_dir"
            fi
            log_info "Deletion completed successfully."
            
            # 삭제 후 남은 파일 목록 1회성 출력
            echo -e "\n[Updated node_exporter files in current directory]"
            for f in node_exporter-*.linux-amd64.tar.gz; do
                if [[ -f "$f" ]]; then
                    local d="${f%.tar.gz}"
                    local d_exists="No"
                    [[ -d "$d" ]] && d_exists="Yes"
                    echo "  - $f (folder: $d_exists)"
                  fi
              done
          else
              log_info "Deletion canceled."
          fi
      else
          log_error "Invalid selection."
      fi
}

# Display system information
system_information

# Set collector parameters based on OS version
set_collector_params

# Handle installation mode selection
while true; do
    case "$INSTALL_MODE_INPUT" in
        1)
            INSTALL_MODE="online"
            log_info "Fetching latest Node Exporter version from GitHub..."
            NODE_EXPORTER_LATEST_VERSION=$(curl --connect-timeout 3 -s https://api.github.com/repos/prometheus/node_exporter/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
            NODE_EXPORTER_LATEST_VERSION=${NODE_EXPORTER_LATEST_VERSION:-$DEFAULT_NODE_EXPORTER_VERSION}
            
            read -p "Enter the Node Exporter version to install (default: $DEFAULT_NODE_EXPORTER_VERSION / latest: $NODE_EXPORTER_LATEST_VERSION, or 'q' to cancel): " NODE_EXPORTER_VERSION
            if [[ "$NODE_EXPORTER_VERSION" == "q" ]] || [[ "$NODE_EXPORTER_VERSION" == "Q" ]]; then
                echo "Installation canceled."
                exit 0
            fi
            NODE_EXPORTER_VERSION=${NODE_EXPORTER_VERSION:-$DEFAULT_NODE_EXPORTER_VERSION}
            break
            ;;
        2)
            INSTALL_MODE="offline"
            read -p "Enter the path to the installation file (default: $DEFAULT_BINARY_PATH, or 'q' to cancel): " BINARY_PATH
            if [[ "$BINARY_PATH" == "q" ]] || [[ "$BINARY_PATH" == "Q" ]]; then
                echo "Installation canceled."
                exit 0
            fi
            BINARY_PATH=${BINARY_PATH:-$DEFAULT_BINARY_PATH}
            break
            ;;
        3)
            INSTALL_MODE="uninstall"
            break
            ;;
        4)
            prune_unused_binaries
            INSTALL_MODE_INPUT=""
            echo
            ;;
        5)
            exit 0
            ;;
        *)
            echo "Choose installation method: "
            echo "1. Online install"
            echo "2. Offline install"
            echo "3. Uninstall"
            echo "4. Prune unused binaries"
            echo "5. exit"
            read -p "Enter your choice (1/2/3/4/5): " INSTALL_MODE_INPUT
            ;;
    esac
done

if [[ "$INSTALL_MODE" == "uninstall" ]]; then
    NODE_EXPORTER_VERSION=${BINARY_PATH:-$DEFAULT_NODE_EXPORTER_VERSION}
    read -p "Enter the uninstallation directory (default: $DEFAULT_INSTALL_DIR, or 'q' to cancel): " INSTALL_DIR
    if [[ "$INSTALL_DIR" == "q" ]] || [[ "$INSTALL_DIR" == "Q" ]]; then
        echo "Uninstallation canceled."
        exit 0
    fi
    INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}

    read -p "Proceed with the uninstallation? (y/n): " CONFIRM
    local clean_confirm="${CONFIRM,,}"
    clean_confirm="${clean_confirm//[[:space:]]/}"
    clean_confirm="${clean_confirm//$'\r'/}"
    if [[ "$clean_confirm" != "y" ]] && [[ "$clean_confirm" != "yes" ]]; then
        echo "Uninstallation aborted."
        exit 0
    fi
else
    read -p "Enter the installation directory (default: $DEFAULT_INSTALL_DIR, or 'q' to cancel): " INSTALL_DIR
    if [[ "$INSTALL_DIR" == "q" ]] || [[ "$INSTALL_DIR" == "Q" ]]; then
        echo "Installation canceled."
        exit 0
    fi
    INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}

    echo "-----------------------------------------------------------------------------------------"
    echo "Installation mode: $INSTALL_MODE"
    if [[ "$INSTALL_MODE" == "offline" ]]; then
        echo "Installation file path: $BINARY_PATH"
    fi
    echo "Installation directory: $INSTALL_DIR"

    read -p "Proceed with the installation? (y/n): " CONFIRM
    local clean_confirm="${CONFIRM,,}"
    clean_confirm="${clean_confirm//[[:space:]]/}"
    clean_confirm="${clean_confirm//$'\r'/}"
    if [[ "$clean_confirm" != "y" ]] && [[ "$clean_confirm" != "yes" ]]; then
        echo "Installation aborted."
        exit 0
    fi
fi

# Branching for online or offline installation
case "$INSTALL_MODE" in
    online)
        check_installation
        check_selinux
        check_install_directory
        online_install
        ;;
    offline)
        check_installation
        check_selinux
        check_install_directory
        offline_install
        ;;
    uninstall)
        uninstall
        ;;
    *)
        error_exit "Invalid installation mode."
        ;;
esac

# Configure Node Exporter service if not uninstalling
if [[ "$INSTALL_MODE" != "uninstall" ]]; then
    configure_service
    log_info "Installation finished successfully."
fi
