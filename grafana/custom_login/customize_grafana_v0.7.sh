#!/bin/bash

# Grafana 커스터마이징 스크립트 v0.7
# 작성일: 2026-07-19
#
# 변경사항 v0.7:
# - 로그인 후 사이드바의 타이틀(AppTitle) 변경 기능 추가
# - 로그인 화면 타이틀(LoginTitle) 및 Welcome to Grafana 문구 치환 로직 개선 (이미 치환된 상태에서도 중복 변경 가능하도록 대응)
# - 백업 및 복구(Restore) 대상에 AppTitle 및 LoginTitle 변경 파일(Branding 관련 JS 번들) 추가
# - 다단계 마법사(Wizard) 단계 재정렬 (백업 -> 로그인 문구 -> 로그인 후 사이드바의 타이틀 -> 테마 선택)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 전역 변수
BACKUP_ENABLED=false
LOGIN_TEXT=""
APP_TITLE=""
THEME_NAME=""
THEME_DIR=""

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# sudo 권한 체크
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        log_error "이 스크립트는 루트(root) 권한으로 실행해야 합니다."
        log_error "다음 명령어를 사용해 다시 실행해주세요: sudo $0"
        exit 1
    fi
    log_info "루트 권한으로 실행 확인되었습니다."
}

# Grafana 설치 확인
check_grafana() {
    log_info "Grafana 설치 상태를 확인하는 중..."
    
    if systemctl list-unit-files | grep -q "grafana-server"; then
        log_success "Grafana 서비스가 발견되었습니다."
        return 0
    elif which grafana-server >/dev/null 2>&1; then
        log_success "Grafana가 설치되어 있습니다."
        return 0
    else
        log_error "Grafana가 설치되어 있지 않습니다."
        exit 1
    fi
}

# 해시가 포함된 파일명 목록 찾기
find_hashed_files() {
    local base_name="$1"
    local search_dir="$2"
    
    local name_without_ext="${base_name%.*}"
    local extension="${base_name##*.}"
    
    # 패턴으로 모든 파일 찾기
    local found_files=$(find "$search_dir" -name "${name_without_ext}.*.${extension}" 2>/dev/null)
    
    if [[ -n "$found_files" ]]; then
        echo "$found_files"
        return 0
    else
        return 1
    fi
}

# 파일 존재 확인 (Grafana 타겟 파일 검증)
check_files() {
    log_info "대상 파일들의 존재를 확인하는 중..."
    
    local required_dirs=(
        "/usr/share/grafana/public/img"
        "/usr/share/grafana/public/build"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_error "필수 디렉토리를 찾을 수 없습니다: $dir"
            exit 1
        fi
    done

    local static_img_dir="/usr/share/grafana/public/build/static/img"
    local legacy_img_dir="/usr/share/grafana/public/img"
    local all_found=true

    if [[ ! -f "$legacy_img_dir/fav32.png" ]]; then
        log_error "필수 파일을 찾을 수 없습니다: $legacy_img_dir/fav32.png"
        all_found=false
    fi

    local image_files=("grafana_icon.svg" "g8_login_dark.svg" "g8_login_light.svg")
    for file in "${image_files[@]}"; do
        local hashed_files=$(find_hashed_files "$file" "$static_img_dir")
        local legacy_file="$legacy_img_dir/$file"
        
        if [[ -z "$hashed_files" && ! -f "$legacy_file" ]]; then
            log_warning "교체할 대상 파일을 찾을 수 없습니다: $file"
            all_found=false
        fi
    done

    if ! $all_found; then
        log_error "일부 필수 파일이 없어 스크립트를 계속할 수 없습니다."
        # exit 1 # 경고만 표시하고 계속 진행하도록 주석 처리
    fi

    log_success "대상 파일 확인 완료."
}

# 백업 메뉴 (반환값: 0-다음단계, 1-메인메뉴)
show_backup_menu() {
    echo "=================================="
    echo "        1. 백업 설정"
    echo "=================================="
    while true; do
        read -p "기존 파일들을 백업하시겠습니까? [Y(예) / N(아니오) / B(메인메뉴로)]: " choice
        case ${choice} in
            [Yy]*) 
                BACKUP_ENABLED=true
                log_info "백업을 생성합니다."
                return 0 
                ;;
            [Nn]*) 
                BACKUP_ENABLED=false
                log_info "백업을 생성하지 않습니다."
                return 0 
                ;;
            [Bb]*) 
                return 1 
                ;;
            *) 
                log_error "Y, N, 또는 B를 입력해주세요." 
                ;;
        esac
    done
}

# 로그인 문구 선택 메뉴 (반환값: 0-다음단계, 1-이전단계)
show_login_text_menu() {
    echo ""
    echo "=================================="
    echo "        2. 로그인 문구 선택"
    echo "=================================="
    echo "1) Integrated Monitoring"
    echo "2) E2E Observability"
    echo "3) 직접 입력하여 변경"
    echo "4) 이전 단계로 돌아가기"
    echo "=================================="
    while true; do
        read -p "선택 (1-4): " choice
        case $choice in
            1) 
                LOGIN_TEXT="Integrated Monitoring"
                log_info "선택된 문구: $LOGIN_TEXT"
                return 0 
                ;;
            2) 
                LOGIN_TEXT="E2E Observability"
                log_info "선택된 문구: $LOGIN_TEXT"
                return 0 
                ;;
            3)
                echo ""
                log_warning "직접 입력 시 문구가 너무 길면 로그인 화면에서 두 줄로 깨질 수 있습니다."
                log_warning "\n 갱신문자(개행)는 적용이 불가합니다."
                log_warning "권장하는 최대 길이는 26자입니다."
                echo ""
                while true; do
                    echo "적용할 로그인 문구를 입력하세요 (아래 눈금 가이드라인을 넘지 않도록 권장):"
                    echo "_________|_________|______"
                    read input_text
                    if [[ -z "$input_text" ]]; then
                        log_error "문구를 입력해야 합니다."
                    elif [ ${#input_text} -gt 26 ]; then
                        log_warning "입력한 문구(${#input_text}자)가 권장 최대 길이(26자)를 초과했습니다."
                        read -p "이대로 적용하시겠습니까? [Y(진행) / N(재입력)]: " confirm_len
                        if [[ "$confirm_len" =~ ^[Yy]$ ]]; then
                            LOGIN_TEXT="$input_text"
                            break
                        fi
                    else
                        LOGIN_TEXT="$input_text"
                        break
                    fi
                done
                log_info "선택된 로그인 문구: $LOGIN_TEXT"
                return 0
                ;;
            4) 
                return 1 
                ;;
            *) 
                log_error "1, 2, 3 또는 4를 입력해주세요." 
                ;;
        esac
    done
}

# 로그인 후 사이드바의 타이틀(AppTitle) 설정 메뉴 (반환값: 0-다음단계, 1-이전단계)
show_app_title_menu() {
    echo ""
    echo "=================================="
    echo " 3. 로그인 후 사이드바의 타이틀(AppTitle) 설정"
    echo "=================================="
    echo "1) 기본값 유지 ('Grafana' 또는 현재 적용값)"
    echo "2) 직접 입력하여 변경"
    echo "3) 이전 단계로 돌아가기"
    echo "=================================="
    while true; do
        read -p "선택 (1-3): " choice
        case $choice in
            1)
                APP_TITLE="Grafana"
                log_info "선택된 문구: $APP_TITLE"
                return 0
                ;;
            2)
                read -p "적용할 문구를 입력하세요: " input_title
                if [[ -z "$input_title" ]]; then
                    log_error "문구를 입력해야 합니다."
                else
                    APP_TITLE="$input_title"
                    log_info "선택된 문구: $APP_TITLE"
                    return 0
                fi
                ;;
            3)
                return 1
                ;;
            *)
                log_error "1, 2, 또는 3을 입력해주세요."
                ;;
        esac
    done
}

# 테마 선택 메뉴 (반환값: 0-다음단계, 1-이전단계)
show_theme_menu() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local img_dir="$script_dir/img"
    
    # img/ 하위 디렉토리(테마) 목록 동적 조회
    local themes=()
    shopt -s nullglob
    for d in "$img_dir"/*/; do
        themes+=("$(basename "$d")")
    done
    shopt -u nullglob
    
    # 만약 하위 디렉토리가 하나도 없다면, 기본 img 폴더 자체를 테마로 사용하도록 함 (하위 호환성)
    if [[ ${#themes[@]} -eq 0 ]]; then
        log_info "img/ 폴더 하위에 별도 테마 폴더가 없어 기본 img/ 폴더의 이미지를 사용합니다."
        THEME_NAME="기본 (img/)"
        THEME_DIR="$img_dir"
        return 0
    fi
    
    echo ""
    echo "=================================="
    echo "        적용할 테마 선택"
    echo "=================================="
    for i in "${!themes[@]}"; do
        echo "$((i+1)) ${themes[$i]}"
    done
    echo "$(( ${#themes[@]} + 1 )) 이전 단계로 돌아가기"
    echo "=================================="
    
    while true; do
        read -p "테마를 선택하세요 (1-$(( ${#themes[@]} + 1 ))): " theme_choice
        if [[ "$theme_choice" =~ ^[0-9]+$ ]] && [ "$theme_choice" -ge 1 ] && [ "$theme_choice" -le "$(( ${#themes[@]} + 1 ))" ]; then
            if [ "$theme_choice" -eq "$(( ${#themes[@]} + 1 ))" ]; then
                return 1
            fi
            local idx=$((theme_choice - 1))
            THEME_NAME="${themes[$idx]}"
            THEME_DIR="$img_dir/$THEME_NAME"
            break
        else
            log_error "올바른 번호를 입력해주세요."
        fi
    done
    log_info "선택된 테마: $THEME_NAME"
    return 0
}

# 커스텀 파일 존재 확인
check_custom_files() {
    log_info "커스텀 파일들의 존재를 확인하는 중..."
    
    local custom_files=(
        "$THEME_DIR/fav32.png"
        "$THEME_DIR/grafana_icon.svg"
        "$THEME_DIR/g8_login_dark.svg"
        "$THEME_DIR/g8_login_light.svg"
    )
    
    for file in "${custom_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "커스텀 파일을 찾을 수 없습니다: $file"
            return 1
        fi
    done
    
    log_success "모든 커스텀 파일이 확인되었습니다."
    return 0
}

# 백업 생성
create_backup() {
    log_info "백업을 생성하는 중..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="/tmp/grafana_backup_$timestamp"
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # 파일명으로 안전한 이름 생성 (공백 제거 및 언더바 치환)
    local safe_theme_name="unknown"
    if [[ -n "$THEME_NAME" ]]; then
        safe_theme_name="${THEME_NAME// /_}"
    fi
    local backup_archive="$script_dir/backup/grafana_custom_${timestamp}_${safe_theme_name}.tar.gz"
    
    mkdir -p "$script_dir/backup"
    mkdir -p "$backup_dir/img"
    mkdir -p "$backup_dir/static_img"
    mkdir -p "$backup_dir/build"
    
    local legacy_img_dir="/usr/share/grafana/public/img"
    local static_img_dir="/usr/share/grafana/public/build/static/img"
    local build_dir="/usr/share/grafana/public/build"

    cp "$legacy_img_dir/fav32.png" "$backup_dir/img/" 2>/dev/null || log_warning "fav32.png 백업 실패"
    
    if [[ -f "$legacy_img_dir/grafana_icon.svg" ]]; then
        cp "$legacy_img_dir/grafana_icon.svg" "$backup_dir/img/" 2>/dev/null || log_warning "레거시 grafana_icon.svg 백업 실패"
    fi
    
    local image_files=("grafana_icon.svg" "g8_login_dark.svg" "g8_login_light.svg")
    for file in "${image_files[@]}"; do
        local found_files=$(find_hashed_files "$file" "$static_img_dir")
        if [[ -n "$found_files" ]]; then
            while IFS= read -r line; do
                cp "$line" "$backup_dir/static_img/" 2>/dev/null || log_warning "$(basename "$line") 백업 실패"
            done <<< "$found_files"
        fi
    done
    
    # 1) Welcome to Grafana 또는 LoginTitle이 정의된 파일 백업
    local welcome_files=$(find "$build_dir" -name "*.js" -not -name "*.js.map" -exec grep -lE "Welcome to Grafana|LoginTitle=" {} \; 2>/dev/null)
    if [[ -n "$welcome_files" ]]; then
        for file in $welcome_files; do
            cp "$file" "$backup_dir/build/" 2>/dev/null || log_warning "$(basename $file) 백업 실패"
        done
    fi

    # 2) AppTitle이 정의된 파일 백업
    local app_title_files=$(find "$build_dir" -name "*.js" -not -name "*.js.map" -exec grep -l "AppTitle=" {} \; 2>/dev/null)
    if [[ -n "$app_title_files" ]]; then
        for file in $app_title_files; do
            cp "$file" "$backup_dir/build/" 2>/dev/null || log_warning "$(basename $file) 백업 실패"
        done
    fi
    
    tar -czf "$backup_archive" -C "/tmp" "grafana_backup_$timestamp" 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        log_success "백업이 생성되었습니다: $backup_archive"
        rm -rf "$backup_dir"
    else
        log_error "백업 생성에 실패했습니다."
        exit 1
    fi
}

# 이미지 파일 교체
replace_images() {
    log_info "이미지 파일들을 교체하는 중..."
    
    local legacy_img_dir="/usr/share/grafana/public/img"
    local static_img_dir="/usr/share/grafana/public/build/static/img"
    
    # 1. 파비콘 교체
    if cp "$THEME_DIR/fav32.png" "$legacy_img_dir/fav32.png"; then
        log_success "fav32.png 교체 완료"
    else
        log_error "fav32.png 교체 실패"; exit 1
    fi
    
    # 2. 레거시 grafana_icon.svg 교체
    local legacy_icon_path="$legacy_img_dir/grafana_icon.svg"
    if [[ -f "$legacy_icon_path" ]]; then
        if cp "$THEME_DIR/grafana_icon.svg" "$legacy_icon_path"; then
            log_success "grafana_icon.svg (레거시) 교체 완료"
        else
            log_warning "grafana_icon.svg (레거시) 교체 실패."
        fi
    fi

    # 3. 해시 포함 이미지 파일 교체
    local image_files=("grafana_icon.svg" "g8_login_dark.svg" "g8_login_light.svg")
    
    for file in "${image_files[@]}"; do
        local source_file="$THEME_DIR/$file"
        local target_files=$(find_hashed_files "$file" "$static_img_dir")
        
        if [[ -n "$target_files" ]]; then
            while IFS= read -r target_file; do
                if cp "$source_file" "$target_file"; then
                    log_success "$file → $(basename "$target_file") 교체 완료"
                else
                    log_error "$file → $(basename "$target_file") 교체 실패"
                fi
            done <<< "$target_files"
        else
            if [[ "$file" != "grafana_icon.svg" ]]; then
                log_warning "$file 의 해시 포함 대상 파일을 찾지 못했습니다."
            fi
        fi
    done
}

# 로그인 문구 변경
change_login_text() {
    local new_text="$1"
    log_info "로그인 문구를 '$new_text'로 변경하는 중..."
    
    # 1차로 LoginTitle= 설정 패턴이 들어간 JS 파일을 찾고, 없으면 Welcome to Grafana 패턴 검색
    local js_files=$(find /usr/share/grafana/public/build -name "*.js" -not -name "*.js.map" -exec grep -lE "LoginTitle=|Welcome to Grafana" {} \; 2>/dev/null)
    
    if [[ -z "$js_files" ]]; then
        log_warning "로그인 문구 설정을 찾을 수 없습니다."
        return 1
    fi
    
    local changed_count=0
    for file in $js_files; do
        # LoginTitle="임의의문구" 형태가 존재하면 정규식으로 안전하게 치환
        if grep -q "LoginTitle=" "$file"; then
            if sed -i -E 's/LoginTitle="[^"]+"/LoginTitle="'"$new_text"'"/g' "$file" 2>/dev/null; then
                log_success "$(basename $file)에서 LoginTitle 치환 완료"
                ((changed_count++))
            else
                log_error "$(basename $file)에서 LoginTitle 치환 실패"
            fi
        # 레거시나 번역 리소스 내 Welcome to Grafana를 직접 교체
        elif grep -q "Welcome to Grafana" "$file"; then
            if sed -i "s/Welcome to Grafana/$new_text/g" "$file" 2>/dev/null; then
                log_success "$(basename $file)에서 Welcome to Grafana 문구 치환 완료"
                ((changed_count++))
            else
                log_error "$(basename $file)에서 Welcome to Grafana 문구 치환 실패"
            fi
        fi
    done
    
    if [[ $changed_count -gt 0 ]]; then
        log_success "총 $changed_count개 파일에서 로그인 문구가 변경되었습니다."
    else
        log_error "로그인 문구 변경에 실패했습니다."
        exit 1
    fi
}

# 로그인 후 사이드바의 타이틀(AppTitle) 변경
change_app_title() {
    local new_title="$1"
    log_info "로그인 후 사이드바의 타이틀(AppTitle)을 '$new_title'로 변경하는 중..."
    
    local js_files=$(find /usr/share/grafana/public/build -name "*.js" -not -name "*.js.map" -exec grep -l "AppTitle=" {} \; 2>/dev/null)
    
    if [[ -z "$js_files" ]]; then
        log_warning "AppTitle 설정을 찾을 수 없습니다."
        return 1
    fi
    
    local changed_count=0
    for file in $js_files; do
        # AppTitle="임의의문구" 패턴을 AppTitle="새로운문구"로 치환
        if sed -i -E 's/AppTitle="[^"]+"/AppTitle="'"$new_title"'"/g' "$file" 2>/dev/null; then
            log_success "$(basename $file)에서 AppTitle 변경 완료"
            ((changed_count++))
        else
            log_error "$(basename $file)에서 AppTitle 변경 실패"
        fi
    done
    
    if [[ $changed_count -gt 0 ]]; then
        log_success "총 $changed_count개 파일에서 AppTitle이 변경되었습니다."
    else
        log_error "AppTitle 변경에 실패했습니다."
        exit 1
    fi
}

# Grafana 서비스 재시작
restart_grafana() {
    log_info "Grafana 서비스를 재시작하는 중..."
    
    if systemctl restart grafana-server; then
        log_success "Grafana 서비스가 재시작되었습니다."
        
        sleep 3
        if systemctl is-active --quiet grafana-server; then
            log_success "Grafana 서비스가 정상적으로 실행 중입니다."
        else
            log_warning "Grafana 서비스 상태를 확인해주세요."
        fi
    else
        log_error "Grafana 서비스 재시작에 실패했습니다."
        exit 1
    fi
}

# 복구(Restore) 서브 메뉴 및 실행
show_restore_menu() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local backup_dir="$script_dir/backup"
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "백업 디렉토리가 존재하지 않습니다: $backup_dir"
        read -p "엔터를 누르면 메인 메뉴로 돌아갑니다..."
        return 1
    fi
    
    local backups=()
    shopt -s nullglob
    for f in "$backup_dir"/grafana_custom_*.tar.gz; do
        backups+=("$(basename "$f")")
    done
    shopt -u nullglob
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        log_warning "복구할 수 있는 백업 파일이 없습니다."
        read -p "엔터를 누르면 메인 메뉴로 돌아갑니다..."
        return 1
    fi
    
    echo ""
    echo "=================================="
    echo "        백업 파일 선택"
    echo "=================================="
    log_warning "Grafana 버전이 변경된 경우 복구 시 시스템 오작동의 원인이 될 수 있습니다."
    echo ""
    
    for i in "${!backups[@]}"; do
        echo "$((i+1)) ${backups[$i]}"
    done
    echo "$(( ${#backups[@]} + 1 )) 메인 메뉴로 돌아가기"
    echo ""
    
    while true; do
        read -p "복구할 백업 파일을 선택하세요 (1-$(( ${#backups[@]} + 1 ))): " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$(( ${#backups[@]} + 1 ))" ]; then
            if [ "$choice" -eq "$(( ${#backups[@]} + 1 ))" ]; then
                return 1
            fi
            local idx=$((choice - 1))
            local selected_backup="${backups[$idx]}"
            
            echo ""
            log_warning "정말 복구를 진행하시겠습니까? (y/N)"
            read -p "선택: " confirm_restore
            if [[ "$confirm_restore" =~ ^[Yy]$ ]]; then
                execute_restore "$backup_dir/$selected_backup"
            else
                log_info "복구가 취소되었습니다."
            fi
            break
        else
            log_error "올바른 번호를 입력해주세요."
        fi
    done
}

execute_restore() {
    local backup_path="$1"
    log_info "복구를 시작합니다: $(basename "$backup_path")"
    
    local temp_dir="/tmp/grafana_restore_temp"
    rm -rf "$temp_dir"
    mkdir -p "$temp_dir"
    
    if ! tar -xzf "$backup_path" -C "$temp_dir"; then
        log_error "백업 압축 해제 실패"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    local inner_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "grafana_backup_*" | head -n 1)
    if [[ -z "$inner_dir" ]]; then
        log_error "백업 파일 내부 구조가 올바르지 않습니다."
        rm -rf "$temp_dir"
        exit 1
    fi
    
    local legacy_img_dir="/usr/share/grafana/public/img"
    local static_img_dir="/usr/share/grafana/public/build/static/img"
    local build_dir="/usr/share/grafana/public/build"
    
    # 1. fav32.png 복구
    if [[ -f "$inner_dir/img/fav32.png" ]]; then
        cp "$inner_dir/img/fav32.png" "$legacy_img_dir/fav32.png" && log_success "fav32.png 복구 완료"
    fi
    
    # 2. 레거시 grafana_icon.svg 복구
    if [[ -f "$inner_dir/img/grafana_icon.svg" ]]; then
        cp "$inner_dir/img/grafana_icon.svg" "$legacy_img_dir/grafana_icon.svg" && log_success "grafana_icon.svg (레거시) 복구 완료"
    fi
    
    # 3. 해시 포함 이미지 복구
    if [[ -d "$inner_dir/static_img" ]]; then
        for f in "$inner_dir/static_img"/*; do
            if [[ -f "$f" ]]; then
                cp "$f" "$static_img_dir/" && log_success "$(basename "$f") 복구 완료"
            fi
        done
    fi
    
    # 4. JS 파일 복구 (문구 및 타이틀 롤백)
    if [[ -d "$inner_dir/build" ]]; then
        for f in "$inner_dir/build"/*; do
            if [[ -f "$f" ]]; then
                cp "$f" "$build_dir/" && log_success "$(basename "$f") 복구 완료"
            fi
        done
    fi
    
    # active_theme.txt 초기화 (복구됨으로 기록)
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "복구됨 (이전 백업)" > "$script_dir/active_theme.txt"
    
    rm -rf "$temp_dir"
    
    log_success "파일 복구가 성공적으로 완료되었습니다."
    restart_grafana
}

# 메인 헤더 메뉴 표시
show_main_menu() {
    clear
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local current_theme="없음 (기본)"
    if [[ -f "$script_dir/active_theme.txt" ]]; then
        current_theme=$(cat "$script_dir/active_theme.txt")
    fi

    echo "=================================="
    echo "   Grafana 커스터마이징 스크립트 v0.7"
    echo "=================================="
    echo "• 현재 적용된 테마: $current_theme"
    echo "=================================="
}

# 작업 승인 확인 (반환값: 0-진행, 1-이전단계, 2-취소/메인메뉴)
show_confirmation() {
    echo ""
    echo "=================================="
    echo "        5. 작업 확인"
    echo "=================================="
    echo "• 적용 테마: $THEME_NAME"
    echo "• 백업 생성: $(if $BACKUP_ENABLED; then echo "예"; else echo "아니오"; fi)"
    echo "• 이미지 파일 교체"
    echo "• 로그인 문구 변경: '$LOGIN_TEXT'"
    echo "• 로그인 후 사이드바의 타이틀(AppTitle) 변경: '$APP_TITLE'"
    echo "• Grafana 서비스 재시작"
    echo ""
    while true; do
        read -p "위 작업을 진행하시겠습니까? [Y(진행) / N(취소/메인메뉴로) / B(이전단계로)]: " confirm
        case ${confirm} in
            [Yy]*) 
                return 0 
                ;;
            [Nn]*) 
                return 2 
                ;;
            [Bb]*) 
                return 1 
                ;;
            *) 
                echo "Y, N, 또는 B를 입력해주세요." 
                ;;
        esac
    done
}

# 실제 작업 실행
execute_tasks() {
    echo ""
    log_info "작업을 시작합니다..."
    
    if $BACKUP_ENABLED; then create_backup; fi
    replace_images
    change_login_text "$LOGIN_TEXT"
    change_app_title "$APP_TITLE"
    
    # 적용된 테마 로컬 기록
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "$THEME_NAME" > "$script_dir/active_theme.txt"
    
    restart_grafana
    
    echo ""
    echo "=================================="
    echo "        작업 완료"
    echo "=================================="
    log_success "모든 작업이 성공적으로 완료되었습니다!"
    echo "브라우저 캐시를 삭제하고 Grafana 페이지를 새로고침하여 변경사항을 확인하세요."
    echo ""
}

# 다단계 마법사(Wizard) 루프 실행
run_wizard() {
    local step=1
    while true; do
        case $step in
            1)
                show_backup_menu
                if [[ $? -eq 1 ]]; then
                    return 1 # 메인 메뉴 복귀
                fi
                step=2
                ;;
            2)
                show_login_text_menu
                if [[ $? -eq 1 ]]; then
                    step=1 # 이전 단계 복귀
                else
                    step=3 # 다음 단계 진행
                fi
                ;;
            3)
                show_app_title_menu
                if [[ $? -eq 1 ]]; then
                    step=2 # 이전 단계 복귀
                else
                    step=4 # 다음 단계 진행
                fi
                ;;
            4)
                show_theme_menu
                if [[ $? -eq 1 ]]; then
                    step=3 # 이전 단계 복귀
                else
                    if check_custom_files; then
                        step=5 # 성공 시 다음 단계 진행
                    else
                        log_error "선택하신 테마 폴더에 필수 이미지가 누락되어 있습니다. 다른 테마를 선택해주세요."
                        read -p "엔터를 누르면 테마를 다시 선택합니다..."
                        step=4 # 테마 재선택
                    fi
                fi
                ;;
            5)
                show_confirmation
                local res=$?
                if [[ $res -eq 0 ]]; then
                    execute_tasks
                    return 0
                elif [[ $res -eq 1 ]]; then
                    step=4 # 이전 단계 복귀
                else
                    log_info "작업이 취소되었습니다."
                    return 1 # 메인 메뉴 복귀
                fi
                ;;
        esac
    done
}

# 메인 엔트리 포인트
main() {
    check_sudo
    check_grafana
    
    while true; do
        show_main_menu
        echo "1) 새 테마 및 로그인/어플리케이션 문구 적용"
        echo "2) 이전 백업에서 복구 (Restore)"
        echo "3) 종료"
        echo "=================================="
        read -p "작업을 선택하세요 (1-3): " main_choice
        
        case $main_choice in
            1)
                check_files
                run_wizard
                if [[ $? -eq 0 ]]; then
                    exit 0 # 적용 성공 시 완전 종료
                fi
                # 메인메뉴로 돌아왔으므로 루프를 돌아 다시 화면 출력
                ;;
            2)
                show_restore_menu
                ;;
            3)
                log_info "스크립트를 종료합니다."
                exit 0
                ;;
            *)
                log_error "올바른 번호를 입력해주세요."
                sleep 1
                ;;
        esac
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
