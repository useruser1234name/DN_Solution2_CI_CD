// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('보안 테스트', () => {
  test('인증되지 않은 사용자는 보호된 페이지에 접근할 수 없음', async ({ page }) => {
    // 대시보드 페이지로 직접 이동 시도
    await page.goto('/dashboard');
    
    // 로그인 페이지로 리디렉션 확인
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('인증되지 않은 사용자는 API에 접근할 수 없음', async ({ request }) => {
    // 인증 필요한 API 엔드포인트 접근 시도
    const response = await request.get('http://localhost:8001/api/companies/');
    
    // 401 Unauthorized 응답 예상
    expect(response.status()).toBe(401);
  });

  test('로그인 시 토큰이 로컬 스토리지에 저장됨', async ({ page }) => {
    // 로그인 페이지로 이동
    await page.goto('/login');
    
    // 로그인
    await page.getByPlaceholder('아이디').fill('admin');
    await page.getByPlaceholder('비밀번호').fill('admin1234');
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 로컬 스토리지에 토큰 저장 확인
    const accessToken = await page.evaluate(() => localStorage.getItem('access_token'));
    const refreshToken = await page.evaluate(() => localStorage.getItem('refresh_token'));
    
    expect(accessToken).not.toBeNull();
    expect(refreshToken).not.toBeNull();
  });

  test('로그아웃 시 토큰이 로컬 스토리지에서 제거됨', async ({ page }) => {
    // 로그인 페이지로 이동
    await page.goto('/login');
    
    // 로그인
    await page.getByPlaceholder('아이디').fill('admin');
    await page.getByPlaceholder('비밀번호').fill('admin1234');
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 대시보드로 리디렉션 확인
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // 로그아웃 버튼 클릭
    await page.locator('.ant-layout-header button').click();
    await page.getByRole('menuitem', { name: '로그아웃' }).click();
    
    // 로컬 스토리지에서 토큰 제거 확인
    const accessToken = await page.evaluate(() => localStorage.getItem('access_token'));
    const refreshToken = await page.evaluate(() => localStorage.getItem('refresh_token'));
    
    expect(accessToken).toBeNull();
    expect(refreshToken).toBeNull();
  });

  test('권한이 없는 사용자는 특정 기능에 접근할 수 없음', async ({ page }) => {
    // 판매점 사용자로 로그인 (권한이 제한된 사용자)
    await page.goto('/login');
    await page.getByPlaceholder('아이디').fill('retail_user');
    await page.getByPlaceholder('비밀번호').fill('retail1234');
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 대시보드로 리디렉션 확인
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // 정책 생성 기능 접근 시도 (권한 없음)
    await page.goto('/policies/create');
    
    // 권한 없음 메시지 또는 대시보드로 리디렉션 확인
    await expect(page.locator('text=권한이 없습니다')).toBeVisible({ timeout: 5000 });
  });
});