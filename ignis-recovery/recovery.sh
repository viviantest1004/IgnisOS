#!/usr/bin/env bash
# IgnisOS Recovery Mode
# 복구 파티션에 포함됨 — GRUB에서 Recovery 선택 시 실행
# 기능: 파일시스템 검사, 초기화, 업타임 커널, 셸 접근, 네트워크 복구

set -o nounset

# ── 색상 ─────────────────────────────────────────────
RED='\033[1;31m'
GRN='\033[1;32m'
YLW='\033[1;33m'
CYN='\033[1;36m'
ORG='\033[38;5;208m'
WHT='\033[1;37m'
DIM='\033[2m'
RST='\033[0m'

IGNIS_VER="1.0.0"
ROOT_DEV="${ROOT_DEV:-/dev/sda1}"
MOUNT_POINT="/mnt/ignis-root"

clear

banner() {
    echo -e "${ORG}"
    cat << 'EOF'
  ██╗ ██████╗ ███╗   ██╗██╗███████╗ ██████╗ ███████╗
  ██║██╔════╝ ████╗  ██║██║██╔════╝██╔═══██╗██╔════╝
  ██║██║  ███╗██╔██╗ ██║██║███████╗██║   ██║███████╗
  ██║██║   ██║██║╚██╗██║██║╚════██║██║   ██║╚════██║
  ██║╚██████╔╝██║ ╚████║██║███████║╚██████╔╝███████║
  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚══════╝ ╚═════╝ ╚══════╝
EOF
    echo -e "${RST}"
    echo -e "${CYN}  IgnisOS ${IGNIS_VER} — Recovery Mode${RST}"
    echo -e "${DIM}  ─────────────────────────────────────────────────────${RST}"
    echo ""
}

separator() { echo -e "${DIM}  ──────────────────────────────────────────${RST}"; }

ok()   { echo -e "  ${GRN}✓${RST} $*"; }
fail() { echo -e "  ${RED}✗${RST} $*"; }
info() { echo -e "  ${CYN}ℹ${RST} $*"; }
warn() { echo -e "  ${YLW}⚠${RST} $*"; }

# ── 메인 메뉴 ─────────────────────────────────────────
main_menu() {
    banner
    echo -e "${WHT}  복구 모드 메뉴${RST}"
    echo ""
    echo -e "  ${GRN}[1]${RST} 파일시스템 검사 및 복구 (fsck)"
    echo -e "  ${GRN}[2]${RST} 루트 셸 (bash)"
    echo -e "  ${GRN}[3]${RST} 업타임 커널 실행"
    echo -e "  ${GRN}[4]${RST} 네트워크 복구"
    echo -e "  ${GRN}[5]${RST} 패키지 복구 (apt --fix-broken)"
    echo -e "  ${GRN}[6]${RST} GRUB 복구"
    echo -e "  ${GRN}[7]${RST} 시스템 초기화 (공장 초기화)"
    echo -e "  ${GRN}[8]${RST} 시스템 정보"
    echo -e "  ${GRN}[9]${RST} 비밀번호 재설정"
    echo -e "  ${RED}[0]${RST} 재시작"
    echo ""
    read -rp "  선택 [0-9]: " choice
    echo ""

    case "$choice" in
        1) menu_fsck ;;
        2) menu_shell ;;
        3) menu_uptime_kernel ;;
        4) menu_network ;;
        5) menu_package_repair ;;
        6) menu_grub_repair ;;
        7) menu_factory_reset ;;
        8) menu_sysinfo ;;
        9) menu_password_reset ;;
        0) do_reboot ;;
        *) warn "잘못된 선택입니다."; sleep 1; main_menu ;;
    esac
}

# ── 1. fsck ───────────────────────────────────────────
menu_fsck() {
    banner
    echo -e "${WHT}  파일시스템 검사${RST}"
    separator
    info "루트 파티션: ${ROOT_DEV}"
    info "검사 전 파티션을 마운트 해제합니다..."
    echo ""

    if mount | grep -q "${ROOT_DEV}"; then
        warn "파티션이 마운트되어 있습니다. 읽기 전용으로 재마운트..."
        mount -o remount,ro / 2>/dev/null || true
    fi

    echo -e "  ${CYN}fsck 실행 중...${RST}"
    if fsck -y "${ROOT_DEV}"; then
        ok "파일시스템 검사 완료"
    else
        fail "오류가 발견됐습니다. 위 메시지를 확인하세요."
    fi

    echo ""
    read -rp "  [Enter] 메인 메뉴로" _
    main_menu
}

# ── 2. 루트 셸 ────────────────────────────────────────
menu_shell() {
    banner
    echo -e "${WHT}  루트 셸 (Bash)${RST}"
    separator
    warn "주의: 루트 권한으로 실행됩니다. 파일 삭제 등에 주의하세요."
    info "'exit' 입력 시 복구 메뉴로 돌아옵니다."
    echo ""
    bash --login || true
    main_menu
}

# ── 3. 업타임 커널 ───────────────────────────────────
menu_uptime_kernel() {
    banner
    echo -e "${WHT}  업타임 커널 실행${RST}"
    separator
    if command -v uptime-kernel &>/dev/null; then
        uptime-kernel
    elif [ -f "/boot/uptime-kernel-init" ]; then
        /boot/uptime-kernel-init
    else
        fail "업타임 커널을 찾을 수 없습니다."
        info "경로: /usr/bin/uptime-kernel 또는 /boot/uptime-kernel-init"
    fi
    main_menu
}

# ── 4. 네트워크 복구 ─────────────────────────────────
menu_network() {
    banner
    echo -e "${WHT}  네트워크 복구${RST}"
    separator

    info "네트워크 인터페이스 목록:"
    ip link show 2>/dev/null || ifconfig 2>/dev/null || echo "    (없음)"
    echo ""

    echo -e "  ${GRN}[1]${RST} DHCP 자동 설정"
    echo -e "  ${GRN}[2]${RST} NetworkManager 재시작"
    echo -e "  ${GRN}[3]${RST} DNS 수동 설정 (8.8.8.8)"
    echo -e "  ${GRN}[0]${RST} 뒤로"
    echo ""
    read -rp "  선택: " c

    case "$c" in
        1)
            IFACE=$(ip link show | awk -F': ' '/^[0-9]+: e/{print $2}' | head -1)
            if [ -n "$IFACE" ]; then
                dhclient "$IFACE" && ok "DHCP 설정 완료: $IFACE" || fail "DHCP 실패"
            else
                warn "이더넷 인터페이스를 찾을 수 없습니다."
            fi
            ;;
        2)
            systemctl restart NetworkManager && ok "NetworkManager 재시작됨" || fail "재시작 실패"
            ;;
        3)
            echo "nameserver 8.8.8.8" > /etc/resolv.conf
            echo "nameserver 8.8.4.4" >> /etc/resolv.conf
            ok "DNS 설정됨: 8.8.8.8, 8.8.4.4"
            ;;
    esac

    sleep 2
    main_menu
}

# ── 5. 패키지 복구 ───────────────────────────────────
menu_package_repair() {
    banner
    echo -e "${WHT}  패키지 복구${RST}"
    separator
    info "손상된 패키지를 복구합니다..."

    dpkg --configure -a 2>&1 | head -20
    apt-get install -f -y 2>&1 | tail -20

    ok "패키지 복구 완료"
    read -rp "  [Enter] 계속" _
    main_menu
}

# ── 6. GRUB 복구 ─────────────────────────────────────
menu_grub_repair() {
    banner
    echo -e "${WHT}  GRUB 복구${RST}"
    separator

    info "루트 파티션 마운트 중..."
    mkdir -p "${MOUNT_POINT}"
    mount "${ROOT_DEV}" "${MOUNT_POINT}" 2>/dev/null || warn "마운트 실패 (이미 마운트된 경우 무시)"

    info "GRUB 재설치 중 (ARM64 EFI)..."
    if grub-install --target=arm64-efi --efi-directory=/boot/efi \
                    --bootloader-id=IgnisOS 2>&1; then
        ok "GRUB 설치 완료"
    else
        fail "GRUB 설치 실패. 수동 복구 필요."
    fi

    info "GRUB 설정 생성 중..."
    update-grub 2>&1 | tail -5 && ok "GRUB 설정 업데이트됨"

    read -rp "  [Enter] 계속" _
    main_menu
}

# ── 7. 공장 초기화 ───────────────────────────────────
menu_factory_reset() {
    banner
    echo -e "${RED}  ⚠️  공장 초기화 (위험!)${RST}"
    separator
    warn "이 작업은 모든 사용자 데이터를 삭제합니다!"
    warn "시스템 파일은 보존됩니다."
    echo ""
    read -rp "  정말 계속하시겠습니까? (yes 입력): " confirm

    if [ "$confirm" != "yes" ]; then
        info "취소됨."
        sleep 1
        main_menu
        return
    fi

    echo ""
    info "사용자 데이터 삭제 중..."

    # 홈 디렉토리 초기화 (시스템 사용자 제외)
    for user_home in /home/*/; do
        user=$(basename "$user_home")
        if [ "$user" != "ignis" ]; then
            warn "삭제: /home/${user}"
            rm -rf "${user_home:?}"
        else
            info "홈 디렉토리 초기화: /home/ignis"
            find "/home/ignis" -mindepth 1 -maxdepth 1 \
                ! -name ".bashrc" ! -name ".profile" \
                -exec rm -rf {} + 2>/dev/null || true
        fi
    done

    # 설정 초기화
    rm -rf /root/.config/* /root/.local/share/* 2>/dev/null || true

    ok "초기화 완료. 재시작합니다..."
    sleep 2
    reboot
}

# ── 8. 시스템 정보 ───────────────────────────────────
menu_sysinfo() {
    banner
    echo -e "${WHT}  시스템 정보${RST}"
    separator

    echo -e "${CYN}  OS         :${RST} IgnisOS ${IGNIS_VER} (ARM64)"
    echo -e "${CYN}  커널       :${RST} $(uname -r 2>/dev/null || echo 'N/A')"
    echo -e "${CYN}  아키텍처   :${RST} $(uname -m 2>/dev/null || echo 'aarch64')"
    echo -e "${CYN}  호스트명   :${RST} $(hostname 2>/dev/null || echo 'ignis')"
    echo ""

    # 메모리
    if [ -f /proc/meminfo ]; then
        total=$(awk '/MemTotal/ {printf "%.0f MB", $2/1024}' /proc/meminfo)
        free=$(awk '/MemAvailable/ {printf "%.0f MB", $2/1024}' /proc/meminfo)
        echo -e "${CYN}  메모리     :${RST} 사용 가능 ${free} / 전체 ${total}"
    fi

    # 디스크
    df -h / 2>/dev/null | awk 'NR==2 {
        printf "  \033[1;36m디스크     :\033[0m 사용 %s / 전체 %s (%s 사용)\n", $3, $2, $5
    }'

    # 업타임
    uptime -p 2>/dev/null && echo "" || echo ""

    # 네트워크
    ip -4 addr show 2>/dev/null | grep "inet " | awk '{
        printf "  \033[1;36m네트워크   :\033[0m %s\n", $2
    }'

    echo ""
    read -rp "  [Enter] 계속" _
    main_menu
}

# ── 9. 비밀번호 재설정 ───────────────────────────────
menu_password_reset() {
    banner
    echo -e "${WHT}  비밀번호 재설정${RST}"
    separator

    echo "  사용자 목록:"
    awk -F: '$3 >= 1000 && $3 < 65534 {print "    "$1}' /etc/passwd

    echo ""
    read -rp "  사용자 이름: " uname_input
    if ! id "$uname_input" &>/dev/null; then
        fail "사용자를 찾을 수 없습니다: $uname_input"
        sleep 2
        main_menu
        return
    fi

    if passwd "$uname_input"; then
        ok "비밀번호가 변경됐습니다."
    else
        fail "비밀번호 변경 실패"
    fi

    read -rp "  [Enter] 계속" _
    main_menu
}

# ── 재시작 ────────────────────────────────────────────
do_reboot() {
    info "시스템을 재시작합니다..."
    sleep 2
    reboot
}

# ── 엔트리포인트 ─────────────────────────────────────
trap 'echo ""; warn "인터럽트됨. Ctrl+C를 다시 누르면 재시작합니다."; sleep 1' INT
main_menu
