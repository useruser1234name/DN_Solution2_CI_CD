// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('업무 흐름 테스트', () => {
  test.beforeEach(async ({ page }) => {
    // 각 테스트 전에 로그인
    await page.goto('/login');
    await page.getByPlaceholder('아이디').fill('admin');
    await page.getByPlaceholder('비밀번호').fill('admin1234');
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 대시보드로 리디렉션 확인
    await expect(page).toHaveURL(/.*\/dashboard/);
  });

  test('정책 관리 페이지 접근 및 기능 확인', async ({ page }) => {
    // 정책 관리 페이지로 이동
    await page.locator('a:has-text("정책 관리")').click();
    await expect(page).toHaveURL(/.*\/policies/);
    
    // 페이지 제목 확인
    await expect(page.locator('h1:has-text("정책 관리")')).toBeVisible();
    
    // 정책 생성 버튼 확인
    await expect(page.getByRole('button', { name: '정책 생성' })).toBeVisible();
    
    // 정책 목록 테이블 확인
    await expect(page.locator('.ant-table-wrapper')).toBeVisible();
  });

  test('업체 관리 페이지 접근 및 기능 확인', async ({ page }) => {
    // 업체 관리 페이지로 이동
    await page.locator('a:has-text("업체 관리")').click();
    await expect(page).toHaveURL(/.*\/companies/);
    
    // 페이지 제목 확인
    await expect(page.locator('h1:has-text("업체 관리")')).toBeVisible();
    
    // 업체 생성 버튼 확인
    await expect(page.getByRole('button', { name: '업체 생성' })).toBeVisible();
    
    // 업체 목록 테이블 확인
    await expect(page.locator('.ant-table-wrapper')).toBeVisible();
  });

  test('주문 관리 페이지 접근 및 기능 확인', async ({ page }) => {
    // 주문 관리 페이지로 이동
    await page.locator('a:has-text("주문 관리")').click();
    await expect(page).toHaveURL(/.*\/orders/);
    
    // 페이지 제목 확인
    await expect(page.locator('h1:has-text("주문 관리")')).toBeVisible();
    
    // 주문 목록 테이블 확인
    await expect(page.locator('.ant-table-wrapper')).toBeVisible();
  });

  test('정산 관리 페이지 접근 및 기능 확인', async ({ page }) => {
    // 정산 관리 페이지로 이동
    await page.locator('a:has-text("정산 관리")').click();
    await expect(page).toHaveURL(/.*\/settlements/);
    
    // 페이지 제목 확인
    await expect(page.locator('h1:has-text("정산 관리")')).toBeVisible();
    
    // 정산 목록 테이블 확인
    await expect(page.locator('.ant-table-wrapper')).toBeVisible();
  });
});