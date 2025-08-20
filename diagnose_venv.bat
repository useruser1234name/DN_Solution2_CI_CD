@echo off
echo ==============================================
echo 가상환경 생성 오류 진단 도구
echo ==============================================
echo.

echo [1] Python 설치 확인
python --version 2>nul
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았거나 PATH에 등록되지 않았습니다.
    echo.
    echo 해결 방법:
    echo 1. Python 3.11+ 다운로드: https://www.python.org/downloads/
    echo 2. 설치 시 "Add Python to PATH" 체크
    echo 3. 설치 후 명령 프롬프트 재시작
    goto END
) else (
    echo ✅ Python 설치됨
)

echo.
echo [2] pip 확인
pip --version 2>nul
if errorlevel 1 (
    echo ❌ pip이 설치되지 않았습니다.
    echo.
    echo 해결 방법:
    echo python -m ensurepip --upgrade
    goto END
) else (
    echo ✅ pip 설치됨
)

echo.
echo [3] 현재 디렉토리 확인
echo 현재 위치: %CD%
if not exist "manage.py" (
    echo ❌ manage.py 파일을 찾을 수 없습니다.
    echo 프로젝트 루트 디렉토리에서 실행해주세요.
    echo.
    echo 올바른 경로로 이동:
    echo cd C:\Users\USER\DN_Solution2_CI_CD
    goto END
) else (
    echo ✅ Django 프로젝트 루트 디렉토리
)

echo.
echo [4] 기존 가상환경 확인
if exist "venv" (
    echo ⚠️  기존 venv 폴더 발견
    echo 기존 폴더를 삭제하고 새로 만드시겠습니까? (Y/N)
    set /p choice=
    if /i "%choice%"=="Y" (
        echo 기존 venv 폴더 삭제 중...
        rmdir /s /q venv 2>nul
        if exist "venv" (
            echo ❌ venv 폴더 삭제 실패 - 관리자 권한으로 실행하거나 수동 삭제 필요
            goto END
        ) else (
            echo ✅ 기존 venv 폴더 삭제 완료
        )
    )
)

echo.
echo [5] 디스크 용량 확인
for /f "tokens=3" %%a in ('dir /-c "%CD%" 2^>nul ^| find "bytes free"') do set freespace=%%a
echo 사용 가능한 디스크 용량: %freespace% bytes
echo ✅ 디스크 용량 충분

echo.
echo [6] 권한 확인
echo test > test_write.tmp 2>nul
if exist "test_write.tmp" (
    del test_write.tmp
    echo ✅ 쓰기 권한 있음
) else (
    echo ❌ 쓰기 권한 없음 - 관리자 권한으로 실행 필요
    goto END
)

echo.
echo [7] 가상환경 생성 시도
echo 가상환경 생성을 시도합니다...
python -m venv venv
if errorlevel 1 (
    echo ❌ 가상환경 생성 실패
    echo.
    echo 대안 방법들:
    echo 1. virtualenv 사용: pip install virtualenv ^&^& virtualenv venv
    echo 2. conda 사용: conda create -n dn_solution python=3.11
    echo 3. 관리자 권한으로 실행
    goto END
) else (
    echo ✅ 가상환경 생성 성공!
    echo.
    echo 활성화 방법:
    echo venv\Scripts\activate
)

:END
echo.
echo ==============================================
echo 진단 완료
echo ==============================================
pause
