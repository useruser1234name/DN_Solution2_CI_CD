// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('인증 테스트', () => {
  test.beforeEach(async ({ page }) => {
    // 각 테스트 전에 로그인 페이지로 이동
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
  });

  test('로그인 페이지가 올바르게 로드됨', async ({ page }) => {
    // 로그인 페이지 UI 요소 확인
    await expect(page.locator('h1:has-text("로그인")')).toBeVisible();
    await expect(page.getByPlaceholder('아이디')).toBeVisible();
    await expect(page.getByPlaceholder('비밀번호')).toBeVisible();
    await expect(page.getByRole('button', { name: '로그인' })).toBeVisible();
  });

  test('잘못된 자격 증명으로 로그인 실패', async ({ page }) => {
    // 잘못된 자격 증명 입력
    await page.getByPlaceholder('아이디').fill('wrong_user');
    await page.getByPlaceholder('비밀번호').fill('wrong_password');
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 에러 메시지 확인
    await expect(page.locator('.ant-message-error')).toBeVisible({ timeout: 5000 });
  });

  test('올바른 자격 증명으로 로그인 성공 (본사 관리자)', async ({ page }) => {
    // 본사 관리자 자격 증명 입력
    await page.getByPlaceholder('아이디').fill('admin');
    await page.getByPlaceholder('비밀번호').fill('admin1234');
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 대시보드로 리디렉션 확인
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // 사용자 정보 확인
    await expect(page.locator('text=안녕하세요, admin님!')).toBeVisible({ timeout: 5000 });
  });

  test('로그아웃 기능', async ({ page }) => {
    // 로그인
    await page.getByPlaceholder('아이디').fill('admin');
    await page.getByPlaceholder('비밀번호').fill('admin1234');
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 대시보드로 리디렉션 확인
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // 로그아웃 버튼 클릭
    await page.locator('.ant-layout-header button').click();
    await page.getByRole('menuitem', { name: '로그아웃' }).click();
    
    // 로그인 페이지로 리디렉션 확인
    await expect(page).toHaveURL(/.*\/login/);
  });
});