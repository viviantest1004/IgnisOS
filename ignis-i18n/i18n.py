#!/usr/bin/env python3
"""IgnisOS 다국어 지원 모듈 — Korean / English"""
import os

def get_lang():
    lang = os.environ.get('LANG', os.environ.get('LANGUAGE', 'en_US'))
    if lang.startswith('ko'):
        return 'ko'
    return 'en'

LANG = get_lang()

_STRINGS = {
    # 공통 버튼
    'ok':           {'ko': '확인',      'en': 'OK'},
    'cancel':       {'ko': '취소',      'en': 'Cancel'},
    'close':        {'ko': '닫기',      'en': 'Close'},
    'save':         {'ko': '저장',      'en': 'Save'},
    'open':         {'ko': '열기',      'en': 'Open'},
    'delete':       {'ko': '삭제',      'en': 'Delete'},
    'add':          {'ko': '추가',      'en': 'Add'},
    'edit':         {'ko': '편집',      'en': 'Edit'},
    'error':        {'ko': '오류',      'en': 'Error'},
    'loading':      {'ko': '로딩 중...','en': 'Loading...'},
    'unknown':      {'ko': '알 수 없음','en': 'Unknown'},

    # 앱 이름
    'app_terminal':   {'ko': '터미널',         'en': 'Terminal'},
    'app_files':      {'ko': '파일 관리자',     'en': 'Files'},
    'app_settings':   {'ko': '설정',           'en': 'Settings'},
    'app_notepad':    {'ko': '메모장',          'en': 'Notepad'},
    'app_calc':       {'ko': '계산기',          'en': 'Calculator'},
    'app_clock':      {'ko': '시계',            'en': 'Clock'},
    'app_calendar':   {'ko': '캘린더',          'en': 'Calendar'},
    'app_taskmanager':{'ko': '작업 관리자',     'en': 'Task Manager'},
    'app_imageviewer':{'ko': '이미지 뷰어',     'en': 'Image Viewer'},
    'app_music':      {'ko': '음악 플레이어',   'en': 'Music Player'},
    'app_video':      {'ko': '동영상 플레이어', 'en': 'Video Player'},
    'app_screenshot': {'ko': '스크린샷',        'en': 'Screenshot'},
    'app_archive':    {'ko': '아카이브',        'en': 'Archive Manager'},
    'app_sysinfo':    {'ko': '시스템 정보',     'en': 'System Info'},
    'app_recovery':   {'ko': '복구 모드',       'en': 'Recovery Mode'},
    'app_browser':    {'ko': '브라우저',        'en': 'Browser'},

    # 시스템 정보
    'si_os':        {'ko': '운영체제',   'en': 'Operating System'},
    'si_hardware':  {'ko': '하드웨어',   'en': 'Hardware'},
    'si_memory':    {'ko': '메모리',     'en': 'Memory'},
    'si_storage':   {'ko': '저장소',     'en': 'Storage'},
    'si_network':   {'ko': '네트워크',   'en': 'Network'},
    'si_name':      {'ko': '이름',       'en': 'Name'},
    'si_kernel':    {'ko': '커널',       'en': 'Kernel'},
    'si_arch':      {'ko': '아키텍처',   'en': 'Architecture'},
    'si_hostname':  {'ko': '호스트명',   'en': 'Hostname'},
    'si_uptime':    {'ko': '업타임',     'en': 'Uptime'},
    'si_cpu':       {'ko': 'CPU',        'en': 'CPU'},
    'si_cores':     {'ko': '코어 수',    'en': 'Cores'},
    'si_gpu':       {'ko': 'GPU',        'en': 'GPU'},
    'si_total':     {'ko': '전체',       'en': 'Total'},
    'si_used':      {'ko': '사용 중',    'en': 'Used'},
    'si_avail':     {'ko': '사용 가능',  'en': 'Available'},
    'si_device':    {'ko': '디바이스',   'en': 'Device'},
    'si_usage':     {'ko': '사용률',     'en': 'Usage'},
    'si_ip':        {'ko': 'IP 주소',    'en': 'IP Address'},
    'si_copy':      {'ko': '📋 정보 복사','en': '📋 Copy Info'},

    # 캘린더
    'cal_today':    {'ko': '오늘',       'en': 'Today'},
    'cal_new_event':{'ko': '새 일정 입력...', 'en': 'New event...'},

    # 아카이브
    'arc_open':     {'ko': '📂 아카이브 열기', 'en': '📂 Open Archive'},
    'arc_compress': {'ko': '📦 압축하기',      'en': '📦 Compress'},
    'arc_extract':  {'ko': '📤 압축 해제',     'en': '📤 Extract'},
    'arc_status':   {'ko': '아카이브를 열어보세요', 'en': 'Open an archive'},

    # 스크린샷
    'ss_full':      {'ko': '📷 지금 캡처',   'en': '📷 Capture Now'},
    'ss_area':      {'ko': '✂️ 영역 선택',   'en': '✂️ Select Area'},
    'ss_record':    {'ko': '● 녹화 시작',    'en': '● Start Recording'},
    'ss_stop':      {'ko': '⏹ 녹화 중지',   'en': '⏹ Stop Recording'},
    'ss_delay':     {'ko': '캡처 딜레이:',   'en': 'Capture Delay:'},

    # 음악
    'music_play':   {'ko': '▶',  'en': '▶'},
    'music_pause':  {'ko': '⏸', 'en': '⏸'},
    'music_prev':   {'ko': '⏮', 'en': '⏮'},
    'music_next':   {'ko': '⏭', 'en': '⏭'},
    'music_add':    {'ko': '📁 파일 추가', 'en': '📁 Add Files'},
    'music_clear':  {'ko': '🗑 목록 지우기','en': '🗑 Clear List'},

    # 작업 관리자
    'tm_process':   {'ko': '프로세스',  'en': 'Process'},
    'tm_pid':       {'ko': 'PID',       'en': 'PID'},
    'tm_cpu':       {'ko': 'CPU%',      'en': 'CPU%'},
    'tm_mem':       {'ko': 'MEM%',      'en': 'MEM%'},
    'tm_kill':      {'ko': '강제 종료', 'en': 'Kill'},
    'tm_refresh':   {'ko': '새로고침',  'en': 'Refresh'},
}

def t(key: str) -> str:
    """번역 문자열 반환"""
    row = _STRINGS.get(key)
    if row is None:
        return key
    return row.get(LANG, row.get('en', key))
