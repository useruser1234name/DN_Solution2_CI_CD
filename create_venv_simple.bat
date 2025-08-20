@echo off
echo ==============================================
echo 간단한 가상환경 생성 (대안 방법)
echo ==============================================
echo.

echo 가장 확실한 방법들을 순서대로 시도합니다...
echo.

REM 방법 1: 기본 venv
echo [방법 1] 기본 python -m venv 시도...
python -m venv myenv
if exist "myenv\Scripts\activate.bat" (
    echo ✅ 성공! myenv 폴더 생성됨
    echo 활성화: myenv\Scripts\activate
    goto SUCCESS
)

REM 방법 2: --clear 옵션
echo [방법 2] --clear 옵션으로 시도...
python -m venv myenv --clear
if exist "myenv\Scripts\activate.bat" (
    echo ✅ 성공! myenv 폴더 생성됨
    goto SUCCESS
)

REM 방법 3: virtualenv 설치 후 사용
echo [방법 3] virtualenv 설치 후 시도...
pip install virtualenv
virtualenv myenv
if exist "myenv\Scripts\activate.bat" (
    echo ✅ 성공! virtualenv로 myenv 생성됨
    goto SUCCESS
)

REM 방법 4: conda (있는 경우)
echo [방법 4] conda 확인...
conda --version >nul 2>&1
if not errorlevel 1 (
    echo conda 발견됨. conda로 환경 생성...
    conda create -n dn_solution python=3.11 -y
    echo ✅ conda 환경 생성됨
    echo 활성화: conda activate dn_solution
    goto SUCCESS
)

REM 방법 5: 다른 위치에서 시도
echo [방법 5] 다른 위치에서 시도...
cd %USERPROFILE%
python -m venv test_env
if exist "%USERPROFILE%\test_env\Scripts\activate.bat" (
    echo ✅ 다른 위치에서 성공!
    echo 환경 위치: %USERPROFILE%\test_env
    echo 활성화: %USERPROFILE%\test_env\Scripts\activate
    goto SUCCESS
)

echo ❌ 모든 방법 실패
echo.
echo 최종 해결책:
echo 1. Python 완전 재설치
echo 2. 시스템 재시작
echo 3. 바이러스 백신 확인 (가상환경 생성 차단 여부)
echo 4. 관리자 권한으로 실행
goto END

:SUCCESS
echo.
echo ==============================================
echo ✅ 가상환경 생성 성공!
echo ==============================================
echo.
echo 다음 단계:
echo 1. 가상환경 활성화
echo 2. pip install -r requirements.txt
echo 3. python manage.py migrate
echo 4. python manage.py runserver
echo.

:END
pause
