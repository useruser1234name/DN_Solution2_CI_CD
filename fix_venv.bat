@echo off
echo ==============================================
echo 가상환경 생성 문제 해결 도구
echo ==============================================
echo.

echo 어떤 오류가 발생했나요?
echo.
echo 1. "python 명령을 찾을 수 없습니다"
echo 2. "Access is denied" (권한 오류)
echo 3. "'venv' is not recognized"
echo 4. "No module named venv"
echo 5. 기타 오류
echo 6. 강제로 가상환경 재생성
echo.
set /p choice="번호를 선택하세요 (1-6): "

if "%choice%"=="1" goto PYTHON_NOT_FOUND
if "%choice%"=="2" goto ACCESS_DENIED
if "%choice%"=="3" goto VENV_NOT_RECOGNIZED
if "%choice%"=="4" goto NO_MODULE_VENV
if "%choice%"=="5" goto OTHER_ERROR
if "%choice%"=="6" goto FORCE_RECREATE

echo 잘못된 선택입니다.
goto END

:PYTHON_NOT_FOUND
echo.
echo ===========================================
echo Python 설치 문제 해결
echo ===========================================
echo.
echo 1. Python 다운로드 및 설치
echo    https://www.python.org/downloads/
echo.
echo 2. 설치 시 반드시 체크할 옵션:
echo    ✅ "Add Python to PATH"
echo    ✅ "Install for all users"
echo.
echo 3. 설치 후 명령 프롬프트 재시작
echo.
echo 4. 설치 확인:
python --version
if errorlevel 1 (
    echo ❌ Python이 여전히 인식되지 않습니다.
    echo PATH 수동 추가가 필요할 수 있습니다.
) else (
    echo ✅ Python 설치 확인됨
)
goto END

:ACCESS_DENIED
echo.
echo ===========================================
echo 권한 문제 해결
echo ===========================================
echo.
echo 해결 방법:
echo 1. 명령 프롬프트를 관리자 권한으로 실행
echo 2. 다른 위치에서 가상환경 생성 시도
echo.
echo 관리자 권한으로 재시도...
mkdir temp_venv 2>nul
if exist "temp_venv" (
    rmdir temp_venv
    echo ✅ 권한 문제 없음
    echo 다른 원인일 수 있습니다.
) else (
    echo ❌ 권한 문제 확인됨
    echo 명령 프롬프트를 관리자 권한으로 실행해주세요.
)
goto END

:VENV_NOT_RECOGNIZED
echo.
echo ===========================================
echo venv 모듈 문제 해결
echo ===========================================
echo.
echo Python venv 모듈 확인 중...
python -m venv --help >nul 2>&1
if errorlevel 1 (
    echo ❌ venv 모듈이 없습니다.
    echo.
    echo 대안 방법:
    echo 1. virtualenv 설치 및 사용
    pip install virtualenv
    echo.
    echo 2. virtualenv로 가상환경 생성
    virtualenv venv
) else (
    echo ✅ venv 모듈 사용 가능
    echo 다른 원인을 확인해주세요.
)
goto END

:NO_MODULE_VENV
echo.
echo ===========================================
echo venv 모듈 설치
echo ===========================================
echo.
echo venv 모듈이 없는 경우 해결 방법:
echo.
echo 1. Python 재설치 (전체 설치)
echo 2. virtualenv 사용
echo.
echo virtualenv 설치 중...
pip install virtualenv
if errorlevel 1 (
    echo ❌ virtualenv 설치 실패
    echo pip 업그레이드 시도...
    python -m pip install --upgrade pip
    pip install virtualenv
) else (
    echo ✅ virtualenv 설치 성공
    echo.
    echo 가상환경 생성 중...
    virtualenv venv
    if errorlevel 1 (
        echo ❌ virtualenv로도 실패
    ) else (
        echo ✅ virtualenv로 가상환경 생성 성공!
    )
)
goto END

:OTHER_ERROR
echo.
echo ===========================================
echo 기타 오류 해결
echo ===========================================
echo.
echo 다음 정보를 확인해주세요:
echo.
echo 1. 정확한 오류 메시지:
echo.
echo 2. Python 버전:
python --version 2>nul || echo "Python 인식 안됨"
echo.
echo 3. pip 버전:
pip --version 2>nul || echo "pip 인식 안됨"
echo.
echo 4. 현재 디렉토리:
echo %CD%
echo.
echo 5. 디스크 용량:
dir /-c | find "bytes free"
echo.
echo 6. 수동 생성 시도:
echo python -c "import venv; venv.create('test_venv')"
python -c "import venv; venv.create('test_venv')" 2>nul
if exist "test_venv" (
    echo ✅ 수동 생성 성공
    rmdir /s /q test_venv
) else (
    echo ❌ 수동 생성도 실패
)
goto END

:FORCE_RECREATE
echo.
echo ===========================================
echo 강제 가상환경 재생성
echo ===========================================
echo.
echo 1. 기존 venv 폴더 삭제
if exist "venv" (
    echo 기존 venv 폴더 삭제 중...
    rmdir /s /q venv
    timeout /t 2 >nul
    if exist "venv" (
        echo ❌ 삭제 실패 - 수동 삭제 필요
        explorer .
        echo 탐색기에서 venv 폴더를 수동으로 삭제한 후 다시 실행해주세요.
        goto END
    ) else (
        echo ✅ 기존 폴더 삭제 완료
    )
)

echo.
echo 2. pip 캐시 정리
pip cache purge 2>nul
echo ✅ pip 캐시 정리 완료

echo.
echo 3. 새 가상환경 생성 시도 (방법 1)
python -m venv venv --clear
if exist "venv\Scripts\activate.bat" (
    echo ✅ 방법 1 성공!
    goto ACTIVATE_ENV
)

echo.
echo 4. 새 가상환경 생성 시도 (방법 2)
python -m venv venv --system-site-packages
if exist "venv\Scripts\activate.bat" (
    echo ✅ 방법 2 성공!
    goto ACTIVATE_ENV
)

echo.
echo 5. virtualenv로 시도
pip install virtualenv 2>nul
virtualenv venv
if exist "venv\Scripts\activate.bat" (
    echo ✅ virtualenv 성공!
    goto ACTIVATE_ENV
)

echo ❌ 모든 방법 실패
echo 시스템 환경을 점검해주세요.
goto END

:ACTIVATE_ENV
echo.
echo ===========================================
echo 가상환경 활성화 및 패키지 설치
echo ===========================================
echo.
echo 가상환경 활성화 중...
call venv\Scripts\activate.bat
echo.
echo Python 버전 확인:
python --version
echo.
echo pip 업그레이드:
python -m pip install --upgrade pip
echo.
echo requirements.txt 설치:
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo ✅ 패키지 설치 완료!
) else (
    echo ⚠️  requirements.txt 없음
)
echo.
echo ✅ 가상환경 설정 완료!
echo.
echo 다음번 활성화 방법:
echo venv\Scripts\activate

:END
echo.
echo ===========================================
echo 도구 실행 완료
echo ===========================================
pause
